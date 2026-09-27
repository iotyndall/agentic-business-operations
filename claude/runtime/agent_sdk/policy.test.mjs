import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { decide } from './policy.mjs';

const repo = mkdtempSync(path.join(tmpdir(), 'cos-policy-'));
mkdirSync(path.join(repo, '.agentic', 'ledger', 'handoffs'), { recursive: true });
const outside = mkdtempSync(path.join(tmpdir(), 'cos-outside-'));
symlinkSync(outside, path.join(repo, '.agentic', 'ledger', 'escape'));
symlinkSync(path.join(outside, 'not-yet'), path.join(repo, '.agentic', 'ledger', 'dangling'));

const base = { repo, isSubagent: false, connectorTools: ['mcp__yalloha__publish_post'], readTools: ['mcp__quickbooks__*', 'mcp__pricelabs__get_listings'] };
const run = (t, i, ctx = {}) => decide(t, i, { ...base, ...ctx }).behavior;
const allow = (t, i, ctx) => assert.equal(run(t, i, ctx), 'allow', `${t} ${JSON.stringify(i)}`);
const deny = (t, i, ctx) => assert.equal(run(t, i, ctx), 'deny', `${t} ${JSON.stringify(i)}`);

test('ledger writes are allowed, absolute or relative, including new directories', () => {
  allow('Write', { file_path: path.join(repo, '.agentic/ledger/handoffs/x-analyst.json') });
  allow('Edit', { file_path: '.agentic/ledger/decisions/x.draft.json' });
  allow('Write', { file_path: '.agentic/ledger/runs/r1.summary.md' });
});

test('writes outside the ledger are denied: runner state, traversal, look-alikes, symlink escapes', () => {
  deny('Write', { file_path: '.agentic/approvals/standing/mcp__x__y.json' });
  deny('Write', { file_path: '.agentic/runs/current.json' });
  deny('Write', { file_path: '.agentic/ledger/../approvals/a.json' });
  deny('Write', { file_path: '.agentic/ledger-evil/a.json' });
  deny('Write', { file_path: '.agentic/ledger' });
  deny('Write', { file_path: '.agentic/ledger/escape/owned.txt' });
  deny('Write', { file_path: '.agentic/ledger/escape/new/dir/owned.txt' });
  deny('Write', { file_path: '.agentic/ledger/dangling/owned.txt' });
  deny('Write', { file_path: '.agentic/ledger/dangling' });
  deny('Edit', { file_path: '.claude/settings.json' });
  deny('Write', { file_path: '/etc/passwd' });
  deny('Write', {});
});

test('reads stay inside the repository', () => {
  allow('Read', { file_path: '.agentic/ledger/intake/x.json' });
  allow('Grep', { pattern: 'x' });
  allow('Glob', { pattern: '**/*.json', path: '.agentic' });
  deny('Read', { file_path: '/root/.ssh/id_ed25519' });
  deny('Read', { file_path: '../neighbour/.env' });
  deny('Read', { file_path: '.agentic/ledger/escape/secret' });
  deny('Grep', { pattern: 'KEY', path: '/etc' });
  deny('Glob', { pattern: '/etc/*' });
  deny('Glob', { pattern: '../../**/.env' });
});

test('web research only inside a subagent', () => {
  deny('WebSearch', { query: 'x' });
  deny('WebFetch', { url: 'https://example.com' });
  allow('WebSearch', { query: 'x' }, { isSubagent: true });
});

test('MCP: described connector tools and charter-declared read tools only', () => {
  allow('mcp__yalloha__publish_post', {});
  allow('mcp__quickbooks__qbo_profit_and_loss', {});
  allow('mcp__pricelabs__get_listings', {});
  deny('mcp__pricelabs__update_listing_data', {});
  deny('mcp__custom__execute_sql', {});
  deny('mcp__quickbooksx__anything', {});
});

test('shell and unknown tools are denied; orchestration is allowed', () => {
  for (const t of ['Bash', 'KillShell', 'SomeFutureTool']) deny(t, {});
  for (const t of ['Task', 'Agent', 'TodoWrite']) allow(t, {});
});
