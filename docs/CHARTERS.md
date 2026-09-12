# Standing charters — cadence and event triggers

A charter turns the Chief of Staff into a chief operating officer, or a department index into a "marketing director": a human-written standing authorization to **initiate** a commission on a schedule or event. The roles, the guard, and the ledger are unchanged. A charter answers only *when*; it can never widen *what*.

## Shape

```json
{
  "id": "marketing-weekly-reviews",
  "owner_role": "marketing",
  "trigger": {"cron": "0 14 * * 1", "timezone": "America/New_York"},
  "commission": "Turn last week's five-star guest reviews into posts, get them cleared, publish the cleared ones.",
  "departments": ["marketing"], "dominant_outcome": "demand-generation",
  "bounds": {"max_external_actions": 5, "max_runtime_minutes": 20, "standing_approvals": ["mcp__yalloha__publish_post"]},
  "approved_by": "you@example.com", "expires": "2026-12-31"
}
```

`schemas/charter.schema.json` · `scripts/validate_charter.py` · `scripts/run_charter.py` · `scripts/charter_selftest.py`

## What keeps it safe

| control | where |
| --- | --- |
| A department charter can only commission its own department; the outcome must route there | validator |
| Standing approvals it relies on must be real external tools of a published connector that an agent in that department can actually call | validator |
| `max_external_actions > 0` requires a standing approval; otherwise the charter is draft-only | validator |
| Missing or expired standing approval at run time → the run is downgraded to draft-only | runner |
| Every allowed external call spends one unit of the run's budget; the guard denies past the cap and fails closed on a malformed run file | guard |
| Two runs can't overlap | runner |
| Expiry and approver required | validator + runner |
| The charter cannot create a standing approval, a clearance, or an approval token | by construction — those live in files only the human (or the reviewer role) writes |

## Running one

Interactive: `python3 .company-os/scripts/run_charter.py cadence/<id>.charter.json` prints the prompt; paste it into `claude`.

Headless: add `--headless`; the runner opens `claude -p` with the commission, times it out at `max_runtime_minutes`, and writes `.agentic/runs/<run_id>.json` with the routing, budget spent, and session output tail.

Scheduled: copy `claude/workflows/charter-cron.yml.template` into the private repo's `.github/workflows/`, fill the cron (converted to UTC), and add `ANTHROPIC_API_KEY`. Each run commits its ledger on a branch and opens a PR, so a human sees every run.

Event-triggered: anything that can write an intake file and invoke the runner — an n8n workflow on a vendor webhook, a mailbox watcher — works the same way. The framework does not ship a webhook receiver.

## Known limits
- Headless runs need MCP credentials the runner can use. OAuth-only servers need a pre-issued token in `.mcp.json`; that is a private-repo concern.
- The budget counts *allowed* calls, not confirmed successes; a call the guard allows but the vendor rejects still spends a unit. That is the conservative direction.
