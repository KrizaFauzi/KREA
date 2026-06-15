// API helpers for KREA. In dev, /api is proxied to the FastAPI backend.

const BASE = "/api";

/**
 * Stream a chat turn. Calls onEvent for each NDJSON event the backend emits:
 *   { type: "text", text }
 *   { type: "video_prompt", product, concept, video_prompt }
 *   { type: "error", error }
 *   { type: "done", session_id }
 */
export async function streamChat({ message, sessionId }, onEvent) {
  const resp = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId ?? null }),
  });

  if (!resp.ok || !resp.body) {
    onEvent({ type: "error", error: `HTTP ${resp.status}` });
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let nl;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      try {
        onEvent(JSON.parse(line));
      } catch {
        // ignore malformed partial lines
      }
    }
  }
  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer.trim()));
    } catch {
      /* ignore */
    }
  }
}
