# Loop 2 — Priority rubric: reflection

Score: v1 16/21 (76%) → v2 19/21 (90%), single run. Overall baseline 6/21 → 19/21. Prompt: `v2_priority_rubric.txt` (v1 + appended rubric block). Still one API call.

## 1. Where my engineering did the work
- Diagnosed that the written P1 rule ("system down, all users affected") let *scope wording* ("entire team of 85", "all 2000 users") trigger P1. Fix: a severity ladder, and "scope never turns a non-outage into P1". Cases 9, 13 fixed.
- Diagnosed tone and churn threats as an uncontrolled input. Fix: explicit "ignore tone, deadlines, threats" plus a "never existed → P4" gate. Case 11 fixed (now P4).
- Found that case 3 was a *spec conflict*, not a model error: the client's own text said "cosmetic = P4". Fix: "a cosmetic bug is P3". This is a client rule change and must be flagged.
- Kept explicit P1 overrides (security/PII, payroll/revenue) as regression guards for cases 5, 17, 19. All three still pass.
- One change per loop, so the +3 net is attributable to the rubric.

## 2. Where Claude's capability did the work
- Haiku applied a multi-level rubric reliably once it was stated, including the P1 overrides, with no examples.
- Case 6's multi-issue schema break disappeared. I did not target it, so I can't credit engineering. Could be the severity framing or run-to-run noise.

## 3. What surprised me
- A rule I added to fix one failure created two: the "nothing is broken → P4" gate probably pushed vague case 8 to P4, and case 21 moved to P2. Vague tickets are the zone where the rubric is weakest.
- The model was following my instructions literally, in both directions. Case 3 failed because the client's rule said so; case 8 plausibly failed because mine did.
- The old "cosmetic = P4" line stayed in the prompt and case 3 still passed. A latent contradiction that works today may not tomorrow.

## 4. What I'd tell a CTO (90 seconds)
"Two structural problems. First, the prompt invited the model to fill every field, so it invented entities: one copy-or-null rule fixed that. Second, priority was defined by how many users were mentioned, so loud tickets and big teams jumped to P1. I replaced that with a severity ladder and explicit overrides for security and payroll. Result: 29% to 90% on our 21-case suite, same model, still one call under the 5-second budget. Two vague tickets still wobble, and I'd validate on fresh tickets before promising 90% in production. I also changed one of your definitions (cosmetic bugs are P3), which you should confirm."

## Open items / not verified
- Single run; variance unmeasured. Rerun v2 2–3 times.
- 21 visible cases, rubric written after seeing the failures: overfitting risk. Hold-out set not yet built.
- Regressions: case 8 (P4, expected P3), case 21 (P2, expected P3).
- Contradictory old rule ("P4 = feature request or cosmetic issue") still in text.
- Confidence field was "high" on wrong priorities; not usable as a router yet.

## Next loop (loop 3 candidates)
1. Vague-ticket handling: "when severity cannot be determined from the text, P3, low confidence, null entities, ask for details" and reconcile with the P4 gate.
2. Remove the contradictory legacy rule.
3. Variance check plus hold-out tickets (E-cases in `../use-case-failure-map.md`).
