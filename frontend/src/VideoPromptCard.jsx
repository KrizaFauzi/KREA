import React, { useState } from "react";

// Renders the generated video prompt (part 2) with a Copy button.
// KREA does not generate the video — the user pastes this into Gemini.
export default function VideoPromptCard({ entry }) {
  const { product, concept, video_prompt } = entry;
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(video_prompt || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="script-card">
      <div className="script-meta">
        <span className="badge">🎬 Prompt Video</span>
        {product && <span className="badge badge-soft">{product}</span>}
      </div>

      {concept && (
        <div className="script-section">
          <div className="script-section-label">Konsep</div>
          <div className="script-section-text">{concept}</div>
        </div>
      )}

      <div className="script-section">
        <div className="script-section-label">Prompt (paste ke Gemini)</div>
        <div className="script-section-text prompt-block">{video_prompt}</div>
      </div>

      <div className="feedback-row">
        <button className="feedback-btn primary" onClick={copy}>
          {copied ? "✓ Tersalin" : "Salin prompt"}
        </button>
      </div>
      <div className="feedback-status muted">
        Langkah 3: tempel prompt ini ke Gemini untuk men-generate videonya.
      </div>
    </div>
  );
}
