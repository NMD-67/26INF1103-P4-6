# Multi-condition compatibility classification

The AI returns interests_lifestyle, personality_values, relationship_goals and a reason.
GroqScorer validates these values before use. ScoreCalculator retains the existing
40/30/30 weighted overall score. CompatibilityClassifier, in Logic_Manager/Matching,
separately classifies the three saved category scores:

- Strong compatibility: interests >= 70 AND personality >= 70 AND goals >= 70.
- Moderate compatibility: all three >= 50, when the strong rule is not satisfied.
- Low compatibility: valid scores that satisfy neither rule.
- Not available: any category is missing or invalid.

These thresholds are project-defined heuristics, not scientific compatibility measures.
The rule prevents a high average masking low alignment in another category. For example,
100/100/40 produces an overall 82%, but Low compatibility because goals are below 50.
The category informs the user's decision; it does not automatically accept, reject or
hide a profile. The same rule applies in CLI and Telegram Find matches and View connections.
No additional AI call or database column is needed: the label is derived from stored scores.

ConsoleIO delegates classification to the Logic Manager; TelegramIO reuses the formatting.
Tests in ci/offline_tests.py cover thresholds, independent effects of all three fields,
invalid/missing scores, parsed AI output, and both interfaces. Run python ci/offline_tests.py.

## Phase 1 preservation
This is a newly documented rule. It does not prove preservation of a Phase 1 rule.
Compare with the original submitted rule and obtain/document instructor approval if this
replaces it, as required by section 7 of the Phase 2 brief. Do not claim approval until obtained.
