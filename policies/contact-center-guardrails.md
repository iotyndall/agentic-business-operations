# Contact Center Guardrails

These defaults apply to any Company OS contact-center implementation unless a stricter private policy overrides them. They define control categories, not jurisdiction-specific legal advice.

## 1. Least privilege and capability binding

- Roles receive named capabilities, not arbitrary connector access.
- Every capability maps to a declared private system/connector and a bounded data/action scope.
- Unknown capabilities, undeclared connectors, or missing scopes fail closed.
- Tool errors and ambiguous results are surfaced; agents may not infer success.

## 2. Approved-content boundary

- Front-line workers use approved, versioned scripts/knowledge for material policy, price, product, legal, safety, or compliance statements.
- Generated suggestions may assist but must not silently replace controlled content.
- Authors draft; independent reviewers gate; a separate release mechanism publishes.
- Live conversations cannot directly mutate production policy or script content.

## 3. Identity and data minimization

- Account-specific data or protected actions require the project-defined verification level.
- Retrieve only data necessary for the current interaction.
- Cross-customer lookup, broad exports, or unrelated transcript access are prohibited by default.
- Sensitive evidence used for QA must be minimized/redacted where practical.

## 4. Consent, suppression, recording, and outbound controls

- The private project must define applicable consent, suppression/do-not-contact, recording, disclosure, channel, locale, and calling-window rules.
- These controls should be implemented as deterministic prerequisites or connector-side enforcement where possible, not remembered ad hoc by a model.
- A customer request to opt out, stop contact, or escalate must not be ignored because it conflicts with a sales/service metric.

## 5. Payments and sensitive credentials

- Raw payment credentials should not enter general-purpose model context or ordinary transcripts when a secure handoff/tokenized mechanism is available.
- Front-line and supervisor roles use `payment.secure_handoff`; they do not store or repeat sensitive payment data unnecessarily.
- Financial commitments, credits, refunds, discounts, or waivers require an explicit bounded authority in the private contract.

## 6. External communication and commitments

- Responding to a live customer is itself an external action and must be explicitly authorized for that role/channel.
- Workers may not create contracts, guarantees, legal positions, policy exceptions, or material value commitments beyond delegated authority.
- Required disclosures cannot be omitted, softened, or reordered merely to increase conversion or shorten handle time.

## 7. Escalation and human/supervisor control

- Every live channel must have an explicit escalation path or a fail-safe termination/recontact procedure.
- Safety, fraud/security, legal threats, vulnerable-customer concerns, identity failure, disputed consent, policy conflict, high-value requests, or repeated tool failure require escalation according to private policy.
- Supervisor monitoring should be exception-driven and purpose-limited.

## 8. Separation of duties

- Script/Knowledge Author cannot approve and publish their own material change.
- QA/Compliance Reviewer cannot alter the artifact being reviewed to make it pass.
- Supervisor exceptions above delegated authority require a separate approver.
- High-risk content/tool changes should use a different reviewer/model/person from the author when practical.

## 9. Evidence and auditability

For material actions record, at minimum:
- interaction/work item identifier;
- relevant script/policy version;
- capability invoked;
- system/connector reference;
- approval or exception evidence when required;
- verified outcome or unresolved state.

Evidence must be sufficient to reconstruct what happened without requiring raw secrets or unnecessary customer data.

## 10. Performance and anti-gaming

Do not optimize a single operational metric at the expense of safety or truthful resolution. In particular:
- handle time cannot override required verification or disclosures;
- conversion cannot override consent/suppression or truthful claims;
- deflection cannot override the right/need to escalate;
- QA pass rate cannot justify suppressing adverse findings;
- supervisor intervention rate should not be minimized by hiding incidents.

## 11. Fail-closed conditions

A worker must pause, escalate, or use a safe fallback when:
- identity/consent status cannot be established;
- authoritative policy/knowledge is unavailable or contradictory;
- required capability/connector is unavailable;
- a tool result cannot be verified;
- requested action exceeds authority;
- customer safety/security/legal risk is unresolved;
- a mandatory escalation path is triggered.

## 12. Local compliance overlay

The private implementation owns the actual legal/compliance controls for its jurisdictions and business model. Examples include telemarketing consent/do-not-call rules, recording consent, accessibility obligations, sector-specific disclosures, privacy/retention requirements, payment-card controls, and regulated-product restrictions. The public framework defines where those controls attach; it does not hard-code the local rule text.
