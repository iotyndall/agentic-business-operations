// Tool policy for headless charter sessions. Pure apart from path canonicalisation, so it is unit-tested without a model.
//
// run_session.mjs enforces it twice:
//   - as an SDK PreToolUse hook, which sees EVERY call, including tools the private repo's .claude/settings.json
//     pre-allows (a permission grant would otherwise skip canUseTool entirely); and
//   - as canUseTool, which answers the permission prompts `claude -p` would auto-deny (e.g. ledger writes).
// The exported company guard hook runs as well; any deny from either is final. This policy never widens the guard.

import { existsSync, realpathSync } from 'node:fs';
import path from 'node:path';

const FILE_WRITERS = new Set(['Write', 'Edit', 'MultiEdit', 'NotebookEdit']);
const FILE_READERS = new Set(['Read', 'Glob', 'Grep']);
const ORCHESTRATION = new Set(['TodoWrite', 'Task', 'Agent', 'Skill']);
// Web research is allowed only inside a subagent: its `tools:` allowlist is how a role opts in.
// The main session has no role, so it gets none.
const WEB = new Set(['WebSearch', 'WebFetch']);

/** Real path of `p` (relative to `repo`), resolving symlinks through the deepest existing ancestor, so a symlinked
 *  directory under the ledger cannot redirect a write that has not been created yet. */
export function canonical(repo, p) {
  let cur = path.resolve(repo, p);
  const rest = [];
  while (!existsSync(cur)) {
    const parent = path.dirname(cur);
    if (parent === cur) break;
    rest.unshift(path.basename(cur)); cur = parent;
  }
  const real = existsSync(cur) ? realpathSync(cur) : cur;
  return path.join(real, ...rest);
}

function inside(base, target) {
  const rel = path.relative(base, target);
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
}

/** MCP tool names allowed by `patterns` (exact names, or `mcp__<server>__*`). */
export function matchesAny(tool, patterns) {
  return patterns.some((p) => (p.endsWith('__*') ? tool.startsWith(p.slice(0, -1)) : tool === p));
}

/**
 * @param {string} tool
 * @param {object} input tool input
 * @param {{repo: string, isSubagent: boolean, connectorTools: string[], readTools: string[]}} ctx
 *   connectorTools: tools of connectors the framework describes (the guard validates each call against them);
 *   readTools: patterns the human-written charter declares as read-only (bounds.read_tools).
 */
export function decide(tool, input, ctx) {
  const repoReal = canonical(ctx.repo, '.');
  const inRepo = (p) => inside(repoReal, canonical(ctx.repo, p));

  if (ORCHESTRATION.has(tool)) return allow();
  if (FILE_READERS.has(tool)) {
    const target = tool === 'Read' ? input?.file_path : (input?.path ?? '.');
    if (typeof target !== 'string' || !target) return deny(`${tool} without a path`);
    if (!inRepo(target)) return deny(`${tool} outside the company repository (${target})`);
    if (tool === 'Glob' && typeof input?.pattern === 'string' && (path.isAbsolute(input.pattern) || input.pattern.split(/[\\/]/).includes('..'))) {
      return deny(`Glob pattern escapes the search path (${input.pattern})`);
    }
    return allow();
  }
  if (FILE_WRITERS.has(tool)) {
    const target = input?.file_path ?? input?.notebook_path;
    if (typeof target !== 'string' || !target) return deny(`${tool} without a file path`);
    const ledger = canonical(ctx.repo, path.join('.agentic', 'ledger'));
    const t = canonical(ctx.repo, target);
    if (t !== ledger && inside(ledger, t) && inside(repoReal, ledger)) return allow();
    return deny(`${tool} outside .agentic/ledger/ (${target})`);
  }
  if (WEB.has(tool)) return ctx.isSubagent ? allow() : deny(`${tool} is only available to roles granted web research`);
  if (tool.startsWith('mcp__')) {
    if (ctx.connectorTools.includes(tool) || matchesAny(tool, ctx.readTools)) return allow();
    return deny(`${tool} is neither a described connector tool nor declared read-only by the charter (bounds.read_tools)`);
  }
  return deny(`${tool} is not available to headless charter sessions`);
}

const allow = () => ({ behavior: 'allow' });
const deny = (message) => ({ behavior: 'deny', message: `Company OS runner: ${message}` });
