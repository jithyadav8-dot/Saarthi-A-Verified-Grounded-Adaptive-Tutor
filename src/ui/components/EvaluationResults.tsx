"use client";

import { useCallback, useEffect, useState } from "react";
import { AblationResult, fetchAblationBenchmarks } from "@/lib/api";

export function EvaluationResults() {
  const [result, setResult] = useState<AblationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setResult(await fetchAblationBenchmarks());
    } catch (error) {
      setResult(null);
      setError(error instanceof Error ? error.message : "Evaluation service unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    let active = true;
    fetchAblationBenchmarks()
      .then(value => { if (active) setResult(value); })
      .catch(error => { if (active) setError(error instanceof Error ? error.message : "Evaluation unavailable."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return <section className="space-y-6" aria-busy={loading}>
    <div className="flex items-center justify-between gap-4">
      <p className="text-sm text-zinc-500">Simulated learners · fixed seed · equal learning rules</p>
      <button onClick={load} disabled={loading} className="rounded-lg border px-4 py-2">
        {loading ? "Running…" : "Run simulation"}
      </button>
    </div>
    {error && <p role="alert" className="text-red-600">{error} No results are available.</p>}
    {result && <>
      <p>{result.sample_size}. Difference in final simulated mastery: <strong>{result.net_gain_percentage}</strong> (percentage points).</p>
      <table className="w-full border-collapse text-left">
        <caption className="mb-3 text-left font-semibold">Mean simulated mastery by session</caption>
        <thead><tr><th className="p-2">Session</th><th>Random selection</th><th>Adaptive BKT</th></tr></thead>
        <tbody>{result.learning_curves.map(curve => <tr key={curve.session} className="border-t">
          <th className="p-2 font-normal">{curve.session}</th><td>{curve.random}%</td><td>{curve.adaptive}%</td>
        </tr>)}</tbody>
      </table>
      <p className="text-sm text-zinc-500">These synthetic results do not establish an improvement for real students. Statistical significance: {result.p_value ?? "Not measured"}.</p>
    </>}
    <div className="rounded-xl border p-5">
      <h2 className="font-semibold">Grounding evaluation</h2>
      <p className="mt-2">RAGAS metrics: Not measured. A labelled dataset and an executed evaluation are required before reporting quality scores.</p>
    </div>
  </section>;
}
