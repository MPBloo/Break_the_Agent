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

// Each scene is timed on its voice-over (video/audio/vo_s*.mp3, placed by video/mix_audio.py): the
// comments give the scene time at which each part of the text is spoken.

// ------------------------------------------------------------------ scene 5 · the real environment (50 s)
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
  file: 's5_environment.mp4', duration: 50,
  init: (P) => P.present(true),
  // 0.5 "This is the environment..." · 3.7 "Everything we just described is here" · 8.5 "The briefing gives the full
  // physics" · 10.5 "only six numbers are hidden" · 12.5 "seven tools over MCP" · 27 "Neither compare nor simulate"
  // · 31.5 "Each fire requires its own heading..." · 47.3 end
  cam: [
    { t0: 0, t1: 0, full: true },
    { t0: 1.2, t1: 3.6, sel: ['#h-how', '.steps'], pad: 50, drift: 0.02 },
    { t0: 5.0, t1: 6.0, full: true },
    { t0: 7.4, t1: 7.4, lines: ['KNOWN PHYSICS', 'UNKNOWN TODAY'], pad: 50 },
    { t0: 10.0, t1: 11.4, lines: ['UNKNOWN TODAY', 'PHASE 1'], pad: 60, w: 1250 },
    { t0: 13.0, t1: 15.0, lines: ['CALCULATIONS', 'PHASE 2'], w: 1500, dx: 103 },
    { t0: 31.2, t1: 33.2, lines: ['PHASE 2', 'SCORING'], pad: 60, w: 1400, drift: 0.03 },
  ],
  cursor: [{ t: 5.4, sel: '#btn-present', dur: 0.8 }, { t: 7.0, hide: true }],
  clicks: [6.5],
  events: [{ t: 7.4, fade: 0.6, act: openBriefing }],
  marks: [
    { t0: 8.2, t1: 10.4, lines: ['KNOWN PHYSICS', 'UNKNOWN TODAY'] },
    { t0: 11.4, t1: 13.2, lines: ['drag', 'Nothing else'], pad: 10 },
    { t0: 26.5, t1: 31.4, lines: ['Neither tool', 'PHASE 2'] },
    { t0: 33.2, t1: 50.5, lines: ['hotspot imposes', 'fire. Use'] },
  ],
  cards: [{ t0: 14.5, t1: 30.5, x: 1180, y: 200, w: 660, html: TOOLS }],
};

// ------------------------------------------------------------------ scene 6 · the reward and the reference (61 s)
const REFCARD = card('The reference solution', [
  ['', 'Same seven tools, same budgets, same briefing. It never reads the physics code.'],
  ['', '6 test drops in clear air: 3 altitudes, 3 speeds'],
  ['', '4 test drops through the smoke, on the same flight paths'],
  ['', 'A least-squares fit on every measurement, wind readings included'],
  ['', 'Deterministic: anyone can reproduce its score'],
]);
const s6 = {
  file: 's6_reward_reference.mp4', duration: 61,
  init: openBriefing,
  // 0.5 the reward · 16.1 the reference · 43 "we degraded one decision at a time" · 58.5 end
  cam: [
    { t0: 0, t1: 0, lines: ['SCORING', 'zzz'], pad: 60, w: 1300 },
    { t0: 16, t1: 16, sel: ['#h-scores', row(1)], pad: 50, dy: 230, drift: 0.02 },
    { t0: 42.5, t1: 45, sel: [row(1), row(10)], pad: 40, w: 1500 },
  ],
  events: [{ t: 16, fade: 0.6, act: (P) => P.present(true) }],
  marks: [
    { t0: 1.2, t1: 8, lines: ['hotspot score', 'A hotspot'] },
    { t0: 8, t1: 15.6, lines: ['A hotspot', 'Mission score'] },
    { t0: 17, t1: 42.5, sel: row(1), pad: 6 },
    { t0: 45.5, t1: 48, sel: row(6), pad: 4 },
    { t0: 48, t1: 50.5, sel: row(7), pad: 4 },
    { t0: 50.5, t1: 53, sel: row(8), pad: 4 },
    { t0: 53, t1: 55.5, sel: row(9), pad: 4 },
    { t0: 55.5, t1: 61.5, sel: row(10), pad: 4 },
  ],
  cards: [{ t0: 18, t1: 42.5, x: 420, y: 560, w: 1080, html: REFCARD }],
};

