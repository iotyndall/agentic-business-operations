#!/usr/bin/env node
// Headless charter session on the Claude Agent SDK. Invoked by scripts/run_charter.py --runtime sdk.
//
// stdin : {"repo": "<private repo>", "prompt": "...", "timeout_minutes": 20, "max_budget_usd": 5, "read_tools": []}
// stdout: one JSON object — the session outcome for the run record.
//
// Loads project settings only (the exported .claude/ agents, the guard hook, CLAUDE.md) and only those .mcp.json
// servers the company contract declares as systems: no user settings, no account-level connectors, no stray servers.
// policy.mjs runs as a PreToolUse hook on every call (settings grants cannot bypass it) and answers permission prompts.
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { query } from '@anthropic-ai/claude-agent-sdk';
import { decide } from './policy.mjs';

const input = JSON.parse(readFileSync(0, 'utf8'));
const repo = path.resolve(input.repo);
const mcpFile = path.join(repo, '.mcp.json');
const readJson = (f, fallback) => (existsSync(f) ? JSON.parse(readFileSync(f, 'utf8')) : fallback);
const declared = new Set((readJson(path.join(repo, '.agentic', 'business-ops.json'), {}).systems ?? []).map((s) => s.id));
const configured = readJson(mcpFile, {}).mcpServers ?? {};
const mcpServers = Object.fromEntries(Object.entries(configured).filter(([name]) => declared.has(name)));
const droppedServers = Object.keys(configured).filter((name) => !declared.has(name));
const ctx = {
  repo,
  connectorTools: Object.keys(readJson(path.join(repo, '.agentic', 'runtime-manifest.json'), {}).connector_tools ?? {}),
  readTools: input.read_tools ?? [],
};

const abort = new AbortController();
const timer = setTimeout(() => abort.abort(), 60_000 * (input.timeout_minutes ?? 30));
const runnerDenials = [];
const toolCalls = {};
let result;
let error;

try {
  for await (const msg of query({
    prompt: input.prompt,
    options: {
      cwd: repo,
      settingSources: ['project'],
      mcpServers,
      strictMcpConfig: true,
      hooks: {
        PreToolUse: [{
          hooks: [async (evt) => {
            // agent_id is present only for calls made inside a subagent; the main session has no role.
            const d = decide(evt.tool_name, evt.tool_input, { ...ctx, isSubagent: Boolean(evt.agent_id) });
            if (d.behavior === 'allow') return {};
            runnerDenials.push({ tool: evt.tool_name, agent: evt.agent_type ?? 'main', reason: d.message });
            return { hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: d.message } };
          }],
        }],
      },
      // Prompts only arrive for calls the hook above already allowed (PreToolUse runs first), and this callback is
      // not told which agent is calling, so the actor check lives in the hook; here the path/tool rules re-apply.
      canUseTool: async (tool, toolInput) => decide(tool, toolInput, { ...ctx, isSubagent: true }),
      maxBudgetUsd: input.max_budget_usd ?? 5,
      abortController: abort,
    },
  })) {
    if (msg.type === 'assistant') {
      for (const b of msg.message.content) if (b.type === 'tool_use') toolCalls[b.name] = (toolCalls[b.name] ?? 0) + 1;
    } else if (msg.type === 'result') {
      result = msg;
    }
  }
} catch (e) {
  error = abort.signal.aborted ? `timed out after ${input.timeout_minutes} minute(s)` : String(e?.message ?? e);
} finally {
  clearTimeout(timer);
}

const outcome = {
  runtime: 'agent-sdk',
  subtype: result?.subtype ?? 'no_result',
  is_error: Boolean(error || result?.is_error || result?.subtype !== 'success'),
  error: error ?? null,
  num_turns: result?.num_turns ?? null,
  total_cost_usd: result?.total_cost_usd ?? null,
  session_id: result?.session_id ?? null,
  tool_calls: toolCalls,
  permission_denials: result?.permission_denials ?? [],
  runner_denials: runnerDenials,
  dropped_mcp_servers: droppedServers,
  result_tail: typeof result?.result === 'string' ? result.result.slice(-4000) : null,
};
process.stdout.write(JSON.stringify(outcome) + '\n');
process.exit(outcome.is_error ? 1 : 0);
