import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  createProject,
  exportImages,
  exportPDF,
  getPageImageUrl,
  getProject,
  listProjects,
  startProcessing,
  streamProgress,
  uploadPages,
} from "../services/api";
import DropZone from "../components/upload/DropZone";
import Button from "../components/common/Button";
import type { ProjectDetail } from "../types";

export default function HomePage() {
  const [projectName, setProjectName] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [projects, setProjects] = useState<ProjectDetail[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeProject, setActiveProject] = useState<ProjectDetail | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewMode, setPreviewMode] = useState<"scroll" | "flip">("scroll");
  const [flipPageIndex, setFlipPageIndex] = useState(0);
  const [projectError, setProjectError] = useState<string | null>(null);
  const [processingStates, setProcessingStates] = useState<Record<string, { status: string; stage: string | null }>>({});

  useEffect(() => {
    listProjects()
      .then((items) => setProjects(Array.isArray(items) ? items : []))
      .catch(() => setProjects([]));
  }, []);

  const filteredProjects = useMemo(() => {
    const normalized = searchTerm.toLowerCase();
    return projects.filter((project) => {
      return project.name.toLowerCase().includes(normalized) || project.status.toLowerCase().includes(normalized);
    });
  }, [projects, searchTerm]);

  const previewPages = (activeProject?.pages || []).filter((page) => page.translated_path || page.original_path);
  const currentFlipPage = previewPages[Math.min(flipPageIndex, Math.max(previewPages.length - 1, 0))];

  const getDisplayStatus = (project: ProjectDetail) => {
    const processingState = processingStates[project.id];
    if (processingState?.status) return processingState.status;
    const normalized = project.status.toLowerCase();
    if (normalized === "completed") return "Review";
    if (normalized === "uploading" || normalized === "pending") return "Queued";
    return project.status;
  };

  const startTranslation = async (projectId: string) => {
    setProcessingStates((current) => ({ ...current, [projectId]: { status: "Queued", stage: "Preparing files" } }));
    try {
      await startProcessing(projectId);
      setProcessingStates((current) => ({ ...current, [projectId]: { status: "Translating", stage: "Starting translation" } }));

      const eventSource = streamProgress(projectId);
      eventSource.onmessage = (event) => {
        const rawValue = event.data || "";
        const [stage] = rawValue.split(":");
        if (stage === "completed") {
          setProcessingStates((current) => ({ ...current, [projectId]: { status: "Review", stage: "Ready for review" } }));
          void getProject(projectId)
            .then((updatedProject) => {
              setProjects((current) => current.map((entry) => (entry.id === projectId ? { ...entry, ...updatedProject } : entry)));
            })
            .catch(console.error);
          eventSource.close();
          return;
        }

        if (stage === "error") {
          setProcessingStates((current) => ({ ...current, [projectId]: { status: "Error", stage: "Translation needs attention" } }));
          eventSource.close();
          return;
        }

        const readableStage = stage.replace(/_/g, " ").replace(/\b\w/g, (letter: string) => letter.toUpperCase());
        setProcessingStates((current) => ({ ...current, [projectId]: { status: "Translating", stage: readableStage } }));
      };

      eventSource.onerror = () => {
        eventSource.close();
      };
    } catch (error) {
      console.error(error);
      setProcessingStates((current) => ({ ...current, [projectId]: { status: "Error", stage: "Translation needs attention" } }));
    }
  };

  const handleCreateProject = async () => {
    if (!projectName.trim() || selectedFiles.length === 0) return;

    setIsSubmitting(true);
    setProjectError(null);

    try {
      const createdProject = await createProject(projectName.trim(), "auto");
      const uploadedPages = await uploadPages(createdProject.id, selectedFiles);
      const newProject: ProjectDetail = {
        ...createdProject,
        total_pages: Array.isArray(uploadedPages) ? uploadedPages.length : selectedFiles.length,
        processed_pages: 0,
        status: "uploading",
        pages: Array.isArray(uploadedPages) ? uploadedPages : [],
      };

      setProjects((current) => [newProject, ...current]);
      setProjectName("");
      setSelectedFiles([]);
      await startTranslation(newProject.id);
    } catch (error) {
      console.error(error);
      setProjectError("The project could not be created or uploaded. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openPreview = async (project: ProjectDetail) => {
    const sourceLanguage = (project.source_language || "").toLowerCase();
    setPreviewMode(sourceLanguage.includes("ja") || sourceLanguage.includes("manga") ? "flip" : "scroll");
    setFlipPageIndex(0);
    setActiveProject(project);
    setIsPreviewOpen(true);
    try {
      const updatedProject = await getProject(project.id);
      setActiveProject(updatedProject);
      setProjects((current) => current.map((entry) => (entry.id === project.id ? { ...entry, ...updatedProject } : entry)));
    } catch (error) {
      console.error(error);
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const safeName = (project: ProjectDetail) =>
    project.name.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase() || "translated-pages";

  const handleDownload = async (project: ProjectDetail, format: "pdf" | "png" | "jpg") => {
    try {
      if (format === "pdf") {
        downloadBlob(await exportPDF(project.id), `${safeName(project)}.pdf`);
        return;
      }

      const blob = await exportImages(project.id, format);
      const filename = project.total_pages === 1 ? `${safeName(project)}.${format}` : `${safeName(project)}-${format}.zip`;
      downloadBlob(blob, filename);
    } catch (error) {
      console.error(error);
      setProjectError("The translated output is not ready to download yet.");
    }
  };

  return (
    <main className="mx-auto max-w-7xl space-y-8">
      <section className="rounded-[2rem] border border-[#1A4C39]/20 bg-[#f7efe0] p-8 shadow-[0_24px_90px_rgba(16,43,33,0.16)] backdrop-blur sm:p-10 lg:p-12">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#1A4C39]">Studio workflow</p>
            <h1 className="mt-3 text-4xl font-semibold text-[#102b21] sm:text-5xl">AI Manga Translator</h1>
          </div>
          <div className="rounded-2xl border border-[#1A4C39]/15 bg-[#fdf8ee] px-4 py-3 text-sm text-[#1A4C39] shadow-[0_10px_28px_rgba(16,43,33,0.08)]">
            Gemini first | OpenAI fallback | Exported page files
          </div>
        </div>

        <p className="mt-6 max-w-3xl text-base leading-8 text-[#1A4C39]/85">
          Upload manga, manhwa, manhua, or PDF pages, then translate them with story-aware context while preserving the page layout.
        </p>

        <div className="mt-10 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-[1.5rem] border border-[#1A4C39]/15 bg-[#fdf8ee] p-6 shadow-[0_20px_60px_rgba(16,43,33,0.12)]">
            <h2 className="text-xl font-semibold text-[#102b21]">Create a new project</h2>
            <label className="mt-5 block text-sm font-medium text-[#1A4C39]">Project name</label>
            <input
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-[#1A4C39]/20 bg-[#f7efe0] px-4 py-3 text-[#102b21] outline-none transition focus:border-[#1A4C39]"
              placeholder="Enter a project name"
            />

            <div className="mt-4">
              <DropZone onFilesSelected={(files) => setSelectedFiles(files)} />
            </div>

            <Button onClick={handleCreateProject} disabled={!projectName.trim() || selectedFiles.length === 0 || isSubmitting} className="mt-4">
              {isSubmitting ? "Queueing project..." : "Create project and translate"}
            </Button>

            {projectError && <p className="mt-3 text-sm text-[#A44D3A]">{projectError}</p>}

            {selectedFiles.length > 0 && (
              <div className="mt-4 rounded-3xl border border-[#1A4C39]/15 bg-[#f7efe0] p-4 text-sm text-[#1A4C39]">
                <p className="font-medium text-[#102b21]">Selected files:</p>
                <ul className="mt-2 space-y-2">
                  {selectedFiles.map((file) => (
                    <li key={`${file.name}-${file.size}`}>{file.name}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="rounded-[1.5rem] border border-[#1A4C39]/15 bg-[#fdf8ee] p-6 shadow-[0_20px_60px_rgba(16,43,33,0.12)]">
            <h2 className="text-xl font-semibold text-[#102b21]">What happens next</h2>
            <div className="mt-4 space-y-3 text-sm leading-7 text-[#1A4C39]/85">
              <div className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] p-4">
                <p className="font-semibold text-[#102b21]">1. Upload pages or PDFs</p>
                <p className="mt-1">PDFs are rendered into page images before processing.</p>
              </div>
              <div className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] p-4">
                <p className="font-semibold text-[#102b21]">2. Preview translated pages</p>
                <p className="mt-1">Use scroll mode for manhwa/manhua or flip mode for page-by-page manga reading.</p>
              </div>
              <div className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] p-4">
                <p className="font-semibold text-[#102b21]">3. Export real files</p>
                <p className="mt-1">Download translated output as PDF, PNG, or JPG.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-[#1A4C39]/20 bg-[#f7efe0] p-8 shadow-[0_24px_90px_rgba(16,43,33,0.16)] sm:p-10">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#1A4C39]">Projects library</p>
            <h2 className="mt-2 text-3xl font-semibold text-[#102b21]">Recent projects</h2>
            <p className="mt-3 text-sm leading-7 text-[#1A4C39]/80">Search your library, preview translated pages, and export finished output.</p>
          </div>
          <input
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            className="w-full rounded-2xl border border-[#1A4C39]/20 bg-[#fdf8ee] px-4 py-3 text-[#102b21] outline-none transition focus:border-[#1A4C39] lg:max-w-xs"
            placeholder="Search projects"
          />
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {filteredProjects.length === 0 ? (
            <div className="rounded-[1.25rem] border border-dashed border-[#1A4C39]/20 bg-[#fdf8ee] p-6 text-[#1A4C39] lg:col-span-2">
              No projects yet.
            </div>
          ) : (
            filteredProjects.map((project) => {
              const displayStatus = getDisplayStatus(project);
              const isTranslating = displayStatus === "Translating";
              const isReviewReady = ["Review", "review", "Translated", "translated"].includes(displayStatus);
              const stageLabel = processingStates[project.id]?.stage;

              return (
                <article
                  key={project.id}
                  className="rounded-[1.25rem] border border-[#1A4C39]/15 bg-[#fdf8ee] p-5 shadow-[0_18px_48px_rgba(16,43,33,0.12)] transition duration-200 hover:-translate-y-1 hover:shadow-[0_24px_64px_rgba(16,43,33,0.18)]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-[#102b21]">{project.name}</p>
                      <p className="mt-2 text-sm text-[#1A4C39]">{project.total_pages} pages | {project.status}</p>
                    </div>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${isTranslating ? "border-[#1A4C39]/20 bg-[#1A4C39] text-[#E5DECA]" : "border-[#1A4C39]/15 bg-[#f7efe0] text-[#1A4C39]"}`}>
                      {displayStatus}
                    </span>
                  </div>

                  {isTranslating && (
                    <div className="mt-4 flex items-center gap-2 rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-3 py-2 text-sm text-[#1A4C39]">
                      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#1A4C39]" />
                      <span>{stageLabel ? `Translating | ${stageLabel}` : "Translating now"}</span>
                    </div>
                  )}

                  <div className="mt-5 flex flex-wrap gap-2">
                    <Button onClick={() => void openPreview(project)} className="px-4 py-2">
                      Preview
                    </Button>
                    {isReviewReady && (
                      <Link
                        to={`/projects/${project.id}/translate`}
                        className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold text-[#1A4C39] transition hover:bg-[#efe3c9]"
                      >
                        Edit
                      </Link>
                    )}
                    <button onClick={() => handleDownload(project, "pdf")} className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold text-[#1A4C39] transition hover:bg-[#efe3c9]">
                      PDF
                    </button>
                    <button onClick={() => handleDownload(project, "png")} className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold text-[#1A4C39] transition hover:bg-[#efe3c9]">
                      PNG
                    </button>
                    <button onClick={() => handleDownload(project, "jpg")} className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold text-[#1A4C39] transition hover:bg-[#efe3c9]">
                      JPG
                    </button>
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>

      {isPreviewOpen && activeProject && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#102b21]/70 p-4">
          <div className="animate-pop-in flex max-h-[92vh] w-full max-w-5xl flex-col rounded-[1.5rem] border border-[#1A4C39]/15 bg-[#fdf8ee] p-6 shadow-[0_30px_100px_rgba(0,0,0,0.3)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-[#1A4C39]">Translated preview</p>
                <h3 className="mt-2 text-2xl font-semibold text-[#102b21]">{activeProject.name}</h3>
              </div>
              <button onClick={() => setIsPreviewOpen(false)} className="rounded-full border border-[#1A4C39]/15 bg-[#f7efe0] px-3 py-1 text-lg text-[#1A4C39]">
                X
              </button>
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              <div className="flex rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] p-1 text-sm font-semibold text-[#1A4C39]">
                <button onClick={() => setPreviewMode("scroll")} className={`rounded-xl px-3 py-2 ${previewMode === "scroll" ? "bg-[#1A4C39] text-[#E5DECA]" : ""}`}>
                  Scroll
                </button>
                <button onClick={() => setPreviewMode("flip")} className={`rounded-xl px-3 py-2 ${previewMode === "flip" ? "bg-[#1A4C39] text-[#E5DECA]" : ""}`}>
                  Flip
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <button onClick={() => handleDownload(activeProject, "pdf")} className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold text-[#1A4C39]">
                  PDF
                </button>
                <button onClick={() => handleDownload(activeProject, "png")} className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold text-[#1A4C39]">
                  PNG
                </button>
                <button onClick={() => handleDownload(activeProject, "jpg")} className="rounded-2xl border border-[#1A4C39]/15 bg-[#f7efe0] px-4 py-2 text-sm font-semibold text-[#1A4C39]">
                  JPG
                </button>
              </div>
            </div>

            <div className="mt-5 min-h-0 flex-1 overflow-hidden rounded-[1.25rem] border border-[#1A4C39]/15 bg-[#102b21]">
              {previewPages.length === 0 ? (
                <div className="flex h-80 items-center justify-center px-6 text-center text-[#E5DECA]">
                  Translated pages are not ready yet. Wait for processing to finish, then open preview again.
                </div>
              ) : previewMode === "scroll" ? (
                <div className="max-h-[64vh] overflow-y-auto px-4 py-5">
                  <div className="mx-auto flex max-w-3xl flex-col gap-5">
                    {previewPages.map((page) => (
                      <img
                        key={page.id}
                        src={getPageImageUrl(activeProject.id, page.id, page.translated_path ? "translated" : "original")}
                        alt={`Page ${page.page_number}`}
                        className="w-full rounded-lg bg-white shadow-[0_18px_48px_rgba(0,0,0,0.35)]"
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex h-[64vh] flex-col">
                  <div className="flex min-h-0 flex-1 items-center justify-center p-4">
                    {currentFlipPage && (
                      <img
                        src={getPageImageUrl(activeProject.id, currentFlipPage.id, currentFlipPage.translated_path ? "translated" : "original")}
                        alt={`Page ${currentFlipPage.page_number}`}
                        className="max-h-full max-w-full rounded-lg bg-white object-contain shadow-[0_18px_48px_rgba(0,0,0,0.35)]"
                      />
                    )}
                  </div>
                  <div className="flex items-center justify-between border-t border-[#E5DECA]/15 bg-[#0d241b] px-4 py-3 text-[#E5DECA]">
                    <button
                      onClick={() => setFlipPageIndex((value) => Math.max(0, value - 1))}
                      disabled={flipPageIndex === 0}
                      className="rounded-xl border border-[#E5DECA]/20 px-4 py-2 text-sm font-semibold disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <span className="text-sm">{Math.min(flipPageIndex + 1, previewPages.length)} / {previewPages.length}</span>
                    <button
                      onClick={() => setFlipPageIndex((value) => Math.min(previewPages.length - 1, value + 1))}
                      disabled={flipPageIndex >= previewPages.length - 1}
                      className="rounded-xl border border-[#E5DECA]/20 px-4 py-2 text-sm font-semibold disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
