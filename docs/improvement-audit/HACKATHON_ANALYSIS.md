# Hackathon evidence and interpretation

Research date: November 5, 2026. The result is verified; the judges' causal reasons are unknown.

## Primary sources and access

- [Official Multimodal AI Hackathon 2026 overview](https://multimodal-ai-hackathon-2026-7.devpost.com/), [rules](https://multimodal-ai-hackathon-2026-7.devpost.com/rules) and [gallery](https://multimodal-ai-hackathon-2026-7.devpost.com/project-gallery).
- [Official problem-statement overview PDF](https://drive.google.com/file/d/1sPrF1CWyJMGk8c3JOwu08_sboeaAE5xc/view), linked from the event; its Track D link leads to [the three-page Track D brief](https://drive.google.com/file/d/1KlbSV3-WFrd3Cs9J59qpWtiWrAkb-DMM/view). Both PDFs were downloaded for read-only inspection; Track D page 3 was rendered and visually checked for rubric labels/weights.
- [Pramana submission](https://devpost.com/software/pramana-v7si9t) explicitly lists **Winner — 1st prize (Track D)**.
- [Saarthi submission](https://devpost.com/software/saarthi-l0esqt) was found. Its stated architecture overlaps substantially with Pramana: grounding, graphs, verification and adaptive learner modeling.
- [Pramana's linked YouTube demo](https://www.youtube.com/watch?v=63be_42pV3k) was identified, but the video could not be retrieved. **It was not watched.** Submission screenshots/text and implementation are not substitutes for observing the demo.
- No public judge scorecards or individual judging feedback were found in the accessed sources.

## Verified Track D requirements

The brief calls for an integrated tutor that ingests videos, textbooks and slides, links topics/subtopics/prerequisites to source locations, extracts image/diagram information, answers with inspectable cited excerpts, refuses unsupported answers and separates outside knowledge. Assessment requirements include source-scoped MCQ/short/numeric questions, answer verification, difficulty control, repetition management, feedback and weakness reporting. Personalization includes learner state after assessment/conversation and an intake/diagnostic. Evaluation calls for established RAG metrics, known-source/off-topic tests, and repeated-session simulated profiles. Optional extensions include revision aids, scheduling, audio and Indian-language support. Delivery includes software, documentation, evaluation and a 3–10 minute demonstration. [Official Track D brief, pages 1–3](https://drive.google.com/file/d/1KlbSV3-WFrd3Cs9J59qpWtiWrAkb-DMM/view).

| Official rubric category | Weight | Relevant evidence to show a judge |
|---|---:|---|
| Knowledge Base & Grounding | 20% | Multimodal content actually recovered; source passage opened; unsupported query refused |
| Assessment | 15% | Question/key verification and scoped feedback; repetition behavior |
| Personalization | 20% | Diagnostic → response → explainable mastery change → next appropriate activity |
| UX & Demo | 15% | Coherent complete workflow, understandable states and graceful failure |
| System Evaluation | 15% | Executed metrics, clear dataset/protocol, ablations and learning simulation |
| Technical | 15% | Working architecture, integration and defensible engineering choices |

Weights are transcribed from page 3 of the [official brief](https://drive.google.com/file/d/1KlbSV3-WFrd3Cs9J59qpWtiWrAkb-DMM/view). They are not reconstructed from project popularity or the winning entry.

## Hackathon judge perspective — interpretations, not scores

Pramana's inspected code connects source material, generated course assessments, learner evidence and source-backed lessons into a single product flow. Its evaluation/replay documentation also gives a judge concrete artifacts to inspect. Those properties align with the rubric's grounding, personalization, assessment and evaluation categories. This is a reasonable interpretation of requirement coverage.

Saarthi already addresses many of the same ideas. Its audited baseline has functioning retrieval, source inspection, a graph, BKT quizzes and simulations. The important gap is integration: an upload enriches retrieval while the default quiz remains a curated bank. Rich ingestion and verification modules are not uniformly connected to that main course workflow. This can make the demonstrated promise broader than the executed product.

**Hypothesis:** an integrated “upload → inspect evidence → answer quiz → explain mistake → personalized lesson” story may have made Pramana's rubric coverage easier to demonstrate. **Unknown:** whether that was decisive, how reliable either live demonstration was, what private tests judges ran, or the relative scores. The award does not prove every algorithm was better.

The repository snapshots examined here are not proven to be the exact competition-deadline commits. It would be unfair to retroactively attribute every current defect or fix to the original submissions.

## Senior AI engineer perspective

Pramana's strongest transferable choices are native-first slide extraction with selective vision, explicit source locators, course-connected assessment/remediation, and reproducible caches. Its additional learner parameters are hypotheses to calibrate, not inherently better science. Its runtime citation filtering is not semantic proof; verifier fallback independence and evaluation leakage weaken broad reliability claims. Lack of authenticated ownership, upload resource limits and durable jobs limits production readiness.

Saarthi's strengths include a modular hybrid retriever, backend-specific refusal calibration, graph edge evidence and a useful offline mode. The current improvement round addresses proven defects before adding model-heavy features: it preserves evidence through the UI, prevents answer retries from teaching the learner twice, and stops quiz planning from pretending the student learned.

Neither project has demonstrated real learning effectiveness in this audit. A publishable learning claim needs independently labeled content, calibrated assessment, a preregistered study design and learner outcomes with appropriate consent. Small synthetic simulations cannot substitute.

## What Saarthi should demonstrate next

1. Upload an owned slide fixture containing text, table, equation and notes; retrieve the recovered material and open its source.
2. Show a sourced answer and explain whether it is extractive, lexically checked or model-checked. Show refusal and a verifier outage.
3. Issue a quiz, answer once, retry the same attempt, and show unchanged mastery/history on retry.
4. Run a diagnostic and explain its observation-only update. Show a short quiz when the ready bank is exhausted.
5. Show the actual benchmark, including the negative adaptive result and unequal practice exposure.
6. State the curated-bank boundary and the next course-bank integration milestone.

This is a proposed honest demonstration sequence, not a claim that a new competition demo was recorded or submitted.
