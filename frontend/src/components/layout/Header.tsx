import { Link } from "react-router-dom";

export default function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-[#1A4C39]/20 bg-[#E5DECA]/95 px-6 py-4 shadow-[0_10px_40px_rgba(20,46,36,0.16)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
        <Link to="/" className="text-2xl font-semibold tracking-wide text-[#102b21]">
          Manga Translator
        </Link>
        <nav className="flex items-center gap-4 text-sm font-medium text-[#1A4C39]">
          <Link to="/" className="transition hover:text-[#102b21]">Home</Link>
          <Link to="/" className="transition hover:text-[#102b21]">Projects</Link>
        </nav>
      </div>
    </header>
  );
}
