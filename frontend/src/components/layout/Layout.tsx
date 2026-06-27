import type { ReactNode } from "react";
import Header from "./Header";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(26,76,57,0.12),_transparent_55%),linear-gradient(135deg,_#E5DECA_0%,_#efe7d3_100%)] text-[#102b21]">
      <Header />
      <main className="px-4 py-8 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}
