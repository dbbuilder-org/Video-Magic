"use client";

import { useState } from "react";

interface Props {
  value: string;
  onChange: (text: string) => void;
  onNext: () => void;
}

export default function WizardUpload({ value, onChange, onNext }: Props) {
  const [dragging, setDragging] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === "text/plain") {
      file.text().then(onChange);
    }
  }

  return (
    <div className="animate-fade-in">
      <h1 className="text-3xl font-bold text-white mb-2">Upload Your Content</h1>
      <p className="text-slate-400 mb-8">
        Paste text, a document excerpt, or drop a .txt file. Gemini will extract
        key messages and write your video script.
      </p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-6 mb-4 transition-colors ${
          dragging ? "border-brand-cyan bg-brand-cyan/10" : "border-white/20 hover:border-white/30"
        }`}
      >
        <textarea
          className="w-full bg-transparent text-slate-200 placeholder-slate-500 resize-none outline-none min-h-[240px] text-sm leading-relaxed"
          placeholder="Paste your document, product description, company overview, or any content you want to turn into a video..."
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        {!value && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center text-slate-600 mt-12">
              <div className="text-3xl mb-2">📄</div>
              <div className="text-sm">Drop a .txt file or paste text above</div>
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">{value.length.toLocaleString()} characters</span>
        <button
          onClick={onNext}
          disabled={value.trim().length < 50}
          className="px-6 py-3 bg-brand-cyan hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed text-brand-navy font-semibold rounded-xl transition-colors"
        >
          Next: Brand Settings →
        </button>
      </div>
      {value.trim().length < 50 && value.length > 0 && (
        <p className="text-xs text-slate-500 mt-2">Add at least 50 characters to continue.</p>
      )}
    </div>
  );
}
