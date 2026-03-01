"use client";

import { useState } from "react";

interface Scene {
  index: number;
  caption: string;
  visual_action: string;
  vo_text: string;
}

interface DocSpec {
  title: string;
  tagline: string;
  key_messages: string[];
  scenes: Scene[];
  cta: string;
}

interface Props {
  projectId: string;
  spec: DocSpec;
  onSaved: () => void;
}

export default function ScriptEditor({ projectId, spec, onSaved }: Props) {
  const [local, setLocal] = useState<DocSpec>(spec);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function updateScene(idx: number, field: keyof Scene, value: string) {
    setLocal((s) => ({
      ...s,
      scenes: s.scenes.map((scene, i) =>
        i === idx ? { ...scene, [field]: value } : scene
      ),
    }));
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    try {
      const res = await fetch(`/api/backend/projects/${projectId}/spec`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ spec: { doc_spec: local } }),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "Save failed");
      }
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error saving");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header fields */}
      <div className="grid grid-cols-1 gap-4">
        <div>
          <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">Video Title</label>
          <input
            className="w-full bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-brand-cyan"
            value={local.title}
            onChange={(e) => setLocal((s) => ({ ...s, title: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">Tagline</label>
          <input
            className="w-full bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-brand-cyan"
            value={local.tagline}
            onChange={(e) => setLocal((s) => ({ ...s, tagline: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-xs text-slate-400 uppercase tracking-wide block mb-1">Call to Action</label>
          <input
            className="w-full bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-brand-cyan"
            value={local.cta}
            onChange={(e) => setLocal((s) => ({ ...s, cta: e.target.value }))}
          />
        </div>
      </div>

      {/* Scene editor */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-3">Scenes ({local.scenes.length})</h3>
        <div className="space-y-4">
          {local.scenes.map((scene, i) => (
            <div key={i} className="border border-white/10 rounded-xl p-4 bg-white/3">
              <div className="text-xs text-brand-cyan font-mono mb-3">Scene {i + 1}</div>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Caption (lower-third)</label>
                  <input
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-brand-cyan"
                    value={scene.caption}
                    onChange={(e) => updateScene(i, "caption", e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">
                    Visual Action Prompt
                    <span className="text-amber-400 ml-1">(no readable words — describe motion only)</span>
                  </label>
                  <textarea
                    rows={3}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-brand-cyan resize-none"
                    value={scene.visual_action}
                    onChange={(e) => updateScene(i, "visual_action", e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 block mb-1">Voiceover Narration</label>
                  <textarea
                    rows={2}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-brand-cyan resize-none"
                    value={scene.vo_text}
                    onChange={(e) => updateScene(i, "vo_text", e.target.value)}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-500/40 rounded-lg px-4 py-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full py-3 bg-brand-cyan hover:bg-cyan-400 disabled:opacity-60 text-brand-navy font-bold rounded-xl transition-colors"
      >
        {saving ? "Saving & Re-generating…" : "Save & Re-run Pipeline →"}
      </button>
      <p className="text-center text-xs text-slate-500">Re-runs are included in your original purchase.</p>
    </div>
  );
}
