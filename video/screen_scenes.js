// Scenes 5 to 9 of the film: the real results site, filmed by video/screen.js.
// Times are seconds within the scene; each scene is timed to its voice-over in the video script.
//   cam:    camera moves {t0, t1, <framing>}: arrive on the framing between t0 and t1, then hold (drift = slow push-in)
//   events: stateful steps at time t (fade: cross-fade over that many seconds to hide a layout change)
//   marks:  highlights that follow the camera; cards: overlay cards in screen space
//   cursor: pointer keyframes {t, sel} (hide: true to fade it out); clicks: times of a click ripple
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');

const row = (i) => `#scores > .row:nth-child(${i})`;          // 1 reference, 2 Opus 5.5, 3 Sonnet 5.5, 4 Sonnet 4.5, 5 Haiku 5.5,
const lostRow = (i) => `#lost > .row:nth-child(${i})`;       // 6-10 heuristics, 11-15 baselines
const hyp = (i) => `#hyp tr:nth-child(${i})`;                // 2 drag, 3 wind speed, 4 wind direction, 5 shear, 6 veer, 7 updraft
const target = (i) => `#targets tr:nth-child(${i + 1})`;

// the briefing, one block per line so the camera and highlights can address lines
async function openBriefing(P) {
  await P.present(false);
  await P.ev(() => {
    const pre = document.getElementById('brief');
    if (!pre.querySelector('.bl')) {
      const lines = pre.textContent.split('\n');
      pre.textContent = '';
      lines.forEach((l) => { const s = document.createElement('span'); s.className = 'bl'; s.style.display = 'block'; s.textContent = l || ' '; pre.appendChild(s); });
    }
    pre.closest('details').open = true;
  });
}

const card = (title, items) => `<div style="font-size:15px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:14px">${title}</div>` +
  items.map(([k, v]) => `<div style="display:grid;grid-template-columns:${k ? '210px 1fr' : '1fr'};gap:14px;padding:8px 0;border-top:1px solid var(--grid)">${k ? `<code style="font-family:ui-monospace,Menlo,monospace;color:var(--s1);font-size:20px">${k}</code>` : ''}<span>${v}</span></div>`).join('');

