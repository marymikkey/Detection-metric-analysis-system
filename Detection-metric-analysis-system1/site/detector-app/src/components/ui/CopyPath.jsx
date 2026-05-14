import { useState } from 'react';

export default function CopyPath({ path }) {
  const [copied, setCopied] = useState(false);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 5, minWidth: 0 }}>
      <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 200 }}>{path}</span>
      <button
        onClick={() => { navigator.clipboard?.writeText(path); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
        style={{ flexShrink: 0, fontSize: 9, color: copied ? 'var(--green)' : 'var(--muted)', background: 'transparent', border: '1px solid var(--border)', borderRadius: 3, padding: '1px 6px', cursor: 'pointer' }}
      >
        {copied ? '✓' : 'copy'}
      </button>
    </div>
  );
}
