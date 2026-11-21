#!/usr/bin/env bash
# Full scripted DelegateCourt demo run on Studio Next (chain 61997):
# deploy -> grant mandate -> deal-001 happy path -> deal-002 dispute ->
# court adjudication (refund + mandate revocation) -> blocked deal-003.
# Prerequisites: npm install; ../.venv with web3 + eth_account;
# ../.keys/keypairs.json (see make_keys.py); both actor accounts funded
# with test GEN via sim_fundAccount (see README).
# Usage: ./run_demo.sh   (prints every tx hash; exits non-zero on any failure)
set -euo pipefail
cd "$(dirname "$0")"
PY="../.venv/bin/python"
KEYS="../.keys/keypairs.json"
DELEGATOR=$($PY -c "import json;print(json.load(open('$KEYS'))['delegator']['address'])")
DELEGATE=$($PY -c "import json;print(json.load(open('$KEYS'))['delegate']['address'])")
SELLER=$($PY -c "import json;print(json.load(open('$KEYS'))['seller']['address'])")
EXPIRES=$(( $(date +%s) + 2592000 ))

echo "== deploy =="
SENDER="$DELEGATOR" node build_deploy.mjs > /tmp/dl_build_deploy.log 2>&1
awk '/---TX---/{flag=1;next}flag' /tmp/dl_build_deploy.log > /tmp/dl_tx_deploy.json
$PY sign_broadcast.py delegator /tmp/dl_tx_deploy.json /tmp/dl_deploy.json
DEPLOY_TX=$($PY -c "import json;print(json.load(open('/tmp/dl_deploy.json'))['txHash'])")
echo "deploy tx: $DEPLOY_TX"
sleep 20
CONTRACT=$(node contract_address.mjs "$DEPLOY_TX")
echo "contract: $CONTRACT"
node wait_for.mjs "$CONTRACT" get_name '[]' 'DelegateCourt' 300

echo "== grant mandate =="
./call.sh delegator "$CONTRACT" grant_delegation "[\"mandate-001\",\"$DELEGATE\",100,60,5,$EXPIRES]" grant
node wait_for.mjs "$CONTRACT" get_mandate '["mandate-001"]' 'active' 300

echo "== deal-001 happy path =="
./call.sh delegate "$CONTRACT" open_deal "[\"mandate-001\",\"deal-001\",\"$SELLER\",\"Logo design pack (3 concepts, SVG + PNG)\",30]" open1
node wait_for.mjs "$CONTRACT" get_status '["deal-001"]' 'created' 300
./call.sh delegator "$CONTRACT" confirm_delivery '["deal-001"]' confirm1
node wait_for.mjs "$CONTRACT" get_status '["deal-001"]' 'delivered' 300

echo "== deal-002 dispute path =="
./call.sh delegate "$CONTRACT" open_deal "[\"mandate-001\",\"deal-002\",\"$SELLER\",\"AI market-research report (10 pages, English)\",50]" open2
node wait_for.mjs "$CONTRACT" get_status '["deal-002"]' 'created' 300
./call.sh delegator "$CONTRACT" dispute '["deal-002","The seller never sent the report. No file, no link, no message after payment. Three days passed and nothing was delivered."]' dispute2
node wait_for.mjs "$CONTRACT" get_status '["deal-002"]' 'disputed' 300
./call.sh delegator "$CONTRACT" adjudicate '["deal-002"]' adjudicate2
node wait_for.mjs "$CONTRACT" get_status '["deal-002"]' 'resolved_refund' 600

echo "== deal-003 blocked redemption (expected FINISHED_WITH_ERROR) =="
./call.sh delegate "$CONTRACT" open_deal "[\"mandate-001\",\"deal-003\",\"$SELLER\",\"Extra report (should be blocked)\",10]" blocked3 || true
sleep 45

echo "== final state =="
node verify.mjs "$CONTRACT" deal-001 mandate-001
node verify.mjs "$CONTRACT" deal-002 mandate-001
echo "DONE. Contract: $CONTRACT"
