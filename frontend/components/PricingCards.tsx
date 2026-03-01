"use client";

import Link from "next/link";

const PLANS = [
  {
    duration: 10,
    label: "10-Second Promo",
    price: "$9.99",
    scenes: 1,
    features: ["1 Veo scene", "Title card overlay", "ElevenLabs VO", "Brand colors"],
    cta: "Get Started",
    highlight: false,
  },
  {
    duration: 30,
    label: "30-Second Overview",
    price: "$14.99",
    scenes: 3,
    features: ["3 Veo scenes", "Title + 3 captions + CTA", "ElevenLabs VO", "Brand colors", "Edit & re-run"],
    cta: "Most Popular",
    highlight: true,
  },
  {
    duration: 60,
    label: "60-Second Deep Dive",
    price: "$19.99",
    scenes: 6,
    features: ["6 Veo scenes", "Full overlay suite", "ElevenLabs VO", "Brand colors", "Edit & re-run"],
    cta: "Go Deep",
    highlight: false,
  },
];

export default function PricingCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {PLANS.map((plan) => (
        <div
          key={plan.duration}
          className={`relative rounded-2xl border p-8 flex flex-col ${
            plan.highlight
              ? "border-brand-cyan bg-brand-cyan/10 shadow-lg shadow-brand-cyan/20"
              : "border-white/15 bg-white/5"
          }`}
        >
          {plan.highlight && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-brand-cyan text-brand-navy text-xs font-bold rounded-full uppercase tracking-wide">
              Most Popular
            </div>
          )}
          <div className="text-slate-400 text-sm font-medium mb-2">{plan.label}</div>
          <div className="text-4xl font-black text-white mb-1">{plan.price}</div>
          <div className="text-slate-500 text-sm mb-6">one-time · {plan.scenes} scene{plan.scenes > 1 ? "s" : ""}</div>
          <ul className="space-y-2 mb-8 flex-1">
            {plan.features.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                <span className="text-brand-cyan text-xs">✓</span> {f}
              </li>
            ))}
          </ul>
          <Link
            href={`/create?duration=${plan.duration}`}
            className={`block text-center py-3 px-6 rounded-xl font-semibold transition-colors ${
              plan.highlight
                ? "bg-brand-cyan text-brand-navy hover:bg-cyan-400"
                : "bg-white/10 text-white hover:bg-white/20"
            }`}
          >
            {plan.cta} →
          </Link>
        </div>
      ))}
    </div>
  );
}
