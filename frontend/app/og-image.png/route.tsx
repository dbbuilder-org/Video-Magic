import { ImageResponse } from "next/og";

export const runtime = "edge";

export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: 1200,
          height: 630,
          background: "#0B1120",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        {/* Brand accent bar */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 8,
            background: "linear-gradient(90deg, #1A56DB, #06B6D4)",
          }}
        />

        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", marginBottom: 32 }}>
          <div
            style={{
              width: 64,
              height: 64,
              background: "linear-gradient(135deg, #1A56DB, #06B6D4)",
              borderRadius: 12,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginRight: 16,
            }}
          >
            <span style={{ color: "white", fontSize: 24, fontWeight: 900 }}>VM</span>
          </div>
          <span style={{ color: "#06B6D4", fontSize: 36, fontWeight: 900 }}>Video</span>
          <span style={{ color: "white", fontSize: 36, fontWeight: 900 }}>Magic</span>
        </div>

        {/* Headline */}
        <div
          style={{
            fontSize: 64,
            fontWeight: 900,
            color: "white",
            textAlign: "center",
            lineHeight: 1.1,
            maxWidth: 900,
            marginBottom: 24,
          }}
        >
          AI Video from Any Document
        </div>

        {/* Subline */}
        <div
          style={{
            fontSize: 28,
            color: "#94A3B8",
            textAlign: "center",
            maxWidth: 700,
          }}
        >
          Powered by Gemini · Veo 3.1 · ElevenLabs
        </div>

        {/* Bottom bar */}
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 8,
            background: "linear-gradient(90deg, #1A56DB, #06B6D4)",
          }}
        />
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
