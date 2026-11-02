# Loop 3 — Vague-ticket and P2/P3 boundaries: reflection

Score: v2 19/21 (twice) → v3 21/21 (twice). Overall 6/21 → 21/21. Prompt: `v3_vague_boundary.txt` (v2 with the P2, P3 and P4 bullets edited). Still one API call per ticket.

## 1. Where my engineering did the work
- Traced both v2 regressions to my own rubric wording, not to the model. Case 8: "P4 = nothing is broken" caught a vague complaint. Case 21: "intermittent failures → P2" had no workaround criterion.
- Fixes were targeted: P4 only for an explicit new-capability request; an explicit P3 default (with low confidence, null entities, ask for details) when severity can't be determined; P2 requires data loss, production impact, or no workaround; "not blocking / workaround exists" → P3.
- Predicted the tension with case 9 (also intermittent, must stay P2) before the change, and made the P2 clause rely on "missing data / production" to separate the two. Case 9 still passes.
- Ran variance checks (v2 twice, v3 twice) instead of trusting a single run. That showed case 21 failing on both v2 runs (systematic) and v3 passing twice.

## 2. Where Claude's capability did the work
- Haiku applied a multi-condition rule ("degraded AND (data loss OR production OR no workaround)") correctly across all P2 cases without examples.
- It already behaved sensibly on vague tickets when not pushed by a wrong gate (v1 had them right).
- The response judge is lenient (defaults to PASS on error), so response quality is lightly tested; I can't credit engineering for it.

## 3. What surprised me
- Every regression so far came from a rule I added. The model followed my instructions literally, in both directions.
- Variance is real: v2 failed case 8 on one run, and case 11 on the judge on another, with identical prompts.
- The P2/P3 line is where the work is. Cases 9 and 21 share a surface feature (intermittent) and differ only in workaround and data loss.

## 4. What I'd tell a CTO (90 seconds)
"Three structural problems, one fix each, always measured. The prompt forced every field to be filled, so entities were invented: copy-or-null. Priority followed user counts and tone: a severity ladder with explicit overrides for security and payroll. The last gaps were boundary cases, vague complaints and intermittent issues with workarounds: a default and a workaround rule. 29% to 100% on our 21-case suite, same model, still one call. I would not promise 100% in production: I tuned on those cases, so I'd first validate on fresh tickets. I also changed three of your definitions (cosmetic bugs P3, vague tickets default to P3, P2 needs impact or no workaround), which you should confirm."

## Open items / not verified
- Overfitting: each edit followed the failing tickets; the case 21 clause mirrors that ticket's wording. No hold-out evaluation yet.
- Small sample: 2 runs × 21 cases. Entity recall not scored.
- Legacy rule "P4 = feature request or cosmetic issue" still in text, contradicting the rubric.
- Stricter P2 rule untested on P2 tickets that don't mention data loss, production, or workaround.
- Confidence calibration not checked beyond a few cases.
- Judge leniency means response quality is only lightly tested.

## Next steps
1. Hold-out set: 8–10 new tickets (prompt injection, empty ticket, PII, P2 without workaround mention, security-only, non-English, follow-up, duplicates). Run v3 and report separately.
2. Remove the legacy contradictory rule and re-validate.
3. Tier 1: iteration log write-up and a monitoring prompt; Tier 2: validator-gated retry.
