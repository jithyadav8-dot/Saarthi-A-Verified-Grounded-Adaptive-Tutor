# Demonstrating Saarthi in three minutes

Start the API with the offline settings and open the frontend as described in the [README](../README.md). For a public demo use your own course material or the included original [physics notes](../src/ui/public/momentum-notes.md).

| Time | Action | Evidence the audience can inspect |
|---|---|---|
| 0:00–0:40 | On the homepage, download the sample notes, then choose **Upload notes** and select that file. | The source picker switches to the uploaded file. The new prompts come from sentences in that file. A judge can change a definition and upload again. |
| 0:40–1:20 | Enter “force” for the momentum prompt. Read the returned sentence, finish the round, then choose **Practice missed terms**. | Feedback names the exact term and cites the uploaded source. The next round contains only missed terms. These are exact-term recall exercises. |
| 1:20–2:00 | Open **Ask your course**, ask “What is the chain rule?”, and inspect the citations. Try an unrelated question with outside knowledge disabled. | The judge can inspect retrieved passages and see how the tutor handles questions beyond its material. |
| 2:00–3:00 | Open **Take adaptive practice** and answer one bundled question. Open **Inspect the evaluation**. | The separate adaptive bank updates BKT after graded practice. The evaluation includes question counts and the observed negative simulation result. |

The first two steps address assessment, grounding and personalization in one visible action sequence. Asking a judge to supply or modify the source makes the provenance claim testable. The last step shows the limits of the current learning evidence. These are reasons the experience could influence a technical assessment. The judges' actual opinions are unknown. See [rubric and sources](improvement-audit/HACKATHON_ANALYSIS.md).

Recall generation uses up to five distinct, explicitly defined English terms from indexed text. Unsupported passages produce an empty state. Grading accepts case, whitespace and leading articles, and compares the term with the source wording. The learner can practice these words without implying that a single recall establishes concept mastery. Replacing a source invalidates its changed cards. No hosted model or provider key is needed for this workflow with text notes.
