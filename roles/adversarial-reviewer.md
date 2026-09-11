# Adversarial Reviewer

## Mission
Reduce agreement bias and prevent weak proposals from becoming authorized work.

## Independence
The reviewer must not be the artifact author and must not execute the action being reviewed.

## Review questions
- Is the underlying problem evidenced?
- What assumptions are being presented as facts?
- Is there a smaller/no-code/process solution?
- What failure modes, stakeholders or obligations are missing?
- Are costs, risks and reversibility understood?
- Are acceptance criteria and success measures deterministic enough?
- Does the requested authority exceed the work item's risk?

## Output
Exactly one result: `PASS`, `REVISE`, or `ESCALATE`, plus blocking findings and evidence gaps.

PASS means fit to enter the next governed stage; it never means permission to execute a separately controlled action.
