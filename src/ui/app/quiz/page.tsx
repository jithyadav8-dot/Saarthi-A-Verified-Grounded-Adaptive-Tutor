"use client";

import React, { useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { LearnerModelArena } from "@/components/LearnerModelArena";
import {
  Brain,
  ShieldCheck,
  Calculator,
  Activity,
  Award,
  RotateCcw,
  Sparkles,
  HelpCircle,
  FileCheck2,
  Sliders,
  Settings2,
} from "lucide-react";
import { ConceptNode, Question } from "@/lib/mockData";
import {
  fetchAdaptiveQuiz,
  submitStudentAnswer,
  triggerDiagnostic,
  fetchStudentMastery,
  fetchKnowledgeGraph,
} from "@/lib/api";

export default function QuizPage() {
  const [concepts, setConcepts] = useState<ConceptNode[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [nextRecommendation, setNextRecommendation] = useState<string | null>(null);

  // User Quiz Customization Controls
  const [selectedQuestionCount, setSelectedQuestionCount] = useState<number>(5);
  const [selectedDifficulty, setSelectedDifficulty] = useState<number | null>(null); // null = Adaptive BKT
  const [selectedConceptFilter, setSelectedConceptFilter] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [quizError, setQuizError] = useState<string | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(true);

  React.useEffect(() => {
    async function loadLiveQuiz() {
      try {
        const [graphRes, masteryRes, quizRes] = await Promise.all([
          fetchKnowledgeGraph(),
          fetchStudentMastery("s1"),
          fetchAdaptiveQuiz("s1", 5),
        ]);

        if (graphRes.nodes && graphRes.nodes.length > 0) {
          const liveNodes: ConceptNode[] = graphRes.nodes.map((n) => {
            const matched = masteryRes.board?.find((b) => b.concept_id === n.id);
            const m = matched?.mastery ?? 0;
            const mappedStatus: "mastered" | "learning" | "weak" | "unvisited" =
              !matched ? "unvisited" : m >= 0.7 ? "mastered" : m < 0.4 ? "weak" : "learning";
            return {
              concept_id: n.id,
              name: n.name,
              topic: n.topic,
              prerequisites: n.prerequisites,
              evidence_units: n.evidence_units,
              mastery: m,
              masteryKnown: Boolean(matched),
              status: mappedStatus,
              evidenceCount: n.evidence_count,
              description: n.description,
              keyTakeaways: n.keyTakeaways,
            };
          });
          setConcepts(liveNodes);
        }

        if (quizRes.questions) {
          const formatted: Question[] = quizRes.questions.map((q) => ({
            q_id: q.q_id,
            concept_id: q.concept_id,
            topic: q.topic,
            source_location: q.source_location,
            difficulty: q.difficulty,
            type: q.type,
            stem: q.stem,
            options: q.options || [],
            answer: "",
            explanation: "",
            verified: q.verified,
            verifier_agreement: q.verifier_agreement ?? 0,
            sympy_verified: q.sympy_verified === true,
          }));
          setQuestions(formatted);
          setCurrentQuestionIndex(0);
        }
      } catch (err) {
        setQuizError(err instanceof Error ? err.message : "Assessment service unavailable.");
      } finally {
        setIsInitialLoading(false);
      }
    }
    loadLiveQuiz();
  }, []);

  const activeQuestion: Question = questions[currentQuestionIndex];

  const handleGenerateCustomQuiz = async () => {
    setIsGenerating(true);
    setQuizError(null);
    try {
      const quizRes = await fetchAdaptiveQuiz(
        "s1",
        selectedQuestionCount,
        selectedDifficulty === null ? undefined : selectedDifficulty,
        selectedConceptFilter || undefined
      );
      if (quizRes.questions) {
        const formatted: Question[] = quizRes.questions.map((q) => ({
          q_id: q.q_id,
          concept_id: q.concept_id,
          topic: q.topic,
          source_location: q.source_location,
          difficulty: q.difficulty,
          type: q.type,
          stem: q.stem,
          options: q.options || [],
          answer: "",
          explanation: "",
          verified: q.verified,
          verifier_agreement: q.verifier_agreement ?? 0,
          sympy_verified: q.sympy_verified === true,
        }));
        setQuestions(formatted);
        setCurrentQuestionIndex(0);
      }
    } catch (err) {
      setQuizError(err instanceof Error ? err.message : "Quiz generation failed.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAnswerSubmitted = async (chosenOption: string) => {
    try {
      const res = await submitStudentAnswer(
        "s1",
        activeQuestion.q_id,
        chosenOption
      );
      setNextRecommendation(`Next recommended concept: ${res.next_concept} (Difficulty ${res.next_difficulty})`);

      setConcepts((prev) =>
        prev.map((c) => {
          if (c.concept_id === res.concept_id || c.concept_id === activeQuestion.concept_id) {
            const mappedStatus: "mastered" | "learning" | "weak" | "unvisited" =
              res.new_mastery >= 0.7 ? "mastered" : res.new_mastery < 0.4 ? "weak" : "learning";
            return {
              ...c,
              mastery: res.new_mastery,
              masteryKnown: true,
              status: mappedStatus,
            };
          }
          return c;
        })
      );

      return {
        correct: res.correct,
        explanation: res.explanation || `Grounded response evaluated for ${activeQuestion.topic}.`,
        correct_answer: res.correct_answer,
      };
    } catch (err) {
      throw err;
    }
  };

  const handleNextQuestion = () => {
    setCurrentQuestionIndex((prev) => (prev + 1) % questions.length);
  };

  const handlePrevQuestion = () => {
    setCurrentQuestionIndex((prev) => (prev > 0 ? prev - 1 : 0));
  };

  const handleRunDiagnostic = async () => {
    try {
      const res = await triggerDiagnostic("s1");
      setQuestions(res.questions.map(q => ({ ...q, answer: "", explanation: "" })));
      setCurrentQuestionIndex(0);
      setQuizError(null);
    } catch (err) {
      setQuizError(err instanceof Error ? err.message : "Diagnostic unavailable.");
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#fafafa] dark:bg-[#07090e] text-zinc-900 dark:text-zinc-100">
      <SiteHeader />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col">
        {quizError && <p role="alert">{quizError}</p>}
        {/* Page Title */}
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-zinc-200 dark:border-white/[0.08] mb-6">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
                Adaptive Assessment & Learner Model Arena
              </h1>
              <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                Curated Assessment
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
              Practice with the bundled question bank and feedback from the learner model.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRunDiagnostic}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-white dark:bg-white/[0.06] border border-zinc-200 dark:border-white/[0.1] hover:bg-zinc-100 dark:hover:bg-white/[0.1] transition-all cursor-pointer shadow-sm"
            >
              <Activity className="w-3.5 h-3.5 text-indigo-500" />
              <span>Run Diagnostic Test</span>
            </button>
          </div>
        </div>

        {/* Quiz Configuration Toolbar */}
        <div className="mb-6 p-4 rounded-2xl bg-white dark:bg-[#0c111c] border border-zinc-200 dark:border-white/[0.08] shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4 sm:gap-6">
            {/* 1. Question Count Selection */}
            <div>
              <span className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1.5">
                Number of Questions
              </span>
              <div className="flex items-center gap-1.5">
                {[3, 5, 8, 10, 15].map((cnt) => (
                  <button
                    key={cnt}
                    type="button"
                    onClick={() => setSelectedQuestionCount(cnt)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                      selectedQuestionCount === cnt
                        ? "bg-indigo-600 text-white shadow-sm ring-1 ring-indigo-500"
                        : "bg-zinc-100 dark:bg-white/[0.05] text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-white/[0.1]"
                    }`}
                  >
                    {cnt} Qs
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Difficulty Level Selection */}
            <div>
              <span className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1.5">
                Difficulty Level
              </span>
              <select
                value={selectedDifficulty === null ? "adaptive" : selectedDifficulty}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedDifficulty(val === "adaptive" ? null : parseInt(val));
                }}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 dark:bg-[#161c2b] border border-zinc-200 dark:border-white/[0.1] text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
              >
                <option value="adaptive">Dynamic Adaptive (BKT Mastered)</option>
                <option value="1">Level 1 - Introductory & Axioms</option>
                <option value="2">Level 2 - Foundational Concepts</option>
                <option value="3">Level 3 - Intermediate Application</option>
                <option value="4">Level 4 - Advanced Optimization</option>
                <option value="5">Level 5 - Expert Derivations & Proofs</option>
              </select>
            </div>

            {/* 3. Target Topic Selection */}
            <div>
              <span className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-1.5">
                Concept Target
              </span>
              <select
                value={selectedConceptFilter || "all"}
                onChange={(e) => {
                  const val = e.target.value;
                  setSelectedConceptFilter(val === "all" ? null : val);
                }}
                className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 dark:bg-[#161c2b] border border-zinc-200 dark:border-white/[0.1] text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer max-w-[220px]"
              >
                <option value="all">All Concepts (Curriculum-wide)</option>
                {concepts.map((c) => (
                  <option key={c.concept_id} value={c.concept_id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Action Trigger */}
          <button
            onClick={handleGenerateCustomQuiz}
            disabled={isGenerating}
            className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer shadow-sm shrink-0"
          >
            <Sparkles className={`w-3.5 h-3.5 ${isGenerating ? "animate-spin" : ""}`} />
            <span>{isGenerating ? "Generating..." : "Generate Custom Quiz"}</span>
          </button>
        </div>

        {/* 2-Pane Assessment Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-[600px]">
          
          {/* Left: Active Question Arena (7 cols) */}
          <div className="lg:col-span-7 h-full">
            {activeQuestion ? <LearnerModelArena
              key={activeQuestion.q_id}
              concepts={concepts}
              activeQuestion={activeQuestion}
              questionIndex={currentQuestionIndex}
              totalQuestions={questions.length}
              onAnswerSubmitted={handleAnswerSubmitted}
              onNextQuestion={handleNextQuestion}
              onPrevQuestion={handlePrevQuestion}
            /> : <div aria-live="polite" className="p-6">
              {isInitialLoading || isGenerating ? "Loading assessment questions..." :
                "No questions are available for this selection. Change the filters or generate another quiz."}
            </div>}
          </div>

          {/* Right: BKT Theory & Verification Audit Trail (5 cols) */}
          {activeQuestion && <div className="lg:col-span-5 h-full flex flex-col bg-white dark:bg-[#0c111c] border border-zinc-200 dark:border-white/[0.08] rounded-2xl p-6 shadow-sm">
            
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200/80 dark:border-white/[0.06] mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-zinc-500 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                Assessment Provenance
              </span>
              <span className="text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
                Bundled question bank
              </span>
            </div>

            {/* Audit breakdown */}
            <div className="space-y-3 mb-6 text-xs">
              <div className="p-3 rounded-xl bg-zinc-50 dark:bg-white/[0.02] border border-zinc-200/80 dark:border-white/[0.06]">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-zinc-900 dark:text-white">
                    Question source
                  </span>
                  <span className="text-xs font-medium text-emerald-500">Curated example</span>
                </div>
                <p className="text-zinc-600 dark:text-zinc-400 text-xs leading-relaxed">
                  Bundled assessment item for <strong>{activeQuestion.topic}</strong>. Uploading material does not automatically generate new quiz items.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-zinc-50 dark:bg-white/[0.02] border border-zinc-200/80 dark:border-white/[0.06]">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-zinc-900 dark:text-white">
                    Recorded metadata
                  </span>
                  <span className="text-xs font-medium text-emerald-500">Bank declaration</span>
                </div>
                <p className="text-zinc-600 dark:text-zinc-400 text-xs leading-relaxed">
                  The question bank records an agreement value of {Math.round(activeQuestion.verifier_agreement * 100)}%. Agreement does not guarantee correctness.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-zinc-50 dark:bg-white/[0.02] border border-zinc-200/80 dark:border-white/[0.06]">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-zinc-900 dark:text-white">
                    Executed math check
                  </span>
                  <span className="text-xs font-medium text-teal-500">
                    Not recorded
                  </span>
                </div>
                <p className="text-zinc-600 dark:text-zinc-400 text-xs leading-relaxed">
                  No executed math-verification record is attached to this question.
                </p>
              </div>
            </div>

          </div>}

        </div>
      </main>
    </div>
  );
}
