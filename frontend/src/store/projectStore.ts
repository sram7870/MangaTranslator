import { create } from "zustand";
import type { ProjectDetail } from "../types";

interface ProjectState {
  projects: ProjectDetail[];
  selectedProject: ProjectDetail | null;
  setProjects: (projects: ProjectDetail[]) => void;
  setSelectedProject: (project: ProjectDetail) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  selectedProject: null,
  setProjects: (projects) => set({ projects }),
  setSelectedProject: (selectedProject) => set({ selectedProject }),
}));
