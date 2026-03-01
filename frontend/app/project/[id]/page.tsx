"use client";

import { useCallback, useEffect, useState, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import ProgressTracker from "@/components/ProgressTracker";
import ScriptEditor from "@/components/ScriptEditor";
import VideoPlayer from "@/components/VideoPlayer";

interface Project {
  id: string;
  status: string;
  spec: {
    doc_spec?: {
      title: string;
      tagline: string;
      key_messages: string[];
      scenes: Array<{ index: number; caption: string; visual_action: string; vo_text: string }>;
      cta: string;
    };
    brand_name?: string;
    duration?: number;
  };
  video_url?: string;
  error?: string;
}

function ProjectPageInner() {
  const { id: projectId } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [videoUrl, setVideoUrl] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [tab, setTab] = useState<"progress" | "editor">("progress");
  const [rerunning, setRerunning] = useState(false);

  useEffect(() => {
    async function loadProject() {
      try {
        const res = await fetch(`/api/backend/projects/${projectId}`);
        if (!res.ok) throw new Error("Project not found");
        const p: Project = await res.json();
        setProject(p);
        if (p.status === "done" && p.video_url) {
          setVideoUrl(p.video_url);
          setTab("editor");
        }
      } catch (e: unknown) {
        setErrorMsg(e instanceof Error ? e.message : "Failed to load project");
      } finally {
        setLoading(false);
      }
    }
    loadProject();
  }, [projectId]);

  const handleComplete = useCallback((url: string) => {
    setVideoUrl(url);
    setRerunning(false);
    // Refresh project to get latest spec
    fetch(`/api/backend/projects/${projectId}`)
      .then((r) => r.json())
      .then(setProject)
      .catch(() => {});
  }, [projectId]);

  const handleError = useCallback((msg: string) => {
    setErrorMsg(msg);
    setRerunning(false);
  }, []);

  const handleRerun = useCallback(() => {
    setRerunning(true);
    setVideoUrl("");
    setErrorMsg("");
    setTab("progress");
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-slate-400">Loading project…</div>
      </div>
    );
  }

  const isProcessing = project?.status === "running" || project?.status === "pending" || rerunning;
  const isDone = !!videoUrl || project?.status === "done";
  const docSpec = project?.spec?.doc_spec;

  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-white/10">
        <a href="/" className="text-xl font-bold text-white">
          <span className="text-brand-cyan">Video</span>Magic
        </a>
        <div className="flex items-center gap-3 text-sm">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${
            isDone ? "bg-green-900/40 text-green-400 border border-green-500/30" :
            isProcessing ? "bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/30" :
            errorMsg ? "bg-red-900/40 text-red-400 border border-red-500/30" :
            "bg-white/10 text-slate-400"
          }`}>
            {isDone ? "Done" : isProcessing ? "Processing…" : errorMsg ? "Error" : project?.status || "Pending"}
          </span>
          <span className="text-slate-500 font-mono text-xs">{projectId?.slice(0, 8)}</span>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-8 py-10">
        {/* Stripe session notice */}
        {sessionId && !isProcessing && !isDone && (
          <div className="bg-brand-cyan/10 border border-brand-cyan/30 rounded-xl p-4 mb-8 text-sm text-brand-cyan">
            Payment confirmed! Your video is being generated. This usually takes 5–20 minutes.
          </div>
        )}

        {/* Title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-1">
            {docSpec?.title || project?.spec?.brand_name || "Your Video"}
          </h1>
          {docSpec?.tagline && (
            <p className="text-slate-400">{docSpec.tagline}</p>
          )}
        </div>

        {/* Video player */}
        {isDone && videoUrl && (
          <div className="mb-8 animate-slide-up">
            <VideoPlayer
              videoUrl={project?.video_url || videoUrl}
              title={docSpec?.title || "Generated Video"}
            />
          </div>
        )}

        {/* Error */}
        {errorMsg && (
          <div className="bg-red-900/30 border border-red-500/40 rounded-xl p-4 mb-8 text-red-300 text-sm">
            <strong>Error:</strong> {errorMsg}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 bg-white/5 rounded-xl p-1 mb-6 w-fit">
          {(["progress", "editor"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
                tab === t ? "bg-white/15 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              {t === "progress" ? "Progress" : "Edit Script"}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === "progress" && (
          <div>
            {isProcessing ? (
              <ProgressTracker
                projectId={projectId}
                onComplete={handleComplete}
                onError={handleError}
              />
            ) : isDone ? (
              <div className="text-center py-16 text-slate-400">
                <div className="text-5xl mb-4">🎉</div>
                <p className="text-lg text-white font-semibold mb-2">Your video is ready!</p>
                <p className="mb-6">Use the Edit Script tab to adjust and re-generate any time.</p>
                <button onClick={handleRerun} className="px-6 py-3 bg-brand-blue hover:bg-brand-cyan text-white rounded-xl font-medium transition-colors">
                  Re-run Pipeline →
                </button>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500">
                Waiting for pipeline to start…
              </div>
            )}
          </div>
        )}

        {tab === "editor" && docSpec ? (
          <ScriptEditor
            projectId={projectId}
            spec={docSpec}
            onSaved={handleRerun}
          />
        ) : tab === "editor" ? (
          <div className="text-center py-16 text-slate-500">
            Script will be available once the pipeline has parsed your document.
          </div>
        ) : null}
      </div>
    </main>
  );
}

export default function ProjectPage() {
  return (
    <Suspense>
      <ProjectPageInner />
    </Suspense>
  );
}
