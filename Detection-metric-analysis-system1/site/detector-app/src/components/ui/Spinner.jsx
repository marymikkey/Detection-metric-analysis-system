import MonoLabel from './MonoLabel';

export default function Spinner({ label }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ width: 32, height: 32, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin .7s linear infinite', margin: '0 auto 12px' }} />
      <MonoLabel>{label}</MonoLabel>
    </div>
  );
}
