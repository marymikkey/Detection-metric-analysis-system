export default function Card({ children, style: s = {} }) {
  return (
    <div style={{ background: 'var(--surf)', border: '1px solid var(--border)', borderRadius: 12, ...s }}>
      {children}
    </div>
  );
}
