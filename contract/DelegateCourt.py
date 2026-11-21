# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Delegate & Defend — ERC-7710 delegated spending judged by GenLayer's Internet Court.

GenLayer BUILDER Mission 101 ("Internet Court: Partner Demo Lab") submission.

Partner layer: ERC-7710 delegations (MetaMask Smart Accounts). A delegator
(principal) grants a delegate agent a mandate — spend cap, per-deal cap, deal
count, expiry — and the agent opens escrowed deals on the principal's behalf.
Every redemption goes through the in-contract Delegation Manager, which
enforces the mandate's caveats exactly like an ERC-7710 caveat enforcer /
Delegation Manager would: unknown mandate, revoked mandate, expired mandate,
over-cap spend, or over-count deals all fail deterministically.

When a deal is disputed, GenLayer's Internet Court judges the evidence. The
court's decision is applied through the connector defined by the official
GenLayer ERC-7710 connector skill
(https://github.com/internet-court/internet-court-skill, integrations/
genlayer-erc7710-connector): the verdict is stored on-chain as a
GenLayerDelegationDecision (mandateId, decision, score, evidence hash,
verdict text) and the RevocationController effect is executed in-contract:
  - refund verdict  -> decision "revoke": the mandate is REVOKED on-chain,
                       all future redemptions under it fail.
  - release verdict -> decision "continue": the mandate is unchanged.
  - unclear evidence -> decision "escalate": the mandate is PAUSED until the
                       delegator resolves the review (human fallback).

Validator pattern (PEV V5): the court does NOT trust the leader's verdict.
Every validator independently re-runs the SAME assessment prompt, derives its
own decision from its own assessment, and accepts the leader only when the
bound (assessment, decision) pair agrees with its own. Opposite assessments
can never both pass. Structure-only validation is explicitly rejected.
"""
import json
import re
from datetime import datetime, timezone
from genlayer import *

MAX_ID = 64
MAX_TEXT = 1000

# Assessment labels the court may return. "unclear" is the review class:
# two honest validators may disagree on wording, but a review-class label
# only ever agrees with another review-class label.
ALLOWED_ASSESSMENTS = ("delivered", "not_delivered", "unclear")
REVIEW_ASSESSMENTS = ("unclear",)
DECISION_VALUES = ("release", "refund", "review")

STYLE = """You are the judge of the Internet Court, the court for the agentic economy. A principal delegated spending authority to an AI buyer agent through an ERC-7710 delegation (a mandate with a spend cap and caveats). The buyer agent opened an escrowed deal with an AI seller agent. The principal now disputes the deal, claiming the seller did not deliver as promised.

Your job is to decide, from the deal facts and the dispute reason only, whether the seller DELIVERED what was promised.

