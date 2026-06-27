import { useCallback, useState } from "react";
import { useUploadStore } from "../store/uploadStore";

export function useFileUpload() {
  const { files, setProgress } = useUploadStore();
  const [isLoading, setIsLoading] = useState(false);

  const uploadFiles = useCallback(
    async (projectId: string, filesToUpload: File[]) => {
      setIsLoading(true);
      const formData = new FormData();
      filesToUpload.forEach((file) => formData.append("files", file));

      try {
        const response = await fetch(
          `http://localhost:8000/api/projects/${projectId}/pages`,
          {
            method: "POST",
            body: formData,
          }
        );
        if (!response.ok) throw new Error("Upload failed");
        setProgress(100);
        return await response.json();
      } catch (error) {
        console.error(error);
        throw error;
      } finally {
        setIsLoading(false);
      }
    },
    [setProgress]
  );

  return { files, isLoading, uploadFiles };
}
