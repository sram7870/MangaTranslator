import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

interface DropZoneProps {
  onFilesSelected: (files: File[]) => void;
}

export default function DropZone({ onFilesSelected }: DropZoneProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    onFilesSelected(acceptedFiles);
  }, [onFilesSelected]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [], "application/pdf": [".pdf"] },
    maxFiles: 5,
  });

  return (
    <div
      {...getRootProps()}
      className={`rounded-3xl border border-dashed border-[#E5DECA]/25 bg-[#102b21]/80 px-6 py-12 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] transition hover:border-[#E5DECA]/50 ${isDragActive ? "scale-[1.01] border-[#E5DECA]/70" : ""}`}
    >
      <input {...getInputProps()} />
      <p className="text-base text-[#E5DECA]">Drag and drop up to 5 pages or PDFs, or click to select files.</p>
      <p className="mt-2 text-sm text-[#E5DECA]/70">Supports JPG, PNG, WEBP, and PDF.</p>
      {isDragActive && <p className="mt-4 text-sm font-semibold text-[#E5DECA]">Drop files to upload.</p>}
    </div>
  );
}
