import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

// ── Copy Message Button ──────────────────────────────────────
export default function MessageCopyButton({ content }) {
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
