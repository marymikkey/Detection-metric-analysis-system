import { useRef, useEffect } from 'react';

export default function FakeIntensityChart({ seed = 1, height = 130 }) {
  const ref = useRef(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext('2d'), W = c.width, H = c.height;
    ctx.fillStyle = '#0d0f1c'; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = '#1c1f35'; ctx.lineWidth = .5;
    for (let x = 0; x < W; x += 32) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H - 14); ctx.stroke(); }
    for (let y = 0; y < H - 14; y += 24) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    let s = seed * 7919;
    const rng = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
    [
      { color: '#f87171', mu: .55, sig: .09 },
      { color: '#4ade80', mu: .5,  sig: .1  },
      { color: '#38bdf8', mu: .4,  sig: .08 },
    ].forEach(({ color, mu, sig }) => {
      const pts = Array.from({ length: 256 }, (_, i) => {
        const x = i / 255;
        return Math.exp(-Math.pow(x - mu, 2) / (2 * sig * sig)) * (0.85 + rng() * .15);
      });
      const mx = Math.max(...pts);
      ctx.globalAlpha = .5; ctx.fillStyle = color;
      ctx.beginPath(); ctx.moveTo(0, H - 14);
      pts.forEach((v, i) => {
        const px = i / 255 * W, py = (H - 14) - (v / mx) * (H - 22);
        i === 0 ? ctx.moveTo(px, H - 14) : ctx.lineTo(px, py);
      });
      ctx.lineTo(W, H - 14); ctx.closePath(); ctx.fill();
      ctx.globalAlpha = 1; ctx.strokeStyle = color; ctx.lineWidth = 1.3;
      ctx.beginPath();
      pts.forEach((v, i) => { const px = i / 255 * W, py = (H - 14) - (v / mx) * (H - 22); i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py); });
      ctx.stroke();
    });
    ctx.fillStyle = '#4e5270'; ctx.font = '8px IBM Plex Mono';
    [0, 64, 128, 192, 255].forEach(v => ctx.fillText(v, (v / 255) * (W - 8), H - 2));
  }, [seed]);

  return <canvas ref={ref} width={460} height={height} style={{ width: '100%', height, display: 'block', borderRadius: 5 }} />;
}
