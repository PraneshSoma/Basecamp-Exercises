"""Evaluate prompts on the hold-out set and the 21 visible cases.

Usage (from day1/03_prompt-rescue):
    uv run --no-sync python iterations/run_v5_eval.py <out.json>
Never prints credentials. Uses the notebook's own harness cells for scoring.
"""
import base64
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v5_pipeline as pv  # noqa: E402

nb = json.load(open(HERE.parent / "Prompt_Rescue_solo.ipynb"))
g = {"__name__": "__main__"}
for i in (2, 5, 7):
    exec("".join(nb["cells"][i]["source"]), g)
client, MODEL = g["client"], g["MODEL"]
viin = g["_value_in_input"]

P = {n: (HERE / f).read_text() for n, f in
     [("v3", "v3_vague_boundary.txt"), ("v4", "v4_redteam_mitigations.txt"), ("v5", "v5_prompt.txt")]}
HOLD = json.load(open(HERE / "holdout_v1.json"))
for h in HOLD:
    if h["id"] == "H7":
        h["no_echo"] = ["evil.example"]
VIS = json.loads(base64.b64decode(re.search(r'_EVAL_CASES_B64 = "([^"]+)"', "".join(nb["cells"][7]["source"])).group(1)))["cases"]


def strict_ok(raw):
    try:
        return isinstance(json.loads(raw.strip()), dict)
    except Exception:
        return False


def run(config, prompt_name, ticket):
    """Return (parsed_or_None, meta) for a raw single call or the full pipeline."""
    if config == "raw":
        raw = g["run_single_prompt"](client, P[prompt_name], ticket)
        parsed, _ = g["parse_output"](raw)
        return parsed, {"strict_json": strict_ok(raw), "attempts": 1}
    parsed, meta = pv.process_ticket(client, MODEL, P[prompt_name], ticket, viin)
    meta["strict_json"] = parsed is not None
    return parsed, meta


def score_hold(h, parsed, meta):
    ok = parsed is not None
    resp = (parsed or {}).get("response", "") or ""
    ent = (parsed or {}).get("entities", {}) or {}
    c = {}
    c["priority"] = ok and (h["priority"] is None or str(parsed.get("priority")).upper() == h["priority"])
    c["grounded"] = ok and g["check_entities"](parsed, h["ticket"], None)[0]
    gold_ok = ok
    for k in ("affected_users", "version"):
        if k in h:
            v = ent.get(k)
            gold_ok = gold_ok and ((None if v in (None, "") else str(v)) == h[k])
    c["gold_entities"] = gold_ok
    c["response_lint"] = ok and not pv.lint_response(resp)
    c["no_echo"] = ok and not any(s.lower() in resp.lower() for s in h.get("no_echo", []))
    c["strict_json"] = bool(meta.get("strict_json"))
    return c


def hold_eval(config, name):
    rows = []
    for h in HOLD:
        parsed, meta = run(config, name, h["ticket"])
        c = score_hold(h, parsed, meta)
        rows.append({"id": h["id"], "pass": all(c.values()), "fails": [k for k, v in c.items() if not v],
                     "priority": (parsed or {}).get("priority"), "needs_human": meta.get("needs_human"),
                     "expect_human": h["expect_human"], "attempts": meta.get("attempts"),
                     "first_errors": meta.get("first_errors")})
    return rows


def vis_eval(config, name):
    rows = []
    for case in VIS:
        parsed, meta = run(config, name, case["input"])
        coh = None
        if case.get("audited_response") and parsed and parsed.get("response"):
            coh = g["judge_response"](client, case["input"], parsed.get("priority", ""), parsed["response"])[0]
        s = g["score_case"](parsed=parsed, parse_error=None if parsed else "invalid", input_text=case["input"],
                            gold_priority=case["gold_priority"], gold_entities=case["gold_entities"],
                            response_coherent=coh, audited=case.get("audited_response", False))
        lint = pv.lint_response((parsed or {}).get("response", ""))
        rows.append({"id": case["id"], "pass": s["pass"], "fails": [k for k, v in s["criteria"].items() if not v["pass"]],
                     "lint": lint, "attempts": meta.get("attempts"), "strict_json": meta.get("strict_json")})
    return rows


results = {}
for label, config, name in [("hold:v3-raw", "raw", "v3"), ("hold:v4-raw", "raw", "v4"),
                            ("hold:v5-raw", "raw", "v5"), ("hold:v5-pipeline", "pipeline", "v5")]:
    results[label] = hold_eval(config, name)
    print(label, sum(r["pass"] for r in results[label]), "/", len(HOLD), flush=True)
for label, config, name in [("vis:v5-raw", "raw", "v5"), ("vis:v5-pipeline-a", "pipeline", "v5"),
                            ("vis:v5-pipeline-b", "pipeline", "v5")]:
    results[label] = vis_eval(config, name)
    print(label, sum(r["pass"] for r in results[label]), "/", len(VIS), flush=True)
json.dump(results, open(sys.argv[1], "w"), indent=1)
print("DONE")
