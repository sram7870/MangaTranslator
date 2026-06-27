import type { ButtonHTMLAttributes, ReactNode } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
}

export default function Button({ children, className = "", ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-2xl border border-[#1A4C39]/20 bg-[#1A4C39] px-5 py-3 text-sm font-semibold text-[#E5DECA] shadow-[0_12px_30px_rgba(16,43,33,0.18)] transition duration-200 hover:-translate-y-0.5 hover:scale-[1.01] hover:bg-[#2b6a4f] hover:shadow-[0_16px_36px_rgba(16,43,33,0.24)] disabled:cursor-not-allowed disabled:opacity-60 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
