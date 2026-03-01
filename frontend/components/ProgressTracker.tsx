"use client";

import { useEffect, useRef, useState } from "react";

interface ProgressEvent {
  stage: string;
  pct: number;
  detail: string;
}

const STAGE_LABELS: Record<string, string> = {
  parse_document: "Parsing Document",
  character_gen: "Generating Brand Character",
  text_overlays: "Creating Text Overlays",
  scene_0: "Scene 1 — Veo Generation",
  scene_1: "Scene 2 — Veo Generation",
  scene_2: "Scene 3 — Veo Generation",
  scene_3: "Scene 4 — Veo Generation",
  scene_4: "Scene 5 — Veo Generation",
  scene_5: "Scene 6 — Veo Generation",
  scene_6: "Scene 7 — Veo Generation",
  scene_7: "Scene 8 — Veo Generation",
  voiceover: "ElevenLabs Voiceover",
  stitch: "Stitching Scenes",
  overlay: "Compositing Text Overlays",
  mix: "Mixing Final Video",
  done: "Complete",
  error: "Error",
};

const STAGE_PCT: Record<string, number> = {
  parse_document: 12,
  character_gen: 27,
  text_overlays: 32,
  scene_0: 38, scene_1: 44, scene_2: 50, scene_3: 56,
  scene_4: 62, scene_5: 66, scene_6: 70, scene_7: 75,
  voiceover: 82,
  stitch: 88,
  overlay: 93,
  mix: 100,
  done: 100,
};

interface Props {
  projectId: string;
  onComplete: (videoUrl: string) => void;
  onError: (msg: string) => void;
}

export default function ProgressTracker({ projectId, onComplete, onError }: Props) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [currentPct, setCurrentPct] = useState(0);
  const [currentStage, setCurrentStage] = useState("");
  const [done, setDone] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`/api/progress/${projectId}`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const data: ProgressEvent = JSON.parse(e.data);
        setEvents((prev) => {
          const idx = prev.findIndex((p) => p.stage === data.stage);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = data;
            return next;
          }
          return [...prev, data];
        });
        setCurrentPct(data.pct);
        setCurrentStage(data.stage);

        if (data.stage === "done" || data.pct === 100) {
          setDone(true);
          es.close();
          onComplete(data.detail || "");
        }
        if (data.stage === "error") {
          es.close();
          onError(data.detail || "Pipeline error");
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => es.close();
  }, [projectId, onComplete, onError]);

  const stageOrder = Object.keys(STAGE_PCT);

  return (
    <div className="space-y-6">
      {/* Overall progress bar */}
      <div>
        <div className="flex justify-between text-sm mb-2">
          <span className="text-slate-400">
            {done ? "Complete!" : STAGE_LABELS[currentStage] || "Starting..."}
          </span>
          <span className="text-brand-cyan font-mono font-bold">{currentPct}%</span>
        </div>
        <div className="h-3 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-brand-blue to-brand-cyan rounded-full progress-bar"
            style={{ width: `${currentPct}%` }}
          />
        </div>
      </div>

      {/* Stage list */}
      <div className="space-y-2">
        {stageOrder.filter(s => s !== "done" && s !== "error").map((stage) => {
          const ev = events.find((e) => e.stage === stage);
          const stagePct = STAGE_PCT[stage];
          const completed = currentPct >= stagePct && ev;
          const active = currentStage === stage;

          return (
            <div
              key={stage}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                active
                  ? "bg-brand-cyan/10 border border-brand-cyan/30"
                  : completed
                  ? "opacity-70"
                  : "opacity-30"
              }`}
            >
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-xs ${
                active ? "bg-brand-cyan stage-active" :
                completed ? "bg-brand-cyan/60" : "bg-white/10"
              }`}>
                {completed && !active ? "✓" : active ? "→" : "○"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-white truncate">
                  {STAGE_LABELS[stage] || stage}
                </div>
                {ev?.detail && (
                  <div className="text-xs text-slate-400 truncate">{ev.detail}</div>
                )}
              </div>
              {ev && (
                <span className="text-xs text-brand-cyan font-mono">{ev.pct}%</span>
              )}
            </div>
          );
        })}
      </div>

      {currentPct < 40 && (
        <p className="text-xs text-center text-slate-500">
          Veo scene generation takes 1–5 minutes per scene. Grab a coffee ☕
        </p>
      )}
    </div>
  );
}
