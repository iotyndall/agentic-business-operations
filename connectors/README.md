# Published connectors

A **connector** is a vendor-published map from an MCP server's tools to Company OS capabilities. It tells the framework what each tool *would do* — observe, propose, execute within bounds, require approval, or is prohibited for agent roles — so that a private company can bind its marketing, service, or finance roles to a real product without hand-writing tool allowlists or guessing where the authority boundary sits.

A connector grants nothing. Authority still comes from the role contract and the private profile; the connector only makes the vendor's tool surface legible to the guard.

## What a connector declares

```
tool → capability → authority → owner roles → external? financial? → clearance rule
```

`schemas/connector.schema.json` is the contract. `scripts/validate_connector.py` proves the invariants:

- an external action is never `observe`/`propose`, and is `execute-bounded` only for named pre-approved content classes with a reviewer clearance key;
- a financial commitment is held by no marketing role;
- the content reviewer only observes — it can never author, execute, or publish;
- every tool a role is granted is either safe or guarded; every tool a role is *not* granted is denied in the Claude Code manifest.

## How the runtime uses it

`claude/agent-manifest.json` lists connectors. The exporter folds each connector's external/approval-required tools into `.agentic/runtime-manifest.json`, and the `PreToolUse` guard enforces three paths for an external tool:

1. **Per-call human token** — `.agentic/approvals/<hash>.json` for that exact tool+input.
2. **Standing approval + clearance** — `.agentic/approvals/standing/<tool>.json` written by the human for a content class, valid only when the reviewer role has written `.agentic/ledger/reviews/clearances/<artifact>.json` with a matching `content_class`. The author role cannot write clearances.
3. **Otherwise: deny.**

## Available connectors

| id | vendor | department | fulfils |
| --- | --- | --- | --- |
| [`yalloha`](yalloha/connector.json) | [Yalloha](https://www.yalloha.com) | marketing | `facebook-pages`, `instagram` — turns short-term-rental guest reviews into governed social posts. See `docs/connectors/YALLOHA.md`. |

## Publishing your own

Copy `yalloha/connector.json`, map your tools, run `python3 scripts/validate_connector.py connectors/<id>/connector.json claude/agent-manifest.json`, and open a PR. A connector that cannot pass the validator does not get listed.
