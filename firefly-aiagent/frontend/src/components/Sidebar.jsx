import { Clock, CreditCard, MessageSquare, Plus, RefreshCw, Sparkles, Target, Trash2, User, Wallet, X } from 'lucide-react';

export default function Sidebar({
  sidebarOpen,
  setSidebarOpen,
  sessions,
  activeSessionId,
  user,
  onNewChat,
  onSelectSession,
  onDeleteSession,
  onSend,
  onRefreshUser,
}) {
  return (
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

        <button className="new-chat-btn" onClick={onNewChat} title="Mulai sesi percakapan baru">
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
                    onClick={() => onSelectSession(s.id)}
                    title={s.title}
                  >
                    <MessageSquare size={14} className="session-item-icon" />
                    <span className="session-item-title">{s.title || 'Percakapan'}</span>
                    <button
                      type="button"
                      className="session-delete-btn"
                      onClick={(e) => onDeleteSession(s.id, e)}
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
              <div className="feature-item" onClick={() => onSend("Berapa saldo rekening saya saat ini?")}>
                <Wallet size={14} className="feature-icon" />
                <span>Cek Saldo Rekening</span>
              </div>
              <div className="feature-item" onClick={() => onSend("Cek status budget dan sisa limit bulan ini")}>
                <CreditCard size={14} className="feature-icon" />
                <span>Pantau Limit Budget</span>
              </div>
              <div className="feature-item" onClick={() => onSend("Lihat daftar celengan atau target tabungan saya")}>
                <Target size={14} className="feature-icon" />
                <span>Target Tabungan / Celengan</span>
              </div>
              <div className="feature-item" onClick={() => onSend("Lihat tagihan rutin dan tanggal jatuh tempo berikutnya")}>
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
            onClick={onRefreshUser}
            title="Sinkronkan ulang info user aktif dari Firefly III"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </aside>
  );
}
