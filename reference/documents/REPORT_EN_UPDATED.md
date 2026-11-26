# Group 7 Deliverable 3 — optimization companion report

Updated 2026-11-17 21:57 PST. This is an additive companion to Group 7_D3_Core_Evidence.zip and Group 7_D3_Representative_Evidence.zip. It does not replace any previous source, test result, screenshot, archive or video. Every new experiment has its own scope and denominator.

## Recorded outcomes

| Scope | Planned / recorded | PASS | FAIL | REVIEW | ERROR | Captured / planned turns |
|---|---:|---:|---:|---:|---:|---:|
| Original formal study, unchanged |114 /114|37|0|58|19|209 /252|
| model_extension_twice (independent) | 16 /16 |12|0|1|3|30 /40|
| timeout_retest_once (independent) | 2 /2 |0|0|0|2|1 /6|
| model_capture_validation_v 2 (independent) | 2 /2 |1|0|0|1|2 /6|
| New recorded generated Demo, excluded from primary 16 |2 /2|2|0|0|0|2 /2|

The original formal 114 stays **37 PASS,0 FAIL,58 REVIEW,19 ERROR**. It has 111 primary cases with prompt-submission evidence plus 3 independent linked coverage retests, not 114 silently rewritten primary submissions. Original completion without ERROR is 95/114(83.33%) and automatic pass is 37/114(32.46%). No local unit test or new extension/retest/Demo record is included in those figures.

The new primary model batch has 16 recorded app/case instances:4 selected coordinates×2 apps×2 independent repeats. It completed 13/16 without ERROR(81.25%), with 12/16 automatic PASS(75.00%),1 REVIEW and 3 ERROR. Thirty of 40 planned prompt turns were captured. Each error is a verified current-prompt foreground generation/completion timeout, with the original status retained. The three are Gemini memory once and Gemini fixed-flow twice.

## 3D model-based execution chain

The existing model has Input×Context×Output dimensions and a deterministic Cartesian candidate generator, truncated to 4 candidates per feature. The original 16 coordinate pool is preserved under generation/. It was not a remotely generated LLM result and it did not contain runnable prompts.

Four feasible coordinates were logically pre-reviewed and concretized:

| Generated ID | Function category | Executable scenario | Automatic validation |
|---|---|---|---|
|GEN-001|Factual/Domain|Fresh-chat Canada capital, city-name reply|Supported affirmative Ottawa assertion; contradictions do not pass|
|GEN-008|Memory|Dog preference, one 8+6 interruption, recall dog|Exact arithmetic 14 and explicit current recall; all 3 turns required|
|GEN-009|NLU|Translate “The cat is sleeping” into French|Whole declared affirmative French forms; defined negated/wrong-animal forms FAIL; unfamiliar prose REVIEW|
|GEN-013|Fixed Flow|Dog preference,14,Hello function,Canberra,dog recall|Arithmetic,Python AST,capital assertion and recall checked independently in one 5-turnchat|

`3D_MODEL_TRACEABILITY.csv` has 20 rows linking each model coordinate to its generated ID, executable data, prompts, expected behavior, oracle/script, app,repeat,attempt ID,source manifest and recorded outcome:16 primary extension rows,2 independent model-validation rows and 2 new Demo rows. `SOURCE_BATCH_MAP.csv` records actual implementation hashes by batch. The historical 19-case CSV and historical semantic evaluator remain unchanged. New catalog injection and separate extension oracles avoid altering the original study.

Validity review is **Codex AI logical pre-review, not a human signature**. `CANDIDATE_VALIDITY_PRE_REVIEW.csv` contains the reasons and blank human approval fields. The other 12 candidate coordinates remain unexecuted; some raw Cartesian combinations are not logically coherent without further preconditions. Therefore this is complete scripting for the four selected coordinates and all four functional categories, not exhaustive automation of the entire 16 candidate pool or every taxonomy combination. `7/8` selected app/case pairs have at least one complete capture across the primary batch and explicitly linked validation. The remaining pair is Gemini GEN-013: no completed 5-turnextensioncapture was obtained within the declared bounds.

## Capture repair and independent error retests

The initial Gemini GEN-009 REVIEW captured a correct French sentence followed by a separate “Gemini Live” promotion. Real XML shows a distinct FrameLayout collection item and ComposeView with exact heading, CTA, action-role button, package and window. Five regressions verify narrow structural exclusion and preserve the same words when present in actual answer text. The translation oracle and prompt did not change. The original REVIEW remains REVIEW.

