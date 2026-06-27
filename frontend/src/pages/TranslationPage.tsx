import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getTranslations,
  updateTranslation,
  getProjectPages,
  getPageImageUrl,
} from "../services/api";
import type { TranslationEntry, PageSummary } from "../types";

interface GroupedPage {
  page: PageSummary;
  entries: TranslationEntry[];
}

export default function TranslationPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [translations, setTranslations] = useState<TranslationEntry[]>([]);
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [activePage, setActivePage] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    Promise.all([
      getTranslations(projectId),
      getProjectPages(projectId),
    ])
      .then(([trans, pgs]) => {
        setTranslations(Array.isArray(trans) ? trans : []);
        setPages(Array.isArray(pgs) ? pgs : []);
        if (pgs.length > 0) setActivePage(pgs[0].id);
      })
      .catch(() => setError("Failed to load translations."));
  }, [projectId]);

  const handleChange = useCallback(
    (id: string, value: string) => {
      setTranslations((prev) =>
        prev.map((t) => (t.id === id ? { ...t, translated_text: value } : t))
      );
    },
    []
  );

  const handleSave = useCallback(
    async (entry: TranslationEntry) => {
      if (!projectId) return;
      setSaving((s) => ({ ...s, [entry.id]: true }));
      try {
        await updateTranslation(projectId, entry.id, entry.translated_text);
        setSaved((s) => ({ ...s, [entry.id]: true }));
        setTimeout(() => setSaved((s) => ({ ...s, [entry.id]: false })), 1500);
      } catch {
        setError("Failed to save translation.");
      } finally {
        setSaving((s) => ({ ...s, [entry.id]: false }));
      }
    },
    [projectId]
  );

  // Group translations by page
  const grouped: GroupedPage[] = pages.map((page) => ({
    page,
    entries: translations.filter((t) => t.page_id === page.id),
  }));

  const activePg = pages.find((p) => p.id === activePage);

  return (
    <main className="mx-auto max-w-7xl space-y-6">
      {/* Header */}
      <div className="rounded-[2rem] border border-[#1A4C39]/20 bg-[#f7efe0] p-6 shadow-[0_24px_90px_rgba(16,43,33,0.16)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#1A4C39]">
              Translation review
            </p>
            <h1 className="mt-1 text-3xl font-semibold text-[#102b21]">Edit Translations</h1>
          </div>
          <Link
            to={`/projects/${projectId}`}
            className="rounded-2xl border border-[#1A4C39]/20 bg-[#fdf8ee] px-4 py-2 text-sm font-semibold text-[#1A4C39] hover:bg-[#efe3c9]"
          >
            ← Back to Project
          </Link>
        </div>
        {error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}
      </div>

      {translations.length === 0 ? (
        <div className="rounded-[1.5rem] border border-[#1A4C39]/20 bg-[#fdf8ee] p-10 text-center text-[#1A4C39]">
          <p className="text-lg font-medium">No translations yet.</p>
          <p className="mt-2 text-sm text-[#1A4C39]/70">
            Start the translation pipeline from the project page first.
          </p>
          <Link
            to={`/projects/${projectId}`}
            className="mt-4 inline-block rounded-2xl bg-[#1A4C39] px-5 py-2 text-sm font-semibold text-[#E5DECA]"
          >
            Go to Project
          </Link>
        </div>
      ) : (
        <div className="flex gap-4">
          {/* Page selector sidebar */}
          <aside className="hidden w-44 shrink-0 lg:block">
            <div className="sticky top-24 rounded-[1.5rem] border border-[#1A4C39]/20 bg-[#fdf8ee] p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#1A4C39]/60">
                Pages
              </p>
              {pages.map((page) => (
                <button
                  key={page.id}
                  onClick={() => setActivePage(page.id)}
                  className={`mb-1 w-full rounded-xl px-3 py-2 text-left text-sm font-medium transition ${
                    activePage === page.id
                      ? "bg-[#1A4C39] text-[#E5DECA]"
                      : "text-[#1A4C39] hover:bg-[#efe3c9]"
                  }`}
                >
                  Page {page.page_number}
                  {page.status === "done" && (
                    <span className="ml-1 text-xs opacity-60">✓</span>
                  )}
                </button>
              ))}
            </div>
          </aside>

          {/* Main content */}
          <div className="min-w-0 flex-1 space-y-4">
            {grouped
              .filter((g) => !activePage || g.page.id === activePage)
              .map(({ page, entries }) => (
                <section
                  key={page.id}
                  className="rounded-[1.5rem] border border-[#1A4C39]/20 bg-[#fdf8ee] overflow-hidden"
                >
                  {/* Page header */}
                  <div className="flex items-center justify-between border-b border-[#1A4C39]/10 bg-[#f0e8d5] px-5 py-3">
                    <p className="font-semibold text-[#102b21]">
                      Page {page.page_number}
                    </p>
                    <span className="text-xs text-[#1A4C39]/60 capitalize">
                      {page.status}
                    </span>
                  </div>

                  <div className="grid gap-6 p-5 lg:grid-cols-[1fr_1fr]">
                    {/* Page image preview */}
                    <div className="overflow-hidden rounded-xl bg-[#102b21]">
                      {page.translated_path || page.original_path ? (
                        <img
                          src={getPageImageUrl(
                            projectId!,
                            page.id,
                            page.translated_path ? "translated" : "original"
                          )}
                          alt={`Page ${page.page_number}`}
                          className="w-full object-contain"
                        />
                      ) : (
                        <div className="flex h-48 items-center justify-center text-[#E5DECA]/50 text-sm">
                          Image not available
                        </div>
                      )}
                    </div>

                    {/* Translation entries */}
                    <div className="space-y-3">
                      {entries.length === 0 ? (
                        <p className="text-sm text-[#1A4C39]/60 italic">
                          No speech bubbles detected on this page.
                        </p>
                      ) : (
                        entries.map((entry) => (
                          <div
                            key={entry.id}
                            className="rounded-xl border border-[#1A4C39]/15 bg-[#f7efe0] p-3"
                          >
                            <p className="text-xs font-medium text-[#1A4C39]/60 uppercase tracking-wider mb-1">
                              Bubble {entry.bubble_index + 1} • Original
                            </p>
                            <p className="text-sm text-[#102b21] mb-2 font-medium">
                              {entry.original_text || <em className="opacity-50">empty</em>}
                            </p>
                            <p className="text-xs font-medium text-[#1A4C39]/60 uppercase tracking-wider mb-1">
                              Translation
                            </p>
                            <textarea
                              value={entry.translated_text}
                              onChange={(e) => handleChange(entry.id, e.target.value)}
                              onBlur={() => handleSave(entry)}
                              rows={3}
                              className="w-full rounded-lg border border-[#1A4C39]/20 bg-white px-3 py-2 text-sm text-[#102b21] outline-none focus:border-[#1A4C39] resize-none"
                            />
                            <div className="mt-2 flex items-center justify-between">
                              <span className="text-xs text-[#1A4C39]/40">
                                {entry.w}×{entry.h}px @ ({entry.x},{entry.y})
                              </span>
                              <button
                                onClick={() => handleSave(entry)}
                                disabled={saving[entry.id]}
                                className="rounded-lg bg-[#1A4C39] px-3 py-1 text-xs font-semibold text-[#E5DECA] disabled:opacity-50"
                              >
                                {saving[entry.id]
                                  ? "Saving…"
                                  : saved[entry.id]
                                  ? "✓ Saved"
                                  : "Save"}
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </section>
              ))}
          </div>
        </div>
      )}
    </main>
  );
}
