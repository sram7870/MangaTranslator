import { create } from "zustand";

interface TranslationEntry {
  id: string;
  bubble_index: number;
  original_text: string;
  translated_text: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Character {
  id: string;
  name_original: string;
  name_translated: string;
  description?: string;
  first_seen_page?: number;
}

interface GlossaryEntry {
  id: string;
  term_original: string;
  term_translated: string;
  category: string;
}

interface TranslationState {
  translations: TranslationEntry[];
  characters: Character[];
  glossary: GlossaryEntry[];
  setTranslations: (translations: TranslationEntry[]) => void;
  setCharacters: (characters: Character[]) => void;
  setGlossary: (glossary: GlossaryEntry[]) => void;
  updateTranslation: (id: string, translated_text: string) => void;
}

export const useTranslationStore = create<TranslationState>((set) => ({
  translations: [],
  characters: [],
  glossary: [],
  setTranslations: (translations) => set({ translations }),
  setCharacters: (characters) => set({ characters }),
  setGlossary: (glossary) => set({ glossary }),
  updateTranslation: (id, translated_text) =>
    set((state) => ({
      translations: state.translations.map((t) =>
        t.id === id ? { ...t, translated_text } : t
      ),
    })),
}));