A new independent translation capture succeeded with PASS. No promotion appeared in that run, so it confirms a complete fresh capture but does **not** demonstrate the exclusion branch firing on-device. The saved real XML exercises that branch in local regression tests. Each batch retains its own frozen native-response implementation.

Two original Gemini timeout cases,TC-FLOW-02 andAI-MEM-05,were each independently retested exactly once with their original whole-case data. Both remained ERROR with verified pending-generation controls. A separate generated-flow validation also remained ERROR on its second prompt. No fixed timeout extension, skipped completion guard, implicit prompt resend or status replacement was used. Visible correct partial text such as 14 does not establish completion while Stop remains active. The underlying backend/service cause remains unknown. HTTP204 proves device DNS/public reachability only.

`ERROR_RECOVERY_SUMMARY.md`, `INDEPENDENT_RETEST_RESULTS.csv` and the audit JSON files distinguish application generation/completion timeout, automation capture limitations and semantic model-answer FAIL. There are no new model-answer FAIL outcomes; that does not turn incomplete executions into successes.

## Repeatability and human review

`REPEATABILITY_DEMONSTRATION.csv` contains all 114 original records, not just a selected success: TestID, app,round,attemptID,UTCstart/end,duration,status,captured/planned turns,completeness and original evidence path. Both-app TC-FA-01 is the explicit representative in the actual viewer recording. The original 19 scenarios each have three recorded attempts per app. Every new selected scenario has two independently recorded primary attempts per app in `MODEL_REPEATABILITY.csv`, including its REVIEW/ERROR records.

`HUMAN_REVIEW_WORKSHEET.csv` contains **exactly 58 formal REVIEW rows**, with all prompt groups and full captured answers,expected criteria,AI advisory suggestions,evidence paths and hashes. Human Decision,Reviewer,Review Date,Reason andSignature remain blank. None is promoted to PASS. No completed human validity or semantic review is claimed.

## Rubric alignment and limits

The professor's supplied rubric awards 1 point for functional executable scripts/data plus automatic validation,1 for repeatable execution across scenarios,and 2 for completed 3D-model automation with Demo,executable scripts and results. `RUBRIC_EVIDENCE_CROSSWALK.csv` maps each criterion to the actual artifacts. Compared with the prior package,this addition supplies the missing coordinate-to-executable-to-Android-result chain and repeated runs of each selected model scenario.

There is stronger evidence for the scripting and repeatability criteria,and a direct execution/Demo chain for all four selected 3D coordinates. **A full 4/4 cannot be asserted by this agent.** The professor may treat 4/16 candidate coverage as partial model automation under the 2-pointcriterion,and Gemini's incomplete generated flow remains a reliability limit. Human signoff is still outstanding. The package makes those limits explicit instead of modifying expected standards or discarding failures.

## Demo and reproducibility

The new English large-text Demo combines actual local Chrome evidence-viewer recordings with actual new Android screenrecords and the prior real Appium clips. The viewer's generation button starts the actual Python generator,whose output files,stdout,exit status and measured 0.065-secondwall interval are retained. Viewer scenes and Android segments are labeled independent edited clips,not one continuous run. The log panel contains timestamped excerpts from the real execution log,not a terminal-window recording. The original 204-secondMP4 remains unchanged.

`reproduction/README.md` gives portable generation and execution commands. The latest extension source passes 197 local framework/regression tests,which are separate from Android results. Its 84 functions have mean approximate AST complexity 8.6 andmaximum 62; these are approximate branch counts,not certified McCabe values or evidence of semantic correctness. Recorded batch snapshots remain available for the exact older versions.

## Measured cost and preservation

The four new Android stages have recorded wall intervals totaling 1676.954 seconds(about 27.95 minutes),including setup,teardown and the new Demo captures. Stage times and recorded-case times are separate in `EXECUTION_COSTS.json`. Development,debugging,human-review labor and financial cost were not measured and remain null. Agent event timestamps are not presented as continuous labor hours; historical or paused gaps are not invented as work.

Only new artifacts are bundled. PreviousCore/Representative/fullarchive and oldDemo hashes are checked before final delivery. Screenshots/XML/logs in this package are privacy derivatives,with raw originals retained locally. `OPTIMIZATION_PRIVACY_PROVENANCE.json` maps raw/export hashes. Source and native-proof hashes reference raw bytes; consult that mapping after redaction. The final archive contains its own SHA-256 manifest and is verified after actual extraction.