// ------------------------------------------------------------------ the README's reward-integrity section, as a page
function readmePage() {
  const md = fs.readFileSync(path.join(ROOT, 'README.md'), 'utf8');
  const sec = md.split('\n## Reward integrity')[1].split('\n## ')[0];
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const inline = (s) => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>');
  const blocks = sec.trim().split(/\n\s*\n/);
  let body = '<h2>Reward integrity</h2>';
  blocks.forEach((b) => {
    const lines = b.trim().split('\n');
    if (lines[0].startsWith('|')) {
      const cells = (l) => l.split('|').slice(1, -1).map((c) => c.trim());
      body += '<table><tr>' + cells(lines[0]).map((c) => `<th>${inline(c)}</th>`).join('') + '</tr>' +
        lines.slice(2).map((l) => '<tr>' + cells(l).map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') + '</table>';
    } else body += `<p>${inline(lines.join(' '))}</p>`;
  });
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
:root { --bg:#0c0e11; --surface:#17191d; --ink:#eef0f3; --ink-2:#c0c5cd; --muted:#868d98; --s1:#3987e5; --axis:#3b3f47; --grid:#2a2d33; }
body { margin:0; background:var(--bg); color:var(--ink); font:18px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif; }
.wrap { max-width:1380px; margin:0 auto; padding:70px 40px; }
.file { color:var(--muted); font-size:16px; letter-spacing:.06em; margin-bottom:18px; font-family:ui-monospace,Menlo,monospace; }
h2 { font-size:34px; margin:0 0 18px; padding-bottom:12px; border-bottom:1px solid var(--axis); }
p { color:var(--ink-2); margin:18px 0; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.88em; background:var(--surface); border:1px solid var(--grid); border-radius:6px; padding:1px 6px; }
table { border-collapse:collapse; width:100%; margin:22px 0; background:var(--surface); border-radius:12px; overflow:hidden; }
th, td { text-align:left; vertical-align:top; padding:13px 18px; border-top:1px solid var(--grid); }
th { color:var(--muted); font-weight:600; font-size:15px; text-transform:uppercase; letter-spacing:.08em; border-top:none; }
td:first-child { width:52%; }
</style></head><body><div class="wrap"><div class="file">README.md</div>${body}</div></body></html>`;
  const file = path.join(ROOT, 'video', 'out', 'readme_integrity.html');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, html);
  return 'video/out/readme_integrity.html';
}

// ------------------------------------------------------------------ scene 5 · the real environment (2:30 - 3:30)
const TOOLS = card('Seven tools, over MCP', [
  ['get_mission', 'read the briefing and the budgets'],
  ['test_drop', 'drop a test load, see where it lands'],
  ['compare', 'check a hypothesis against the test drops'],
  ['simulate', 'predict any drop under a hypothesis'],
  ['begin_operation', 'end calibration, reveal the five fires'],
  ['drop', 'one water drop per fire, no feedback'],
  ['declare_done', 'end the mission'],
]);
const s5 = {
  file: 's5_environment.mp4', duration: 60,
  init: (P) => P.present(true),
  cam: [
    { t0: 0, t1: 0, full: true },
    { t0: 3, t1: 8, sel: '.hero .head', pad: 70, drift: 0.04 },
    { t0: 11, t1: 15, sel: ['#h-how', '.steps'], pad: 50, drift: 0.03 },
    { t0: 16, t1: 17.6, full: true },
    { t0: 20, t1: 20, lines: ['CANADAIR', 'KNOWN PHYSICS'], pad: 50, align: 'top' },
    { t0: 23, t1: 26, lines: ['KNOWN PHYSICS', 'UNKNOWN TODAY'], pad: 50 },
    { t0: 29, t1: 32, lines: ['UNKNOWN TODAY', 'PHASE 1'], pad: 60, w: 1250 },
    { t0: 38, t1: 41, lines: ['CALCULATIONS', 'PHASE 2'], w: 1500, dx: 103 },
    { t0: 50, t1: 53, lines: ['PHASE 2', 'SCORING'], pad: 60, w: 1400 },
  ],
  cursor: [{ t: 17.4, sel: '#btn-present', dur: 0.9 }, { t: 19.8, hide: true }],
  clicks: [19.0],
  events: [
    { t: 20, fade: 0.7, act: openBriefing },
  ],
  marks: [
    { t0: 24.5, t1: 29.5, lines: ['KNOWN PHYSICS', 'UNKNOWN TODAY'] },
    { t0: 32, t1: 38.5, lines: ['drag', 'Nothing else'], pad: 10 },
    { t0: 45, t1: 50.5, lines: ['Neither tool', 'PHASE 2'] },
    { t0: 54, t1: 60.5, lines: ['hotspot imposes', 'fire. Use'] },
  ],
  cards: [{ t0: 39.5, t1: 50, x: 1180, y: 200, w: 660, html: TOOLS }],
};

// ------------------------------------------------------------------ scene 6 · the reward and the reference (3:30 - 4:30)
const REFCARD = card('The reference solution', [
  ['', 'Same seven tools, same budgets, same briefing. It never reads the physics code.'],
  ['', '6 test drops in clear air: 3 altitudes, 3 speeds'],
  ['', '4 test drops through the smoke, on the same flight paths'],
  ['', 'A least-squares fit on every measurement, wind readings included'],
  ['', 'Deterministic: anyone can reproduce its score'],
]);
const s6 = {
  file: 's6_reward_reference.mp4', duration: 60,
  init: openBriefing,
  cam: [
    { t0: 0, t1: 0, lines: ['SCORING', 'zzz'], pad: 60, w: 1300 },
    { t0: 13, t1: 13, sel: ['#h-scores', row(1)], pad: 50, dy: 230, drift: 0.02 },
    { t0: 35, t1: 39, sel: [row(1), row(10)], pad: 40, w: 1500 },
  ],
  events: [{ t: 13, fade: 0.7, act: (P) => P.present(true) }],
  marks: [
    { t0: 1.5, t1: 7, lines: ['hotspot score', 'A hotspot'] },
    { t0: 7, t1: 12.5, lines: ['A hotspot', 'Mission score'] },
    { t0: 14.5, t1: 34, sel: row(1), pad: 6 },
    { t0: 40, t1: 43, sel: row(6), pad: 4 },
    { t0: 43, t1: 46, sel: row(7), pad: 4 },
    { t0: 46, t1: 49, sel: row(8), pad: 4 },
    { t0: 49, t1: 52, sel: row(9), pad: 4 },
    { t0: 52, t1: 60.5, sel: row(10), pad: 4 },
  ],
  cards: [{ t0: 17, t1: 34, x: 420, y: 560, w: 1080, html: REFCARD }],
};

// ------------------------------------------------------------------ scene 7 · the results (4:30 - 5:50)
const s7 = {
  file: 's7_results.mp4', duration: 80,
  init: (P) => P.present(true),
  cam: [
    { t0: 0, t1: 0, sel: '.hero', pad: 50, drift: 0.04 },
    { t0: 8, t1: 12, sel: [row(1), row(4)], pad: 40, w: 1500, drift: 0.03 },
    { t0: 28, t1: 28, sel: ['#h-ep', '#bench'], pad: 40 },
    { t0: 34.5, t1: 38, sel: ['.scene-ref .scene-head', '#scene'], pad: 30, drift: 0.06 },
    { t0: 62, t1: 65, sel: ['#tiles', '#targets'], pad: 40 },
    { t0: 72, t1: 72, sel: [row(1), row(2)], pad: 60, w: 1500, drift: 0.03 },
  ],
  events: [
    { t: 28, fade: 0.7, act: async (P) => { await P.episode('claude-opus-5-5-canadair', 1, 1);} },
    { t: 30.2, act: (P) => P.episode('claude-sonnet-5-5-canadair', 2, 1) },
    { t: 33.2, act: (P) => P.clickText('#seg-focus button', 'Hotspot 3') },
    { t: 72, fade: 0.7, act: async () => {} },
  ],
  cursor: [
    { t: 28.8, sel: '#sel-agent', dur: 0.9 }, { t: 30.6, sel: '#sel-ep', dur: 0.7 },
    { t: 32.0, sel: '#seg-focus', at: [0.5, 0.5], dur: 0.8 }, { t: 34.3, hide: true },
  ],
  clicks: [29.9, 31.5, 33.1],
  tweens: [
    { key: 'yaw', t0: 38, t1: 62, from: -35, to: 30 },
    { key: 'elev', t0: 38, t1: 62, from: 32, to: 20 },
  ],
  marks: [
    { t0: 13, t1: 17.5, sel: row(4), pad: 4 },
    { t0: 17.5, t1: 22, sel: row(3), pad: 4 },
    { t0: 22, t1: 27.5, sel: row(2), pad: 4 },
    { t0: 40, t1: 47, sel: '.scene-ref .scene-head', pad: 6 },
    { t0: 47, t1: 55, sel: '#scene', pad: 0, at: null },
    { t0: 66, t1: 71.5, sel: target(3), pad: 4 },
    { t0: 74, t1: 80.5, sel: row(2), pad: 4 },
  ],
};
// the 3D view of hotspot 3 comes from a cursor-picked menu entry; mark the agent caption, not the whole canvas
s7.marks[4] = { t0: 47, t1: 55, sel: '.scene:not(.scene-ref) .scene-head', pad: 6 };

// ------------------------------------------------------------------ scene 8 · why agents fail (5:50 - 7:40)
async function tagLog(P) {
  await P.ev(() => {
    const es = [...document.querySelectorAll('#log .e')];
    const tool = (e) => (e.querySelector('.t') || {}).textContent;
    const cmp = es.filter((e) => tool(e) === 'compare' && !e.classList.contains('op'));
    if (cmp.length) cmp[cmp.length - 1].id = 'e-lastcmp';
    es.filter((e) => tool(e) === 'drop').forEach((e, i) => { e.id = 'e-d' + i; });
  });
}
const s8 = {
  file: 's8_why_agents_fail.mp4', duration: 110,
  init: (P) => P.present(true),
  cam: [
    { t0: 0, t1: 0, sel: ['#h-lost', '#lost'], pad: 40, drift: 0.05 },
    { t0: 24, t1: 24, sel: '#log', pad: 30 },
    { t0: 42, t1: 45, sel: ['#hyp'], pad: 40, w: 1100 },
    { t0: 57, t1: 57, sel: '#tiles', pad: 40, w: 1500 },
    { t0: 65, t1: 68, sel: '#fit', pad: 40, w: 1100 },
    { t0: 74, t1: 77, sel: '#hyp', pad: 40, w: 1100 },
    { t0: 82, t1: 82, sel: '#hyp', pad: 40, w: 1100, drift: 0.03 },
    { t0: 92, t1: 95, sel: '#targets', pad: 40, w: 1300 },
    { t0: 100, t1: 103, sel: '#hyp', pad: 40, w: 1000, drift: 0.04 },
  ],
  events: [
    { t: 24, fade: 0.7, act: async (P) => { await P.present(false); await P.episode('claude-sonnet-4-5', 1, 2); await tagLog(P); } },
    { t: 57, fade: 0.7, act: (P) => P.episode('claude-sonnet-5-5-canadair', 2, 1) },
    { t: 82, fade: 0.7, act: (P) => P.episode('claude-opus-5-5-canadair', 3, 2) },
  ],
  scrolls: [
    { sel: '#log', t0: 24, t1: 24.01, to: '#e-lastcmp', offset: 160 },
    { sel: '#log', t0: 34, t1: 37, to: '#e-d0', offset: 40 },
  ],
  marks: [
    { t0: 6, t1: 12, sel: lostRow(3), pad: 4 },
    { t0: 12, t1: 18, sel: lostRow(2), pad: 4 },
    { t0: 18, t1: 23.5, sel: lostRow(1), pad: 4 },
    { t0: 26, t1: 34, sel: '#e-lastcmp', pad: 2 },
    { t0: 37.5, t1: 42, sel: ['#e-d0', '#e-d4'], pad: 2 },
    { t0: 46, t1: 50, sel: hyp(2), pad: 2 },
    { t0: 50, t1: 56.5, sel: hyp(4), pad: 2 },
    { t0: 59, t1: 64.5, sel: '#tiles > .tile:nth-child(4)', pad: 4 },
    { t0: 78, t1: 81.5, sel: hyp(5), pad: 2 },
    { t0: 85, t1: 91.5, sel: hyp(5), pad: 2 },
    { t0: 104, t1: 110.5, sel: hyp(5), pad: 2 },
  ],
};

// ------------------------------------------------------------------ scene 9 · trying to cheat (7:40 - 9:00)
const s9 = {
  file: 's9_reward_integrity.mp4', duration: 80,
  init: (P) => P.present(true),
  cam: [
    { t0: 0, t1: 0, sel: [row(10), row(15)], pad: 40, w: 1500, drift: 0.03 },
    { t0: 28, t1: 28, sel: ['h2', 'table'], pad: 40, align: 'top' },
    { t0: 55, t1: 58, sel: 'table tr:nth-child(10)', w: 1500 },
    { t0: 69, t1: 72, sel: ['table tr:nth-child(11)', 'p:last-child'], pad: 60, w: 1500 },
  ],
  events: [{ t: 28, fade: 0.7, act: async () => {}, url: readmePage() }],
  marks: [
    { t0: 3, t1: 7, sel: row(15), pad: 4 },
    { t0: 7, t1: 11, sel: row(12), pad: 4 },
    { t0: 11, t1: 15, sel: row(11), pad: 4 },
    { t0: 15, t1: 19, sel: row(13), pad: 4 },
    { t0: 19, t1: 24, sel: row(14), pad: 4 },
    { t0: 30, t1: 34, sel: 'table tr:nth-child(2)', pad: 0 },
    { t0: 34, t1: 38, sel: 'table tr:nth-child(3)', pad: 0 },
    { t0: 38, t1: 42, sel: 'table tr:nth-child(4)', pad: 0 },
    { t0: 42, t1: 46, sel: 'table tr:nth-child(5)', pad: 0 },
    { t0: 46, t1: 50, sel: 'table tr:nth-child(7)', pad: 0 },
    { t0: 50, t1: 54.5, sel: 'table tr:nth-child(8)', pad: 0 },
    { t0: 58, t1: 69, sel: 'table tr:nth-child(10)', pad: 0 },
    { t0: 73, t1: 80.5, sel: 'p:last-child', pad: 6 },
  ],
};

module.exports = { s5, s6, s7, s8, s9 };
