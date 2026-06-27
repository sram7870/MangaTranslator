import { useState } from "react";

interface BubbleEditorProps {
  original: string;
  translation: string;
  onChange: (value: string) => void;
}

export default function BubbleEditor({ original, translation, onChange }: BubbleEditorProps) {
  const [value, setValue] = useState(translation);

  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/80 p-4">
      <p className="text-sm text-slate-400">Original</p>
      <p className="mt-2 text-white">{original}</p>
      <textarea
        value={value}
        onChange={(event) => {
          setValue(event.target.value);
          onChange(event.target.value);
        }}
        className="mt-3 w-full rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-slate-100 outline-none"
        rows={4}
      />
    </div>
  );
}
