# SUBMISSION.md — ready-to-paste portal text (Mission 101: Internet Court Partner Demo Lab)

> Paste the sections below into the Mission 101 contribution form. Replace
> `<REPO-URL>` and `<VIDEO-URL>` with the public GitHub repo URL and the
> uploaded demo video URL.
>
> BEFORE SUBMITTING — open question: the mission form shows a notice that
> the Discord builder-wg role is required. Verify at submit time whether
> the submitting account holds that role (or how to obtain it) — this does
> not affect the build, only the submission step.

---

## Title
Delegate & Defend — ERC-7710 delegations judged by GenLayer's Internet Court

## Description
A principal delegates spending authority to an AI buyer agent through an
ERC-7710 delegation (MetaMask Smart Accounts): spend cap 0.1 GEN, per-deal
cap 0.06 GEN, 5 deals, 30-day expiry. The agent opens escrowed deals on the
principal's behalf, and every redemption is enforced by an in-contract
Delegation Manager. When a deal is disputed, GenLayer's Internet Court
judges the evidence with LLM consensus — and the verdict is enforced
on-chain: a refund verdict revokes the delegation, so the agent can never
spend under it again.

Both paths are proven live on GenLayer Studio Next (chain 61997):
deal-001 (logo pack, 0.03 GEN) went happy-path to DELIVERED, and deal-002
(market-research report, 0.05 GEN) was disputed and adjudicated to REFUNDED,
with the court's verdict text stored on-chain and mandate-001 revoked by the
court's decision. A third redemption attempt after the revocation was
rejected on-chain (FINISHED_WITH_ERROR) — the revocation actually blocks
future spending.

The court uses the PEV V5 validator pattern: every validator independently
re-runs the same assessment prompt and derives its own decision; the leader
is accepted only when the bound (assessment, decision) pair agrees. The
court decision is stored as a GenLayerDelegationDecision following the
official GenLayer ERC-7710 connector skill, and its effects map to the
skill's decision table (refund → revoke, release → continue, unclear →
escalate/pause with a delegator human-review fallback).

## What it integrates
- **ERC-7710 delegations / MetaMask Smart Accounts** (Internet Court stack
  layer 03, contracts & obligations): mandate granting with caveats
  (spend cap, per-deal cap, deal count, expiry), redemption enforcement,
  emergency revoke, and a RevocationController driven by court decisions.
- **GenLayer Internet Court** (layer 06, verification & disputes):
  LLM-consensus adjudication with independent validator re-evaluation.
- **GenLayer Studio Next (chain 61997)**: the live deployment, both deals,
  and the blocked redemption are all on-chain and reproducible from the repo.

## Links
- Repo: <REPO-URL>
- Contract: https://explorer-studio-dev.genlayer.com/address/0xD6D0C6C90CCcED47835bf790Ea3a2BcD52be6437
- On-chain proof (every tx hash + explorer links): <REPO-URL>/blob/main/ONCHAIN_PROOF.md
- Demo video (39s, 9:16): <VIDEO-URL>

## Evidence summary
- Contract `0xD6D0C6C90CCcED47835bf790Ea3a2BcD52be6437`, deploy tx
  `0x56004c5282c8d0e4dd0ca6912525f83254e223381abded10ddb2c8682fba7aed`
- deal-001 DELIVERED (open `0x33bce181…`, confirm `0xdfc79aef…`)
- deal-002 REFUNDED by the court (open `0x5b45670c…`, dispute `0xc984a1af…`,
  adjudicate `0x19f1e309…`); verdict text on-chain; mandate-001 REVOKED
- deal-003 redemption after revocation BLOCKED on-chain (`0x646b114f…`,
  FINISHED_WITH_ERROR)
