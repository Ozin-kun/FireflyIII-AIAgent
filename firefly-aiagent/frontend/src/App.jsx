import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Wallet,
  Clock,
  Brain,
  RefreshCw,
  Plus,
  X,
  CreditCard,
  Target,
} from 'lucide-react';
import { useChatSessions } from './hooks/useChatSessions.js';
import { useChatStream } from './hooks/useChatStream.js';
import { useHealth } from './hooks/useHealth.js';
import { useMemory } from './hooks/useMemory.js';
import { useSpeech } from './hooks/useSpeech.js';
import Sidebar from './components/Sidebar.jsx';
import ChatWindow from './components/ChatWindow.jsx';
import './styles/layout.css';
import './styles/messages.css';
import './styles/input.css';
import './styles/markdown.css';

export default function App() {
  // ── Conversation Sessions (Multi-Thread History) ─────────────
  const {
    sessions,
    setSessions,
    activeSessionId,
    messages,
    setMessages,
    createNewSession,
    selectSession,
    deleteSession,
  } = useChatSessions();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, refreshHealthAndUser } = useHealth();
  const { facts, showMemoryModal, closeMemory } = useMemory();
  const updateInputFromSpeech = useCallback((transcript) => {
    setInput((previousInput) => (previousInput ? `${previousInput} ${transcript}` : transcript));
  }, []);
  const {
    isListening,
    toggleListening,
    stopListening,
  } = useSpeech(updateInputFromSpeech);
  const { loading, sendMessage } = useChatStream({
    activeSessionId,
    messages,
    setMessages,
    setSessions,
    stopListening,
  });

  // Quick Suggestion Chips
  const suggestions = [
    { label: "Tampilkan rincian seluruh rekening dan saldonya", icon: <Wallet size={14} /> },
    { label: "Cek status budget dan sisa limit bulan ini", icon: <CreditCard size={14} /> },
    { label: "Catat pemasukan gaji Rp 10.000.000 ke Rekening BCA", icon: <Plus size={14} /> },
    { label: "Transfer Rp 500.000 dari Rekening BCA ke Dompet Tunai", icon: <RefreshCw size={14} /> },
    { label: "Lihat daftar celengan (piggy banks) dan progresnya", icon: <Target size={14} /> },
    { label: "Lihat tagihan rutin dan tanggal jatuh tempo berikutnya", icon: <Clock size={14} /> },
  ];

  // Auto-scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ── Session Switch / Creation / Deletion Handlers ─────────
  const handleNewChat = () => {
    if (loading) return;
    if (messages.length === 0) return; // already in an empty new session

    createNewSession();
    setInput('');
    setSidebarOpen(false);
  };

  const handleSelectSession = (sessionId) => {
    if (loading || sessionId === activeSessionId) return;
    if (selectSession(sessionId)) {
      setInput('');
      setSidebarOpen(false);
    }
  };

  const handleDeleteSession = (sessionId, e) => {
    e.stopPropagation();
    if (loading) return;

    deleteSession(sessionId);
  };

  const handleSend = (customText = null) => {
    const textToSend = customText || input;
    if (!textToSend.trim() || loading) return;
    setInput('');
    sendMessage(textToSend);
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
      <Sidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        sessions={sessions}
        activeSessionId={activeSessionId}
        user={user}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onSend={handleSend}
        onRefreshUser={refreshHealthAndUser}
      />

      {/* ── Main Chat Feed ───────────────────────────── */}
      <ChatWindow
        sessions={sessions}
        activeSessionId={activeSessionId}
        messages={messages}
        user={user}
        suggestions={suggestions}
        messagesEndRef={messagesEndRef}
        setSidebarOpen={setSidebarOpen}
        isListening={isListening}
        toggleListening={toggleListening}
        input={input}
        setInput={setInput}
        loading={loading}
        onSend={handleSend}
        onKeyDown={handleKeyDown}
      />

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
          onClick={closeMemory}
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
              <button className="icon-btn" style={{ width: '30px', height: '30px' }} onClick={closeMemory}>
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
