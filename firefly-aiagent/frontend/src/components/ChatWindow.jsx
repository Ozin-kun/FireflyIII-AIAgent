import { Bot, Menu, Mic, MicOff, RefreshCw, Send, Sparkles, User } from 'lucide-react';
import CognitionAccordion from './CognitionAccordion.jsx';
import MarkdownRenderer from './MarkdownRenderer.jsx';
import MessageCopyButton from './MessageCopyButton.jsx';

export default function ChatWindow({
  sessions,
  activeSessionId,
  messages,
  user,
  suggestions,
  messagesEndRef,
  setSidebarOpen,
  isListening,
  toggleListening,
  input,
  setInput,
  loading,
  onSend,
  onKeyDown,
}) {
  return (
      <main className="main-chat">
        {/* Header */}
        <header className="chat-header">
          <div className="chat-header-title">
            <button className="mobile-toggle-btn" onClick={() => setSidebarOpen(true)}>
              <Menu size={22} />
            </button>
            <div>
              <h2 style={{ margin: 0, fontSize: '1.05rem' }}>
                {sessions.find((s) => s.id === activeSessionId)?.title || 'Percakapan Baru'}
              </h2>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {messages.length > 0 ? `${messages.length} pesan dalam sesi ini` : 'Sesi percakapan baru'}
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Model: <strong style={{ color: 'var(--accent-cyan)' }}>Gemini Flash</strong>
            </span>
          </div>
        </header>

        {/* Messages List */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-chat animate-fade-in">
              <div className="empty-icon">
                <Bot size={34} />
              </div>
              <h3>Halo, {user.email ? user.email.split('@')[0] : 'Pengguna'}! 👋</h3>
              <p>
                Saya adalah AI Agent Firefly III Anda. Saya dapat memeriksa saldo, menganalisis budget, 
                mencari transaksi historis, dan mencatat pengeluaran Anda.
              </p>

              <div className="suggestion-chips">
                {suggestions.map((s, idx) => (
                  <button key={idx} className="chip-btn" onClick={() => onSend(s.label)}>
                    {s.icon}
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`message-row ${msg.role} animate-fade-in`}>
                <div className={`message-avatar ${msg.role === 'user' ? 'user-av' : 'agent-av'}`}>
                  {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                </div>

                <div className="message-bubble">
                  {/* Top Bar for Assistant Message: Model Tag + Quick Copy */}
                  {msg.role === 'assistant' && (
                    <div className="message-bubble-header">
                      <div className="message-header-meta">
                        <Sparkles size={13} className={`sparkle-icon ${msg.isStreaming ? 'animate-pulse' : ''}`} />
                        <span className="agent-label">
                          {msg.isStreaming ? 'Firefly Sedang Mengetik...' : 'Firefly Assistant'}
                        </span>
                      </div>
                      {!msg.isStreaming && msg.content && <MessageCopyButton content={msg.content} />}
                    </div>
                  )}

                  {/* Cognition Accordion for Agent Thought Process */}
                  {msg.role === 'assistant' && (msg.plan?.length > 0 || msg.actions?.length > 0) && (
                    <CognitionAccordion plan={msg.plan} actions={msg.actions} reflection={msg.reflection} />
                  )}

                  {/* Formatted Markdown Body with react-markdown */}
                  <div className="markdown-body">
                    {msg.role === 'assistant' ? (
                      msg.isStreaming && !msg.content ? (
                        <div className="streaming-thinking">
                          <RefreshCw size={15} className="animate-spin" style={{ animation: 'spinSlow 1.5s linear infinite' }} />
                          <span>Sedang memproses & menganalisis di Firefly III...</span>
                        </div>
                      ) : (
                        <MarkdownRenderer content={msg.content} isStreaming={msg.isStreaming} />
                      )
                    ) : (
                      <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                    )}
                  </div>

                  <div className="message-footer-info">
                    <span>{msg.timestamp}</span>
                  </div>
                </div>
              </div>
            ))
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Bottom Input Dock ──────────────────────── */}
        <div className="input-dock">
          {/* Active Voice Wave Animation */}
          {isListening && (
            <div className="recording-bar animate-fade-in">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="wave-container">
                  <span className="wave-bar"></span>
                  <span className="wave-bar"></span>
                  <span className="wave-bar"></span>
                  <span className="wave-bar"></span>
                </span>
                <span>Mendengarkan suara Anda (Bahasa Indonesia)... Berbicaralah sekarang</span>
              </div>
              <button
                style={{ background: 'none', border: 'none', color: '#f43f5e', cursor: 'pointer', fontWeight: 600 }}
                onClick={toggleListening}
              >
                Selesai
              </button>
            </div>
          )}

          <div className="input-container">
            <textarea
              className="input-textarea"
              placeholder={isListening ? 'Mendengarkan...' : 'Ketik instruksi atau gunakan tombol suara... (Enter untuk kirim)'}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
            />

            <div className="action-buttons">
              {/* Audio-to-Text Microphone Button */}
              <button
                type="button"
                className={`icon-btn ${isListening ? 'mic-recording' : ''}`}
                onClick={toggleListening}
                title={isListening ? 'Hentikan rekaman suara' : 'Bicara dengan suara (Audio-to-Text)'}
              >
                {isListening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>

              {/* Send Button */}
              <button
                type="button"
                className="icon-btn send-btn"
                disabled={!input.trim() || loading}
                onClick={() => onSend()}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </main>
  );
}
