import type { PageSummary } from "../../types";

interface PageGridProps {
  pages: PageSummary[];
}

export default function PageGrid({ pages }: PageGridProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {pages.map((page) => (
        <div key={page.id} className="rounded-3xl border border-white/10 bg-slate-900/70 p-4">
          <div className="aspect-[4/5] rounded-2xl bg-slate-950" />
          <div className="mt-4 text-slate-300">
            <p className="font-semibold text-white">Page {page.page_number}</p>
            <p className="text-sm">Status: {page.status}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
