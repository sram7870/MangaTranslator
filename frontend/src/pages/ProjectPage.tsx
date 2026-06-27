import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getProject, getProjectPages, startProjectProcess } from "../services/api";
import type { PageSummary, ProjectDetail } from "../types";
import PageGrid from "../components/project/PageGrid";
import Button from "../components/common/Button";

export default function ProjectPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [pages, setPages] = useState<PageSummary[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    getProject(projectId).then(setProject).catch(console.error);
    getProjectPages(projectId).then(setPages).catch(console.error);
  }, [projectId]);

  const handleProcess = async () => {
    if (!projectId) return;
    setIsProcessing(true);
    try {
      await startProjectProcess(projectId);
    } catch (error) {
      console.error(error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <main className="px-6 py-12">
      <section className="max-w-6xl mx-auto rounded-3xl border border-white/10 bg-slate-900/70 p-10 shadow-2xl shadow-slate-950/40">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-semibold">Project {project?.name || projectId}</h1>
            <p className="mt-2 text-slate-300">Status: {project?.status ?? "loading..."}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={handleProcess} disabled={isProcessing || !project}>
              {isProcessing ? "Starting process..." : "Start translation"}
            </Button>
            <Link to={`/projects/${projectId}/translate`} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-slate-100 hover:bg-white/5">
              Review Translation
            </Link>
            <Link to={`/projects/${projectId}/glossary`} className="rounded-2xl border border-white/10 px-5 py-3 text-sm font-semibold text-slate-100 hover:bg-white/5">
              Glossary
            </Link>
          </div>
        </div>

        <div className="mt-10">
          <h2 className="text-xl font-semibold text-white">Pages</h2>
          {pages.length === 0 ? (
            <p className="mt-4 text-slate-400">No pages uploaded yet.</p>
          ) : (
            <PageGrid pages={pages} />
          )}
        </div>
      </section>
    </main>
  );
}
