# Agentic Business Operations

A public-safe, reusable Company OS for governed AI-assisted business operations.

This repository defines reusable business roles, authority policies, work-item and evidence schemas, model/provider selection, routing, review, handoff and learning patterns. Company-specific data, credentials, internal policies, customer context, live connector configuration and proprietary operating content belong in private adopter repositories.

## Core functions

- Chief of Staff / routing
- Sales
- Marketing
- Customer / Guest Service
- Operations
- Legal
- Finance / Controller
- Product

## Specialized operating modules

### Contact center / service operations

`docs/CONTACT_CENTER_OPERATING_MODEL.md` decomposes Service into separable Front-Line Worker, Service Supervisor, Script / Knowledge Author, and QA / Compliance Reviewer roles. It defines vendor-neutral capability classes, escalation boundaries, and a private `contact-center-profile` contract so adopters can bind their own scripts, policies, models, systems and connectors without leaking them into this public repository.

## Architecture

The public framework owns reusable roles, schemas, policies, synthetic examples and deterministic validation. Private companies consume an immutable framework commit and supply local contracts for their systems, authority, models, content references and connectors.

See:
- `docs/ARCHITECTURE.md`
- `docs/MODEL_SELECTION.md`
- `docs/CONTACT_CENTER_OPERATING_MODEL.md`
- `docs/CONTACT_CENTER_REFERENCES.md`
- `policies/company-constitution.md`
- `policies/contact-center-guardrails.md`
- `templates/private-company/`

## Safety boundary

Public framework roles do not receive credentials or live customer/company data. Model choice never expands authority. External actions require explicit capability and authority grants in the private adopter contract. High-risk actions remain approval-gated and independently verifiable.
