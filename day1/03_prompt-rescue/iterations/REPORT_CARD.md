# Prompt Rescue: report card

Model: Claude Haiku (fixed). Eval: the exercise's 21 visible cases, plus a 17-ticket red-team hold-out (`holdout_v1.json`, gold labels written by me).
Raw data: `v5_eval.json` (scratchpad) for v5; earlier runs from the notebook harness.

## 1. Progression on the 21 visible cases

| Version | What changed | Pass rate | Runs |
|---|---|---|---|
| Baseline | broken prompt | **6/21 = 29%** | 1 |
| v1 | entity copy-or-null contract | **16/21 = 76%** | 1 |
| v2 | priority severity rubric | **19/21 = 90%** | 2 (19, 19) |
| v3 | vague-ticket and workaround boundaries | **21/21 = 100%** | 2 (21, 21) |
| v4 | red-team mitigations (prompt only) | **19-20/21 = 90-95%** | 2 |
| v5 raw | v4 + exposure definition, response rules | **19/21 = 90%** | 1 |
| v5 + code wrapper | v5 prompt + validator, retry, lint | **17-18/21 = 81-86%** | 2 |
| v6 raw | v5 + "many users" P2 threshold, response rule about *when* someone acts | **20/21 = 95%** | 1 |
| v6 + code wrapper | v6 prompt + lint that no longer rejects "immediately"; lint-only failures return the output flagged for human review | **19-20/21 = 90-95%** | 2 (20, 19) |

## 2. Did it retrogress? Yes, in four places

| Step | Effect | Detail |
|---|---|---|
| v1 to v2 | net +3, but 2 cases regressed | cases 8 and 21 (vague tickets); fixed in v3 |
| v3 to v4 | **-1 to -2** | case 21 failed both runs; judge failed case 11 once |
| v3 to v5 raw | **-2** | case 21 (P2 instead of P3), case 11 (judge) |
| v3 to v5 + wrapper | **-3 to -4** | cases 17 and 19 returned no output after the retry (the response lint rejected them twice), plus 11 and 21 |
| v3 to v6 raw | **-1** | case 21 still P2 |
| v3 to v6 + wrapper | **-1 to -2** | case 11 judge failed on both runs; case 1 response lint; case 21 on one run |

Case 21 failed on every version after v3. A diagnostic run showed it is systematic (v3: P3 on 4/4 runs, v5: P2 on 4/4), not noise. My hypothesis is that v5 deleted v3's legacy "few users affected" anchor. v6 adds a "many users" threshold to P2, and case 21 then passed on only 1 of 3 v6 runs, so the hypothesis is only weakly supported and the case is still flaky.

## 3. The data point: failures before red-teaming

v3 scored 100% on the visible cases. On the 17 hold-out tickets built from the red-team's attack scenarios, with the markdown-fence problem scored separately:

| Check | v3 failures on the 17 attack tickets |
|---|---|
| Output is strict JSON (not fenced) | **17/17 fail (100%)** |
| Response breaks policy (time promises, refunds, security claims, placeholders) | **9/17 (53%)** |
| Wrong priority | **5/17 (29%)** |
| Entity not copied from the ticket | **3/17 (18%)** |
| Passing every check except fenced JSON | **7/17 (41%)** |

**One-line demo version:** "The prompt scored 100% on the 21 tickets we tuned on. Fresh, adversarial tickets exposed failures in 59% of cases, and 100% of outputs were fenced JSON that a strict parser rejects."

## 4. Hold-out by version (excluding the fenced-JSON check for raw prompts)

| Config | Pass | Notes |
|---|---|---|
| v3 raw | 7/17 = 41% | the "before red-team" baseline |
| v4 raw | 6/17 = 35% | the prompt-only mitigations did **not** help |
| v5 raw | 10/17 = 59% | |
| v5 + wrapper | 14/17 = 82% | strict JSON passes 15/17; the 3 failures are H14 (wrong priority) and H15 and H17 (no output, sent to a human) |
| v6 raw | 13/17 = 76% | fails: H2, H9 (ungrounded entity), H14 (priority and entities), H15 (response lint) |
| v6 + wrapper | 14/17 = 82% | strict JSON passes **17/17**; no missing outputs. Fails: H14 (wrong priority), H2 and H17 (response lint, returned but flagged for human review) |

v6 wrapper human-review flag: 0 missed escalations, 2 unneeded (H3, H14).

Human-review flag on the wrapper: 0 missed escalations, 2 unneeded ones (H3, H14).

## 5. Caveats you should state if you present this

- **The hold-out is no longer unseen for v4 and v5.** Its tickets came from the reviewers' attacks, and I wrote v4 and v5 after reading them. Only the v3 row is a clean "before" number.
- **The hold-out gold labels are mine,** and a few are policy calls (sandbox failure is P3).
- **The response lint is strict and my own choice.** It rejects words like "immediately" and "today". That drives the 53% response failures and the wrapper's no-output cases, so it overstates how often the model's answer was wrong.
- **Small samples:** 17 tickets, mostly one run each; a one-ticket difference is noise.
- **Baseline and v1 to v3 numbers** use the harness's lenient entity check (a value only has to appear in the ticket, never compared to gold).
