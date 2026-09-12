# Contact Center Operating Model

This module defines reusable operating roles, lifecycle steps, capability classes, approval boundaries, and safety defaults for human or AI-assisted contact centers. It intentionally does **not** define company scripts, legal disclosures, customer policies, system credentials, vendor connectors, refund thresholds, or channel-specific compliance rules. Those belong in the private company implementation.

## Design principles

1. **Roles are operating contracts, not personas.** Each role has a mission, allowed capability classes, authority limits, evidence requirements, escalation conditions, and measurable outcomes.
2. **Capabilities are vendor-neutral.** The framework names what a role may do; the private project maps that capability to Genesys, NICE, Twilio, Salesforce, ServiceNow, a PMS, CRM, payment system, or another connector.
3. **Approved content is versioned.** Front-line workers consume approved scripts, policies, and knowledge. They do not silently rewrite them during a live interaction.
4. **High autonomy does not imply high authority.** A worker may autonomously classify, search, summarize, draft, or route while remaining unable to make material commitments.
5. **Supervisor authority is bounded.** Supervisors may monitor, coach, route, intervene, and exercise only explicitly delegated overrides.
6. **Authors do not approve their own content.** Script and knowledge changes require independent QA/compliance review before publication.
7. **Every material external action is verifiable.** The system records what was attempted, under what authority, through which capability, and whether the result was confirmed.
8. **Failure is fail-closed.** Missing identity, missing policy, unresolved tool state, uncertain consent, or an unavailable escalation path cannot be reasoned around.

## Reusable roles

- **Service Supervisor** — owns live queue health, escalations, intervention, coaching, workload balancing, exception management, and service performance.
- **Script / Knowledge Author** — converts approved policy, product, legal, and operational source material into versioned scripts, playbooks, knowledge articles, and decision trees.
- **Front-Line Service Worker** — handles live conversations using approved knowledge and bounded capabilities; may be human, AI-assisted human, or an autonomous virtual worker when the private contract explicitly permits it.
- **Service QA / Compliance Reviewer** — independently evaluates scripts and interactions against policy, required disclosures, quality rubrics, safety rules, and evidence standards.

The department-level `roles/service.md` role remains accountable for the service function as a whole and may delegate work to these specialized roles.

## Operating lifecycle

### A. Design and govern

1. **Define service journeys and intents.** Private project specifies supported reasons for contact, channels, customer groups, risk tiers, and target outcomes.
2. **Define sources of truth.** Register the authoritative policy, product, account, order/reservation, case, consent, identity, and knowledge systems.
3. **Map capability classes to connectors.** The private project maps vendor-neutral capabilities to concrete systems and scopes.
4. **Define authority and escalation.** Set bounded actions, monetary/value thresholds, identity requirements, prohibited actions, approval paths, supervisor triggers, and emergency handoffs.
5. **Author scripts and knowledge.** Script / Knowledge Author drafts content from approved sources and identifies assumptions, decision points, required disclosures, and tool steps.
6. **Test with synthetic scenarios.** Exercise normal, ambiguous, adversarial, accessibility, failure, regulatory, security, and escalation cases.
7. **Independent QA/compliance review.** Reviewer can PASS, REVISE, or ESCALATE. The author cannot approve publication.
8. **Version and publish.** Only an approved release mechanism may promote content into the live knowledge/script surface.

### B. Handle an interaction

9. **Receive and establish channel context.** Identify inbound/outbound context, channel, locale, recording/consent state, and any project-defined compliance prerequisites.
10. **Authenticate or verify when required.** Do not expose account-specific information or perform protected actions until the required verification level is satisfied.
11. **Classify intent, urgency, and risk.** Determine the service journey, likely resolution path, and whether mandatory escalation conditions already apply.
12. **Retrieve scoped context.** Read only the minimum customer/account/case context required for the current task.
13. **Retrieve approved knowledge/script.** Use the current approved version; generated suggestions are advisory unless the private contract explicitly permits direct use.
14. **Resolve or propose a bounded action.** Inform, create/update a case, schedule, transfer, or invoke another explicitly allowed capability within project-defined authority.
15. **Escalate when triggered.** Ambiguity, threats, safety, fraud/security signals, legal/regulatory issues, policy exceptions, repeated failure, high-value commitments, or customer requests for escalation route to the Supervisor or another function.
16. **Verify the outcome.** Confirm the external system state or customer-visible result rather than assuming a tool call succeeded.
17. **Record disposition and evidence.** Capture outcome, unresolved items, policy/script version, material actions, approvals, escalations, and follow-up obligations.

