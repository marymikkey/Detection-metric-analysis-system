export default function SelectField({ label, value, onChange, options, strOpts = false }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 7 }}>{label}</div>
      <select
        value={value}
        onChange={e => onChange(strOpts ? e.target.value : +e.target.value)}
        style={{ width: '100%', padding: '7px 11px', background: 'var(--surf2)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', fontFamily: 'IBM Plex Mono', fontSize: 12, cursor: 'pointer' }}
      >
        {options.map(o => <option key={o}>{o}</option>)}
      </select>
    </div>
  );
}
