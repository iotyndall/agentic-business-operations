# Agentic Business Operations

A public-safe, reusable operating system for governed AI departments and cross-functional business workflows.

## Mission

Model a company as a set of specialist operational functions with explicit missions, inputs, systems of record, decision rights, approvals, handoffs, evidence requirements, quality controls, and learning loops.

The goal is not a collection of personas. The goal is an auditable operating model in which agents can take initiative while deterministic policy limits what they may authorize or execute.

## Operating loop

`observe → orient → propose → review → act within authority → verify → learn`

## Initial departments

- Chief of Staff / Company Router
- Sales
- Marketing
- Customer / Guest Service
- Operations
- Legal
- Finance / Controller
- Product

Departments may contain multiple specialist roles. Separation of duties is preferred over a single all-powerful agent.

## Repository boundary

This repository is designed to be safe to share publicly.

Allowed here:
- generic role contracts;
- public-safe authority and approval patterns;
- work-item, handoff, evidence, decision, approval, and outcome schemas;
- synthetic examples and scenario tests;
- generic SOP templates;
- reusable orchestration patterns;
- public documentation.

Never place here:
- company-specific credentials or secrets;
- customer or employee data;
- account, tax, banking, portfolio, or family-office information;
- private contracts, legal matters, financial records, or production evidence;
- proprietary pricing, internal KPIs, property/account identifiers, private prompts, or system credentials;
- Mesa Global, YALLOHA, Tyndall Personal Finance, or other private-company configuration.

Private companies consume this framework through local contracts and adapters in their own private repositories.

## Relationship to other control planes

- `agentic-platform-operations` governs software engineering and release operations.
- `agentic-business-operations` governs business roles, work, decisions, approvals, and cross-functional handoffs.
- company repositories provide private local context, tools, systems of record, authority limits, and domain-specific policy.

## Architecture direction

```text
Private company request/event
        ↓
Company Router / Chief of Staff
        ↓
Structured work item
        ↓
Owning department
        ↓
Specialist analysis / proposed action
        ↓
Independent review or approval gate when required
        ↓
Bounded execution adapter in private company repo
        ↓
Verification / outcome
        ↓
Learning
```

## Design principles

1. High autonomy does not imply high authority.
2. Agents may investigate more broadly than they may execute.
3. External or irreversible actions require explicit policy and appropriate approval.
4. Work moves through durable work items rather than unbounded agent chat.
5. Evidence, assumptions, recommendations, approvals, and outcomes remain distinguishable.
6. The agent that authors a material recommendation should not be its sole approver.
7. Ambiguity defaults to escalation, not invented authority.
8. Company-specific data and adapters stay outside this public repository.

## Status

Foundation stage. Initial work will define the company constitution, work-item lifecycle, role contracts, department authority model, handoff schemas, and evaluation framework before enabling execution adapters.
