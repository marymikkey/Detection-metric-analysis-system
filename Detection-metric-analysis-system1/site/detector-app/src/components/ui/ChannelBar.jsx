const CH_COLORS = { '1': '#fbbf24', '3': '#818cf8', '4': '#4ade80' };
const CH_LABELS = { '1': 'Grayscale (1ch)', '3': 'RGB (3ch)', '4': 'RGBA (4ch)' };

export default function ChannelBar({ channels }) {
  const entries = Object.entries(channels);
  const total = entries.reduce((a, [, v]) => a + v, 0) || 1;
  return (
    <div>
      <div style={{ display: 'flex', height: 10, borderRadius: 3, overflow: 'hidden', marginBottom: 8, gap: 1 }}>
        {entries.map(([ch, v]) => v > 0 && (
          <div key={ch} style={{ width: `${v / total * 100}%`, background: CH_COLORS[ch] || '#8c91b0' }} />
        ))}
      </div>
      {entries.map(([ch, v]) => (
        <div key={ch} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 4, color: v > 0 ? 'var(--text2)' : 'var(--dim)' }}>
          <span style={{ color: v > 0 ? (CH_COLORS[ch] || 'var(--muted)') : 'var(--dim)' }}>{CH_LABELS[ch] || `${ch}ch`}</span>
          <span style={{ fontFamily: 'IBM Plex Mono', color: v > 0 ? 'var(--text)' : 'var(--dim)' }}>{v.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}