// ------------------------------------------------------------------ scene 7 · the results (72 s)
const s7 = {
  file: 's7_results.mp4', duration: 72,
  init: (P) => P.present(true),
  // 0.5 "We ran each model..." · 10 Sonnet 4.5 and 5.5 · 22 Opus · 31.6 side by side · 51.5 "Opus comes close" · 68.5 end
  cam: [
    { t0: 0, t1: 0, sel: '.hero', pad: 50, drift: 0.04 },
    { t0: 8.5, t1: 11, sel: [row(1), row(4)], pad: 40, w: 1500, drift: 0.03 },
    { t0: 31, t1: 31, sel: ['#h-ep', '#bench'], pad: 40 },
    { t0: 37.4, t1: 40, sel: ['.scene-ref .scene-head', '#scene'], pad: 30, drift: 0.05 },
    { t0: 51.3, t1: 51.3, sel: [row(1), row(2)], pad: 60, w: 1500, drift: 0.03 },
  ],
  events: [
    { t: 31, fade: 0.6, act: (P) => P.episode('claude-opus-5-5-canadair', 1, 1) },
    { t: 33.2, act: (P) => P.episode('claude-sonnet-5-5-canadair', 2, 1) },
    { t: 36.1, act: (P) => P.clickText('#seg-focus button', 'Hotspot 3') },
    { t: 51.3, fade: 0.6, act: async () => {} },
  ],
  cursor: [
    { t: 31.8, sel: '#sel-agent', dur: 0.9 }, { t: 33.6, sel: '#sel-ep', dur: 0.7 },
    { t: 35.0, sel: '#seg-focus', at: [0.5, 0.5], dur: 0.8 }, { t: 37.2, hide: true },
  ],
  clicks: [32.9, 34.5, 36.0],
  tweens: [
    { key: 'yaw', t0: 40, t1: 51.3, from: -35, to: 20 },
    { key: 'elev', t0: 40, t1: 51.3, from: 32, to: 22 },
  ],
  marks: [
    { t0: 10.5, t1: 14.5, sel: row(4), pad: 4 },
    { t0: 14.5, t1: 21.5, sel: row(3), pad: 4 },
    { t0: 22, t1: 31.2, sel: row(2), pad: 4 },
    { t0: 41, t1: 45.5, sel: '.scene-ref .scene-head', pad: 6 },
    { t0: 45.5, t1: 51.2, sel: '.scene:not(.scene-ref) .scene-head', pad: 6 },
    { t0: 53, t1: 72.5, sel: row(2), pad: 4 },
  ],
};

