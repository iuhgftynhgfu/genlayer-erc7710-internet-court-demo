# Delegate & Defend — on-chain proof (Studio Next, chain 61997)

## Contract
- **DelegateCourt**: `0xD6D0C6C90CCcED47835bf790Ea3a2BcD52be6437`
- **Deploy TX**: `0x56004c5282c8d0e4dd0ca6912525f83254e223381abded10ddb2c8682fba7aed`
- **Explorer (contract)**: https://explorer-studio-dev.genlayer.com/address/0xD6D0C6C90CCcED47835bf790Ea3a2BcD52be6437
- **Explorer (deploy tx)**: https://explorer-studio-dev.genlayer.com/tx/0x56004c5282c8d0e4dd0ca6912525f83254e223381abded10ddb2c8682fba7aed
- **Consensus contract**: `0xb7278A61aa25c888815aFC32Ad3cC52fF24fE575`
- **RPC**: https://studio-next.genlayer.com/api (also https://studio-dev.genlayer.com/api)
- **Delegator / deployer (fresh keypair)**: `0x71e0Ca8C4a96fA1b1a1bbF1993BBf53cBF742F73`
- **Delegate agent (fresh keypair)**: `0x69074fe02EE996Deaf64A769c8D14F7EdcB6493C`
- **Seller**: `0xEfF25B0D6231e9d55d5a9CDc3c458bDd7a572F65`
- **py-genlayer version (Depends)**: `1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
- Both actor accounts were funded with 100 test GEN each from the Studio
  faucet (`sim_fundAccount`, the same RPC the Studio faucet button calls).
  Funding txs: delegator
  `0xae82f2b9b1a1be8faa3f5de159196780c4f8ca838ddee743644b360014eb4fe2`,
  delegate
  `0x9c151db828375e5ba540b72989c5523b38186741cb0e6706b153e63af06dddf5`.
  No real wallet and no real money were used anywhere in this demo.

## Verified lifecycle (all on-chain, read back via genlayer-js readContract)

### mandate-001 — ERC-7710 delegation granted
- Delegator `0x71e0Ca8C…2F73` grants delegate agent `0x69074fe0…493C` a mandate:
  spend cap 0.1 GEN, per-deal cap 0.06 GEN, max 5 deals, 30-day expiry.
- grant_delegation TX: `0x4f838095a5f45c0148ee8256e88c5d0204e50b89cd1b7c9fce6844f53b4bcf54` → status `active`, `is_revoked` → `false`
- Explorer: https://explorer-studio-dev.genlayer.com/tx/0x4f838095a5f45c0148ee8256e88c5d0204e50b89cd1b7c9fce6844f53b4bcf54

### deal-001 — happy path → DELIVERED
- Item: "Logo design pack (3 concepts, SVG + PNG)", amount 0.03 GEN
- open_deal TX (by the delegate agent, redeeming mandate-001): `0x33bce1811d2666513cee0df7f702a3a40e7e9cc3a23e418199a1e29c655001b4` → status `created`
  - Explorer: https://explorer-studio-dev.genlayer.com/tx/0x33bce1811d2666513cee0df7f702a3a40e7e9cc3a23e418199a1e29c655001b4
- confirm_delivery TX (by the delegator): `0xdfc79aefa8eb7ced5daba8af1382a87f8ebc1559a78e339abcfc8bc03e6e51c1` → status `delivered`, outcome `release`
  - Explorer: https://explorer-studio-dev.genlayer.com/tx/0xdfc79aefa8eb7ced5daba8af1382a87f8ebc1559a78e339abcfc8bc03e6e51c1
- Mandate after deal-001: spent 30/100 mGEN, deals_used 1/5, still `active`.

### deal-002 — dispute → Internet Court adjudication → REFUNDED + MANDATE REVOKED
- Item: "AI market-research report (10 pages, English)", amount 0.05 GEN
- open_deal TX (by the delegate agent): `0x5b45670c7a8052b535d009e50b0a3bd4f620cbcd767f7f7906d88be31619c989` → status `created`
  - Explorer: https://explorer-studio-dev.genlayer.com/tx/0x5b45670c7a8052b535d009e50b0a3bd4f620cbcd767f7f7906d88be31619c989
- dispute TX (by the delegator): `0xc984a1afdc869484fc34ebbe9de21eb8a07c08c8b14a2d323ec6fa67fd3c6b0d` → status `disputed`
  - Explorer: https://explorer-studio-dev.genlayer.com/tx/0xc984a1afdc869484fc34ebbe9de21eb8a07c08c8b14a2d323ec6fa67fd3c6b0d
  - Reason: "The seller never sent the report. No file, no link, no message after payment. Three days passed and nothing was delivered."
- adjudicate TX: `0x19f1e30989f9301770f3c9636e46dd6f0640c40239ce0a67c7bf2952d35f23b3` → status `resolved_refund`, outcome `refund`
  - Explorer: https://explorer-studio-dev.genlayer.com/tx/0x19f1e30989f9301770f3c9636e46dd6f0640c40239ce0a67c7bf2952d35f23b3
  - Verdict (LLM consensus, stored verbatim on-chain): "The dispute gives a concrete account of non-delivery: no file, link, or message arrived in the three days after payment. The deal facts show no delivery by the seller, so the report was not delivered as promised."
  - Court decision stored on-chain (`get_decision("deal-002")`):
    `{"mandateId": "mandate-001", "dealId": "deal-002", "decision": "refund", "court_effect": "revoke", "assessment": "not_delivered", "score": 1, "verdict": "...", "issuedAt": 1795300826}`
  - **Mandate effect (the ERC-7710 connector in action):** mandate-001 is now
    `revoked`, `is_revoked` → `true`, `court_decision` → `revoke`. The
    court's refund verdict revoked the delegation on-chain.

### deal-003 — redemption under the revoked mandate is BLOCKED
- open_deal TX (by the delegate agent, after revocation): `0x646b114f75901db2686f3f8429d506daadac6374a8effde07ddf6046c7f034a0`
  - Explorer: https://explorer-studio-dev.genlayer.com/tx/0x646b114f75901db2686f3f8429d506daadac6374a8effde07ddf6046c7f034a0
  - Result: `FINISHED_WITH_ERROR` (txExecutionResult 2) — the Delegation
    Manager rejected the redemption (`[EXPECTED] mandate revoked: redemption
    blocked`). `get_deal("deal-003")` returns empty: the deal was never created.

## How the adjudication works
`adjudicate(deal_id)` builds a prompt from the deal facts + dispute reason and
calls `gl.nondet.exec_prompt(prompt, response_format="json")` inside
`gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`. The leader proposes an
assessment (`delivered` / `not_delivered` / `unclear` + evidence flag +
reply); the contract derives the decision deterministically from the
assessment (delivered → release, not_delivered → refund, unclear → review).
Every validator independently re-runs the SAME prompt, derives its own
decision from its own assessment, and accepts the leader only when the bound
(assessment, decision) pair agrees with its own. The agreed verdict is stored
on-chain, and the resulting `GenLayerDelegationDecision` is applied to the
mandate: refund → revoke, release → continue, review → escalate (pause until
the delegator resolves it via `resolve_review`).

## Deploy method (proven)
- Build addTransaction calldata with genlayer-js 2.0.0-rc.3 + viem in Node
  (`scripts/build_deploy.mjs` for deploys, `scripts/build_call.mjs` for
  method calls).
- Sign + broadcast with fresh demo keypairs
  (`scripts/sign_broadcast.py`, eth_account; keys in `.keys/keypairs.json`,
  never committed).
- GenLayer node `eth_estimateGas` accepts ONLY 1 param — use
  `w3.manager.request_blocking("eth_estimateGas", [txobj])`, gas = estimate
  x 1.2, gasPrice 0, legacy tx WITHOUT a `type` field, chainId 61997.
- Method calls: `data = [encode(makeCalldataObject(fn, args, kwargs)), leaderOnly]`,
  `serialized = serialize(data)`, `recipient = <contract address>`.
- The deployed contract address is the `to_address` of the deploy transaction
  (`client.getTransaction`); it is NOT in the eth receipt.
- `gen_getTransactionLifecycle` reports Finalized; `getTransaction` reports
  `txExecutionResultName` (`FINISHED_WITH_ERROR` for the blocked redemption).
