# Model and Provider Selection

Model choice is configuration, not role logic. A department or agent should describe **what capability it needs**; a private company contract decides **which provider/model supplies it**.

## Provider table

`model_policy.providers` defines the available execution backends. Supported provider kinds are `openai`, `anthropic`, `xai`, `openrouter`, `openai-compatible`, and `custom`.

| Field | Meaning |
|---|---|
| `id` | Stable local provider reference used by model rows. |
| `kind` | Adapter family. |
| `credential_ref` | Reference such as `secret://OPENAI_API_KEY`; never the credential value. |
| `endpoint_ref` | Optional configuration reference for custom/OpenAI-compatible endpoints. |
| `enabled` | Whether this provider may be selected. |

## Model table

`model_policy.models` is intentionally company-local because vendor model catalogs change faster than this framework.

| Field | Meaning |
|---|---|
| `id` | Stable local model alias such as `openai-primary` or `anthropic-review`. |
| `provider` | Provider table row. |
| `model` | Provider-native model identifier. Treated as an opaque string. |
| `execution_modes` | `interactive`, `batch`, or both. Batch is declared only when that model/provider path is actually usable that way. |
| `capabilities` | Required traits such as `reasoning`, `tools`, `structured-output`, `vision`, etc. |
| `cost_tier` | Relative planning tier, not a hard-coded price. |
| `latency_tier` | Relative planning tier. |
| `quality_tier` | Relative planning tier. |
| `enabled` | Whether assignments and user overrides may select it. |

The framework deliberately does **not** hard-code current OpenAI, Anthropic, xAI, or OpenRouter model names or prices. Private company configuration can change them without a framework release.

## Assignment table

`model_policy.assignments` binds a model to a scope. Resolution is deterministic:

`task override → agent default → department default → company default`

Each row specifies a primary model, optional fallbacks, interactive/batch execution mode, required capabilities, and whether a user may override the selected model for that scope.

Example scopes:

- department: `marketing`
- agent: `adversarial-reviewer`
- task: `chief-of-staff.route`

## User choice

A user-selected model is allowed only when both are true:

1. `selection.allow_user_override` is true; and
2. the winning assignment row has `user_selectable: true` (company-default selection is user-selectable when global override is enabled).

The requested model still must be declared, enabled, support the assignment's execution mode, and satisfy the required capabilities. User choice changes the model, not the agent's authority.

## Fallbacks

Fallbacks are explicit and ordered. They may be used only for the configured failure classes such as rate limit, timeout, provider error, or capacity. A fallback must satisfy the same execution-mode and capability requirements as the primary model.

Do not silently fall back after a semantic failure, policy refusal, failed deterministic check, or adversarial-review rejection.

## Independent review

`selection.review_independence` can require the reviewer to differ from the authoring agent by model and optionally by provider. This is useful for adversarial review: for example, a builder on one provider and an independent reviewer on another.

The runtime must compare the **actual model/provider used for the authoring step** with the review selection. A static assignment alone cannot prove independence.

## Secrets

Contracts contain references such as `secret://OPENAI_API_KEY`; they never contain API keys. Credential resolution belongs to the private execution adapter or deployment environment.

## CLI resolver

The reference resolver is executable:

```bash
python scripts/resolve_model.py .agentic/business-ops.json \
  --department marketing \
  --agent marketing.content-writer \
  --task marketing.monthly-content
```

A UI can render the same provider/model/assignment arrays as editable tables without changing the underlying policy model.
