# Private-company adoption template

Keep company-specific context in the private implementation repository. Copy these assets into that repository:

- `business-ops.example.json` → `.agentic/business-ops.json`
- `business-ops.lock.example.json` → `.agentic/business-ops.lock.json`
- `.github/workflows/business-ops-contract.yml` → the same workflow path in the private repo

## Pinning

Set `.agentic/business-ops.lock.json.commit` to the exact 40-character commit SHA of the reviewed Company OS release you intend to consume. The workflow reads that SHA from the lock and checks out exactly that commit; there is no second framework-ref value to keep synchronized.

The lock also names the contract schema inside that exact checkout. The workflow:

1. checks out the private repo without persisted Git credentials;
2. reads the immutable Company OS SHA from the lock;
3. checks out that exact public framework commit without persisted credentials;
4. verifies the checkout origin is exactly `github.com/iotyndall/agentic-business-operations` and HEAD matches the lock;
5. applies the locked JSON schema to `.agentic/business-ops.json`, including referenced model-policy schemas;
6. applies semantic Company OS invariants such as resolvable `system://` references, provider/model references, assignment capabilities, and authority defaults.

Never put API keys in the contract or lock. Provider credentials are references such as `secret://OPENAI_API_KEY`; the actual secret remains in the private execution environment.
