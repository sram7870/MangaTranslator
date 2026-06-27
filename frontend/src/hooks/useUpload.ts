import { useState } from "react";

export function useUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState(0);

  function addFiles(newFiles: File[]) {
    setFiles((current) => [...current, ...newFiles].slice(0, 5));
  }

  function reset() {
    setFiles([]);
    setProgress(0);
  }

  return { files, progress, setProgress, addFiles, reset };
}
