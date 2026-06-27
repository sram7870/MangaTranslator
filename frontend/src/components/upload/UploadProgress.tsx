interface UploadProgressProps {
  progress: number;
}

export default function UploadProgress({ progress }: UploadProgressProps) {
  return (
    <div className="rounded-3xl bg-slate-900/70 p-4 text-sm text-slate-300">
      <div className="mb-2 flex items-center justify-between">
        <span>Upload progress</span>
        <span>{progress}%</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-electric-500" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