### C. Supervise, assure quality, and learn

18. **Monitor live operations by exception.** Supervisor receives queue, SLA, sentiment/risk, repeat-contact, abandonment, failure, and escalation signals rather than reading every conversation by default.
19. **Intervene and recover.** Supervisor may join/transfer/reassign or invoke explicitly delegated exception paths; unsupported policy exceptions escalate outside Service.
20. **Sample and score interactions.** QA applies a versioned rubric across human and automated interactions, with higher sampling for high-risk journeys and newly changed scripts/models.
21. **Coach and remediate.** Convert repeated errors into targeted coaching, workflow fixes, clearer knowledge, or capability restrictions.
22. **Analyze trends.** Aggregate failure reasons, repeat contacts, escalations, customer friction, knowledge gaps, and policy ambiguity.
23. **Propose content/process changes.** Script Author, Supervisor, Product, Operations, Legal, or another function may open a governed change request.
24. **Re-test and release.** No live behavior changes simply because an agent learned something during a call; improvements re-enter the controlled author/review/release loop.

## Canonical capability classes

The public framework defines capability names; private projects bind them to systems and connectors.

### Conversation
- `interaction.observe`
- `interaction.respond`
- `interaction.transfer`
- `interaction.terminate`
- `interaction.escalate`

### Customer / case context
- `customer.read_scoped`
- `case.read`
- `case.create`
- `case.update_bounded`
- `history.read_scoped`

### Knowledge and scripts
- `knowledge.search_approved`
- `script.read_approved`
- `knowledge.draft`
- `script.draft`
- `content.request_review`
- `content.publish_approved`

### Identity, consent, and security
- `identity.verify`
- `consent.read`
- `consent.record`
- `suppression.read`
- `suppression.record`
- `security.escalate`

### Business actions
- `schedule.read`
- `schedule.update_bounded`
- `offer.read_approved`
- `business_action.execute_bounded`
- `business_action.request_approval`
- `payment.secure_handoff`

### Supervision and quality
- `queue.observe`
- `queue.reassign_bounded`
- `supervisor.monitor_flagged`
- `supervisor.intervene`
- `quality.sample`
- `quality.score`
- `analytics.read_aggregate`
- `coaching.create`

## Default role-to-capability posture

| Capability class | Front line | Supervisor | Script/Knowledge Author | QA/Compliance |
| --- | --- | --- | --- | --- |
| Observe current interaction | Yes | Flagged/scoped | Synthetic or approved samples only | Sampled/scoped |
| Respond to customer | Bounded | During explicit intervention | No | No |
| Transfer / escalate | Yes | Yes | No | Escalation finding only |
| Scoped customer/case read | Minimum required | Escalation scope | Normally no live customer access | Sampled/minimized |
| Case create/update | Bounded | Bounded exception handling | No | No |
| Search approved knowledge | Yes | Yes | Yes | Yes |
| Draft scripts/knowledge | Feedback only | Feedback/propose | Yes | Required revisions only |
| Publish content | No | No | No | Gate decision only; release mechanism publishes |
| Identity / consent operations | Follow deterministic procedure | Verify/recover only | Design procedure, no live action | Test/inspect procedure |
| Financial/value action | Only explicit bounded capability | Only explicit supervisor bound | No | No |
| Payment data | Secure handoff only | Secure handoff only | No | Redacted evidence only |
| Queue controls | No | Bounded | No | No |
| Quality scoring | Self-check only | Coaching view | Draft test cases | Independent score/gate |
| Aggregate analytics | Limited | Yes | Yes | Yes |

## Project-local contract

A private project should define a contact-center profile using `schemas/contact-center-profile.schema.json`. It should contain only references and mappings such as:

- enabled roles and channels;
- approved content/policy references;
- capability-to-system/connector bindings;
- role authority for each capability;
- identity and consent policy references;
- escalation policy and supervisor triggers;
- QA rubric and sampling policy references;
- model assignments for each role/task;
- business-specific thresholds and approval routes.

The public framework must never contain customer records, live transcripts, credentials, private scripts, internal policies, proprietary offers, private legal advice, or production connector secrets.

## External design analogs

The operating model is informed by mature contact-center patterns rather than copied from any single vendor: COPC CX performance management; Google Agent Assist / Supervisor Assist; NICE agent-assist concepts; NIST AI RMF governance; PCI DSS treatment of call-center payment data; and U.S. telemarketing consent/suppression controls as examples of rules that should be mechanized rather than left to agent discretion.
