import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Video Magic — AI Video from Any Document",
  description: "Turn any document into a branded animated video in minutes. Powered by Gemini, Veo, and ElevenLabs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="min-h-screen bg-brand-navy text-slate-100 antialiased">
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
