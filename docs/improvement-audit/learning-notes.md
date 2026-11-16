# Learner and assessment audit notes

Baseline: `42b0b63cf0e8334597ff53d00b91995fe962cc73`, recorded before changes in `learning-baseline.json`.

## Design recorded before implementation

1. Preserve canonical four-parameter BKT and default values. Validate probabilities and forgetting inputs so invalid values cannot poison persistent mastery. Expose the existing diagnostic no-learning update through `LearnerModel.observe(..., learning_opportunity=False)` for service integration. Do not introduce uncalibrated item parameters or prerequisite evidence propagation.
2. Fix automatic quiz readiness: use real mastery throughout planning; select only concepts with available unseen verified questions and satisfied prerequisites. Stop at exhaustion. Manual concept practice remains an explicit override. Scheduling diversity may use a separate count, but must not change readiness or difficulty beliefs.
3. Make the existing simulation describe its assumptions and unequal effort honestly, and add paired uncertainty estimates rather than claiming statistical significance. Both arms retain their existing response and learning equations; difficulty remains unmodeled.

Evidence: a 25-item quiz with all eight concepts at 0.30 mastery selected 14 questions with unmet prerequisites. `build_quiz` selected an arbitrary remaining question when the chosen concept exhausted and incremented a local mastery copy by 0.05 for planned questions. `BKTParams` and `BKTConcept` accepted nonfinite/out-of-range inputs, and negative decay time increased mastery. These are reproduced in `tests/test_adaptive_integrity.py`.

Integration: default `/quiz` already uses `build_quiz`; `/answer` uses `LearnerModel.observe`; `/eval/ablation` uses `AblationSimulator`. Parent owns service issuance/replay protections and diagnostic grading integration. No new runtime dependencies or model calls are required.
