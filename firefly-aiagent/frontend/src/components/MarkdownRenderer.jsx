import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock.jsx';

// ── Enhanced Markdown Renderer using react-markdown ─────────
export default function MarkdownRenderer({ content, isStreaming = false }) {
  return (
    <div className={`markdown-wrapper ${isStreaming ? 'is-streaming' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ ...props }) => (
            <div className="table-responsive-wrapper">
              <table className="custom-markdown-table" {...props} />
            </div>
          ),
          thead: ({ ...props }) => <thead className="custom-thead" {...props} />,
          th: ({ ...props }) => <th className="custom-th" {...props} />,
          tr: ({ ...props }) => <tr className="custom-tr" {...props} />,
          td: ({ ...props }) => <td className="custom-td" {...props} />,
          blockquote: ({ ...props }) => (
            <div className="custom-callout-card">
              <div className="callout-accent-bar" />
              <blockquote className="callout-body" {...props} />
            </div>
          ),
          code: ({ inline, className, children, ...props }) => {
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
          p: ({ children, ...props }) => <p className="markdown-p" {...props}>{children}</p>,
          ul: ({ ...props }) => <ul className="custom-ul" {...props} />,
          ol: ({ ...props }) => <ol className="custom-ol" {...props} />,
          li: ({ ...props }) => <li className="custom-li" {...props} />,
          h1: ({ ...props }) => <h1 className="markdown-h1" {...props} />,
          h2: ({ ...props }) => <h2 className="markdown-h2" {...props} />,
          h3: ({ ...props }) => <h3 className="markdown-h3" {...props} />,
          h4: ({ ...props }) => <h4 className="markdown-h4" {...props} />,
          a: ({ ...props }) => (
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
