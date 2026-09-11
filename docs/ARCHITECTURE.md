# Company OS Architecture

## Model

The Company OS is a public, reusable governance and coordination layer. It defines what a business role is, how work is represented, how functions hand work to one another, when independent review/approval is required, and how outcomes become learning.

It intentionally does not contain a real company's credentials, customers, employees, economics, contracts, private policies or adapters.

```text
request / signal
      ↓
Chief of Staff / Router
      ↓
structured work item
      ↓
accountable department
      ↓
proposal / artifact
      ↓
independent review when required
      ↓
authority check / approval
      ↓
private company execution adapter
      ↓
verification / outcome
      ↓
learning
```

## Shared Engine + Private Contract

Public repo owns role contracts, schemas, generic policies, workflows, synthetic evaluations and public-safety controls.

Private company repo owns company facts, integrations, customer/employee data, private KPIs, detailed authority thresholds, credentials and execution adapters.

## Core principle

Agents are organizational functions, not personas. Their contracts define mission, evidence, outputs, authority, red lines, handoffs and quality tests. The work ledger is more important than agent-to-agent conversation.
