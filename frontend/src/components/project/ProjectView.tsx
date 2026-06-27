import type { ProjectDetail } from "../../types";

interface ProjectViewProps {
  project: ProjectDetail;
}

export default function ProjectView({ project }: ProjectViewProps) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/80 p-6 shadow-lg shadow-slate-950/40">
      <h2 className="text-xl font-semibold text-white">{project.name}</h2>
      <p className="mt-2 text-sm text-slate-400">Status: {project.status}</p>
      <p className="text-sm text-slate-400">Pages: {project.total_pages}</p>
    </div>
  );
}
