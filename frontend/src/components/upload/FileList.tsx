interface FileListProps {
  files: File[];
}

export default function FileList({ files }: FileListProps) {
  return (
    <div className="rounded-3xl border border-white/10 bg-slate-900/70 p-4 text-slate-300">
      <h3 className="text-sm font-semibold text-white">Upload preview</h3>
      <ul className="mt-3 space-y-2 text-sm">
        {files.map((file) => (
          <li key={file.name} className="flex items-center justify-between rounded-2xl bg-slate-950/80 px-4 py-3">
            <span>{file.name}</span>
            <span className="text-slate-500">{(file.size / 1024).toFixed(1)} KB</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
