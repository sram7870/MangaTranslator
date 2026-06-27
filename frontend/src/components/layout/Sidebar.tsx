export default function Sidebar() {
  return (
    <aside className="hidden w-72 shrink-0 space-y-4 lg:block">
      <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
        <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Quick links</h3>
        <ul className="mt-4 space-y-3 text-slate-300">
          <li>Project</li>
          <li>Translation</li>
          <li>Glossary</li>
          <li>Export</li>
        </ul>
      </div>
    </aside>
  );
}
