"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, BookOpen, RotateCcw, Upload } from "lucide-react";
import { checkRecall, listPracticeSources, loadRecallCards, uploadCourseFiles, type RecallCard, type RecallFeedback } from "@/lib/api";

export function SourcePractice() {
  const [sources, setSources] = useState<string[]>([]);
  const [source, setSource] = useState("");
  const [cards, setCards] = useState<RecallCard[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<RecallFeedback | null>(null);
  const [missed, setMissed] = useState<RecallCard[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const file = useRef<HTMLInputElement>(null);
  const answerBox = useRef<HTMLInputElement>(null);
  const card = cards[index];

  function begin(items: RecallCard[]) {
    setCards(items); setIndex(0); setAnswer(""); setFeedback(null); setMissed([]);
  }

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const { sources: names } = await listPracticeSources();
        const name = names.includes("ML_Slides_L2") ? "ML_Slides_L2" : names[0];
        const items = name ? (await loadRecallCards(name)).cards : [];
        if (active) { setSources(names); setSource(name || ""); begin(items); }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "Could not load sources."); }
      finally { if (active) setBusy(false); }
    }
    void load();
    return () => { active = false; };
  }, [reload]);

  async function select(name: string, upload?: File) {
    setBusy(true); setError(""); begin([]); setSource(name);
    try {
      if (upload) {
        const result = await uploadCourseFiles([upload]);
        name = result.sample_units[0]?.source_id || name;
        setSources(current => [...new Set([...current, name])].sort());
        setSource(name);
      }
      begin((await loadRecallCards(name)).cards);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not read this source."); }
    finally { setBusy(false); }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!answer.trim() || !card || feedback || busy) return;
    setBusy(true); setError("");
    try {
      const result = await checkRecall(source, card.item_id, answer);
      setFeedback(result);
      if (!result.matches) setMissed(previous => [...previous, card]);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not check this answer."); }
    finally { setBusy(false); }
  }

  const button = "rounded-xl bg-indigo-700 px-4 py-2.5 font-semibold text-sm text-white hover:bg-indigo-800 disabled:opacity-50";
  return <section id="practice" aria-labelledby="practice-title" className="rounded-3xl border border-indigo-200 bg-white p-5 text-slate-900 shadow-xl shadow-indigo-950/10 sm:p-8 dark:border-slate-700 dark:bg-slate-900 dark:text-white">
    <div className="mb-5 flex items-center gap-3"><BookOpen aria-hidden="true" className="text-indigo-500"/><h2 id="practice-title" className="text-2xl font-semibold tracking-tight">Source practice</h2></div>
    <div className="flex flex-wrap items-end gap-3">
      <label className="min-w-0 flex-1 text-xs font-semibold">Course source
        <select value={source} disabled={busy || !sources.length} onChange={e => void select(e.target.value)}
          className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-transparent px-2 py-2 text-sm dark:border-slate-600 dark:bg-slate-900">
          {!sources.length && <option value="">No source selected</option>}
          {sources.map(name => <option key={name}>{name}</option>)}
        </select>
      </label>
      <button type="button" disabled={busy} onClick={() => file.current?.click()} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold dark:border-slate-600"><Upload size={15}/>Upload notes</button>
      <input aria-label="Upload course notes" type="file" accept=".md,.txt,.pdf,.pptx" ref={file} hidden onChange={e => {
        const chosen = e.target.files?.[0]; e.target.value = ""; if (chosen) void select(chosen.name, chosen);
      }}/>
    </div>
    <div className="mt-5 border-t border-slate-200 pt-5 dark:border-slate-700" aria-busy={busy}>
      {error && <div role="alert" className="mb-4"><p>{error}</p><button disabled={busy} className="mt-2 underline" onClick={() => {
        if (source && sources.includes(source)) void select(source);
        else { setError(""); setBusy(true); setReload(n => n+1); }
      }}>Reload practice</button></div>}
      {busy && <p role="status" className="text-sm">Working with your source…</p>}
      {card && <form onSubmit={submit}>
        <p className="mb-2 text-xs font-semibold text-indigo-700 dark:text-indigo-300">{card.location} · Recall {index+1} of {cards.length}</p>
        <p className="mb-4 text-lg leading-relaxed">{card.prompt}</p>
        <label className="block text-sm font-medium" htmlFor="recall-term">Which term completes the source sentence?</label>
        <div className="mt-2 flex flex-wrap gap-2"><input id="recall-term" ref={answerBox} maxLength={256} autoComplete="off" disabled={busy || !!feedback}
          value={answer} onChange={e => setAnswer(e.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-600"/>
          {!feedback && <button className={button} disabled={busy || !answer.trim()}>Check answer</button>}</div>
      </form>}
      {feedback && <div aria-live="polite" className="mt-4 rounded-xl bg-indigo-50 p-4 dark:bg-slate-800">
        <strong>{feedback.matches ? "You recalled the source term." : "The source uses “" + feedback.term + "”."}</strong>
        <blockquote className="my-3 border-l-2 border-indigo-400 pl-3">{feedback.citation.excerpt}</blockquote>
        <p className="break-words text-xs">{feedback.citation.source_id} · {feedback.citation.label}</p>
        <button className="mt-4 inline-flex items-center gap-2 text-sm font-semibold underline" onClick={() => {
          setIndex(index+1); setFeedback(null); setAnswer(""); requestAnimationFrame(() => answerBox.current?.focus());
        }}>{index+1 === cards.length ? "Finish round" : "Next question"} <ArrowRight size={14}/></button>
      </div>}
      {!busy && !error && !card && (cards.length ? <div aria-live="polite"><h3 className="text-lg font-semibold">Round complete</h3>
        <p className="my-2">{cards.length-missed.length} of {cards.length} source terms recalled.</p>
        <button className={button} onClick={() => begin(missed.length ? missed : cards)}><RotateCcw size={14} className="mr-2 inline"/>{missed.length ? "Practice missed terms" : "Practice again"}</button>
      </div> : <p>No suitable definition sentences found. Choose another source or upload notes with a definition such as “Momentum equals mass multiplied by velocity.”</p>)}
    </div>
  </section>;
}
