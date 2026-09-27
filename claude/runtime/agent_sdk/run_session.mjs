#!/usr/bin/env node
// Headless charter session on the Claude Agent SDK. Invoked by scripts/run_charter.py --runtime sdk.
//
// stdin : {"repo": "<private repo>", "prompt": "...", "timeout_minutes": 20, "max_budget_usd": 5, "model": null}
// stdout: one JSON object — the session outcome for the run record.
//
// Loads project settings only (the exported .claude/ agents, the guard hook, CLAUDE.md), the repo's .mcp.json
// and nothing else: no user settings, no account-level connectors. Permission prompts are answered by policy.mjs.
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { query } from '@anthropic-ai/claude-agent-sdk';
import { decide } from './policy.mjs';

const input = JSON.parse(readFileSync(0, 'utf8'));
const repo = path.resolve(input.repo);
const mcpFile = path.join(repo, '.mcp.json');
const mcpServers = existsSync(mcpFile) ? JSON.parse(readFileSync(mcpFile, 'utf8')).mcpServers ?? {} : {};

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
      canUseTool: async (tool, toolInput) => {
        const d = decide(tool, toolInput, repo);
        if (d.behavior === 'deny') runnerDenials.push({ tool, reason: d.message });
        return d;
      },
      maxBudgetUsd: input.max_budget_usd ?? 5,
      ...(input.model ? { model: input.model } : {}),
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
  result_tail: typeof result?.result === 'string' ? result.result.slice(-4000) : null,
};
process.stdout.write(JSON.stringify(outcome) + '\n');
process.exit(outcome.is_error ? 1 : 0);
