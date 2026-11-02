"""v5 code-side guard around the v5 prompt: strict parse, schema + grounding validation,
one validator-driven retry, response lint, and a human-review flag.

Max 2 sequential model calls per ticket (the retry only fires on a validator failure).
"""
import json
import re
import time

PRIORITIES = {"P1", "P2", "P3", "P4"}
CONFIDENCES = {"high", "medium", "low"}
ENTITY_KEYS = {"product", "version", "error_codes", "affected_users"}

# Things the customer response must never contain (policy: no commitments, no placeholders,
# no security-status claims).
FORBIDDEN_RESPONSE = [
    ("time_commitment", r"\b(within|in)\s+(the\s+next\s+)?(\d+|one|two|three|a few|several)\s*(minutes?|hours?|days?|business days?|weeks?)\b"),
    ("contact_time", r"\b(contact|reach out|respond|follow up|update|get back|call)\w*\b[^.]{0,40}\b(shortly|immediately|right away|today|tomorrow|soon|asap|by end of day)\b"),
    ("compensation", r"\b(refund|refunded|credit|credited|compensat\w+|reimburse\w*)\b"),
    ("placeholder", r"\[[^\]]{2,}\]"),
    ("root_cause", r"\broot cause\b"),
    ("phone", r"\b(call you|phone call|call back|contact you by phone)\b"),
    ("security_claim", r"(data is (safe|secure|protected)|not (been )?breached|no breach|have not experienced a breach|encrypt\w*)"),
    ("fix_promise", r"\b(we will fix|will be fixed|fix will|release date|next release|patch will)\b"),
]
FORBIDDEN_RE = [(n, re.compile(p, re.I)) for n, p in FORBIDDEN_RESPONSE]

# Tickets that must reach a human regardless of what the model says.
SECURITY_RE = re.compile(
    r"breach|leak|another (company|customer|tenant|user|organi[sz]ation)|someone else|unauthori[sz]ed|"
    r"compromis|credential|password|\bpii\b|gdpr|personal data|stolen|hacked|cross-tenant",
    re.I,
)

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def lint_response(text):
    return [name for name, rx in FORBIDDEN_RE if rx.search(text or "")]


def parse_strict(raw):
    """Strip an optional markdown fence, then require the WHOLE text to be one JSON object."""
    s = _FENCE_RE.sub("", (raw or "").strip()).strip()
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def validate(obj, ticket, value_in_input, lint=True):
    errs = []
    if obj is None:
        return ["output is not a single valid JSON object"]
    missing = {"priority", "entities", "response", "confidence"} - set(obj)
    if missing:
        return ["missing top-level fields: " + ", ".join(sorted(missing))]
    if obj["priority"] not in PRIORITIES:
        errs.append("priority must be one of P1,P2,P3,P4")
    if obj["confidence"] not in CONFIDENCES:
        errs.append("confidence must be high, medium or low")
    ent = obj["entities"]
    if not isinstance(ent, dict) or ENTITY_KEYS - set(ent):
        errs.append("entities must contain product, version, error_codes, affected_users")
    else:
        for k in ("product", "version"):
            v = ent[k]
            if v is not None and not isinstance(v, str):
                errs.append(f"{k} must be a string or null")
            elif v is not None and not value_in_input(v, ticket):
                errs.append(f"{k}={v!r} is not copied from the ticket; use null if not stated")
        codes = ent["error_codes"]
        if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
            errs.append("error_codes must be a list of strings")
        elif not all(value_in_input(c, ticket) for c in codes):
            errs.append("error_codes contains a value that is not quoted in the ticket")
        au = ent["affected_users"]
        if au is not None and not (isinstance(au, str) and re.fullmatch(r"\d+", au)):
            errs.append("affected_users must be digits-only text or null")
        elif au is not None and not value_in_input(au, ticket):
            errs.append("affected_users is not stated in the ticket; use null")
    if not isinstance(obj["response"], str) or not obj["response"].strip():
        errs.append("response must be a non-empty string")
    elif lint:
        bad = lint_response(obj["response"])
        if bad:
            errs.append("response contains forbidden content: " + ", ".join(bad))
    return errs


def _call(client, model, system_prompt, user_msg, max_tokens=1024):
    """One model call; try a '{' assistant prefill to force raw JSON, fall back if rejected."""
    msgs = [{"role": "user", "content": user_msg}, {"role": "assistant", "content": "{"}]
    prefill = True
    try:
        r = client.messages.create(model=model, max_tokens=max_tokens, system=system_prompt, messages=msgs)
    except Exception as e:  # prefill unsupported on some models/gateways
        if "prefill" in str(e).lower() or "assistant" in str(e).lower() or getattr(e, "status_code", None) == 400:
            prefill = False
            r = client.messages.create(model=model, max_tokens=max_tokens, system=system_prompt,
                                       messages=msgs[:1])
        else:
            raise
    text = r.content[0].text
    return ("{" + text) if prefill else text, prefill


def process_ticket(client, model, system_prompt, ticket, value_in_input):
    t0 = time.time()
    meta = {"attempts": 0, "first_errors": [], "prefill": None, "fenced_first": False}
    user_msg = ticket
    best = None
    fallback = None  # schema-valid output whose only problem is the response lint
    errs = ["not run"]
    for attempt in range(2):
        raw, prefill = _call(client, model, system_prompt, user_msg)
        meta["attempts"] += 1
        meta["prefill"] = prefill
        if attempt == 0:
            meta["fenced_first"] = raw.lstrip().startswith("```")
        obj = parse_strict(raw)
        errs = validate(obj, ticket, value_in_input)
        if attempt == 0:
            meta["first_errors"] = list(errs)
        if not errs:
            best = obj
            break
        if obj is not None and not validate(obj, ticket, value_in_input, lint=False):
            fallback = obj
        user_msg = (ticket + "\n\n---\nYour previous output was rejected by a validator:\n- "
                    + "\n- ".join(errs) + "\nReturn the corrected JSON object only.")
    meta["lint_failed"] = False
    if best is None and fallback is not None:
        best, meta["lint_failed"] = fallback, True
    meta["final_errors"] = errs
    meta["latency_s"] = round(time.time() - t0, 2)
    pri = (best or {}).get("priority")
    conf = (best or {}).get("confidence")
    meta["needs_human"] = bool(
        best is None or meta["lint_failed"] or pri == "P1" or conf == "low" or SECURITY_RE.search(ticket)
    )
    return best, meta
