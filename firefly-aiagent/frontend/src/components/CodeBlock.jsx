import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

// ── Code Block with Copy ────────────────────────────────────
export default function CodeBlock({ language, value }) {
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
