# Running Company OS in Claude Code

Claude Code is the reference runtime for ad hoc work: the human sits in a terminal in their private company repo, the framework's role contracts run as subagents, and a hook enforces authority before any tool call executes.

## What maps to what

| Company OS | Claude Code |
| --- | --- |
| Chief of Staff / router | The main session, instructed by `CLAUDE.md` |
| Role contract (`roles/*.md`) | Subagent system prompt, verbatim, in `.claude/agents/<name>.md` |
| Allowed capabilities (built-in tools) | Subagent `tools:` frontmatter |
| Allowed systems | Subagent `mcpServers:` frontmatter |
| Prohibited / approval-required capabilities | `PreToolUse` hook (`company_os_guard.py`) — denies before execution |
| Work ledger | `.agentic/ledger/` files, committed to git; `PostToolUse` hook appends events |
| Human decision | The human edits `*.draft.json` → `*.json` and fills `decided_by` |
| Human approval for an external action | A token file in `.agentic/approvals/<hash>.json` with `status: approved` |

## What the guard enforces
1. Any tool matching an external-action pattern is denied company-wide unless an approval token exists for that exact call (tool + input hash).
2. Per-role deny patterns from `claude/agent-manifest.json` (e.g. corp-dev can't touch MCP, web, or shell; analysts can't call write-shaped MCP tools).
3. Confidential scopes: only the owning role reads or writes inside them.
4. Decision records: agents write drafts only; a draft needs ≥2 options, a review reference, and fully-owned assumptions; agents never populate the decision.
5. Missing manifest → fail closed for everything except plain reads.

## Setting up a private repo
```
mkdir my-company-ops && cd my-company-ops && git init
cp <framework>/templates/private-company/business-ops.example.json .agentic/business-ops.json   # edit
cp <framework>/templates/private-company/business-ops.lock.example.json .agentic/business-ops.lock.json  # set commit
cp <framework>/claude/CLAUDE.md.template CLAUDE.md   # fill company name
cp <framework>/claude/bootstrap.sh scripts/bootstrap.sh
bash scripts/bootstrap.sh
claude
```
Then: *"Should we exit market X or hold two years?"* — the main session routes it, fans out to analysts, synthesizes, reviews, and hands you a decision draft.

## What this does not cover
Cadence and event triggers need something outside the laptop (a scheduler that opens a session, or a mailbox watcher that writes an intake file). Commission-only is a complete, useful first deployment.