// ------------------------------------------------------------------ scene 8 · why agents fail (101 s)
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
  file: 's8_why_agents_fail.mp4', duration: 101,
  init: (P) => P.present(true),
  // 0.8 counterfactuals · 21.3 Sonnet 4.5 · 35.5 Sonnet 5.5 · 50.5 Opus · 57.6 the common finding · 79.9 weather · 98.4 end
  cam: [
    { t0: 0, t1: 0, sel: ['#h-lost', '#lost'], pad: 40, drift: 0.05 },
    { t0: 21.4, t1: 21.4, sel: '#log', pad: 30 },
    { t0: 35.6, t1: 35.6, sel: '#tiles', pad: 40, w: 1500 },
    { t0: 43, t1: 45.5, sel: '#hyp', pad: 40, w: 1100 },
    { t0: 50.6, t1: 50.6, sel: '#hyp', pad: 40, w: 1100 },
    { t0: 57.5, t1: 60.5, sel: '#hyp', pad: 40, w: 950, drift: 0.04 },
    { t0: 79.8, t1: 79.8, sel: ['.controls', '#tiles'], pad: 40 },
  ],
  events: [
    { t: 21.4, fade: 0.6, act: async (P) => { await P.present(false); await P.episode('claude-sonnet-4-5', 1, 2); await tagLog(P); } },
    { t: 35.6, fade: 0.6, act: (P) => P.episode('claude-sonnet-5-5-canadair', 2, 1) },
    { t: 50.6, fade: 0.6, act: (P) => P.episode('claude-opus-5-5-canadair', 3, 2) },
    { t: 79.8, fade: 0.6, act: (P) => P.episode('claude-opus-5-5-weather', 1, 1) },
  ],
  scrolls: [
    { sel: '#log', t0: 21.4, t1: 21.41, to: '#e-lastcmp', offset: 160 },
    { sel: '#log', t0: 28.5, t1: 30.5, to: '#e-d0', offset: 40 },
  ],
  marks: [
    { t0: 5, t1: 10, sel: lostRow(3), pad: 4 },
    { t0: 10, t1: 15, sel: lostRow(2), pad: 4 },
    { t0: 15, t1: 21, sel: lostRow(1), pad: 4 },
    { t0: 22.5, t1: 28.5, sel: '#e-lastcmp', pad: 2 },
    { t0: 30.8, t1: 35.4, sel: ['#e-d0', '#e-d4'], pad: 2 },
    { t0: 37.5, t1: 43, sel: '#tiles > .tile:nth-child(4)', pad: 4 },
    { t0: 45.5, t1: 50.4, sel: hyp(5), pad: 2 },
    { t0: 51.5, t1: 57.5, sel: hyp(5), pad: 2 },
    { t0: 60.5, t1: 79.6, sel: hyp(5), pad: 2 },
    { t0: 81, t1: 90, sel: '#sel-agent', pad: 4 },
    { t0: 90, t1: 101.5, sel: ['#tiles > .tile:nth-child(1)', '#tiles > .tile:nth-child(2)'], pad: 4 },
  ],
};

// ------------------------------------------------------------------ scene 9 · trying to cheat (67 s)
const s9 = {
  file: 's9_reward_integrity.mp4', duration: 67,
  init: (P) => P.present(true),
  // 0.5 the baselines · 20.7 the seed exploit · 55 transcripts replayed · 63.6 end
  cam: [
    { t0: 0, t1: 0, sel: [row(10), row(15)], pad: 40, w: 1500, drift: 0.03 },
    { t0: 20.5, t1: 20.5, sel: ['h2', 'table'], pad: 40, align: 'top' },
    { t0: 21.2, t1: 23.5, sel: 'table tr:nth-child(10)', w: 1500 },
    { t0: 53, t1: 55.5, sel: ['table tr:nth-child(11)', 'p:last-child'], pad: 60, w: 1500 },
  ],
  events: [{ t: 20.5, fade: 0.6, act: async () => {}, url: readmePage() }],
  marks: [
    { t0: 1.5, t1: 4.5, sel: row(15), pad: 4 },
    { t0: 4.5, t1: 7.5, sel: row(12), pad: 4 },
    { t0: 7.5, t1: 10.5, sel: row(11), pad: 4 },
    { t0: 10.5, t1: 13.5, sel: row(13), pad: 4 },
    { t0: 13.5, t1: 17, sel: row(14), pad: 4 },
    { t0: 23.5, t1: 53, sel: 'table tr:nth-child(10)', pad: 0 },
    { t0: 55.5, t1: 67.5, sel: 'p:last-child', pad: 6 },
  ],
};

module.exports = { s5, s6, s7, s8, s9 };