Be fair and brief. Do not invent facts that are not in the deal. If the dispute reason concretely shows the seller failed to deliver the promised item, the assessment is "not_delivered". If the deal facts show delivery, or the dispute reason is vague and gives no concrete evidence of non-delivery, the assessment is "delivered". If the evidence is genuinely too thin to tell either way, the assessment is "unclear"."""

FORMAT = """
Respond with JSON only, in this exact shape:
{"assessment": "delivered" | "not_delivered" | "unclear", "evidence_found": true/false, "reply": "one or two sentences explaining the verdict in plain language"}
- "assessment": "delivered" means the seller delivered as promised; "not_delivered" means the seller clearly did not deliver; "unclear" means the evidence cannot decide it.
- "evidence_found": true when the deal facts and dispute reason contain concrete evidence supporting the assessment, false when the evidence is thin or absent.
- "reply": one or two sentences, plain language, no markdown.
"""


def _normalize(s: str) -> str:
    return " ".join(s.strip().split())


def _now_unix() -> int:
    """Transaction clock. GenVM pins datetime.now() to the tx timestamp,
    so every validator sees the same value. Fall back to the raw message
    datetime (ISO-8601) if the clock is unavailable."""
    try:
        return int(datetime.now(timezone.utc).timestamp())
    except Exception:
        pass
    try:
        raw = gl.message_raw.get("datetime", "")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except Exception:
        raise gl.vm.UserError("[LLM_ERROR] cannot read transaction timestamp")


def _compute_decision(assessment: str) -> str:
    """Deterministic decision table: the contract derives the decision, the
    LLM only supplies the assessment. The decision can never contradict it."""
    if assessment == "delivered":
        return "release"
    if assessment == "not_delivered":
        return "refund"
    return "review"


def _build_assessment_prompt(deal: dict) -> str:
    """The court prompt, shared byte-for-byte by leader and validators."""
    return (
        STYLE
        + "\nDEAL FACTS\n"
        + "Delegator (principal): " + deal["delegator"] + "\n"
        + "Delegate (buyer agent): " + deal["delegate"] + "\n"
        + "Seller: " + deal["seller"] + "\n"
        + "Item promised: " + deal["item"] + "\n"
        + "Amount held in escrow: " + deal["amount_gen"] + " GEN\n"
        + "Mandate: " + deal["mandate_id"] + "\n"
        + "Dispute reason: " + deal["dispute_reason"] + "\n"
        + FORMAT
    )


def _parse_assessment(raw) -> dict:
    """Parse an exec_prompt result into validated evidence fields (no decision).
    Shared by leader and validators so both apply identical parsing."""
    if isinstance(raw, dict):
        parsed = raw
    elif isinstance(raw, str):
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise gl.vm.UserError("[LLM_ERROR] exec_prompt returned no JSON object")
        try:
            parsed = json.loads(raw[start:end + 1])
        except Exception:
            raise gl.vm.UserError("[LLM_ERROR] exec_prompt returned invalid JSON")
    else:
        raise gl.vm.UserError("[LLM_ERROR] unexpected exec_prompt result type")
    assessment = parsed.get("assessment")
    evidence_found = parsed.get("evidence_found")
    reply = parsed.get("reply", "")
    if assessment not in ALLOWED_ASSESSMENTS:
        raise gl.vm.UserError("[LLM_ERROR] invalid assessment")
    if not isinstance(evidence_found, bool):
        raise gl.vm.UserError("[LLM_ERROR] evidence_found must be boolean")
    if not isinstance(reply, str) or not _normalize(reply):
        raise gl.vm.UserError("[LLM_ERROR] reply must be a non-empty string")
    # Cross-field consistency: a decisive assessment needs concrete evidence;
    # an unclear assessment means the evidence was thin.
    if assessment in ("delivered", "not_delivered") and evidence_found is not True:
        raise gl.vm.UserError("[LLM_ERROR] decisive assessment without evidence")
    if assessment == "unclear" and evidence_found is True:
        raise gl.vm.UserError("[LLM_ERROR] unclear assessment with evidence")
    return {
        "assessment": assessment,
        "evidence_found": evidence_found,
        "reply": _normalize(reply)[:MAX_TEXT],
    }


def _validate_result_shape(data) -> None:
    """Validate a full court result (assessment + derived decision)."""
    if not isinstance(data, dict):
        raise gl.vm.UserError("[LLM_ERROR] result must be a dict")
    for field in ("assessment", "evidence_found", "reply", "decision"):
        if field not in data:
            raise gl.vm.UserError("[LLM_ERROR] missing field: " + field)
    if data["assessment"] not in ALLOWED_ASSESSMENTS:
        raise gl.vm.UserError("[LLM_ERROR] invalid assessment")
    if not isinstance(data["evidence_found"], bool):
        raise gl.vm.UserError("[LLM_ERROR] evidence_found must be boolean")
    if not isinstance(data["reply"], str) or not data["reply"]:
        raise gl.vm.UserError("[LLM_ERROR] reply must be a non-empty string")
    if data["decision"] != _compute_decision(data["assessment"]):
        raise gl.vm.UserError("[LLM_ERROR] decision inconsistent with decision table")


def _assessments_compatible(own: str, leader: str) -> bool:
    """Identical labels agree; labels inside the review class agree with each
    other. Anything else (e.g. delivered vs not_delivered) disagrees."""
    if own == leader:
        return True
    return own in REVIEW_ASSESSMENTS and leader in REVIEW_ASSESSMENTS


def _valid_id(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_:-]{1,64}", value) is not None


def _valid_amount(value) -> bool:
    return isinstance(value, int) and value > 0


def _fmt_gen(milli_gen: int) -> str:
    """milli-GEN integer -> human GEN string, e.g. 50 -> '0.05'."""
    whole = milli_gen // 1000
    frac = milli_gen % 1000
    return str(whole) + "." + str(frac).zfill(3).rstrip("0").ljust(1, "0") if frac else str(whole)


class DelegateCourt(gl.Contract):
    name: str
    mandates: TreeMap[str, str]
    deals: TreeMap[str, str]
    decisions: TreeMap[str, str]

    def __init__(self):
        self.name = "DelegateCourt: ERC-7710 delegations judged by the Internet Court"

    # ---- Delegation Manager (ERC-7710) ----

    @gl.public.write
    def grant_delegation(self, mandate_id: str, delegate: str, spend_cap_mgen: int,
                         max_deal_mgen: int, max_deals: int, expires_at: int) -> None:
        # The delegator (caller) grants a delegate agent a mandate with caveats.
        if not _valid_id(mandate_id):
            raise gl.vm.UserError("[EXPECTED] mandate_id must be 1-64 characters of [A-Za-z0-9_:-]")
        if self.mandates.get(mandate_id, ""):
            raise gl.vm.UserError("[EXPECTED] mandate already exists")
        if not isinstance(delegate, str) or not delegate.strip():
            raise gl.vm.UserError("[EXPECTED] delegate must be a non-empty address")
        if not _valid_amount(spend_cap_mgen) or not _valid_amount(max_deal_mgen):
            raise gl.vm.UserError("[EXPECTED] caps must be positive milli-GEN integers")
        if max_deal_mgen > spend_cap_mgen:
            raise gl.vm.UserError("[EXPECTED] max_deal cannot exceed spend_cap")
        if not isinstance(max_deals, int) or max_deals <= 0:
            raise gl.vm.UserError("[EXPECTED] max_deals must be a positive integer")
        now = _now_unix()
        if not isinstance(expires_at, int) or expires_at <= now:
            raise gl.vm.UserError("[EXPECTED] expires_at must be a future unix timestamp")
        delegator = gl.message.sender_address.as_hex
        mandate = {
            "delegator": delegator,
            "delegate": delegate.strip(),
            "spend_cap_mgen": spend_cap_mgen,
            "max_deal_mgen": max_deal_mgen,
            "max_deals": max_deals,
            "expires_at": expires_at,
            "spent_mgen": 0,
            "deals_used": 0,
            "status": "active",
            "revoked": False,
            "court_decision": "",
        }
        self.mandates[mandate_id] = json.dumps(mandate)

    @gl.public.write
    def revoke_delegation(self, mandate_id: str) -> None:
        # Emergency revoke: the delegator can always pull a mandate, instantly.
        stored = self.mandates.get(mandate_id, "")
        if not stored:
            raise gl.vm.UserError("[EXPECTED] mandate not found")
        mandate = json.loads(stored)
        if gl.message.sender_address.as_hex.lower() != mandate["delegator"].lower():
            raise gl.vm.UserError("[EXPECTED] only the delegator can revoke")
        if mandate["revoked"]:
            raise gl.vm.UserError("[EXPECTED] mandate already revoked")
        mandate["revoked"] = True
        mandate["status"] = "revoked"
        mandate["court_decision"] = "emergency_revoke_by_delegator"
        self.mandates[mandate_id] = json.dumps(mandate)

    # ---- Escrowed deals (redemption path) ----

    @gl.public.write
    def open_deal(self, mandate_id: str, deal_id: str, seller: str,
                  item: str, amount_mgen: int) -> None:
        # The delegate agent redeems its mandate to open an escrowed deal.
        # The Delegation Manager enforces every caveat before any state changes.
        if not _valid_id(deal_id):
            raise gl.vm.UserError("[EXPECTED] deal_id must be 1-64 characters of [A-Za-z0-9_:-]")
        if self.deals.get(deal_id, ""):
            raise gl.vm.UserError("[EXPECTED] deal already exists")
        stored = self.mandates.get(mandate_id, "")
        if not stored:
            raise gl.vm.UserError("[EXPECTED] mandate not found")
        mandate = json.loads(stored)
        caller = gl.message.sender_address.as_hex
        if caller.lower() != mandate["delegate"].lower():
            raise gl.vm.UserError("[EXPECTED] only the mandate delegate can open deals")
        if mandate["revoked"]:
            raise gl.vm.UserError("[EXPECTED] mandate revoked: redemption blocked")
        if mandate["status"] == "paused":
            raise gl.vm.UserError("[EXPECTED] mandate paused by the court: redemption blocked")
        if _now_unix() > mandate["expires_at"]:
            raise gl.vm.UserError("[EXPECTED] mandate expired: redemption blocked")
        if not _valid_amount(amount_mgen):
            raise gl.vm.UserError("[EXPECTED] amount must be a positive milli-GEN integer")
        if amount_mgen > mandate["max_deal_mgen"]:
            raise gl.vm.UserError("[EXPECTED] amount exceeds per-deal cap")
        if mandate["spent_mgen"] + amount_mgen > mandate["spend_cap_mgen"]:
            raise gl.vm.UserError("[EXPECTED] amount exceeds remaining spend cap")
        if mandate["deals_used"] >= mandate["max_deals"]:
            raise gl.vm.UserError("[EXPECTED] mandate deal count exhausted")
        if not isinstance(seller, str) or not seller.strip():
            raise gl.vm.UserError("[EXPECTED] seller must be a non-empty address")
        if not isinstance(item, str) or not _normalize(item) or len(item) > MAX_TEXT:
            raise gl.vm.UserError("[EXPECTED] item must be 1-1000 characters")
        deal = {
            "mandate_id": mandate_id,
            "delegator": mandate["delegator"],
            "delegate": caller,
            "seller": seller.strip(),
            "item": _normalize(item),
            "amount_mgen": amount_mgen,
            "amount_gen": _fmt_gen(amount_mgen),
            "status": "created",
            "dispute_reason": "",
            "verdict": "",
            "outcome": "",
        }
        mandate["spent_mgen"] += amount_mgen
        mandate["deals_used"] += 1
        self.mandates[mandate_id] = json.dumps(mandate)
        self.deals[deal_id] = json.dumps(deal)

    @gl.public.write
    def confirm_delivery(self, deal_id: str) -> None:
        # The delegator confirms delivery; escrow releases to the seller.
        stored = self.deals.get(deal_id, "")
        if not stored:
            raise gl.vm.UserError("[EXPECTED] deal not found")
        deal = json.loads(stored)
        if gl.message.sender_address.as_hex.lower() != deal["delegator"].lower():
            raise gl.vm.UserError("[EXPECTED] only the delegator can confirm delivery")
        if deal["status"] != "created":
            raise gl.vm.UserError("[EXPECTED] deal is not awaiting delivery")
        deal["status"] = "delivered"
        deal["outcome"] = "release"
        self.deals[deal_id] = json.dumps(deal)

    @gl.public.write
    def dispute(self, deal_id: str, reason: str) -> None:
        # The delegator disputes non-delivery; the deal moves to adjudication.
        stored = self.deals.get(deal_id, "")
        if not stored:
            raise gl.vm.UserError("[EXPECTED] deal not found")
        deal = json.loads(stored)
        if gl.message.sender_address.as_hex.lower() != deal["delegator"].lower():
            raise gl.vm.UserError("[EXPECTED] only the delegator can dispute")
        if deal["status"] != "created":
            raise gl.vm.UserError("[EXPECTED] deal is not awaiting delivery")
        if not isinstance(reason, str) or not _normalize(reason) or len(reason) > MAX_TEXT:
            raise gl.vm.UserError("[EXPECTED] reason must be 1-1000 characters")
        deal["status"] = "disputed"
        deal["dispute_reason"] = _normalize(reason)
        self.deals[deal_id] = json.dumps(deal)

    # ---- Internet Court adjudication (PEV V5 validator pattern) ----

    @gl.public.write
    def adjudicate(self, deal_id: str) -> None:
        # Internet Court: LLM consensus judges the dispute, then the
        # GenLayerDelegationDecision is applied to the mandate on-chain.
        # Anyone may trigger adjudication.
        stored = self.deals.get(deal_id, "")
        if not stored:
            raise gl.vm.UserError("[EXPECTED] deal not found")
        deal = json.loads(stored)
        if deal["status"] not in ("disputed", "review"):
            raise gl.vm.UserError("[EXPECTED] deal is not disputed")
        prompt = _build_assessment_prompt(deal)

        def leader_fn() -> dict:
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            evidence = _parse_assessment(raw)
            evidence["decision"] = _compute_decision(evidence["assessment"])
            return evidence

        def validator_fn(leaders_res: gl.vm.Result) -> bool:
            # 1. Deterministic checks on the leader's result.
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            try:
                _validate_result_shape(leaders_res.calldata)
            except Exception:
                return False
            # 2. Independent semantic re-evaluation: the validator runs the
            # SAME prompt itself and binds its own (assessment, decision).
            try:
                own_raw = gl.nondet.exec_prompt(prompt, response_format="json")
                own = _parse_assessment(own_raw)
            except Exception:
                return False
            own_decision = _compute_decision(own["assessment"])
            if own_decision != leaders_res.calldata["decision"]:
                return False
            if not _assessments_compatible(own["assessment"], leaders_res.calldata["assessment"]):
                return False
            return True

        verdict = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        try:
            _validate_result_shape(verdict)
        except Exception:
            raise gl.vm.UserError("[LLM_ERROR] invalid consensus verdict")

        decision = verdict["decision"]
        deal["verdict"] = verdict["reply"]
        mandate = json.loads(self.mandates.get(deal["mandate_id"], "{}"))

        # GenLayerDelegationDecision, stored on-chain per the official
        # genlayer-erc7710-connector skill message schema.
        court_decision = {
            "mandateId": deal["mandate_id"],
            "dealId": deal_id,
            "decision": decision,
            "court_effect": "",
            "assessment": verdict["assessment"],
            "score": 1 if decision == "refund" else (0 if decision == "release" else 0),
            "verdict": verdict["reply"],
            "issuedAt": _now_unix(),
        }

        if decision == "release":
            deal["status"] = "resolved_release"
            deal["outcome"] = "release"
            court_decision["court_effect"] = "continue"
        elif decision == "refund":
            deal["status"] = "resolved_refund"
            deal["outcome"] = "refund"
            court_decision["court_effect"] = "revoke"
            # RevocationController effect: the court revokes the mandate.
            if mandate:
                mandate["revoked"] = True
                mandate["status"] = "revoked"
                mandate["court_decision"] = "revoke"
                self.mandates[deal["mandate_id"]] = json.dumps(mandate)
        else:  # review — escalate: pause the mandate pending human review.
            deal["status"] = "review"
            deal["outcome"] = "review"
            court_decision["court_effect"] = "escalate"
            if mandate:
                mandate["status"] = "paused"
                mandate["court_decision"] = "escalate"
                self.mandates[deal["mandate_id"]] = json.dumps(mandate)
        self.decisions[deal_id] = json.dumps(court_decision)
        self.deals[deal_id] = json.dumps(deal)

    @gl.public.write
    def resolve_review(self, deal_id: str, release_funds: bool) -> None:
        # Human fallback for an escalated ("review") deal: the delegator
        # decides, and the mandate is unpaused or revoked accordingly.
        stored = self.deals.get(deal_id, "")
        if not stored:
            raise gl.vm.UserError("[EXPECTED] deal not found")
        deal = json.loads(stored)
        if gl.message.sender_address.as_hex.lower() != deal["delegator"].lower():
            raise gl.vm.UserError("[EXPECTED] only the delegator can resolve a review")
        if deal["status"] != "review":
            raise gl.vm.UserError("[EXPECTED] deal is not under review")
        mandate = json.loads(self.mandates.get(deal["mandate_id"], "{}"))
        court_decision = json.loads(self.decisions.get(deal_id, "{}"))
        if release_funds:
            deal["status"] = "resolved_release"
            deal["outcome"] = "release"
            court_decision["court_effect"] = "continue"
            if mandate:
                mandate["status"] = "active"
                mandate["court_decision"] = "continue"
        else:
            deal["status"] = "resolved_refund"
            deal["outcome"] = "refund"
            court_decision["court_effect"] = "revoke"
            if mandate:
                mandate["revoked"] = True
                mandate["status"] = "revoked"
                mandate["court_decision"] = "revoke"
        court_decision["resolved_by"] = "delegator_review"
        self.decisions[deal_id] = json.dumps(court_decision)
        if mandate:
            self.mandates[deal["mandate_id"]] = json.dumps(mandate)
        self.deals[deal_id] = json.dumps(deal)

    # ---- Views ----

    @gl.public.view
    def get_deal(self, deal_id: str) -> str:
        return self.deals.get(deal_id, "")

    @gl.public.view
    def get_status(self, deal_id: str) -> str:
        stored = self.deals.get(deal_id, "")
        if not stored:
            return ""
        return json.loads(stored)["status"]

    @gl.public.view
    def get_mandate(self, mandate_id: str) -> str:
        return self.mandates.get(mandate_id, "")

    @gl.public.view
    def is_revoked(self, mandate_id: str) -> str:
        stored = self.mandates.get(mandate_id, "")
        if not stored:
            return ""
        return "true" if json.loads(stored)["revoked"] else "false"

    @gl.public.view
    def get_decision(self, deal_id: str) -> str:
        return self.decisions.get(deal_id, "")

    @gl.public.view
    def get_name(self) -> str:
        return self.name
