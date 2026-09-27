import { test } from 'node:test';
import assert from 'node:assert/strict';
import { decide } from './policy.mjs';

const repo = '/work/company';
const allow = (t, i) => assert.equal(decide(t, i, repo).behavior, 'allow', `${t} ${JSON.stringify(i)}`);
const deny = (t, i) => assert.equal(decide(t, i, repo).behavior, 'deny', `${t} ${JSON.stringify(i)}`);

test('ledger writes are allowed, absolute or relative', () => {
  allow('Write', { file_path: '/work/company/.agentic/ledger/handoffs/x-analyst.json' });
  allow('Edit', { file_path: '.agentic/ledger/decisions/x.draft.json' });
  allow('Write', { file_path: '/work/company/.agentic/ledger/runs/r1.summary.md' });
});

test('writes outside the ledger are denied, including traversal and look-alikes', () => {
  deny('Write', { file_path: '/work/company/.agentic/approvals/standing/mcp__x__y.json' });
  deny('Write', { file_path: '/work/company/.agentic/runs/current.json' });
  deny('Write', { file_path: '/work/company/.agentic/runs/r1.summary.md' });
  deny('Write', { file_path: '/work/company/.agentic/ledger/../approvals/a.json' });
  deny('Write', { file_path: '/work/company/.agentic/ledger-evil/a.json' });
  deny('Edit', { file_path: '/work/company/.claude/settings.json' });
  deny('Write', { file_path: '/etc/passwd' });
  deny('Write', {});
});

test('shell and unknown tools are denied; reads, web research, subagents and guard-cleared MCP calls are allowed', () => {
  for (const t of ['Bash', 'KillShell', 'SomeFutureTool']) deny(t, {});
  for (const t of ['Read', 'Glob', 'Grep', 'Task', 'Agent', 'WebSearch', 'WebFetch']) allow(t, {});
  allow('mcp__quickbooks__qbo_profit_and_loss', {});
});
