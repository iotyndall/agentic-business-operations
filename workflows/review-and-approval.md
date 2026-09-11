# Review and Approval Workflow

1. Domain owner produces a proposal/decision artifact.
2. Risk policy determines whether independent review is required.
3. Independent reviewer returns PASS / REVISE / ESCALATE using `review.schema.json`.
4. Any action beyond the role's authority ceiling requires a separate `approval.schema.json` artifact.
5. Approval is bound to the specific action/conditions; it is not blanket authority.
6. Execution occurs only through a company-local adapter/tool with its own permissions.
7. Verification records actual result/evidence.
8. Learning updates reusable policy/SOP only through reviewable change management.
