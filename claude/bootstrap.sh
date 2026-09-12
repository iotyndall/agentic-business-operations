#!/usr/bin/env bash
# Clone the locked Company OS framework and export Claude Code subagents into this private repo.
set -euo pipefail
LOCK=.agentic/business-ops.lock.json
test -f "$LOCK" || { echo "missing $LOCK"; exit 1; }
COMMIT=$(python3 -c "import json;print(json.load(open('$LOCK'))['commit'])")
REPO=$(python3 -c "import json;print(json.load(open('$LOCK'))['repository'])")
rm -rf .company-os
git clone -q "https://github.com/$REPO.git" .company-os
git -C .company-os checkout -q "$COMMIT"
python3 .company-os/scripts/validate_framework_lock.py "$LOCK" .company-os
python3 .company-os/scripts/validate_company_contract.py .agentic/business-ops.json
PROFILE=""; test -f .agentic/marketing-profile.json && PROFILE="--marketing-profile .agentic/marketing-profile.json"
python3 .company-os/scripts/export_claude_code.py .agentic/business-ops.json . ${ENABLE:+--enable "$ENABLE"} $PROFILE
grep -q '^\.company-os/$' .gitignore 2>/dev/null || echo '.company-os/' >> .gitignore
echo "Company OS ready at framework $COMMIT"
