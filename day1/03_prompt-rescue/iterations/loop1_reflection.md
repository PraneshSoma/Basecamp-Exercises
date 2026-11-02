# Loop 1 — Entity contract: reflection

Score: baseline 6/21 (29%) → v1 16/21 (76%), single run. Prompt: `v1_entity_contract.txt`.

## 1. Where my engineering did the work
- I diagnosed "decorated values", not "hallucination". The model wasn't mostly inventing facts, it was writing descriptions (`"200+ (export feature), 3 (billing accuracy)"`, `"Unknown - General Platform"`) into fields that expected a value. So the fix was a **copy-or-null contract** per field, not a generic "don't hallucinate".
- I replaced the cause: "Always include all JSON fields even if empty" invited fill-in. Null and `[]` were made the explicit correct answer for a vague ticket.
- Per-field rules were targeted to observed failures: bare number for `affected_users`, literal codes only for `error_codes`, verbatim `product`, no ".0" on `version`.
- I changed one thing, so the gain (13 → 1 entity failures) can be attributed to it.

## 2. Where Claude's capability did the work
- Haiku followed the contract almost perfectly once it was explicit. I did not teach it to extract, only removed the pressure to fill.
- Cases 7 and 21 had their *priority* corrected without any priority change. Claude was already able to rate vague tickets P3; it was being pushed off by the forced-fill behaviour.
- The judge never failed a response by itself, so response quality was not a bottleneck, and I should not claim credit for it.

## 3. What surprised me
- Priority improved as a side effect of an entity-only change (7, 13, 21). Supports task interference, but it is two or three cases.
- Most of the "hallucination" was formatting. Part of the 29% → 76% gain depends on the harness's literal-span check (and its "CRM tool" vs "CRM platform" quirk), so it overstates real extraction quality for the client.
- I expected the contract to leave priority alone.

## 4. What I'd tell a CTO (90 seconds)
"The prompt asked for every field to be filled, so the model filled them, even when the ticket gave nothing. Most of the failures were values that were descriptions, not facts. One instruction change: copy exactly from the ticket or return null. Pass rate went from 29% to 76% on our 21-case suite with the same model and one API call. The remaining failures are all about priority and one multi-issue format break, which is a different cause and a separate fix."

## Open questions / not verified
- One run only. Variance not measured; rerun v1 2–3 times before quoting 76%.
- 21 cases are visible to me, so the result may not generalise. Need hold-out tickets (E-cases in `use-case-failure-map.md`).
- Entity completeness is not scored by the harness. A null-everywhere answer would also pass, so recall is untested.

## Next loop
Loop 2 — priority rubric. Remaining priority failures: case 3 (P4 for a cosmetic bug), 9 and 13 (P1 vs P2), 11 (P4 feature request escalated to P1). Case 6 (multi-issue array) goes to loop 3.
