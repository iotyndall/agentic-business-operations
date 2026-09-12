# Yalloha connector — governed social marketing for short-term rental hosts

[Yalloha](https://www.yalloha.com) turns Airbnb guest reviews into Facebook and Instagram posts. This connector lets a Company OS marketing department run that loop with separated duties and a hard authority boundary: the Social Media Specialist drafts, the Content Reviewer clears, the human sets a standing approval per content class, and the guard blocks any publish that lacks all three.

## The flow

```
new 5-star review (Yalloha)
      ↓ social-media-specialist: generate_post → draft (nothing published)
      ↓ marketing-content-reviewer: reads the draft, writes
        .agentic/ledger/reviews/clearances/<postId>.json {cleared, content_class, reviewer, review_id}
      ↓ guard checks .agentic/approvals/standing/mcp__yalloha__publish_post.json
        (human-written: status, approved_by, expires, content_classes)
      ↓ social-media-specialist: publish_post → Facebook / Instagram
      ↓ PostToolUse: ledger event
```

What the guard denies, proven in `scripts/claude_export_selftest.py`:

- publish with no approval, no clearance, a clearance for a different class, or an expired standing approval;
- the reviewer drafting or publishing; the specialist writing its own clearance;
- the specialist changing brand settings; anyone in marketing touching affiliate commissions;
- any non-marketing role calling Yalloha at all;
- editing a post after the reviewer cleared it; any Yalloha tool not in the published map; publishing past `max_per_day`.

## Setup (about ten minutes)

1. **Yalloha account** — sign up at [yalloha.com](https://www.yalloha.com), connect Airbnb (via Hospitable) and your Facebook Page / Instagram professional account. `get_setup_status` tells you what is left.
2. **Private company repo** — follow `docs/CLAUDE_CODE.md`. Enable `marketing` in `.agentic/business-ops.json` and declare `{"id": "yalloha", "kind": "social", "write_authority": "bounded"}` under `systems`. (`none` exposes only read tools; `approval-required` disables standing approvals so every publish needs a per-call token.)
3. **Marketing profile** — start from `examples/yalloha-host/marketing-profile.json`. It enables `social_media`, `brand_manager`, and `content_reviewer` only, binds both channels to `system://yalloha`, and pre-approves one content class: `consented-review-repost`.
4. **MCP server** — register `https://www.yalloha.com/api/mcp` in Claude Code under the name **`yalloha`** exactly; the subagents reference it by that name.
5. **Standing approval** — write `.agentic/approvals/standing/mcp__yalloha__publish_post.json`:
   ```json
   {"status": "approved", "approved_by": "you@example.com", "expires": "2026-12-31",
    "content_classes": ["consented-review-repost"], "clearance_key": "postId"}
   ```
   Omit this file and every publish needs a per-call token instead.
6. `bash scripts/bootstrap.sh` then `claude`. Bootstrap passes `.agentic/marketing-profile.json` to the exporter, so roles marked `enabled: false` are not installed. Ask: *"Turn this week's five-star reviews into posts and get them cleared."*

## What the roles hold on Yalloha

| tool | specialist | reviewer | brand manager |
| --- | --- | --- | --- |
| reviews, properties, posts, analytics (read) | ✓ | ✓ | ✓ |
| `generate_post`, `update_caption`, `update_review_status` | ✓ | — | — |
| `publish_post` | guarded | — | — |
| `update_preferences`, `update_property` | — | — | per-call token |
| affiliate program / commissions (write) | — | — | — (Sales/Finance) |
| connect URLs | human only | | |

Full map: `connectors/yalloha/connector.json`.
