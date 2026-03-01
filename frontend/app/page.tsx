import Link from "next/link";
import PricingCards from "@/components/PricingCards";

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/10">
        <span className="text-xl font-bold text-white">
          <span className="text-brand-cyan">Video</span>Magic
        </span>
        <Link
          href="/create"
          className="px-5 py-2 bg-brand-blue hover:bg-brand-cyan text-white rounded-lg font-medium transition-colors"
        >
          Create Video →
        </Link>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-8 pt-24 pb-20 text-center">
        <div className="inline-block px-4 py-1.5 bg-brand-blue/20 border border-brand-blue/40 rounded-full text-brand-cyan text-sm font-medium mb-8">
          Powered by Gemini Veo 3.1 + ElevenLabs
        </div>
        <h1 className="text-6xl font-bold leading-tight text-white mb-6">
          Turn Any Document Into a{" "}
          <span className="text-brand-cyan">Branded Video</span>
        </h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10">
          Upload a PDF, paste text, or drop a URL. Video Magic generates a professional
          animated video with accurate text overlays, voiceover, and your brand colors —
          in minutes.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/create"
            className="px-8 py-4 bg-brand-cyan hover:bg-cyan-400 text-brand-navy font-bold rounded-xl text-lg transition-colors shadow-lg shadow-brand-cyan/25"
          >
            Create Your Video
          </Link>
          <a
            href="#how-it-works"
            className="px-8 py-4 border border-white/20 hover:border-white/40 text-white rounded-xl text-lg transition-colors"
          >
            How It Works
          </a>
        </div>
      </section>

      {/* Social proof */}
      <section className="border-y border-white/10 py-8 px-8">
        <div className="max-w-4xl mx-auto flex flex-wrap justify-center gap-x-12 gap-y-4 text-slate-400 text-sm">
          {["100% Accurate Text Overlays", "Pillow + ffmpeg (not baked-in)", "ElevenLabs Voiceover", "Your Brand Colors", "Edit & Re-run Included"].map((f) => (
            <span key={f} className="flex items-center gap-2">
              <span className="text-brand-cyan">✓</span> {f}
            </span>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="max-w-5xl mx-auto px-8 py-24">
        <h2 className="text-4xl font-bold text-center text-white mb-4">How It Works</h2>
        <p className="text-center text-slate-400 mb-16">From document to video in four steps.</p>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {[
            { step: "01", title: "Upload Document", desc: "Paste text, upload a PDF, or type your content. Any format works." },
            { step: "02", title: "Set Your Brand", desc: "Add your brand name, color, and choose video duration (10s, 30s, or 60s)." },
            { step: "03", title: "Pay & Generate", desc: "Checkout with Stripe. Your video pipeline starts immediately after payment." },
            { step: "04", title: "Download & Edit", desc: "Watch live progress. Edit scenes and re-run any time — included free." },
          ].map(({ step, title, desc }) => (
            <div key={step} className="relative">
              <div className="text-5xl font-black text-brand-navy mb-4">{step}</div>
              <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Text accuracy callout */}
      <section className="bg-white/5 border-y border-white/10 py-16 px-8">
        <div className="max-w-3xl mx-auto text-center">
          <div className="text-4xl mb-4">🎯</div>
          <h2 className="text-3xl font-bold text-white mb-4">100% Accurate Text</h2>
          <p className="text-slate-400 leading-relaxed">
            AI video models can&apos;t render readable text reliably. Video Magic uses{" "}
            <strong className="text-white">Pillow + ffmpeg overlays</strong> to composite
            your title cards, captions, and CTAs at pixel-perfect accuracy — every time.
            Veo prompts contain zero readable words.
          </p>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-5xl mx-auto px-8 py-24">
        <h2 className="text-4xl font-bold text-center text-white mb-4">Simple Pricing</h2>
        <p className="text-center text-slate-400 mb-16">Pay once. Edit and re-run as many times as you need.</p>
        <PricingCards />
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-10 px-8 text-center text-slate-500 text-sm">
        <p>© {new Date().getFullYear()} Video Magic. Built with Gemini Veo 3.1, ElevenLabs, and ffmpeg.</p>
      </footer>
    </main>
  );
}
