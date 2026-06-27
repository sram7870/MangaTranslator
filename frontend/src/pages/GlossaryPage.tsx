import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getGlossary, updateGlossaryEntry, getCharacters, updateCharacter } from "../services/api";
import type { GlossaryEntry, Character } from "../types";

type Tab = "glossary" | "characters";

export default function GlossaryPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [tab, setTab] = useState<Tab>("glossary");
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [editingGlossary, setEditingGlossary] = useState<Record<string, GlossaryEntry>>({});
  const [editingChars, setEditingChars] = useState<Record<string, Character>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    getGlossary(projectId)
      .then((data) => setGlossary(Array.isArray(data) ? data : []))
      .catch(() => setError("Failed to load glossary."));
    getCharacters(projectId)
      .then((data) => setCharacters(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [projectId]);

  // ---- Glossary editing ----
  const getGlossaryEdit = (entry: GlossaryEntry): GlossaryEntry =>
    editingGlossary[entry.id] ?? entry;

  const handleGlossaryChange = (id: string, field: keyof GlossaryEntry, value: string) => {
    setEditingGlossary((prev) => ({
      ...prev,
      [id]: { ...(prev[id] ?? glossary.find((g) => g.id === id)!), [field]: value },
    }));
  };

  const saveGlossaryEntry = async (entry: GlossaryEntry) => {
    if (!projectId) return;
    const current = getGlossaryEdit(entry);
    setSaving((s) => ({ ...s, [entry.id]: true }));
    try {
      const updated = await updateGlossaryEntry(
        projectId,
        entry.id,
        current.term_original,
        current.term_translated,
        current.category
      );
      setGlossary((prev) => prev.map((g) => (g.id === entry.id ? updated : g)));
      setEditingGlossary((prev) => {
        const copy = { ...prev };
        delete copy[entry.id];
        return copy;
      });
      setSaved((s) => ({ ...s, [entry.id]: true }));
      setTimeout(() => setSaved((s) => ({ ...s, [entry.id]: false })), 1500);
    } catch {
      setError("Failed to save glossary entry.");
    } finally {
      setSaving((s) => ({ ...s, [entry.id]: false }));
    }
  };

  // ---- Character editing ----
  const getCharEdit = (ch: Character): Character => editingChars[ch.id] ?? ch;

  const handleCharChange = (id: string, field: keyof Character, value: string | number) => {
    setEditingChars((prev) => ({
      ...prev,
      [id]: { ...(prev[id] ?? characters.find((c) => c.id === id)!), [field]: value },
    }));
  };

  const saveCharacter = async (ch: Character) => {
    if (!projectId) return;
    const current = getCharEdit(ch);
    setSaving((s) => ({ ...s, [ch.id]: true }));
    try {
      const updated = await updateCharacter(
        projectId,
        ch.id,
        current.name_original,
        current.name_translated,
        current.description,
        current.first_seen_page
      );
      setCharacters((prev) => prev.map((c) => (c.id === ch.id ? updated : c)));
      setSaved((s) => ({ ...s, [ch.id]: true }));
      setTimeout(() => setSaved((s) => ({ ...s, [ch.id]: false })), 1500);
    } catch {
      setError("Failed to save character.");
    } finally {
      setSaving((s) => ({ ...s, [ch.id]: false }));
    }
  };

  const CATEGORIES = ["general", "character", "technique", "organization", "place"];

  return (
    <main className="mx-auto max-w-5xl space-y-6">
      {/* Header */}
      <div className="rounded-[2rem] border border-[#1A4C39]/20 bg-[#f7efe0] p-6 shadow-[0_24px_90px_rgba(16,43,33,0.16)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#1A4C39]">
              Project knowledge
            </p>
            <h1 className="mt-1 text-3xl font-semibold text-[#102b21]">Glossary & Characters</h1>
          </div>
          <Link
            to={`/projects/${projectId}`}
            className="rounded-2xl border border-[#1A4C39]/20 bg-[#fdf8ee] px-4 py-2 text-sm font-semibold text-[#1A4C39] hover:bg-[#efe3c9]"
          >
            ← Back to Project
          </Link>
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>

      {/* Tabs */}
      <div className="flex rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] p-1 w-fit">
        {(["glossary", "characters"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-xl px-5 py-2 text-sm font-semibold capitalize transition ${
              tab === t ? "bg-[#1A4C39] text-[#E5DECA]" : "text-[#1A4C39] hover:bg-[#efe3c9]"
            }`}
          >
            {t} ({t === "glossary" ? glossary.length : characters.length})
          </button>
        ))}
      </div>

      {/* Glossary tab */}
      {tab === "glossary" && (
        <div className="rounded-[1.5rem] border border-[#1A4C39]/20 bg-[#fdf8ee] overflow-hidden">
          {glossary.length === 0 ? (
            <div className="p-10 text-center text-[#1A4C39]/60 text-sm">
              No glossary terms yet. Run the translation pipeline to generate them.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-[#1A4C39]/10 bg-[#f0e8d5]">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-[#102b21]">Original</th>
                  <th className="px-4 py-3 text-left font-semibold text-[#102b21]">Translated</th>
                  <th className="px-4 py-3 text-left font-semibold text-[#102b21]">Category</th>
                  <th className="px-4 py-3 text-left font-semibold text-[#102b21]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {glossary.map((entry, i) => {
                  const edit = getGlossaryEdit(entry);
                  return (
                    <tr
                      key={entry.id}
                      className={i % 2 === 0 ? "bg-[#fdf8ee]" : "bg-[#f7efe0]"}
                    >
                      <td className="px-4 py-2">
                        <input
                          value={edit.term_original}
                          onChange={(e) => handleGlossaryChange(entry.id, "term_original", e.target.value)}
                          className="w-full rounded-lg border border-[#1A4C39]/15 bg-white px-2 py-1 text-sm outline-none focus:border-[#1A4C39]"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          value={edit.term_translated}
                          onChange={(e) => handleGlossaryChange(entry.id, "term_translated", e.target.value)}
                          className="w-full rounded-lg border border-[#1A4C39]/15 bg-white px-2 py-1 text-sm outline-none focus:border-[#1A4C39]"
                        />
                      </td>
                      <td className="px-4 py-2">
                        <select
                          value={edit.category}
                          onChange={(e) => handleGlossaryChange(entry.id, "category", e.target.value)}
                          className="rounded-lg border border-[#1A4C39]/15 bg-white px-2 py-1 text-sm outline-none"
                        >
                          {CATEGORIES.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-2">
                        <button
                          onClick={() => saveGlossaryEntry(entry)}
                          disabled={saving[entry.id]}
                          className="rounded-lg bg-[#1A4C39] px-3 py-1 text-xs font-semibold text-[#E5DECA] disabled:opacity-50"
                        >
                          {saving[entry.id] ? "…" : saved[entry.id] ? "✓" : "Save"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Characters tab */}
      {tab === "characters" && (
        <div className="space-y-3">
          {characters.length === 0 ? (
            <div className="rounded-[1.5rem] border border-[#1A4C39]/20 bg-[#fdf8ee] p-10 text-center text-[#1A4C39]/60 text-sm">
              No characters detected yet. Run the translation pipeline to extract them.
            </div>
          ) : (
            characters.map((ch) => {
              const edit = getCharEdit(ch);
              return (
                <div
                  key={ch.id}
                  className="rounded-[1.5rem] border border-[#1A4C39]/15 bg-[#fdf8ee] p-5"
                >
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block">
                      <span className="text-xs font-semibold uppercase tracking-wider text-[#1A4C39]/60">
                        Original name
                      </span>
                      <input
                        value={edit.name_original}
                        onChange={(e) => handleCharChange(ch.id, "name_original", e.target.value)}
                        className="mt-1 w-full rounded-lg border border-[#1A4C39]/15 bg-white px-3 py-1.5 text-sm outline-none focus:border-[#1A4C39]"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-semibold uppercase tracking-wider text-[#1A4C39]/60">
                        English name
                      </span>
                      <input
                        value={edit.name_translated}
                        onChange={(e) => handleCharChange(ch.id, "name_translated", e.target.value)}
                        className="mt-1 w-full rounded-lg border border-[#1A4C39]/15 bg-white px-3 py-1.5 text-sm outline-none focus:border-[#1A4C39]"
                      />
                    </label>
                    <label className="block sm:col-span-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-[#1A4C39]/60">
                        Description
                      </span>
                      <input
                        value={edit.description ?? ""}
                        onChange={(e) => handleCharChange(ch.id, "description", e.target.value)}
                        className="mt-1 w-full rounded-lg border border-[#1A4C39]/15 bg-white px-3 py-1.5 text-sm outline-none focus:border-[#1A4C39]"
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs font-semibold uppercase tracking-wider text-[#1A4C39]/60">
                        First seen page
                      </span>
                      <input
                        type="number"
                        min={1}
                        value={edit.first_seen_page ?? ""}
                        onChange={(e) => handleCharChange(ch.id, "first_seen_page", Number(e.target.value))}
                        className="mt-1 w-full rounded-lg border border-[#1A4C39]/15 bg-white px-3 py-1.5 text-sm outline-none focus:border-[#1A4C39]"
                      />
                    </label>
                    <div className="flex items-end">
                      <button
                        onClick={() => saveCharacter(ch)}
                        disabled={saving[ch.id]}
                        className="rounded-xl bg-[#1A4C39] px-4 py-2 text-sm font-semibold text-[#E5DECA] disabled:opacity-50"
                      >
                        {saving[ch.id] ? "Saving…" : saved[ch.id] ? "✓ Saved" : "Save character"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </main>
  );
}
