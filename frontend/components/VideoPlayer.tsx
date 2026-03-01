"use client";

interface Props {
  videoUrl: string;
  title?: string;
}

export default function VideoPlayer({ videoUrl, title }: Props) {
  const fullUrl = videoUrl.startsWith("http")
    ? videoUrl
    : `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}${videoUrl}`;

  return (
    <div className="rounded-2xl overflow-hidden bg-black border border-white/10">
      <video
        src={fullUrl}
        controls
        autoPlay
        playsInline
        className="w-full aspect-video"
        title={title || "Generated Video"}
      />
      <div className="px-4 py-3 flex items-center justify-between">
        <span className="text-sm text-slate-400 truncate">{title || "Your Video"}</span>
        <a
          href={fullUrl}
          download="video-magic.mp4"
          className="text-xs px-4 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors font-medium"
        >
          ↓ Download
        </a>
      </div>
    </div>
  );
}
