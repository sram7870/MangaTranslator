import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getTranslations } from "../services/api";
import BubbleEditor from "../components/translation/BubbleEditor";

interface TranslationEntry {
  id: string;
  original_text: string;
  translated_text: string;
}

export default function TranslationPage() {
  const { projectId } = useParams();
  const [translations, setTranslations] = useState<TranslationEntry[]>([]);

  useEffect(() => {
    if (!projectId) return;
    getTranslations(projectId)
      .then(setTranslations)
      .catch(console.error);
  }, [projectId]);

  return (
    <main className="px-6 py-12">
      <section className="max-w-6xl mx-auto rounded-3xl border border-white/10 bg-slate-900/70 p-10 shadow-2xl shadow-slate-950/40">
        <h1 className="text-3xl font-semibold">Translation Review</h1>
        <p className="mt-4 text-slate-300">Edit translations, override glossary terms, and review rendered text.</p>

        <div className="mt-8 space-y-6">
          {translations.length === 0 ? (
            <p className="text-slate-400">No translation entries yet. Start the pipeline to generate translations.</p>
          ) : (
            translations.map((entry) => (
              <BubbleEditor
                key={entry.id}
                original={entry.original_text}
                translation={entry.translated_text}
                onChange={(value) => console.log("Update translation", entry.id, value)}
              />
            ))
          )}
        </div>
      </section>
    </main>
  );
}
