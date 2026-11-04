"use client";
import { EvaluationResults } from "./EvaluationResults";

export function EvaluationAblationModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  if (!isOpen) return null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
    <div role="dialog" aria-modal="true" aria-labelledby="evaluation-title" className="max-h-[90vh] overflow-auto rounded-2xl bg-white dark:bg-[#0c111c] p-6 max-w-3xl w-full">
      <div className="flex justify-between mb-6">
        <h2 id="evaluation-title" className="text-xl font-bold">Evaluation & Simulation</h2>
        <button onClick={onClose} aria-label="Close evaluation">Close</button>
      </div>
      <EvaluationResults />
    </div>
  </div>;
}
