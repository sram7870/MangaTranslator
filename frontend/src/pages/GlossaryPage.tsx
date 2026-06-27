import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getGlossary } from "../services/api";
import GlossaryManager from "../components/glossary/GlossaryManager";

interface GlossaryEntry {
  id: string;
  term_original: string;
  term_translated: string;
  category: string;
}

export default function GlossaryPage() {
  const { projectId } = useParams();
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);

  useEffect(() => {
    if (!projectId) return;
    getGlossary(projectId).then(setEntries).catch(console.error);
  }, [projectId]);

  return (
    <main className="px-6 py-12">
      <section className="max-w-6xl mx-auto rounded-3xl border border-white/10 bg-slate-900/70 p-10 shadow-2xl shadow-slate-950/40">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Glossary</h1>
            <p className="mt-2 text-slate-300">Manage translated terms, character names, and story glossary.</p>
          </div>
        </div>

        <div className="mt-8">
          <GlossaryManager />
          {entries.length > 0 && (
            <div className="mt-6 space-y-3 text-slate-300">
              {entries.map((entry) => (
                <div key={entry.id} className="rounded-3xl border border-white/10 bg-slate-900/80 p-4">
                  <p className="font-semibold text-white">{entry.term_original}</p>
                  <p className="text-slate-400">Translated: {entry.term_translated}</p>
                  <p className="text-slate-400">Category: {entry.category}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
