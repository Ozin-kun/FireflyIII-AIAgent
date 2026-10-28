import { useState } from 'react';
import { Brain, CheckCircle2, ChevronDown, ChevronRight } from 'lucide-react';

// Collapsible Agent Cognition Accordion Component
export default function CognitionAccordion({ plan = [], actions = [], reflection = '' }) {
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
