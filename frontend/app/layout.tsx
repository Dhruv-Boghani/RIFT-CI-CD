import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Autonomous CI/CD Healing Agent",
  description: "AI-powered DevOps agent for RIFT 2026",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${inter.className} bg-slate-900 text-white min-h-screen`}
      >
        {children}
      </body>
    </html>
  );
}
