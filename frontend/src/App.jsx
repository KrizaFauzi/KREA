import React, { useEffect, useRef, useState } from "react";
import { streamChat } from "./api.js";
import VideoPromptCard from "./VideoPromptCard.jsx";
import Markdown from "./Markdown.jsx";

let _id = 0;
const nextId = () => ++_id;

export default function App() {
  // Flat timeline of entries: user/assistant text bubbles + video-prompt cards.
  const [timeline, setTimeline] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [timeline]);

  const pushEntry = (entry) => {
    const id = nextId();
    setTimeline((t) => [...t, { id, ...entry }]);
    return id;
  };

  const updateEntry = (id, fn) =>
    setTimeline((t) => t.map((e) => (e.id === id ? fn(e) : e)));

  async function sendMessage(rawText) {
    const text = (rawText ?? "").trim();
    if (!text || busy) return;
    setInput("");
    setBusy(true);

    pushEntry({ type: "user", text });
    const assistantId = pushEntry({ type: "assistant", text: "" });

    try {
      await streamChat({ message: text, sessionId }, (ev) => {
        if (ev.type === "text") {
          updateEntry(assistantId, (a) => ({ ...a, text: a.text + ev.text }));
        } else if (ev.type === "video_prompt") {
          pushEntry({
            type: "video_prompt",
            product: ev.product,
            concept: ev.concept,
            video_prompt: ev.video_prompt,
          });
        } else if (ev.type === "error") {
          updateEntry(assistantId, (a) => ({ ...a, text: a.text + `\n\n⚠️ ${ev.error}` }));
        } else if (ev.type === "done") {
          if (ev.session_id) setSessionId(ev.session_id);
        }
      });
    } catch (e) {
      updateEntry(assistantId, (a) => ({ ...a, text: a.text + `\n\n⚠️ ${e.message}` }));
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <img src="/logo.png" alt="KREA" className="logo" />
          <div>
            <h1>KREA</h1>
            <p className="tagline">Riset produk TikTok → prompt video, KREA yang urus.</p>
          </div>
        </div>
        <div className="steps">
          <span>1· Riset produk</span>
          <span>2· Prompt video</span>
          <span>3· Copy ke Gemini</span>
        </div>
      </header>

      <main className="chat" ref={scrollRef}>
        {timeline.length === 0 && (
          <div className="empty">
            <p>Sebutkan bidang yang kamu minati, contoh: <em>"riset produk skincare"</em>.</p>
            <p>KREA akan riset tren TikTok-nya, bantu pilih produk, lalu kasih
              prompt video yang tinggal kamu salin ke Gemini.</p>
          </div>
        )}

        {timeline.map((e) => {
          if (e.type === "user" || e.type === "assistant") {
            if (e.type === "assistant" && !e.text && busy) {
              return (
                <div key={e.id} className="msg msg-assistant">
                  <div className="msg-role">KREA</div>
                  <div className="msg-text typing">KREA sedang mengetik…</div>
                </div>
              );
            }
            if (!e.text) return null;
            return (
              <div key={e.id} className={`msg msg-${e.type}`}>
                <div className="msg-role">{e.type === "user" ? "Kamu" : "KREA"}</div>
                <div className="msg-text">
                  {e.type === "assistant" ? <Markdown>{e.text}</Markdown> : e.text}
                </div>
              </div>
            );
          }
          if (e.type === "video_prompt") {
            return <VideoPromptCard key={e.id} entry={e} />;
          }
          return null;
        })}
      </main>

      <footer className="composer">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ketik bidang/produk… (Enter untuk kirim, Shift+Enter baris baru)"
          rows={2}
          disabled={busy}
        />
        <button className="send-btn" onClick={() => sendMessage(input)} disabled={busy || !input.trim()}>
          {busy ? "…" : "Kirim"}
        </button>
      </footer>
    </div>
  );
}
