# Agentic Business Operations

A public-safe, reusable operating system for governed AI departments, specialist roles, and cross-functional business workflows.

The project models a company as an auditable set of operating functions rather than a collection of autonomous personas. Agents can take initiative, but policy, evidence, approvals, separation of duties, and deterministic controls limit what they may authorize or execute.

## Core operating loop

`observe → orient → propose → review → act within authority → verify → learn`

Work moves through durable work items, decisions, approvals, handoffs, evidence, outcomes, and learning artifacts rather than unbounded agent-to-agent chat.

## Company operating model

The reusable framework currently defines these top-level functions:

- Chief of Staff / Company Router
- Sales
- Marketing
- Customer / Guest Service
- Operations
- Legal
- Finance / Controller
- Product
- Independent adversarial review

Departments can contain multiple specialist roles. The preferred design is separation of duties rather than one all-powerful agent.

## Service and contact-center operating model

Service is decomposed into four governed specialist roles:

1. **Front-Line Service Worker** — handles customer interactions and executes only explicitly bounded actions.
2. **Service Supervisor** — monitors flagged interactions, manages queues and escalations, intervenes within bounded authority, and creates coaching actions.
3. **Script / Knowledge Author** — drafts scripts, decision trees, knowledge, and tool instructions but cannot self-publish controlled content.
4. **Service QA / Compliance Reviewer** — independently samples interactions and reviews controlled content against approved policy and QA criteria.

The reusable lifecycle is:

`design → govern → handle → escalate → verify → QA → coach → learn → change → re-release`

The framework defines vendor-neutral capabilities such as:

- `interaction.respond`
- `interaction.transfer`
- `interaction.escalate`
- `customer.read_scoped`
- `case.read`, `case.create`, `case.update_bounded`
- `knowledge.search_approved`
- `script.read_approved`
- `identity.verify`
- `consent.read`, `consent.record`
- `suppression.read`, `suppression.record`
- `business_action.execute_bounded`
- `business_action.request_approval`
- `payment.secure_handoff`
- `supervisor.monitor_flagged`
- `supervisor.intervene`
- `queue.reassign_bounded`
- `quality.sample`, `quality.score`
- `script.draft`, `knowledge.draft`
- `content.request_review`
- `analytics.read_aggregate`

Private adopters map these capabilities to their own connectors, systems, scripts, policies, channels, models, thresholds, and approval rules through a private contact-center profile. The public framework never needs to know whether an implementation uses Twilio, Genesys, NICE, Salesforce, ServiceNow, Hospitable, Stripe, or another system.

See:

- `docs/CONTACT_CENTER_OPERATING_MODEL.md`
- `policies/contact-center-guardrails.md`
- `schemas/contact-center-profile.schema.json`
- `docs/CONTACT_CENTER_REFERENCES.md`

## Model and provider control plane

Agent roles are independent from model vendors. Private company contracts can register providers such as OpenAI, Anthropic, xAI, OpenRouter, OpenAI-compatible endpoints, or custom adapters and assign provider-native model IDs by department, agent, or task.

Selection precedence is deterministic:

`task → agent → department → company default`

Assignments can specify:

- interactive or batch execution;
- required capabilities;
- primary and fallback models;
- cost, latency, and quality preferences;
- whether a user may override the selected model;
- independent-review requirements such as a different model or different provider.

Changing the model never changes the role's authority. Credentials are referenced by secret/environment name only and are never committed to this public repository.

See `docs/MODEL_SELECTION.md`.

## Public framework vs. private company implementation

The intended architecture is:

```text
agentic-business-operations             public / reusable
        ↓ immutable framework lock
private company contract                private
        ↓
company-specific policies + content     private
        ↓
connectors / systems / credentials      private
        ↓
bounded execution
```

### Safe to publish here

- generic role contracts;
- authority and approval patterns;
- capability catalogs;
- work-item, handoff, evidence, decision, approval, outcome, and review schemas;
- synthetic examples and scenario tests;
- generic SOP templates;
- reusable orchestration patterns;
- public design references and documentation.

### Never publish here

- company credentials or secrets;
- customer or employee data;
- private prompts or production evidence;
- proprietary pricing or internal KPIs;
- account, tax, banking, portfolio, or family-office information;
- private contracts, legal matters, or financial records;
- real property/account/customer identifiers;
- Mesa Global, YALLOHA, Tyndall Personal Finance, or other private-company configuration.

## Private adoption contract

A private company pins this repository to an immutable commit and supplies its own `.agentic/business-ops.json` contract. The framework lock binds the consumer to the exact repository commit and contract schema used for validation.

A private implementation defines:

- company mission and enabled departments;
- systems of record;
- allowed context references;
- authority defaults and bounded actions;
- provider/model policy;
- private policy/content references;
- connector mappings;
- execution constraints;
- approval and verification requirements.

The framework validates structure and generic safety invariants; the private company owns actual operating content and execution adapters.

## Relationship to Platform OS

- **`agentic-business-operations`** governs business roles, work, authority, approvals, handoffs, evidence, and outcomes.
- **`agentic-platform-operations`** governs software engineering, testing, security, release, bounded repair, and independent engineering review.
- **Private company repositories** provide domain context, connectors, systems of record, credentials, policies, content, KPIs, and execution adapters.

Business approval never bypasses engineering/release controls. A Product or Operations agent may authorize work to proceed, but software changes still pass through Platform OS.

## Reference architecture

```text
Request / event / observation
        ↓
Chief of Staff / Company Router
        ↓
Structured work item
        ↓
Owning department
        ↓
Specialist role
        ↓
Evidence + proposed action
        ↓
Independent review / approval when required
        ↓
Private bounded execution adapter
        ↓
Verification
        ↓
Outcome record
        ↓
QA / learning / policy improvement
```

For service operations, the specialist layer expands into:

```text
Customer interaction
        ↓
Front-Line Worker
        ├── approved knowledge + script
        ├── scoped customer/case context
        └── bounded tools
        ↓
resolve or escalate
        ↓
Supervisor when triggered
        ↓
verified outcome
        ↓
QA / Compliance sample
        ↓
coaching or Script/Knowledge change request
        ↓
independent review
        ↓
controlled re-release
```

## Design principles

1. **High autonomy does not imply high authority.**
2. Agents may investigate more broadly than they may execute.
3. External, financial, legal, customer-impacting, or irreversible actions require explicit authority.
4. Ambiguity fails closed into escalation rather than invented authority.
5. The author of a material recommendation or controlled artifact should not be its sole approver.
6. Evidence, assumptions, recommendations, approvals, actions, and outcomes remain distinguishable.
7. Tools are exposed as least-privilege capabilities, not unrestricted backend access.
8. Material actions require independent verification.
9. Production learning is governed: an interaction may create a finding, but it does not directly rewrite policy or scripts.
10. Model/provider choice is configurable and cannot weaken safety, authority, or validation rules.
11. Company-specific data, policy, content, and connectors stay in private repositories.
12. Reusable frameworks are pinned to immutable commits and validated before use.

## Current status

The repository now contains the Company OS foundation, department role contracts, durable business-work schemas, authority/separation-of-duties policies, provider/model routing, private-adoption validation, synthetic scenario tests, and the reusable Service / Contact Center operating module.

The next major layer is controlled execution: reusable patterns for private adapters, richer cross-functional workflows, KPI/outcome measurement, and additional department-specific operating modules while preserving the same authority and public/private boundaries.
