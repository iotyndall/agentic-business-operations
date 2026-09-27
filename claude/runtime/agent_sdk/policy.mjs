// Permission policy for headless charter sessions. Pure, so it is unit-tested without a model.
//
// Order of enforcement in a session:
//   1. PreToolUse guard hook (.claude/hooks/company_os_guard.py, loaded from project settings) — role
//      authority, approvals, clearances, the per-run external-action budget. A guard deny is final.
//   2. This policy — answers the permission prompts the guard leaves open. Under bare `claude -p` those
//      prompts have no one to answer them and are denied, so a headless run could never write its ledger.
// The policy never widens the guard: it only answers "may this tool run at all, headless?".

import path from 'node:path';

// Built-ins that write files: only inside the ledger (the run summary included, at .agentic/ledger/runs/).
const FILE_WRITERS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
// Built-ins that change nothing. Web research is here because roles opt into it through their subagent `tools:`
// allowlist (only market intelligence does); the shell and anything unlisted are denied.
const READ_ONLY = new Set(['Read', 'Glob', 'Grep', 'TodoWrite', 'Task', 'Agent', 'Skill', 'WebSearch', 'WebFetch']);

function within(repo, target, ...segments) {
  const base = path.resolve(repo, ...segments) + path.sep;
  return path.resolve(repo, target).startsWith(base);
}

/** @returns {{behavior:'allow'} | {behavior:'deny', message:string}} */
export function decide(tool, input, repo) {
  if (READ_ONLY.has(tool)) return { behavior: 'allow' };
  if (FILE_WRITERS.has(tool)) {
    const target = input?.file_path ?? input?.notebook_path;
    if (typeof target !== 'string' || !target) return deny(`${tool} without a file path`);
    if (within(repo, target, '.agentic', 'ledger')) return { behavior: 'allow' };
    return deny(`${tool} outside .agentic/ledger/ (${target})`);
  }
  // MCP tools reach here only after the guard let them through; the guard is the authority for them.
  if (tool.startsWith('mcp__')) return { behavior: 'allow' };
  return deny(`${tool} is not available to headless charter sessions`);
}

function deny(message) {
  return { behavior: 'deny', message: `Company OS runner: ${message}` };
}
