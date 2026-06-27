import { useState } from "react";
import type { PageSummary } from "../../types";
import { getPageImageUrl } from "../../services/api";

interface PageGridProps {
  pages: PageSummary[];
  projectId: string;
}

const STATUS_BADGE: Record<string, string> = {
  pending:    "bg-slate-500/20 text-slate-300",
  detecting:  "bg-yellow-500/20 text-yellow-300",
  ocr:        "bg-blue-500/20 text-blue-300",
  inpainting: "bg-purple-500/20 text-purple-300",
  typesetting:"bg-indigo-500/20 text-indigo-300",
  done:       "bg-emerald-500/20 text-emerald-300",
  error:      "bg-red-500/20 text-red-300",
};

export default function PageGrid({ pages, projectId }: PageGridProps) {
  const [preview, setPreview] = useState<PageSummary | null>(null);

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {pages.map((page) => {
          const imageType = page.translated_path
            ? "translated"
            : page.cleaned_path
            ? "cleaned"
            : "original";
          const badgeClass = STATUS_BADGE[page.status] ?? "bg-slate-500/20 text-slate-300";

          return (
            <div
              key={page.id}
              onClick={() => setPreview(page)}
              className="cursor-pointer rounded-2xl border border-[#1A4C39]/20 bg-[#fdf8ee] p-3 shadow-[0_8px_24px_rgba(16,43,33,0.10)] transition hover:-translate-y-0.5 hover:shadow-[0_12px_32px_rgba(16,43,33,0.16)]"
            >
              {/* Thumbnail */}
              <div className="aspect-[3/4] overflow-hidden rounded-xl bg-[#102b21]">
                <img
                  src={getPageImageUrl(projectId, page.id, imageType)}
                  alt={`Page ${page.page_number}`}
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              </div>

              {/* Meta */}
              <div className="mt-3 flex items-center justify-between">
                <p className="text-sm font-semibold text-[#102b21]">
                  Page {page.page_number}
                </p>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${badgeClass}`}>
                  {page.status}
                </span>
              </div>

              {page.translated_path && (
                <p className="mt-1 text-xs text-[#1A4C39]/60">✓ Translation ready</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Lightbox */}
      {preview && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onClick={() => setPreview(null)}
        >
          <div
            className="relative max-h-[90vh] max-w-3xl overflow-auto rounded-2xl bg-white"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setPreview(null)}
              className="absolute right-3 top-3 rounded-full bg-black/30 px-2 py-0.5 text-white text-sm hover:bg-black/60"
            >
              ✕
            </button>
            <img
              src={getPageImageUrl(
                projectId,
                preview.id,
                preview.translated_path ? "translated" : "original"
              )}
              alt={`Page ${preview.page_number}`}
              className="w-full rounded-2xl"
            />
          </div>
        </div>
      )}
    </>
  );
}
