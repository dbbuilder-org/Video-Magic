"use client";

const DURATIONS = [
  { value: 10, label: "10 Seconds", price: "$9.99", scenes: 1, desc: "Perfect for social media promos and quick pitches." },
  { value: 30, label: "30 Seconds", price: "$14.99", scenes: 3, desc: "The ideal length for explainers and product overviews." },
  { value: 60, label: "60 Seconds", price: "$19.99", scenes: 6, desc: "Full story arc with intro, body, and strong CTA." },
];

interface Props {
  duration: number;
  onChange: (d: number) => void;
  onBack: () => void;
  onCheckout: () => void;
  loading: boolean;
  error: string;
}

export default function WizardDuration({ duration, onChange, onBack, onCheckout, loading, error }: Props) {
  const selected = DURATIONS.find((d) => d.value === duration) || DURATIONS[1];

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-bold text-white mb-2">Choose Duration</h1>
      <p className="text-slate-400 mb-8">
        Longer videos include more Veo scenes and a richer overlay suite. Re-runs are always free.
      </p>

      <div className="space-y-3 mb-8">
        {DURATIONS.map((d) => (
          <button
            key={d.value}
            onClick={() => onChange(d.value)}
            className={`w-full text-left rounded-xl border p-5 transition-all ${
              duration === d.value
                ? "border-brand-cyan bg-brand-cyan/10"
                : "border-white/15 bg-white/5 hover:border-white/30"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-white">{d.label}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400">{d.scenes} scene{d.scenes > 1 ? "s" : ""}</span>
                <span className="text-brand-cyan font-bold">{d.price}</span>
              </div>
            </div>
            <p className="text-sm text-slate-400">{d.desc}</p>
          </button>
        ))}
      </div>

      {/* Summary */}
      <div className="bg-white/5 rounded-xl p-5 mb-6 border border-white/10">
        <div className="text-xs text-slate-400 uppercase tracking-wide mb-3">Order Summary</div>
        <div className="flex justify-between items-center text-sm text-slate-300 mb-2">
          <span>{selected.label} Video</span>
          <span>{selected.price}</span>
        </div>
        <div className="flex justify-between items-center text-xs text-slate-500 mb-4">
          <span>Unlimited re-runs</span>
          <span>Included</span>
        </div>
        <div className="border-t border-white/10 pt-3 flex justify-between font-bold text-white">
          <span>Total</span>
          <span>{selected.price}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-500/40 rounded-lg px-4 py-3 text-red-300 text-sm mb-4">
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={onBack} className="px-6 py-3 border border-white/20 hover:border-white/40 text-white rounded-xl transition-colors">
          ← Back
        </button>
        <button
          onClick={onCheckout}
          disabled={loading}
          className="flex-1 py-4 bg-brand-cyan hover:bg-cyan-400 disabled:opacity-60 text-brand-navy font-bold rounded-xl text-lg transition-colors shadow-lg shadow-brand-cyan/25"
        >
          {loading ? "Redirecting to Stripe…" : `Pay ${selected.price} & Generate →`}
        </button>
      </div>
      <p className="text-center text-xs text-slate-500 mt-4">
        Secured by Stripe. Your video starts generating immediately after payment.
      </p>
    </div>
  );
}
