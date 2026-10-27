import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Send,
  Mic,
  MicOff,
  Bot,
  User,
  Wallet,
  Clock,
  Brain,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Plus,
  CheckCircle2,
  AlertCircle,
  Menu,
  X,
  CreditCard,
  Target,
  Copy,
  Check,
  MessageSquare,
  Trash2
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

export default function App() {
  // ── Conversation Sessions (Multi-Thread History) ─────────────
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('firefly_chat_sessions');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch (e) {
      console.warn('Could not read sessions from localStorage:', e);
    }
    return [];
  });

  const [activeSessionId, setActiveSessionId] = useState(() => {
    try {
      const saved = localStorage.getItem('firefly_chat_sessions');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed[0].id;
        }
      }
    } catch (e) {}
    return 'session_' + Date.now();
  });

  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem('firefly_chat_sessions');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed[0].messages || [];
        }
      }
    } catch (e) {}
    return [];
  });

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState({ email: '', role: '', id: null });
  const [health, setHealth] = useState({ status: 'checking', firefly_status: 'checking' });
  const [memoryStats, setMemoryStats] = useState(null);
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [facts, setFacts] = useState([]);

  // Audio / Speech-to-Text State
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Quick Suggestion Chips
  const suggestions = [
    { label: "Tampilkan rincian seluruh rekening dan saldonya", icon: <Wallet size={14} /> },
    { label: "Cek status budget dan sisa limit bulan ini", icon: <CreditCard size={14} /> },
    { label: "Catat pemasukan gaji Rp 10.000.000 ke Rekening BCA", icon: <Plus size={14} /> },
    { label: "Transfer Rp 500.000 dari Rekening BCA ke Dompet Tunai", icon: <RefreshCw size={14} /> },
    { label: "Lihat daftar celengan (piggy banks) dan progresnya", icon: <Target size={14} /> },
    { label: "Lihat tagihan rutin dan tanggal jatuh tempo berikutnya", icon: <Clock size={14} /> },
  ];

  // Initialize Speech Recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'id-ID'; // Default Bahasa Indonesia

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map((result) => result[0].transcript)
          .join('');
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      };

      recognition.onerror = (event) => {
        console.warn('Speech recognition notice:', event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } else {
      setSpeechSupported(false);
    }
  }, []);

  // Fetch initial data (User profile dynamically from Firefly III & Health)
  useEffect(() => {
    fetchHealthAndUser();
  }, []);

  // Auto-scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const fetchHealthAndUser = async () => {
    try {
      // 1. Fetch live user profile dynamically from Firefly III
      const userRes = await fetch('/api/user');
      if (userRes.ok) {
        const userData = await userRes.json();
        if (userData.success && userData.user && userData.user.email) {
          setUser(userData.user);
        }
      }

      // 2. Fetch health & connection status
      const healthRes = await fetch('/api/health');
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth(healthData);
        if (healthData.user && healthData.user.email) {
          setUser((prev) => ({ ...prev, ...healthData.user }));
        }
      }
    } catch (e) {
      console.warn('Backend connecting...', e);
    }
  };

  const fetchMemory = async () => {
    try {
      const res = await fetch('/api/memory');
      if (res.ok) {
        const data = await res.json();
        setFacts(data.facts || []);
        setMemoryStats(data.stats || {});
        setShowMemoryModal(true);
      }
    } catch (e) {
      console.warn('Could not fetch memory:', e);
    }
  };

  const toggleListening = () => {
    if (!speechSupported) {
      alert('Browser Anda belum mendukung Web Speech Recognition. Gunakan Chrome, Edge, atau Safari.');
      return;
    }
    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      try {
        recognitionRef.current?.start();
      } catch (err) {
        console.warn('Speech recognition restart error:', err);
      }
    }
  };

  // ── Session Switch / Creation / Deletion Handlers ─────────
  const handleNewChat = () => {
    if (loading) return;
    if (messages.length === 0) return; // already in an empty new session

    const freshId = 'session_' + Date.now();
    setActiveSessionId(freshId);
    setMessages([]);
    setInput('');
    setSidebarOpen(false);
  };

  const handleSelectSession = (sessionId) => {
    if (loading || sessionId === activeSessionId) return;
    const target = sessions.find((s) => s.id === sessionId);
    if (target) {
      setActiveSessionId(target.id);
      setMessages(target.messages || []);
      setInput('');
      setSidebarOpen(false);
    }
  };

  const handleDeleteSession = (sessionId, e) => {
    e.stopPropagation();
    if (loading) return;

    const remaining = sessions.filter((s) => s.id !== sessionId);
    setSessions(remaining);
    try {
      localStorage.setItem('firefly_chat_sessions', JSON.stringify(remaining));
    } catch (err) {}

    if (sessionId === activeSessionId) {
      if (remaining.length > 0) {
        setActiveSessionId(remaining[0].id);
        setMessages(remaining[0].messages || []);
      } else {
        const freshId = 'session_' + Date.now();
        setActiveSessionId(freshId);
        setMessages([]);
      }
    }
  };

  const handleSend = async (customText = null) => {
    const textToSend = customText || input;
    if (!textToSend.trim() || loading) return;

    if (isListening) {
      recognitionRef.current?.stop();
    }

    const currentSessionId = activeSessionId;
    const historyPayload = messages
      .filter((m) => m.content && !m.isStreaming)
      .map((m) => ({ role: m.role, content: m.content }));

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const assistantId = (Date.now() + 1).toString();
    const initialAssistantMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      plan: [],
      is_complex: false,
      actions: [],
      reflection: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isStreaming: true,
    };

    const nextMessages = [...messages, userMessage, initialAssistantMessage];
    setMessages(nextMessages);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          thread_id: currentSessionId,
          history: historyPayload,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream tidak didukung pada browser ini');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.type === 'token' && data.content) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId ? { ...m, content: m.content + data.content } : m
                )
              );
            } else if (data.type === 'plan') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        plan: data.plan || m.plan,
                        is_complex: data.is_complex !== undefined ? data.is_complex : m.is_complex,
                      }
                    : m
                )
              );
            } else if (data.type === 'action' && data.action) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        actions: [...(m.actions || []), data.action],
                      }
                    : m
                )
              );
            } else if (data.type === 'done') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        isStreaming: false,
                        content: m.content || data.reply || 'Tugas selesai dieksekusi.',
                        plan: data.plan && data.plan.length > 0 ? data.plan : m.plan,
                        actions: data.actions && data.actions.length > 0 ? data.actions : m.actions,
                        reflection: data.reflection || m.reflection,
                        is_complex: data.is_complex !== undefined ? data.is_complex : m.is_complex,
                      }
                    : m
                )
              );
            } else if (data.type === 'error') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        isStreaming: false,
                        content: m.content
                          ? `${m.content}\n\n⚠️ ${data.reply || data.error}`
                          : (data.reply || `Terjadi kesalahan: ${data.error}`),
                      }
                    : m
                )
              );
            }
          } catch (parseErr) {
            console.warn('SSE parse error:', parseErr, jsonStr);
          }
        }
      }

      // Check remaining buffer if any
      if (buffer.trim().startsWith('data:')) {
        try {
          const jsonStr = buffer.trim().slice(5).trim();
          const data = JSON.parse(jsonStr);
          if (data.type === 'token' && data.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + data.content } : m
              )
            );
          }
        } catch (e) {}
      }

      // Finalize and sync session to localStorage
      setMessages((prev) => {
        const finalized = prev.map((m) =>
          m.id === assistantId
            ? { ...m, isStreaming: false, content: m.content || 'Tugas selesai dieksekusi.' }
            : m
        );

        setSessions((prevSessions) => {
          let found = false;
          let sessionTitle = textToSend.length > 28 ? textToSend.slice(0, 28) + '...' : textToSend;

          const updated = prevSessions.map((s) => {
            if (s.id === currentSessionId) {
              found = true;
              return {
                ...s,
                title: s.title && s.title !== 'Percakapan Baru' ? s.title : sessionTitle,
                messages: finalized,
                updatedAt: Date.now(),
              };
            }
            return s;
          });

          if (!found) {
            updated.unshift({
              id: currentSessionId,
              title: sessionTitle,
              createdAt: new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'short' }),
              updatedAt: Date.now(),
              messages: finalized,
            });
          }

          updated.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
          try {
            localStorage.setItem('firefly_chat_sessions', JSON.stringify(updated));
          } catch (e) {}
          return updated;
        });

        return finalized;
      });
    } catch (err) {
      console.error('Chat stream error:', err);
      setMessages((prev) => {
        const finalized = prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                isStreaming: false,
                content: m.content
                  ? `${m.content}\n\n⚠️ Terjadi kendala streaming: ${err.message}`
                  : `Terjadi kendala saat menghubungi server: ${err.message}`,
              }
            : m
        );

        setSessions((prevSessions) => {
          const updated = prevSessions.map((s) =>
            s.id === currentSessionId ? { ...s, messages: finalized, updatedAt: Date.now() } : s
          );
          try {
            localStorage.setItem('firefly_chat_sessions', JSON.stringify(updated));
          } catch (e) {}
          return updated;
        });

        return finalized;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-layout">
      {/* ── Left Sidebar ─────────────────────────────── */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-icon">
              <Sparkles size={20} />
            </div>
            <div className="brand-text">
              <h1>Firefly AI</h1>
              <span className="brand-badge">Agent</span>
            </div>
          </div>
          <button className="mobile-toggle-btn" onClick={() => setSidebarOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <button className="new-chat-btn" onClick={handleNewChat} title="Mulai sesi percakapan baru">
          <Plus size={16} />
          Percakapan Baru
        </button>

        <div className="sidebar-scroll">
          {/* Riwayat Percakapan (Conversation History) */}
          <div>
            <div className="sidebar-section-title">
              <MessageSquare size={13} />
              Riwayat Percakapan ({sessions.length})
            </div>
            <div className="session-history-list">
              {sessions.length === 0 ? (
                <div className="session-empty-hint">Belum ada percakapan tersimpan</div>
              ) : (
                sessions.map((s) => (
                  <div
                    key={s.id}
                    className={`session-item ${s.id === activeSessionId ? 'active' : ''}`}
                    onClick={() => handleSelectSession(s.id)}
                    title={s.title}
                  >
                    <MessageSquare size={14} className="session-item-icon" />
                    <span className="session-item-title">{s.title || 'Percakapan'}</span>
                    <button
                      type="button"
                      className="session-delete-btn"
                      onClick={(e) => handleDeleteSession(s.id, e)}
                      title="Hapus riwayat percakapan ini"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Quick AI Capabilities Shortcuts (Without leaking balances) */}
          <div style={{ marginTop: '14px' }}>
            <div className="sidebar-section-title">
              <Sparkles size={13} />
              Kapabilitas AI Agent
            </div>
            <div className="features-list">
              <div className="feature-item" onClick={() => handleSend("Berapa saldo rekening saya saat ini?")}>
                <Wallet size={14} className="feature-icon" />
                <span>Cek Saldo Rekening</span>
              </div>
              <div className="feature-item" onClick={() => handleSend("Cek status budget dan sisa limit bulan ini")}>
                <CreditCard size={14} className="feature-icon" />
                <span>Pantau Limit Budget</span>
              </div>
              <div className="feature-item" onClick={() => handleSend("Lihat daftar celengan atau target tabungan saya")}>
                <Target size={14} className="feature-icon" />
                <span>Target Tabungan / Celengan</span>
              </div>
              <div className="feature-item" onClick={() => handleSend("Lihat tagihan rutin dan tanggal jatuh tempo berikutnya")}>
                <Clock size={14} className="feature-icon" />
                <span>Tagihan & Langganan</span>
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic User Profile Bar at bottom */}
        <div className="user-profile-bar">
          <div className="user-profile-info">
            <div className="user-avatar">
              {user.email ? user.email.charAt(0).toUpperCase() : <User size={18} />}
            </div>
            <div className="user-details">
              <div className="email" title={user.email}>
                {user.email || 'Memuat profil...'}
              </div>
              <div className="role">
                <span className="role-badge">{user.role || 'Member'}</span>
                {user.id && <span className="id-badge">ID: #{user.id}</span>}
              </div>
            </div>
          </div>
          <button
            type="button"
            className="icon-btn-tiny"
            onClick={fetchHealthAndUser}
            title="Sinkronkan ulang info user aktif dari Firefly III"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </aside>

      {/* ── Main Chat Feed ───────────────────────────── */}
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
                  <button key={idx} className="chip-btn" onClick={() => handleSend(s.label)}>
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
              onKeyDown={handleKeyDown}
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
                onClick={() => handleSend()}
              >
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* ── Memory Viewer Modal ──────────────────────── */}
      {showMemoryModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.7)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
          onClick={() => setShowMemoryModal(false)}
        >
          <div
            className="glass-panel"
            style={{
              width: '90%',
              maxWidth: '560px',
              borderRadius: '16px',
              padding: '24px',
              maxHeight: '80vh',
              overflowY: 'auto',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Brain size={20} color="var(--accent-cyan)" />
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem' }}>Agentic Memory Store</h3>
              </div>
              <button className="icon-btn" style={{ width: '30px', height: '30px' }} onClick={() => setShowMemoryModal(false)}>
                <X size={16} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Aturan dan preferensi keuangan yang dipelajari dan diingat oleh agent lintas percakapan (SQLite Long-Term Facts):
            </p>

            {facts.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
                Belum ada preferensi yang tersimpan. Coba katakan: "Ingat ya, batas makan siang saya Rp 35.000"
              </div>
            ) : (
              facts.map((f, i) => (
                <div key={i} className="glass-card" style={{ padding: '12px', marginBottom: '10px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <strong style={{ color: 'var(--accent-cyan)', fontSize: '0.85rem' }}>{f.key}</strong>
                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-emerald)', textTransform: 'uppercase' }}>
                      {f.category}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.88rem', color: 'var(--text-primary)' }}>{f.value}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Collapsible Agent Cognition Accordion Component
function CognitionAccordion({ plan = [], actions = [], reflection = '' }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="cognition-box">
      <div className="cognition-header" onClick={() => setOpen(!open)}>
        <div className="cognition-title">
          <Brain size={15} />
          <span>Alur Berpikir & Eksekusi Alat ({actions.length} Tindakan)</span>
        </div>
        {open ? <ChevronDown size={15} color="var(--accent-cyan)" /> : <ChevronRight size={15} color="var(--accent-cyan)" />}
      </div>

      {open && (
        <div className="cognition-content animate-fade-in">
          {/* Planning Steps */}
          {plan.length > 0 && (
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>
                📋 RENCANA KERJA DEKOMPOSISI:
              </div>
              {plan.map((step, idx) => (
                <div key={idx} className="plan-item">
                  <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{idx + 1}.</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          )}

          {/* Tool Actions & Observations */}
          {actions.length > 0 && (
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>
                🔧 EKSEKUSI TOOL API:
              </div>
              {actions.map((act, idx) => (
                <div key={idx} style={{ marginBottom: '8px' }}>
                  <span className="action-badge">
                    <CheckCircle2 size={12} />
                    {act.tool}
                  </span>
                  {act.output && (
                    <div className="action-preview">
                      {act.output}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Self-Reflection Note */}
          {reflection && (
            <div style={{ fontSize: '0.78rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
              💡 <em>Refleksi Pasca-Tugas: {reflection}</em>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Copy Message Button ──────────────────────────────────────
function MessageCopyButton({ content }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e) => {
    e.stopPropagation();
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      type="button"
      className={`msg-copy-btn ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      title="Salin jawaban lengkap"
    >
      {copied ? (
        <>
          <Check size={12} color="var(--accent-emerald)" />
          <span>Tersalin!</span>
        </>
      ) : (
        <>
          <Copy size={12} />
          <span>Salin</span>
        </>
      )}
    </button>
  );
}

// ── Code Block with Copy ────────────────────────────────────
function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!value) return;
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-container">
      <div className="code-block-header">
        <span className="code-language">{language || 'code'}</span>
        <button type="button" className="code-copy-btn" onClick={handleCopy}>
          {copied ? (
            <>
              <Check size={12} color="var(--accent-emerald)" />
              <span style={{ color: 'var(--accent-emerald)' }}>Tersalin!</span>
            </>
          ) : (
            <>
              <Copy size={12} />
              <span>Salin Kode</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-pre">
        <code>{value}</code>
      </pre>
    </div>
  );
}

// ── Enhanced Markdown Renderer using react-markdown ─────────
function MarkdownRenderer({ content, isStreaming = false }) {
  return (
    <div className={`markdown-wrapper ${isStreaming ? 'is-streaming' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ node, ...props }) => (
            <div className="table-responsive-wrapper">
              <table className="custom-markdown-table" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => <thead className="custom-thead" {...props} />,
          th: ({ node, ...props }) => <th className="custom-th" {...props} />,
          tr: ({ node, ...props }) => <tr className="custom-tr" {...props} />,
          td: ({ node, ...props }) => <td className="custom-td" {...props} />,
          blockquote: ({ node, ...props }) => (
            <div className="custom-callout-card">
              <div className="callout-accent-bar" />
              <blockquote className="callout-body" {...props} />
            </div>
          ),
          code: ({ node, inline, className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '');
            const isMultiLine = typeof children === 'string' && children.includes('\n');
            if (!inline && (match || isMultiLine)) {
              return (
                <CodeBlock
                  language={match ? match[1] : ''}
                  value={String(children).replace(/\n$/, '')}
                />
              );
            }
            return <code className="custom-inline-chip" {...props}>{children}</code>;
          },
          p: ({ node, children, ...props }) => <p className="markdown-p" {...props}>{children}</p>,
          ul: ({ node, ...props }) => <ul className="custom-ul" {...props} />,
          ol: ({ node, ...props }) => <ol className="custom-ol" {...props} />,
          li: ({ node, ...props }) => <li className="custom-li" {...props} />,
          h1: ({ node, ...props }) => <h1 className="markdown-h1" {...props} />,
          h2: ({ node, ...props }) => <h2 className="markdown-h2" {...props} />,
          h3: ({ node, ...props }) => <h3 className="markdown-h3" {...props} />,
          h4: ({ node, ...props }) => <h4 className="markdown-h4" {...props} />,
          a: ({ node, ...props }) => (
            <a target="_blank" rel="noopener noreferrer" className="custom-markdown-link" {...props} />
          ),
          hr: () => <hr className="custom-markdown-hr" />,
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && <span className="streaming-cursor">▊</span>}
    </div>
  );
}
