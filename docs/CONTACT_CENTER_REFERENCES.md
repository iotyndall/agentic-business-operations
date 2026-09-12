# Contact Center Design References

This public framework uses external standards and product patterns as design inspiration. These references do not replace company-specific legal, compliance, privacy, security, or operational review.

## COPC Customer Experience Standard

- https://www.copc.com/copc-standards/
- https://www.copc.com/copc-standards/cx-standard/

Design lessons used here: manage human and AI service under a common performance framework; define service journeys; govern knowledge, quality, corrective action, technology, and performance verification; measure outcomes rather than merely deploying technology.

## Google Contact Center AI / Agent Assist

- https://docs.cloud.google.com/contact-center/ccai-platform/docs/agent-assist
- https://docs.cloud.google.com/gemini-enterprise-cx/agent-assist/sa-human-agent
- https://docs.cloud.google.com/gemini-enterprise-cx/agent-assist/sa-virtual-agent

Design lessons used here: separate knowledge suggestions from agent action; monitor interactions for escalation triggers; route only flagged conversations to supervisors; support explicit transfer from virtual to human/supervisor handling.

## NICE Agent Assist Hub

- https://www.nice.com/faq/products-faqs/what-is-agent-assist-hub

Design lessons used here: present contextual customer information, knowledge, recommended next steps, and workflow actions in one governed agent workspace rather than giving unrestricted access to every backend system.

## NIST AI Risk Management Framework — Generative AI Profile

- https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence

Design lessons used here: lifecycle governance, explicit actor responsibilities, risk identification, evaluation, monitoring, and human/organizational controls around generative systems.

## FTC Telemarketing Sales Rule

- https://www.ftc.gov/business-guidance/resources/complying-telemarketing-sales-rule
- https://www.ftc.gov/legal-library/browse/rules/telemarketing-sales-rule

Design lessons used here: operationalize required disclosures, calling windows, do-not-call/suppression, training, recordkeeping, and opt-out procedures rather than depending on worker memory or free-form model judgment.

## FCC TCPA consent/revocation controls

- https://docs.fcc.gov/public/attachments/FCC-24-24A1.pdf

Design lesson used here: consent/revocation handling is a controlled state transition that should be captured through a dedicated capability and promptly honored according to applicable rules.

## PCI Security Standards Council — call-center environments

- https://www.pcisecuritystandards.org/faqs/are-call-center-environments-considered-sensitive-areas-for-pci-dss-requirement-9-1-1/

Design lesson used here: customer-service tooling may enter sensitive-data environments; payment data should be minimized and routed through dedicated secure mechanisms rather than ordinary conversation/model context.

## Framework interpretation

These references inspire the **shape** of the reusable operating system: separation of duties, explicit capabilities, escalation triggers, controlled knowledge, monitoring, QA, and evidence. The private adopter remains responsible for deciding which rules actually apply, supplying approved content, selecting vendors/connectors, setting thresholds, and obtaining appropriate legal/compliance review.
