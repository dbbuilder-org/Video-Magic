"use client";

interface Props {
  brandName: string;
  brandColor: string;
  onChange: (name: string, color: string) => void;
  onBack: () => void;
  onNext: () => void;
}

const PRESET_COLORS = [
  { label: "Navy Blue", value: "#1A56DB" },
  { label: "Cyan", value: "#06B6D4" },
  { label: "Gold", value: "#F59E0B" },
  { label: "Violet", value: "#7C3AED" },
  { label: "Emerald", value: "#059669" },
  { label: "Rose", value: "#E11D48" },
];

export default function WizardBrand({ brandName, brandColor, onChange, onBack, onNext }: Props) {
  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-bold text-white mb-2">Brand Settings</h1>
      <p className="text-slate-400 mb-8">
        Your brand name and color appear on the title card, lower-thirds, and CTA overlay.
      </p>

      <div className="space-y-6 mb-10">
        {/* Brand name */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Brand / Company Name</label>
          <input
            type="text"
            value={brandName}
            onChange={(e) => onChange(e.target.value, brandColor)}
            placeholder="Acme Corp"
            className="w-full bg-white/5 border border-white/15 rounded-xl px-4 py-3 text-white placeholder-slate-500 outline-none focus:border-brand-cyan transition-colors"
          />
        </div>

        {/* Brand color */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">Brand Color</label>
          <div className="flex flex-wrap gap-3 mb-3">
            {PRESET_COLORS.map((preset) => (
              <button
                key={preset.value}
                onClick={() => onChange(brandName, preset.value)}
                title={preset.label}
                className={`w-9 h-9 rounded-lg border-2 transition-transform hover:scale-110 ${
                  brandColor === preset.value ? "border-white scale-110" : "border-transparent"
                }`}
                style={{ backgroundColor: preset.value }}
              />
            ))}
          </div>
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={brandColor}
              onChange={(e) => onChange(brandName, e.target.value)}
              className="w-10 h-10 rounded-lg border-0 cursor-pointer bg-transparent"
            />
            <input
              type="text"
              value={brandColor}
              onChange={(e) => onChange(brandName, e.target.value)}
              className="bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-white text-sm font-mono w-28 outline-none focus:border-brand-cyan"
            />
            <span className="text-slate-500 text-sm">Custom hex</span>
          </div>
        </div>

        {/* Preview */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Preview</label>
          <div
            className="rounded-xl px-6 py-4 text-white font-bold text-lg"
            style={{ backgroundColor: brandColor + "33", borderLeft: `4px solid ${brandColor}` }}
          >
            {brandName || "Your Brand Name"}
            <div className="text-xs font-normal mt-1 opacity-70">Title card preview · {brandColor}</div>
          </div>
        </div>
      </div>

      <div className="flex gap-3">
        <button onClick={onBack} className="px-6 py-3 border border-white/20 hover:border-white/40 text-white rounded-xl transition-colors">
          ← Back
        </button>
        <button
          onClick={onNext}
          disabled={!brandName.trim()}
          className="flex-1 px-6 py-3 bg-brand-cyan hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed text-brand-navy font-semibold rounded-xl transition-colors"
        >
          Next: Choose Duration →
        </button>
      </div>
    </div>
  );
}
