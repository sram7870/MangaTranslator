import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getProject,
  getProjectPages,
  startProjectProcess,
  streamProgress,
  exportPDF,
  exportZip,
  exportCBZ,
  exportImages,
} from "../services/api";
import type { PageSummary, ProjectDetail } from "../types";
import PageGrid from "../components/project/PageGrid";
import Button from "../components/common/Button";
import { downloadBlob } from "../utils/helpers";

const STAGE_LABELS: Record<string, string> = {
  bubble_detection: "Detecting speech bubbles",
  ocr:             "Reading text (OCR)",
  context_built:   "Building story context",
  translation:     "Translating",
  inpainting:      "Cleaning bubbles",
  typesetting:     "Typesetting translated text",
  completed:       "Done",
  error:           "Error",
};

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [stage, setStage] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const load = async () => {
    if (!projectId) return;
    try {
      const [proj, pgs] = await Promise.all([
        getProject(projectId),
        getProjectPages(projectId),
      ]);
      setProject(proj);
      setPages(Array.isArray(pgs) ? pgs : []);
    } catch {
      setError("Failed to load project.");
    }
  };

  useEffect(() => {
    load();
    return () => esRef.current?.close();
  }, [projectId]);

  const startProcessing = async () => {
    if (!projectId) return;
    setError(null);
    setIsProcessing(true);
    setStage("starting");

    try {
      await startProjectProcess(projectId);
    } catch {
      setError("Failed to start processing.");
      setIsProcessing(false);
      return;
    }

    // Listen to SSE progress
    const es = streamProgress(projectId);
    esRef.current = es;

    es.onmessage = (evt) => {
      const raw: string = evt.data ?? "";
      const [stagePart] = raw.split(":");
      setStage(stagePart);

      if (stagePart === "completed" || stagePart === "error") {
        es.close();
        setIsProcessing(false);
        // Refresh project / pages after completion
        load();
      }
    };

    es.onerror = () => {
      es.close();
      setIsProcessing(false);
    };
  };

  const handleExport = async (format: "pdf" | "zip" | "cbz" | "png" | "jpg") => {
    if (!projectId || !project) return;
    try {
      const safeName =
        project.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "translated";
      let blob: Blob;
      if (format === "pdf") {
        blob = await exportPDF(projectId);
        downloadBlob(blob, `${safeName}.pdf`);
      } else if (format === "zip") {
        blob = await exportZip(projectId);
        downloadBlob(blob, `${safeName}.zip`);
      } else if (format === "cbz") {
        blob = await exportCBZ(projectId);
        downloadBlob(blob, `${safeName}.cbz`);
      } else {
        blob = await exportImages(projectId, format);
        const ext = format;
        const fname =
          (project.total_pages ?? 1) > 1
            ? `${safeName}-${ext}.zip`
            : `${safeName}.${ext}`;
        downloadBlob(blob, fname);
      }
    } catch {
      setError("Export failed — make sure translation is complete.");
    }
  };

  const stageLabel = STAGE_LABELS[stage] ?? stage.replace(/_/g, " ");
  const isReady =
    project?.status === "review" || project?.status === "completed";

  return (
    <main className="mx-auto max-w-6xl space-y-6">
      {/* Header card */}
      <section className="rounded-[2rem] border border-[#1A4C39]/20 bg-[#f7efe0] p-8 shadow-[0_24px_90px_rgba(16,43,33,0.16)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link
              to="/"
              className="text-sm text-[#1A4C39]/60 hover:text-[#1A4C39]"
            >
              ← All projects
            </Link>
            <h1 className="mt-2 text-3xl font-semibold text-[#102b21]">
              {project?.name ?? "Loading…"}
            </h1>
            <p className="mt-1 text-sm text-[#1A4C39]">
              {project?.total_pages ?? 0} pages · status:{" "}
              <span className="font-medium capitalize">{project?.status ?? "—"}</span>
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              onClick={startProcessing}
              disabled={isProcessing || !project}
            >
              {isProcessing ? "Processing…" : "Start translation"}
            </Button>
            {isReady && (
              <>
                <Link
                  to={`/projects/${projectId}/translate`}
                  className="rounded-2xl border border-[#1A4C39]/15 bg-[#fdf8ee] px-4 py-3 text-sm font-semibold text-[#1A4C39] hover:bg-[#efe3c9]"
                >
                  Edit translations
                </Link>
                <Link
                  to={`/projects/${projectId}/glossary`}
                  className="rounded-2xl border border-[#1A4C39]/15 bg-[#fdf8ee] px-4 py-3 text-sm font-semibold text-[#1A4C39] hover:bg-[#efe3c9]"
                >
                  Glossary & characters
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Processing progress */}
        {isProcessing && stage && (
          <div className="mt-5 flex items-center gap-3 rounded-2xl border border-[#1A4C39]/15 bg-[#fdf8ee] px-4 py-3">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#1A4C39]" />
            <span className="text-sm text-[#1A4C39]">{stageLabel}</span>
          </div>
        )}

        {/* Export buttons */}
        {isReady && (
          <div className="mt-5 flex flex-wrap gap-2">
            <p className="w-full text-xs font-semibold uppercase tracking-widest text-[#1A4C39]/50">
              Export
            </p>
            {(["pdf", "png", "jpg", "zip", "cbz"] as const).map((fmt) => (
              <button
                key={fmt}
                onClick={() => handleExport(fmt)}
                className="rounded-xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold uppercase text-[#1A4C39] hover:bg-[#efe3c9]"
              >
                {fmt}
              </button>
            ))}
          </div>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </section>

      {/* Page grid */}
      <section className="rounded-[2rem] border border-[#1A4C39]/20 bg-[#f7efe0] p-6 shadow-[0_24px_90px_rgba(16,43,33,0.16)]">
        <h2 className="mb-4 text-xl font-semibold text-[#102b21]">
          Pages ({pages.length})
        </h2>
        {pages.length === 0 ? (
          <p className="text-sm text-[#1A4C39]/60">No pages uploaded yet.</p>
        ) : (
          <PageGrid pages={pages} projectId={projectId!} />
        )}
      </section>
    </main>
  );
}
