# Delegate & Defend — ERC-7710 delegations judged by GenLayer's Internet Court

**GenLayer BUILDER Mission 101 — "Internet Court: Partner Demo Lab"** (Projects, 20–4,000 PTS)

A principal delegates spending authority to an AI buyer agent through an
**ERC-7710 delegation** (MetaMask Smart Accounts) — spend cap, per-deal cap,
deal count, expiry. The agent opens escrowed deals on the principal's behalf.
When a deal goes wrong, **GenLayer's Internet Court** judges the dispute, and
the verdict is enforced on-chain: a refund verdict **revokes the delegation**,
so the agent can never spend under it again.

Live on **GenLayer Studio Next (chain 61997)**. Every claim below links to a
transaction — see [ONCHAIN_PROOF.md](ONCHAIN_PROOF.md).

> **Partner layer: ERC-7710 (contracts & obligations)** — layer 03 of the
> Internet Court stack. This is a different partner and a different contract
> from the x402 payment demo; the integration point is delegated authority,
> not payment rails.

## The flow

```
Delegator (principal)                Delegate (buyer agent)              Seller
      │                                        │                          │
      │  grant_delegation(mandate-001)         │                          │
      │  cap 0.1 GEN · max deal 0.06 GEN       │                          │
      │  5 deals · 30-day expiry               │                          │
      ├───────────────────────────────────────►│                          │
      │                                        │  open_deal(deal-001)     │
      │                                        ├─────────────────────────►│
      │  confirm_delivery  ──►  DELIVERED, escrow released                │
      │                                        │  open_deal(deal-002)     │
      │                                        ├─────────────────────────►│
      │  dispute("never delivered") ──► Internet Court adjudicates        │
      │  verdict: REFUNDED ──► mandate-001 REVOKED on-chain               │
      │                                        │  open_deal(deal-003) ✗   │
      │                                        │  blocked: mandate revoked │
```

## What the contract does

`contract/DelegateCourt.py` — one intelligent contract, three roles in one:

1. **Delegation Manager (ERC-7710).** `grant_delegation` stores a mandate with
   caveats. Every `open_deal` is a redemption: it fails deterministically when
   the mandate is unknown, revoked, paused, expired, over the per-deal cap,
   over the remaining spend cap, or out of deals. The delegator keeps an
   emergency `revoke_delegation` at all times.
2. **Escrow.** Deals hold funds in escrow. `confirm_delivery` releases to the
   seller; `dispute` sends the deal to the court.
