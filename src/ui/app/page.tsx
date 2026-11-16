import Link from "next/link";
import { ArrowUpRight, MessageSquare, GitBranch, Brain, ChartColumn } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SourcePractice } from "@/components/SourcePractice";

const tools = [
  { href: "/chat", title: "Ask your course", detail: "Follow an answer back to its page, slide or lecture timestamp.", Icon: MessageSquare },
  { href: "/graph", title: "Explore prerequisites", detail: "See how concepts connect and which foundations to review.", Icon: GitBranch },
  { href: "/quiz", title: "Take adaptive practice", detail: "Use the curated bank to practice at your current mastery level.", Icon: Brain },
  { href: "/benchmark", title: "Inspect the evaluation", detail: "Compare simulated outcomes, practice counts and uncertainty.", Icon: ChartColumn },
];

export default function LandingPage() {
  return <div className="min-h-screen bg-[#f4f5f0] text-slate-950 dark:bg-[#0b1016] dark:text-slate-100">
    <SiteHeader/>
    <main className="mx-auto max-w-7xl px-5 pb-16 sm:px-10">
      <div className="grid items-center gap-10 py-12 lg:grid-cols-[.9fr_1.1fr] lg:gap-16 lg:py-20">
        <div>
          <h1 className="max-w-lg text-5xl font-bold leading-[1.03] tracking-tight sm:text-6xl">Turn your notes into practice.</h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-slate-600 dark:text-slate-300">Try a term from the sample slides, or upload your own notes. Recall the missing term, check the original sentence and practice what you missed.</p>
          <a className="mt-5 inline-block text-sm font-semibold underline underline-offset-4" href="/momentum-notes.md" download>Download sample physics notes</a>
        </div>
        <SourcePractice/>
      </div>
      <section className="border-t border-slate-300 pt-7 dark:border-slate-700"><h2 className="mb-5 text-2xl font-semibold tracking-tight">Keep studying</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{tools.map(({href,title,detail,Icon}) =>
          <Link href={href} key={href} className="group rounded-2xl border border-slate-300 bg-white p-5 transition hover:border-indigo-500 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex justify-between text-indigo-600 dark:text-indigo-300"><Icon size={22}/><ArrowUpRight size={17}/></div>
            <h3 className="mb-2 mt-5 font-semibold">{title}</h3><p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{detail}</p>
          </Link>)}</div>
      </section>
    </main>
  </div>;
}
