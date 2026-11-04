import { SiteHeader } from "@/components/SiteHeader";
import { EvaluationResults } from "@/components/EvaluationResults";

export default function BenchmarkPage() {
  return <div className="min-h-screen bg-[#fafafa] dark:bg-[#07090e] text-zinc-900 dark:text-zinc-100">
    <SiteHeader />
    <main className="max-w-5xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">System Evaluation & Benchmark Harness</h1>
      <EvaluationResults />
    </main>
  </div>;
}