3. **Internet Court + RevocationController.** `adjudicate` runs the court's
   LLM consensus (see below) and applies the resulting
   `GenLayerDelegationDecision` on-chain, following the official
   [GenLayer ERC-7710 connector skill](https://github.com/internet-court/internet-court-skill/tree/main/integrations/genlayer-erc7710-connector):
   refund → `revoke`, release → `continue`, unclear evidence → `escalate`
   (mandate paused until the delegator resolves the review via
   `resolve_review`).

### The court does not trust the leader (PEV V5 validator pattern)

`adjudicate` uses `gl.vm.run_nondet_unsafe` with a validator that
**independently re-runs the same assessment prompt**, derives its own decision
from its own assessment through the contract's deterministic decision table,
and accepts the leader only when the bound `(assessment, decision)` pair
agrees with its own (identical labels, or both in the review class).
Structure-only validation is explicitly not used: a leader claiming
"delivered → release" and a leader claiming "not_delivered → refund" for the
same evidence cannot both pass.

## On-chain proof

| Step | Result |
|---|---|
| Contract | `0xD6D0C6C90CCcED47835bf790Ea3a2BcD52be6437` |
| deal-001 (happy path) | `delivered`, outcome `release` |
| deal-002 (dispute) | `resolved_refund`, outcome `refund` |
| mandate-001 after verdict | `revoked`, `is_revoked` → `true` |
| deal-003 after revocation | blocked — redemption rejected |

Full transaction hashes, explorer links, and the verbatim verdict text:
[ONCHAIN_PROOF.md](ONCHAIN_PROOF.md).

## Reproduce it

```bash
# 1. Install dependencies
cd scripts && npm install            # genlayer-js + viem (builds addTransaction calldata)
python3 -m venv ../.venv && ../.venv/bin/pip install web3 eth_account

# 2. Fresh demo keypairs (never a real wallet) + test GEN from the Studio faucet
../.venv/bin/python make_keys.py     # writes .keys/keypairs.json (mode 600)
# fund via sim_fundAccount, the same RPC the Studio faucet button calls:
curl -s -X POST https://studio-next.genlayer.com/api -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"sim_fundAccount","params":["<address>","0x56BC75E2D63100000"]}'

# 3. Deploy (prints the deploy tx; contract address comes from getTransaction)
SENDER=<delegator> node build_deploy.mjs
../.venv/bin/python sign_broadcast.py delegator /tmp/tx_deploy.json

# 4. Run the demo (see scripts/run_demo.sh for the full scripted run)
./call.sh delegator <contract> grant_delegation '["mandate-001","<delegate>",100,60,5,<expires_at>]'
./call.sh delegate  <contract> open_deal '["mandate-001","deal-001","<seller>","Logo design pack (3 concepts, SVG + PNG)",30]'
./call.sh delegator <contract> confirm_delivery '["deal-001"]'
./call.sh delegate  <contract> open_deal '["mandate-001","deal-002","<seller>","AI market-research report (10 pages, English)",50]'
./call.sh delegator <contract> dispute '["deal-002","The seller never sent the report. No file, no link, no message after payment. Three days passed and nothing was delivered."]'
./call.sh delegator <contract> adjudicate '["deal-002"]'

# 5. Verify
node verify.mjs <contract> deal-002 mandate-001
```

Notes on the deploy path (all verified live on Studio Next):

- Transactions go to the consensus contract
  (`0xb7278A61aa25c888815aFC32Ad3cC52fF24fE575`) via `addTransaction`, never
  directly to the intelligent contract.
- The GenLayer node rejects 2-param `eth_estimateGas` — use the 1-param form,
  gas = estimate × 1.2, gas price 0, legacy tx with no `type` field.
- The `genlayer` PyPI package is an empty placeholder; there is no `genlayer`
  CLI in this flow. Calldata is built with `genlayer-js` 2.0.0-rc.3 + `viem`.
- The contract header pins `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`
  (TreeMap + `from genlayer import *` support).
- The deployed contract address is the `to_address` of the deploy transaction
  (`client.getTransaction`); it is not in the receipt.

## Demo video

`video/delegate-and-defend-demo.mp4` — 39s vertical (9:16) demo built from the
real on-chain data (contract address, deal facts, verdict text, tx hash) with
the Internet Court, GenLayer, and MetaMask logos. Built with ffmpeg from
`video/build_video.sh` (slides + logos + real data overlay).

## Files

```
contract/DelegateCourt.py   the intelligent contract
scripts/                    deploy / call / verify / wait helpers + run_demo.sh
video/                      demo video + build script + logo assets
ONCHAIN_PROOF.md            every tx hash + explorer links + verbatim verdict
SUBMISSION.md               ready-to-paste portal text
```

## Trust assumptions (stated honestly)

- The Delegation Manager and RevocationController live in the same intelligent
  contract as the court. There is no separate EVM Delegation Manager on
  another chain: this demo proves the **decision → revocation loop** on
  GenLayer, following the connector skill's "manual demo relay / single-chain"
  mode, not a cross-chain bridge proof.
- Amounts are milli-GEN integers recorded in escrow state; no GEN is moved
  between accounts in this demo (the escrow is a state ledger, as in the
  reference x402 demo).
- The court's LLM verdict is consensus over 5 validators (Studio Next
  defaults); the verdict text is stored verbatim on-chain.
