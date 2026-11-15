// Shared look for the 2-minute pitch scenes: the same palette, type and helpers as M3 and M4.
const W = 1920, H = 1080;
const C = { ch: '#0E0F12', bone: '#F2EEE6', ember: '#FF5A1F', water: '#3BA3FF', smoke: '#6B6F78', dim: '#2a2c33', panel: '#17191d' };
const cv = document.getElementById('c'), x = cv.getContext('2d');
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const seg = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const ease = (k) => k * k * k * (k * (k * 6 - 15) + 10);
const eOut = (k) => 1 - Math.pow(1 - k, 3);
const eBack = (k) => { const c1 = 1.5, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
function text(s, px, py, size, o = {}) {
  x.save(); x.font = `${o.weight || 400} ${size}px ${o.font || 'Inter'}`; x.fillStyle = o.color || C.bone;
  x.globalAlpha *= o.alpha == null ? 1 : o.alpha; x.textAlign = o.align || 'left'; x.textBaseline = o.baseline || 'alphabetic';
  x.letterSpacing = (o.spacing || 0) + 'px'; x.fillText(s, px, py); x.restore();
}
function tw(s, size, font = 'Inter', weight = 400, spacing = 0) { x.save(); x.font = `${weight} ${size}px ${font}`; x.letterSpacing = spacing + 'px'; const w = x.measureText(s).width; x.restore(); return w; }
function rect(px, py, w, h, r, fill, alpha = 1, stroke = null) {
  x.save(); x.globalAlpha *= alpha; x.beginPath(); x.roundRect(px, py, w, h, r);
  if (fill) { x.fillStyle = fill; x.fill(); } if (stroke) { x.strokeStyle = stroke; x.lineWidth = 1.5; x.stroke(); } x.restore();
}
function line(x0, y0, x1, y1, color, w = 2, dash = null, alpha = 1) {
  x.save(); x.strokeStyle = color; x.lineWidth = w; x.globalAlpha *= alpha; if (dash) x.setLineDash(dash); x.lineCap = 'round';
  x.beginPath(); x.moveTo(x0, y0); x.lineTo(x1, y1); x.stroke(); x.restore();
}
function dot(px, py, r, color, alpha = 1) { x.save(); x.globalAlpha *= alpha; x.fillStyle = color; x.beginPath(); x.arc(px, py, r, 0, Math.PI * 2); x.fill(); x.restore(); }
function ring(px, py, r, color, w = 2, alpha = 1, dash = null) { x.save(); x.globalAlpha *= alpha; x.strokeStyle = color; x.lineWidth = w; if (dash) x.setLineDash(dash); x.beginPath(); x.arc(px, py, r, 0, Math.PI * 2); x.stroke(); x.restore(); }
// a header that rises out of a mask, with a thin line under it
function header(s, t, t0, y = 150, size = 64, alpha = 1) {
  const k = eOut(seg(t, t0, t0 + 0.7));
  if (k <= 0 || alpha <= 0) return;
  x.save(); x.globalAlpha = alpha; x.beginPath(); x.rect(0, y - size * 1.05, W, size * 1.2); x.clip();
  text(s, W / 2, y + (1 - k) * size, size, { font: 'Anton', align: 'center', spacing: 2 });
  x.restore();
  const lw = tw(s, size, 'Anton', 400, 2) * ease(seg(t, t0 + 0.3, t0 + 1.1));
  line(W / 2 - lw / 2, y + 26, W / 2 + lw / 2, y + 26, C.bone, 1.5, null, 0.5 * alpha);
}
function bg() { x.setTransform(1, 0, 0, 1, 0, 0); x.globalAlpha = 1; x.fillStyle = C.ch; x.fillRect(0, 0, W, H); }
window.ready = Promise.all(['400 100px Anton', '400 20px Inter', '600 20px Inter', '400 20px JBM', '700 20px JBM'].map((f) => document.fonts.load(f)));
