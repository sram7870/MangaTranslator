import { useEffect, useState } from "react";

interface ProgressEvent {
  stage: string;
  page: number;
}

export function useSSEProgress(projectId: string) {
  const [stage, setStage] = useState<string>("idle");
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!projectId) return;

    const eventSource = new EventSource(
      `http://localhost:8000/api/projects/${projectId}/progress`
    );

    eventSource.onopen = () => setConnected(true);
    eventSource.onmessage = (event) => {
      const data = event.data;
      setStage(data);
    };
    eventSource.onerror = () => {
      setConnected(false);
      eventSource.close();
    };

    return () => eventSource.close();
  }, [projectId]);

  return { stage, connected };
}
