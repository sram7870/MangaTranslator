interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
}

interface ImportMetaWithEnv {
  readonly env: ImportMetaEnv;
}

const API_BASE = (import.meta as unknown as ImportMetaWithEnv).env.VITE_API_BASE || "http://localhost:8000";

export function getPageImageUrl(
  projectId: string,
  pageId: string,
  type: "original" | "cleaned" | "translated"
) {
  return `${API_BASE}/api/projects/${projectId}/pages/${pageId}/image/${type}`;
}

// Projects
export async function createProject(name: string, sourceLanguage: string = "auto") {
  const response = await fetch(`${API_BASE}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, source_language: sourceLanguage }),
  });
  if (!response.ok) throw new Error("Failed to create project");
  return response.json();
}

export async function listProjects() {
  const response = await fetch(`${API_BASE}/api/projects`);
  if (!response.ok) throw new Error("Failed to list projects");
  return response.json();
}

export async function getProject(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}`);
  if (!response.ok) throw new Error("Failed to get project");
  return response.json();
}

export async function getProjectPages(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/pages`);
  if (!response.ok) throw new Error("Failed to get project pages");
  return response.json();
}

export async function startProjectProcess(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/process`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to start project process");
  return response.json();
}

export async function deleteProject(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete project");
  return response.json();
}

// Pages
export async function uploadPages(projectId: string, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/pages`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error("Failed to upload pages");
  return response.json();
}

export async function listPages(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/pages`);
  if (!response.ok) throw new Error("Failed to list pages");
  return response.json();
}

export async function getPageImage(
  projectId: string,
  pageId: string,
  type: "original" | "cleaned" | "translated"
) {
  const response = await fetch(
    `${API_BASE}/api/projects/${projectId}/pages/${pageId}/image/${type}`
  );
  if (!response.ok) throw new Error("Failed to get page image");
  return response.blob();
}

// Translations
export async function getTranslations(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/translations`);
  if (!response.ok) throw new Error("Failed to get translations");
  return response.json();
}

export async function updateTranslation(
  projectId: string,
  translationId: string,
  translatedText: string
) {
  const response = await fetch(
    `${API_BASE}/api/projects/${projectId}/translations/${translationId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ translated_text: translatedText }),
    }
  );
  if (!response.ok) throw new Error("Failed to update translation");
  return response.json();
}

// Glossary
export async function getGlossary(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/glossary`);
  if (!response.ok) throw new Error("Failed to get glossary");
  return response.json();
}

export async function updateGlossaryEntry(
  projectId: string,
  glossaryId: string,
  termOriginal: string,
  termTranslated: string,
  category: string
) {
  const response = await fetch(
    `${API_BASE}/api/projects/${projectId}/glossary/${glossaryId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term_original: termOriginal, term_translated: termTranslated, category }),
    }
  );
  if (!response.ok) throw new Error("Failed to update glossary entry");
  return response.json();
}

// Characters
export async function getCharacters(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/characters`);
  if (!response.ok) throw new Error("Failed to get characters");
  return response.json();
}

export async function updateCharacter(
  projectId: string,
  characterId: string,
  nameOriginal: string,
  nameTranslated: string,
  description?: string,
  firstSeenPage?: number
) {
  const response = await fetch(
    `${API_BASE}/api/projects/${projectId}/characters/${characterId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name_original: nameOriginal,
        name_translated: nameTranslated,
        description,
        first_seen_page: firstSeenPage,
      }),
    }
  );
  if (!response.ok) throw new Error("Failed to update character");
  return response.json();
}

// Processing
export async function startProcessing(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/process`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to start processing");
  return response.json();
}

export function streamProgress(projectId: string) {
  return new EventSource(`${API_BASE}/api/projects/${projectId}/progress`);
}

// Export
export async function exportZip(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/export/zip`);
  if (!response.ok) throw new Error("Failed to export ZIP");
  return response.blob();
}

export async function exportPDF(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/export/pdf`);
  if (!response.ok) throw new Error("Failed to export PDF");
  return response.blob();
}

export async function exportImages(projectId: string, imageFormat: "png" | "jpg") {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/export/images/${imageFormat}`);
  if (!response.ok) throw new Error(`Failed to export ${imageFormat.toUpperCase()}`);
  return response.blob();
}

export async function exportCBZ(projectId: string) {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}/export/cbz`);
  if (!response.ok) throw new Error("Failed to export CBZ");
  return response.blob();
}

