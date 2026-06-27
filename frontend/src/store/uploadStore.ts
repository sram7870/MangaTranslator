import { create } from "zustand";

interface UploadState {
  files: File[];
  progress: number;
  status: "idle" | "uploading" | "done" | "error";
  error: string | null;
  addFiles: (files: File[]) => void;
  setProgress: (progress: number) => void;
  setStatus: (status: UploadState["status"]) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useUploadStore = create<UploadState>((set) => ({
  files: [],
  progress: 0,
  status: "idle",
  error: null,
  addFiles: (files: File[]) => set({ files }),
  setProgress: (progress: number) => set({ progress }),
  setStatus: (status: UploadState["status"]) => set({ status }),
  setError: (error: string | null) => set({ error }),
  reset: () => set({ files: [], progress: 0, status: "idle", error: null }),
}));
