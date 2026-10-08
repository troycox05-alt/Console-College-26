// Console College — desktop window front end.
// Reads what the game prints from the local bridge (play.py), draws it, and sends back what you click or type.
"use strict";

const $ = (id) => document.getElementById(id);
// Phone/tablet (mobile_web.py loads mobile.js first, which sets CC_MOBILE). The desktop window never sets it.
const MOBILE = window.CC_MOBILE === true;
function focusLine() { if (!MOBILE) lineEl.focus(); }   // a phone keyboard shouldn't pop up on every tap
const screenEl = $("screen"), wrapEl = $("screenwrap"), quickEl = $("quick"), barEl = $("bar"), lineEl = $("line");

const S = {
  since: 0,
  screens: [""],          // raw text of each screen (a clear starts a new one)
  views: [null],          // native web screens (webview.py): the data each screen sent, if any
  marks: [0],             // where the text after that view starts (prompts, notes under the native screen)
  view: null,             // null = live; otherwise an index into screens
  waiting: false,
  prompt: "",
  done: false,
  dirty: true,
  sent: [], sentIdx: -1,
  prefs: { zoom: 1, theme: "dark", sound: true, sidebar: true, tab: "home", shut: [], sbw: 330 },
  players: [], nameKey: "", nameRe: null, byName: new Map(),
  links: new Map(), linkKey: null, cardStack: [],
  inbox: null,
  lastTD: 0,
};
const MAX_SCREENS = 40;
const ECHO_ON = "\x1b[1;96m", RESET = "\x1b[0m";

// ═══ Talking to the game ════════════════════════════════════════════════════

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", body: JSON.stringify(body),
    headers: { "Content-Type": "application/json" } };
  const r = await fetch(path, opt);
  return r.json();
}

async function poll() {
  try {
    const catchUp = S.since === 0;               // the first poll replays old events: don't reopen old copy boxes
    const d = await api(`/poll?since=${S.since}`);
    if (d && d.error === "login") { location.reload(); return; }
    for (const [seq, kind, text] of d.events) {
      S.since = seq;
      if (kind === "out") { cur(text); sounds(text); }
      else if (kind === "echo") cur(ECHO_ON + text + RESET);
      else if (kind === "clear") newScreen();
      else if (kind === "wait") { S.prompt = text; refreshState(); }
      else if (kind === "done") S.done = true;
      else if (kind === "restart") { location.reload(); return; }
      else if (kind === "clip") { if (!catchUp) showClip(text); }
      else if (kind === "view" || kind === "add") {
        try {
          const v = JSON.parse(text), i = S.screens.length - 1;
          if (kind === "view") S.views[i] = { kind: v.kind, data: v.data, adds: [] };
          else if (S.views[i]) S.views[i].adds.push(v);
          S.marks[i] = S.screens[i].length;
        } catch (e) { /* a view that doesn't parse: the text is still there */ }
      }
    }
    if (d.events.length) S.dirty = true;
    if (d.waiting !== S.waiting) { S.waiting = d.waiting; S.dirty = true; }
    if (d.done && !S.done) { S.done = true; S.dirty = true; }
  } catch (e) { /* the game is starting or gone */ }
  setTimeout(poll, S.waiting ? 120 : 40);
}

function cur(text) { S.screens[S.screens.length - 1] += text; }
function newScreen() {
  S.screens.push("");
  S.views.push(null);
  S.marks.push(0);
  if (S.screens.length > MAX_SCREENS) {
    S.screens.shift();
    S.views.shift();
    S.marks.shift();
    if (S.view !== null) S.view = Math.max(0, S.view - 1);
  }
}

function send(line) {
  if (S.done) return;
  if (S.view !== null) goLive();
  api("/send", { line });
  if (line) { S.sent.push(line); if (S.sent.length > 100) S.sent.shift(); }
  S.sentIdx = -1;
  S.waiting = false;
  S.dirty = true;
}

// ═══ ANSI → HTML ════════════════════════════════════════════════════════════

const XTERM = (() => {
  const base = ["#000000","#cd0000","#00cd00","#cdcd00","#0000ee","#cd00cd","#00cdcd","#e5e5e5",
                "#7f7f7f","#ff0000","#00ff00","#ffff00","#5c5cff","#ff00ff","#00ffff","#ffffff"];
  const out = base.slice();
  const lv = [0, 95, 135, 175, 215, 255];
  for (let r = 0; r < 6; r++) for (let g = 0; g < 6; g++) for (let b = 0; b < 6; b++)
    out.push(`rgb(${lv[r]},${lv[g]},${lv[b]})`);
  for (let i = 0; i < 24; i++) { const v = 8 + i * 10; out.push(`rgb(${v},${v},${v})`); }
  return out;
})();

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const KEY_RE_SRC = String.raw`\[(Enter|[A-Za-z0-9$?+/]{1,4})\]|\b([1-8]) (?=HOME|SCHEDULE|TEAM|RECRUITING|RANKINGS|COACH|MEDIA|SYSTEM)`;

function sgr(st, codes) {
  const c = codes.length ? codes : [0];
  for (let i = 0; i < c.length; i++) {
    const n = c[i];
    if (n === 0) { st.fg = null; st.bg = null; st.b = st.d = st.i = st.u = false; }
    else if (n === 1) st.b = true;
    else if (n === 2) st.d = true;
    else if (n === 3) st.i = true;
    else if (n === 4) st.u = true;
    else if (n === 22) st.b = st.d = false;
    else if (n === 23) st.i = false;
    else if (n === 24) st.u = false;
    else if ((n >= 30 && n <= 37) || (n >= 90 && n <= 97)) st.fg = `var(--c${n})`;
    else if (n === 39) st.fg = null;
    else if ((n >= 40 && n <= 47) || (n >= 100 && n <= 107)) st.bg = `var(--b${n})`;
    else if (n === 49) st.bg = null;
    else if ((n === 38 || n === 48) && c[i + 1] === 5) {
      const idx = c[i + 2];
      let col = XTERM[idx] || null;
      if (idx >= 232 && idx <= 255 && document.documentElement.dataset.theme === "light") {
        const v = 255 - (8 + (idx - 232) * 10);              // the gray ramp turns over in the light theme:
        col = `rgb(${v},${v - 2},${v - 6})`;                  // charcoal bars become paper, faint text stays faint
      }
      if (n === 38) st.fg = col; else st.bg = col;
      i += 2;
    } else if ((n === 38 || n === 48) && c[i + 1] === 2) {                 // 24-bit color (the faces)
      const col = `rgb(${c[i + 2] | 0},${c[i + 3] | 0},${c[i + 4] | 0})`;
      if (n === 38) st.fg = col; else st.bg = col;
      i += 4;
    }
  }
}

function spanOpen(st) {
  const cls = [st.b && "b", st.d && "d", st.i && "i", st.u && "u"].filter(Boolean).join(" ");
  let style = "";
  if (st.fg) style += `color:${st.fg};`;
  if (st.bg) style += `background:${st.bg};`;
  if (!cls && !style) return null;
  return `<span${cls ? ` class="${cls}"` : ""}${style ? ` style="${style}"` : ""}>`;
}

// A run of capitalized words ("Texas Tech", "Jacob Hobbs", "Miami (OH)", "A&amp;M"): every name the
// game links (links.py) is looked up inside it, longest first, so "Dallas Bonner" beats "Dallas".
const WORD = String.raw`[\p{Lu}][\p{L}\p{M}\p{N}'’.&;\-]*`;
const RUN_SRC = String.raw`(?<![\p{L}\p{M}\p{N}'’&])(${WORD}(?: (?:${WORD}|\([A-Z]{2}\)|of|de|la|du|van|von|der|and))*…?)`;
const RE_CACHE = {
  keys: new RegExp(KEY_RE_SRC, "gu"),
  withNames: new RegExp(KEY_RE_SRC + "|" + RUN_SRC, "gu"),
};
const TRAIL = /^(.*?)((?:['’]s)?[.,;:!?)…]*)$/u;
function lookup(key) {
  return S.links.get(key) || S.byName.get(key);
}
// A name cut short to fit a column ("South Carol…"): the one linked name that starts that way, if only one does.
const PREFIX = new Map();
function byPrefix(pre) {
  if (pre.length < 4) return null;
  if (PREFIX.has(pre)) return PREFIX.get(pre);
  let found = null;
  for (const [k, id] of S.links) {
    if (id !== "-" && k.startsWith(pre) && k.length > pre.length) {
      if (found && found !== id) { found = null; break; }
      found = id;
    }
  }
  PREFIX.set(pre, found);
  return found;
}
function linkRun(run) {
  if (run.endsWith("…")) {
    const t = run.slice(0, -1).split(" ");
    for (let i = 0; i < t.length; i++) {                 // the longest cut-off tail that names one thing
      const pre = t.slice(i).join(" "), id = byPrefix(pre);
      if (id) return (i ? linkRun(t.slice(0, i).join(" ")) + " " : "") + `<span class="n" data-p="${id}">${pre}…</span>`;
    }
    return linkRun(run.slice(0, -1)) + "…";
  }
  const t = run.split(" "), out = [];
  let i = 0;
  while (i < t.length) {
    let hit = null;
    for (let j = Math.min(t.length, i + 7); j > i && !hit; j--) {
      const key = t.slice(i, j).join(" ");
      let id = lookup(key);
      if (id) { hit = [j, key, ""]; break; }
      const m = TRAIL.exec(key);
      if (m && m[2] && m[1] && (id = lookup(m[1]))) hit = [j, m[1], m[2]];
    }
    if (hit) {
      const [j, name, rest] = hit, id = lookup(name);
      out.push(id === "-" ? name + rest : `<span class="n" data-p="${id}">${name}</span>${rest}`);   // "-": read whole, no page
      i = j;
    } else { out.push(t[i]); i++; }
  }
  return out.join(" ");
}

// A face is rows of "▀" with the top pixel as text color and the bottom as background. In a web page the line
// spacing would leave thin seams between rows, so each such cell is drawn as a two-tone box that fills its line.
function halfBlocks(text, st) {
  if (!st.fg || !st.bg || text.indexOf("▀") < 0) return text;
  return text.replace(/▀/g, `<i class="hb" style="--t:${st.fg};--b:${st.bg}"></i>`);
}

function decorate(text, opts) {
  // text is already HTML-escaped. Turn [K] into buttons and known names into links.
  const linking = opts.names && (S.links.size || S.byName.size);
  const re = linking ? RE_CACHE.withNames : RE_CACHE.keys;
  re.lastIndex = 0;
  return text.replace(re, (m, key, tab, run) => {
    if (key !== undefined) return opts.keys === false ? m : `<span class="k" data-k="${key}">${m}</span>`;
    if (tab !== undefined) return opts.keys === false ? m : `<span class="k kt" data-k="${tab}">${m}</span>`;
    return run !== undefined ? linkRun(run) : m;
  });
}

function renderAnsi(raw, opts = { names: true }) {
  const st = { fg: null, bg: null, b: false, d: false, i: false, u: false };
  const lines = raw.split("\n");
  const out = [];
  const fold = false;                                          // footers stay on screen (no button row)
  for (let line of lines) {
    if (line.charCodeAt(0) === 0x2063) {
      if (fold) continue;
      line = line.slice(1);
    }
    if (line.includes("\r")) {                              // a line that rewrote itself (progress counters)
      const bits = line.split("\r").filter((x) => x.length);
      line = bits.length ? bits[bits.length - 1] : "";
    }
    let html = "", open = spanOpen(st);
    if (open) html += open;
    const re = /\x1b\[([0-9;?]*)([A-Za-z])/g;
    let last = 0, m;
    while ((m = re.exec(line))) {
      if (m.index > last) html += decorate(halfBlocks(esc(line.slice(last, m.index)), st), opts);
      if (open) { html += "</span>"; open = null; }
      if (m[2] === "m") sgr(st, m[1] ? m[1].split(";").map(Number) : []);
      open = spanOpen(st);
      if (open) html += open;
      last = re.lastIndex;
    }
    if (last < line.length) html += decorate(halfBlocks(esc(line.slice(last)), st), opts);
    if (open) html += "</span>";
    out.push(html);
  }
  return out.join("\n");
}

const strip = (s) => s.replace(/\x1b\[[0-9;?]*[A-Za-z]/g, "").replace(/\u2063/g, "");

// ═══ Drawing ════════════════════════════════════════════════════════════════

function draw() {
  if (!S.dirty) return requestAnimationFrame(draw);
  S.dirty = false;
  const live = S.view === null;
  const idx = live ? S.screens.length - 1 : S.view;
  let raw = S.screens[idx] || "";
  const full = raw;
  // A native web screen (native.js) replaces the text the game printed for it; anything printed
  // after it (prompts, notes) still shows underneath as text.
  const nv = S.views[idx];
  const useNative = !!(nv && window.NATIVE && window.NATIVE.has(nv.kind) && S.prefs.native !== false);
  if (useNative) {
    window.NATIVE.render(nv, live);
    raw = raw.slice(S.marks[idx] || 0).split("\n")            // drop divider lines: they wrap into noise on a phone
      .filter((l) => { const t = strip(l); return !t.trim() || !/^[\s─━═▀▄_\-·]+$/.test(t); })
      .join("\n").replace(/^\s*\n/, "");
  }
  else if (window.NATIVE && window.NATIVE.auto && MOBILE && S.prefs.native !== false && raw.trim()) {
    window.NATIVE.auto(raw, idx, live);                          // any other screen: laid out app-style
    raw = "";
  }
  else if (window.NATIVE) window.NATIVE.hide();
  window.NV_NOQUICK = useNative && ["game", "plays", "matchup"].includes(nv.kind);   // its own buttons cover every key
  wrapEl.classList.toggle("native", useNative || (raw === "" && !!window.NATIVE && !document.getElementById("native").hidden));
  const slot = useNative ? document.getElementById("nv-tail") : null;   // a native screen can say where its text goes
  if (slot) { if (screenEl.parentElement !== slot) slot.appendChild(screenEl); }
  else if (screenEl.parentElement !== wrapEl) wrapEl.appendChild(screenEl);
  // Keep the active prompt in the game screen.  The old window removed it from
  // here and squeezed only its final line into the bottom input bar, which hid
  // long questions/options.  The bar is now just the typing control.
  const nearBottom = wrapEl.scrollHeight - wrapEl.scrollTop - wrapEl.clientHeight < 60;
  const cols = strip(raw).split("\n").reduce((m, ln) => Math.max(m, [...ln.split("\r").pop()].length), 0);
  const rows = raw.split("\n").length;
  if (cols !== S.cols || rows !== S.rows) { S.cols = cols; S.rows = rows; fit(); }
  screenEl.innerHTML = renderAnsi(raw);
  screenEl.parentElement.classList.toggle("dead", !live);
  if (live && nearBottom) wrapEl.scrollTop = wrapEl.scrollHeight;

  $("banner").hidden = live;
  const hl = $("hlabel");
  hl.textContent = live ? "LIVE" : `${S.screens.length - 1 - S.view} back`;
  hl.classList.toggle("live", live);
  $("hprev").disabled = idx <= 0;
  $("hnext").disabled = live;

  // the input bar
  const p = strip(S.prompt).split("\n").filter((x) => x.trim()).pop() || "";
  $("prompt").textContent = S.waiting ? (/⏎|Press Enter/.test(p) ? "Continue" : "Your answer") : "";
  barEl.classList.toggle("cont", S.waiting && /⏎|Press Enter/.test(p));
  barEl.classList.toggle("idle", !S.waiting);
  $("busy").hidden = S.waiting || S.done;
  if (S.done) { $("prompt").textContent = "The game has ended. You can close the window."; lineEl.disabled = true; }

  quickButtons(live ? full : "");
  requestAnimationFrame(draw);
}

// The command lines at the bottom of a screen ([R] Roster  [P] Player card ...) are the same
// keys the button row shows, so they fold away: lines after the screen's last full-width rule
// that carry two or more keys (and the rule itself when nothing else follows it).
function foldCommands(raw) {
  const lines = raw.split("\n");
  const plain = lines.map((l) => strip(l));
  let ruleAt = -1;
  for (let i = plain.length - 1; i >= 0; i--) {
    if (/^\s*[─━═]{60,}\s*$/.test(plain[i])) { ruleAt = i; break; }
  }
  if (ruleAt < 0 || plain.length - ruleAt > 9) return raw;
  const keys = (t) => (t.match(/\[(Enter|[A-Za-z0-9$?+/#]{1,5})\]/g) || []).length;
  const keep = [];
  let folded = 0, other = 0;
  for (let i = ruleAt + 1; i < lines.length; i++) {
    if (keys(plain[i]) >= 2) { folded++; continue; }
    if (plain[i].trim()) other++;
    keep.push(lines[i]);
  }
  if (!folded) return raw;
  return lines.slice(0, other ? ruleAt + 1 : ruleAt).concat(keep).join("\n").replace(/\s+$/, "");
}

function quickButtons(raw) {
  quickEl.innerHTML = "";
  if (!MOBILE || window.NV_NOQUICK) return;            // desktop: the auto button row is gone (it guessed wrong and got in the way);
                                  // phones keep it — the on-screen [keys] are too small to hit with a thumb
  if (!raw || !S.waiting) return;
  const found = new Map();
  const re = /\[(Enter|[A-Za-z0-9$?+/]{1,4})\]([^\[\]\n]*)/g;
  // how each key was colored on screen: green = the main thing to do, red = can't undo, gray = a way out
  const tone = new Map();
  const tre = /((?:\x1b\[[0-9;]*m)+)\[(Enter|[A-Za-z0-9$?+/]{1,4})\]/g;
  let tm;
  while ((tm = tre.exec(raw))) {
    const c = tm[1];
    tone.set(tm[2], /\[(?:[0-9;]*;)?92m|\[1;92m/.test(c) ? "go" : /\[(?:[0-9;]*;)?91m/.test(c) ? "warn"
      : /\[(?:[0-9;]*;)?90m|38;5;24[0-9]m/.test(c) ? "quiet" : "");
  }
  const tabs = /\b([1-8]) (HOME|SCHEDULE|TEAM|RECRUITING|RANKINGS|COACH|MEDIA|SYSTEM)\b/g;
  for (const line of strip(raw).split("\n")) {
    let m;
    while ((m = tabs.exec(line))) { found.delete(m[1]); found.set(m[1], m[2][0] + m[2].slice(1).toLowerCase()); }
    while ((m = re.exec(line))) {
      let label = m[2].replace(/^[\s:=·-]+/, "").split(/\s{2,}/)[0].trim();
      if (label.length > 32) label = label.slice(0, 31) + "…";
      found.delete(m[1]);                                    // keep the last place it appears
      found.set(m[1], label);
    }
  }
  if (!found.size) return;
  const rank = (k) => ({ go: 0, "": 1, warn: 2, quiet: 3 })[tone.get(k) || ""];
  const ordered = [...found].map((e, i) => [e, i]).sort((a, b) => rank(a[0][0]) - rank(b[0][0]) || a[1] - b[1]).map((x) => x[0]);
  let n = 0;
  for (const [k, label] of ordered) {
    if (++n > 28) break;
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.k = k;
    b.innerHTML = `<b>${esc(k)}</b>${esc(label)}`;
    if (tone.get(k)) b.classList.add(tone.get(k));
    b.title = `[${k}] ${label}`;
    quickEl.appendChild(b);
  }
}

// ═══ Fit the 100-column screen to the window ════════════════════════════════

let charW = null;
function fit() {
  if (charW === null) {
    const probe = document.createElement("span");
    probe.style.cssText = "position:absolute;visibility:hidden;white-space:pre;font-size:100px;font-family:var(--mono)";
    probe.textContent = "M".repeat(100);
    document.body.appendChild(probe);
    charW = probe.getBoundingClientRect().width / 100 / 100;
    probe.remove();
  }
  if (MOBILE) {                                                      // phone: fit the screen's real width, scroll down
    const w = wrapEl.clientWidth - 14;
    let ms = w / (Math.max(44, (S.cols || 100) + 1) * charW);
    ms = Math.min(20, ms) * (S.prefs.mzoom || 1);
    screenEl.style.fontSize = ms.toFixed(2) + "px";
    const cw = $("modal").querySelector(".sheet").clientWidth || window.innerWidth;
    $("mbody").style.fontSize = Math.max(6, Math.min(15, (cw - 24) / (101 * charW))).toFixed(2) + "px";
    return;
  }
  const avail = wrapEl.clientWidth - 30;
  let size = avail / (Math.max(101, (S.cols || 100) + 1) * charW);   // a wider screen (the WIDE tablet) shrinks to fit
  const tall = (wrapEl.clientHeight - 28) / (Math.max(20, S.rows || 0) * 1.24);
  if (tall < size) size = Math.max(size * 0.82, tall);               // a screen a little too tall shrinks to fit, not scroll
  size = Math.max(9, Math.min(22, size)) * S.prefs.zoom;
  screenEl.style.fontSize = size.toFixed(2) + "px";
  $("mbody").style.fontSize = Math.max(11, Math.min(17, size)).toFixed(2) + "px";
}

// ═══ Sidebar ════════════════════════════════════════════════════════════════

const TABS = ["home", "games", "league", "team", "news"];
const ANSI_HEX = { 30: "#1b2029", 31: "#e5534b", 32: "#57ab5a", 33: "#c69026", 34: "#539bf5", 35: "#b083f0", 36: "#39c5cf",
  37: "#adbac7", 90: "#768390", 91: "#ff7b72", 92: "#7ee787", 93: "#f2cc60", 94: "#79c0ff", 95: "#d2a8ff", 96: "#56d4dd", 97: "#f0f6fc" };
const colorOf = (c) => !c ? null : c.x !== undefined ? XTERM[c.x] : (ANSI_HEX[c.c] || null);
const h = (s) => esc(String(s ?? ""));
const pl = (id, name) => id ? `<span class="plink" data-p="${id}">${h(name)}</span>` : h(name);
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
S.last = null;          // for toasts: last result and rank we saw
S.pollAll = false;
S.rchip = "";

async function refreshState() {
  let d;
  try { d = await api("/state"); } catch (e) { return; }
  if (!d.ready) { $("sb").hidden = true; $("sb-empty").hidden = false; return; }
  $("sb").hidden = false; $("sb-empty").hidden = true;
  const run = (fn, x) => { try { if (x !== undefined) fn(x); } catch (e) { console.warn(e); } };
  run(drawHero, d.team);
  const live = $("h-live");
  live.classList.toggle("on", !d.busy && S.waiting);
  live.classList.toggle("busy", !!d.busy || !S.waiting);
  live.querySelector("b").textContent = d.busy || !S.waiting ? "WORKING" : "YOUR MOVE";
  run(drawNext, d.next ?? null);
  run(drawLast, d.last ?? null);
  run(drawActions, d);
  run(drawCoach, d.coach ?? null);
  run(drawAD, d.ad ?? null);
  run(drawBook, d.book ?? null);
  run(drawGames, d);
  run(drawLeague, d);
  run(drawTeam, d);
  if (d.news) run((n) => drawNews(n, d), d.news);
  run(toasts, d);
  setPlayers(d.players || []);
  if (d.linkKey && d.linkKey !== S.linkKey) loadLinks(d.linkKey);
  linkify($("sb"));
}

// The sidebar's text gets the same links as the screen (not buttons, not what's already a link).
function linkify(root) {
  if (!root || !S.links.size) return;
  const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (!n.nodeValue.trim() || n.parentElement.closest("button,[data-p],[data-act],[data-k],input,.n")
      ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  });
  const nodes = [];
  while (walk.nextNode()) nodes.push(walk.currentNode);
  for (const n of nodes) {
    const html = decorate(esc(n.nodeValue), { names: true, keys: false });
    if (html.includes('class="n"')) {
      const span = document.createElement("span");
      span.innerHTML = html;
      n.replaceWith(span);
    }
  }
}

async function loadLinks(key) {
  S.linkKey = key;                                   // ask once per change, even if it fails
  try {
    const d = await api("/links");
    const m = new Map();
    for (const [text, id] of d.list || []) m.set(esc(text), id);
    S.links = m;
    PREFIX.clear();
    S.linkKey = d.key || key;
    S.dirty = true;
    linkify($("sb"));
  } catch (e) { S.linkKey = null; }
}

function drawHero(t) {
  const col = colorOf(t.color) || "var(--accent)";
  document.documentElement.style.setProperty("--tc", col);
  $("h-mode").textContent = (t.mode || "").toUpperCase();
  $("h-rank").textContent = t.rank ? `#${t.rank}` : "";
  $("h-school").textContent = t.school;
  $("h-sub").textContent = [t.nickname, t.confName].filter(Boolean).join(" · ") + (t.cfp ? `  ·  NP #${t.cfp}` : "");
  $("h-record").textContent = t.record;
  $("h-conf").textContent = t.confRecord ? `${t.confRecord} ${t.conference}` : "";
  const st = $("h-streak");
  st.textContent = t.streak || "";
  st.className = "chip " + (t.streak ? t.streak[0].toLowerCase() : "");
  $("h-form").innerHTML = (t.form || []).map((g) =>
    `<span class="${g.r}" title="${h(g.r)} ${h(g.s)} vs ${h(g.o)}">${g.r}</span>`).join("");
  $("h-prog").style.width = Math.round((t.progress || 0) * 100) + "%";
  $("h-when").textContent = `${t.year} · ${t.complete ? "Season complete" : t.when}`;
  $("h-pts").textContent = t.games ? `${(t.pf / t.games).toFixed(1)} PPG · ${(t.pa / t.games).toFixed(1)} allowed` : "";
}

function gauge(p, words) {
  // a half-circle dial: the needle is the chance to win
  const ang = Math.PI * (1 - p);
  const x = 39 + 30 * Math.cos(ang), y = 42 - 30 * Math.sin(ang);
  const col = p >= 0.6 ? "var(--good)" : p >= 0.4 ? "var(--accent)" : "var(--bad)";
  const arc = (a0, a1, c) => {
    const p0 = [39 + 30 * Math.cos(Math.PI * (1 - a0)), 42 - 30 * Math.sin(Math.PI * (1 - a0))];
    const p1 = [39 + 30 * Math.cos(Math.PI * (1 - a1)), 42 - 30 * Math.sin(Math.PI * (1 - a1))];
    return `<path d="M${p0[0].toFixed(1)},${p0[1].toFixed(1)} A30,30 0 0 1 ${p1[0].toFixed(1)},${p1[1].toFixed(1)}" stroke="${c}" stroke-width="6" fill="none" stroke-linecap="round" opacity=".85"/>`;
  };
  const txt = words ? "" : `<text class="gt" x="39" y="35" text-anchor="middle">${Math.round(p * 100)}%</text>`;
  return `<svg viewBox="0 0 78 58">${arc(0.01, 0.4, "var(--bad)")}${arc(0.4, 0.6, "var(--accent)")}${arc(0.6, 0.99, "var(--good)")}
    <line x1="39" y1="42" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--text)" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="39" cy="42" r="3.5" fill="${col}"/>${txt}<text class="gs" x="39" y="56" text-anchor="middle">${words ? "OUTLOOK" : "WIN"}</text></svg>`;
}

function drawNext(n) {
  $("c-next").hidden = !n;
  if (!n) return;
  $("n-label").textContent = n.label;
  $("n-site").textContent = n.site;
  $("n-rank").textContent = n.oppRank ? `#${n.oppRank}` : "";
  $("n-opp").textContent = n.opp;
  $("n-opp").style.color = colorOf(n.oppColor) || "";
  $("n-meta").textContent = [n.oppRecord, n.oppConf].filter(Boolean).join(" · ");
  $("n-gauge").innerHTML = gauge(n.wpBand ?? 0.5, n.wp === null);
  const o = $("n-odds");
  o.textContent = n.odds ? n.odds[0].toUpperCase() + n.odds.slice(1) : "";
  o.className = "odds " + ((n.wpBand ?? .5) >= 0.6 ? "good" : (n.wpBand ?? .5) >= 0.4 ? "gold" : "bad");
  const kv = [];
  if (n.kick) kv.push(["Kickoff", n.kick]);
  if (n.forecast) kv.push(["Forecast", n.forecast]);
  kv.push(["Where", n.venue + (n.noise ? ` · ${n.noise.toLowerCase()}` : "") + (n.toughRank && n.toughRank <= 25 ? ` · No. ${n.toughRank} toughest` : "")]);
  if (n.us !== undefined) kv.push(["Matchup", `us ${n.us} · them ${n.them}`]);
  if (n.series) kv.push(["Series", n.series]);
  if (n.lastMeeting) kv.push(["Last met", n.lastMeeting]);
  $("n-kv").innerHTML = kv.map(([k, v]) => `<b>${h(k)}</b><span>${h(v)}</span>`).join("");
  $("n-riv").textContent = n.rivalry ? `★ ${n.rivalry}` + (n.trophy ? ` — ${n.trophy}` : "") : "";
}

function drawLast(l) {
  $("c-last").hidden = !l;
  if (!l) return;
  const r = l.won ? "W" : "L";
  $("l-result").innerHTML = `<span class="wl ${r}">${r}</span><span class="big">${l.us}-${l.them}</span>
    <span>${h(l.site)} ${l.oppRank ? `<span class="rk">#${l.oppRank}</span>` : ""}${h(l.opp)}<br><span class="muted small">${h(l.label)}</span></span>`;
}

function drawActions(d) {
  const acts = d.actions || [];
  const ok = d.atDash && S.waiting && !d.busy;
  $("a-hint").textContent = ok ? "one click" : "from the dashboard";
  const prim = acts.find((a) => a.primary);
  const pb = $("a-primary");
  pb.hidden = !prim;
  if (prim) { pb.textContent = `${prim.icon}  ${prim.label}`; pb.dataset.act = prim.id; pb.disabled = !ok; }
  const key = acts.map((a) => a.id).join(",") + ok;
  if (S.actKey === key) return;
  S.actKey = key;
  const rest = acts.filter((a) => !a.primary);
  const shown = S.moreActs ? rest : rest.slice(0, 8);
  $("a-grid").innerHTML = shown.map((a) =>
    `<button data-act="${a.id}" ${ok ? "" : "disabled"} title="${h(a.label)}"><i>${a.icon}</i>${h(a.label)}</button>`).join("")
    + (rest.length > 8 ? `<button class="more" id="a-more">${S.moreActs ? "▴ Fewer" : `▾ ${rest.length - 8} more`}</button>` : "");
}

async function runAction(id) {
  if (MOBILE && S.prefs.sidebar) { S.prefs.sidebar = false; savePrefs(); }
  const r = await api("/action", { id });
  if (!r.ok) toast(r.text || "Not right now.", "bad");
  else { if (S.view !== null) goLive(); S.waiting = false; S.dirty = true; }
}

function drawCoach(c) {
  $("c-coach").hidden = !c || c.open;
  if (!c || c.open) return;
  $("co-name").textContent = c.name + (c.interim ? " (interim)" : "");
  $("co-age").textContent = c.age ? `age ${c.age}` : "";
  const seat = $("co-seat");
  seat.style.width = Math.max(3, Math.min(100, c.seat)) + "%";
  seat.style.background = c.seat >= 70 ? "var(--bad)" : c.seat >= 50 ? "var(--accent)" : "var(--good)";
  const mv = c.seatMove ? (c.seatMove > 0 ? ` ▲${c.seatMove}` : ` ▼${-c.seatMove}`) : "";
  const lbl = $("co-seatlbl");
  lbl.textContent = (c.seatLabel || "") + mv;
  lbl.className = "seatlbl " + (c.seat >= 70 ? "bad" : c.seat >= 50 ? "gold" : "good");
  $("co-stats").hidden = !c.you;
  if (c.you) {
    $("co-inbox").textContent = c.inbox; $("co-replies").textContent = c.replies; $("co-pts").textContent = c.points;
    $("co-inbox").classList.toggle("hot", c.inbox > 0); $("co-pts").classList.toggle("hot", c.points > 0);
    if (S.inbox !== null && c.inbox > S.inbox) { chime("mail"); toast(`✉ New mail — ${plural(c.inbox, "unread message")}`); }
    S.inbox = c.inbox;
  }
  $("co-contract").textContent = c.contract ? `Contract ${c.contract}` + (c.bank ? ` · bank ${c.bank}` : "") : "";
  $("co-ad").textContent = c.ad ? `AD ${c.ad}` : "";
  $("c-mail").hidden = !(c.mail || []).length;
  $("co-mail").innerHTML = (c.mail || []).map((m) =>
    `<li class="${m.unread ? "unread" : ""}"><b>${h(m.from)}</b><span>${h(m.subject)}</span>${m.reply ? '<i title="wants a reply">↩</i>' : ""}</li>`).join("");
  $("co-goals").innerHTML = (c.goals || []).map((g) => {
    const mark = g.status === "met" ? '<span class="good">✔</span>' : g.status === "failed" ? '<span class="bad">✘</span>' : '<span class="gold">•</span>';
    return `<li>${mark}<span>${h(g.text)}</span><small>${h(g.note)}</small></li>`;
  }).join("");
}

function meterRow(label, v) {
  const col = v >= 65 ? "var(--good)" : v >= 40 ? "var(--accent)" : "var(--bad)";
  return `<div><span class="muted">${h(label)}</span><div class="meter"><div style="width:${Math.max(3, Math.min(100, v))}%;background:${col}"></div></div><b>${v}</b></div>`;
}
function drawAD(a) {
  $("c-ad").hidden = !a;
  if (!a) return;
  $("ad-name").textContent = a.name;
  $("ad-meters").innerHTML = `<div class="bars">${meterRow("Board", a.board)}${meterRow("Fans", a.fans)}${meterRow("Boosters", a.boosters)}</div>`;
}

function drawBook(b) {
  $("c-book").hidden = !b;
  if (!b) return;
  if (b.fresh) {
    $("bk-bank").textContent = "";
    $("bk-delta").innerHTML = '<span class="muted small">Spreads, totals, parlays, props and futures — press [B] on the dashboard.</span>';
    $("bk-spark").innerHTML = ""; $("bk-stats").innerHTML = ""; $("bk-open").innerHTML = ""; $("bk-sub").textContent = "";
    return;
  }
  const bank = $("bk-bank");
  bank.textContent = b.bank;
  bank.className = b.up ? "" : "down";
  $("bk-delta").innerHTML = `<span class="${b.up ? "good" : "bad"}">${h(b.delta)}</span> <span class="muted small">since start</span>`;
  $("bk-sub").textContent = [b.rank, b.unseen ? `${b.unseen} new result${b.unseen === 1 ? "" : "s"}` : ""].filter(Boolean).join(" · ");
  const v = b.spark || [];
  if (v.length > 1) {
    const lo = Math.min(...v), hi = Math.max(...v), span = (hi - lo) || 1;
    const pts = v.map((x, i) => `${(i / (v.length - 1) * 200).toFixed(1)},${(34 - (x - lo) / span * 32).toFixed(1)}`).join(" ");
    const col = b.up ? "var(--good)" : "var(--bad)";
    $("bk-spark").innerHTML = `<polygon class="area" fill="${col}" points="0,36 ${pts} 200,36"></polygon><polyline stroke="${col}" points="${pts}"></polyline>`;
  } else $("bk-spark").innerHTML = "";
  $("bk-stats").innerHTML = `<div><b>${b.open}</b><span>open bets</span></div><div><b>${h(b.risk)}</b><span>at risk</span></div><div><b class="good">${h(b.toWin)}</b><span>to win</span></div>`;
  $("bk-open").innerHTML = (b.bets || []).map((x) =>
    `<div><span title="${h(x.t)}">${h(x.t)}</span><span class="gold">${h(x.o)}</span><span class="muted">${h(x.s)}</span></div>`).join("")
    + (b.more ? `<div class="muted small">+${b.more} more</div>` : "");
}

function drawGames(d) {
  const t = d.team || {};
  const hist = (t.rankHistory || []);
  const pts = hist.map((r, i) => [i, r || 26]);
  let svg = "";
  if (pts.length >= 2 && !hist.some(Boolean)) {
    svg = `<div class="muted small">Unranked all season — ${t.record}. Win a few and the voters notice.</div>`;
  } else if (pts.length >= 2) {
    const W = 290, H = 70, n = pts.length - 1;
    const X = (i) => 8 + (W - 16) * i / n, Y = (r) => 6 + (H - 14) * (Math.min(26, r) - 1) / 25;
    const line = pts.map(([i, r], k) => `${k ? "L" : "M"}${X(i).toFixed(1)},${Y(r).toFixed(1)}`).join(" ");
    const dots = pts.map(([i, r]) => `<circle cx="${X(i).toFixed(1)}" cy="${Y(r).toFixed(1)}" r="2.6" fill="${r > 25 ? "var(--muted)" : "var(--tc,var(--accent))"}"><title>${r > 25 ? "unranked" : "#" + r}</title></circle>`).join("");
    svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
      <line x1="0" x2="${W}" y1="${Y(10)}" y2="${Y(10)}" stroke="var(--line)" stroke-dasharray="3 3"/>
      <line x1="0" x2="${W}" y1="${Y(25)}" y2="${Y(25)}" stroke="var(--line)" stroke-dasharray="3 3"/>
      <text x="2" y="${Y(10) - 2}" font-size="8" fill="var(--muted)">10</text><text x="2" y="${Y(25) - 2}" font-size="8" fill="var(--muted)">25</text>
      <path d="${line}" fill="none" stroke="var(--tc,var(--accent))" stroke-width="2"/>${dots}</svg>`;
  } else svg = `<div class="muted small">The line starts after a couple of games.</div>`;
  $("g-spark").innerHTML = svg;
  const best = hist.filter(Boolean).length ? Math.min(...hist.filter(Boolean)) : null;
  $("g-trio").innerHTML = `<div><b>${t.pf ?? 0}</b><span>points for</span></div><div><b>${t.pa ?? 0}</b><span>points against</span></div>
    <div><b>${best ? "#" + best : "—"}</b><span>highest rank</span></div>`;
  $("g-sched").innerHTML = (d.schedule || []).map((g) => {
    const res = g.played ? `<span class="${g.won ? "good" : "bad"}"><b>${g.won ? "W" : "L"}</b> ${h(g.score)}</span>` : g.next ? '<span class="gold">NEXT</span>' : '<span class="muted">—</span>';
    return `<div class="${g.next ? "next" : ""}"><span class="wk">${h(g.wk)}</span><span class="muted">${h(g.site)}</span>
      <span class="${g.conf ? "cf" : ""}">${g.oppRank ? `<span class="rk">#${g.oppRank}</span>` : ""}${h(g.opp)}</span>${res}</div>`;
  }).join("") || '<span class="muted small">No games yet.</span>';
  const so = d.sos;
  if (so) {
    const bits = [`<b>SOS No. ${so.rank}</b> <span class="muted">(${h(so.word)})</span>`];
    if (so.played && so.ahead) bits.push(`<span class="muted">played</span> ${so.played} · <span class="muted">ahead</span> ${so.ahead}`);
    bits.push(`<span class="muted">opp</span> ${h(so.opp)}`);
    $("g-sched").insertAdjacentHTML("afterbegin", `<div class="small sos" style="display:block;margin-bottom:4px">${bits.join(" · ")}</div>`);
  }
}

function drawLeague(d) {
  const s = d.standings;
  if (s) {
    $("s-title").firstChild.textContent = `${s.conf.toUpperCase()} STANDINGS`;
    $("s-table").innerHTML = `<tr class="muted small"><td></td><td></td><td>CONF</td><td>ALL</td></tr>` +
      s.rows.map((r, i) => `<tr class="${r.me ? "me" : ""}"><td class="ix">${i + 1}</td><td>${r.rank ? `<span class="rk">#${r.rank}</span>` : ""}${h(r.school)}</td><td>${h(r.conf)}</td><td>${h(r.all)}</td></tr>`).join("");
  }
  const p = d.top25;
  if (p) {
    $("p-label").textContent = p.label;
    const rows = S.pollAll ? p.poll : p.poll.slice(0, 10);
    const mine = p.poll.find((r) => r.me);
    if (!S.pollAll && mine && mine.rank > 10) rows.push(mine);
    $("p-list").innerHTML = rows.map((r) => {
      const mv = r.new ? '<span class="good">NEW</span>' : r.move > 0 ? `<span class="good">▲${r.move}</span>` : r.move < 0 ? `<span class="bad">▼${-r.move}</span>` : '<span class="muted">–</span>';
      return `<div class="${r.me ? "me" : ""}"><span class="ix">${r.rank}</span><span><i class="dot" style="background:${colorOf(r.color) || "var(--muted)"}"></i>${h(r.school)}</span><span class="r">${h(r.record)}</span><span class="mv">${mv}</span></div>`;
    }).join("") || '<span class="muted small">The first poll comes out in the preseason.</span>';
    $("p-more").textContent = S.pollAll ? "Top 10" : "All 25";
    $("c-cfp").hidden = !p.cfp.length;
    $("cfp-list").innerHTML = p.cfp.map((r) => `<div class="${r.me ? "me" : ""}"><span class="ix">${r.rank}</span><span>${h(r.school)}</span><span></span><span></span></div>`).join("");
    $("hz-list").innerHTML = `<div class="list1">` + (p.heisman.map((x, i) => `<div><span class="ix">${i + 1}</span>${pl(x.id, x.name)}<span class="aside">${h(x.pos)} · ${h(x.school)}</span></div>`).join("") || '<span class="muted small">Watch list after week one.</span>') + `</div>`;
    $("t-list").innerHTML = `<div class="list1">` + p.tough.map((x, i) => `<div class="${x.me ? "gold" : ""}"><span class="ix">${i + 1}</span><span>${h(x.school)}</span><span class="aside">${h(x.stadium)}</span></div>`).join("") + `</div>`;
  }
}

function drawTeam(d) {
  $("t-lineup").innerHTML = (d.lineup || []).map((p) =>
    `<div data-p="${p.id}" title="${h(p.yr)}${p.ovrLong ? " · " + h(p.ovrLong) : ""}${p.fill ? " · filling in for an injured starter" : ""}"><span class="pos">${p.pos}</span><span class="${p.hurt ? "hurt" : p.fill ? "gold" : ""}">${h(p.name)}${p.hurt ? " ✚" : p.fill ? " ↺" : ""}</span><span class="o">${h(p.ovr)}</span></div>`).join("");
  const inj = d.injuries || [];
  $("t-inj").innerHTML = inj.length ? `<div class="list1">` + inj.map((p) =>
    `<div><span class="lineup"><span class="pos">${p.pos}</span></span>${pl(p.id, p.name)}${p.starter ? ' <span class="gold small">starter</span>' : ""}<span class="aside bad">${h(p.status)}</span></div>`).join("") + `</div>`
    : '<span class="muted small">Everybody\'s healthy. ✔</span>';
  const L = d.leaders || { rows: [] };
  $("t-ldyr").textContent = L.lastYear ? "(last season)" : "";
  $("t-leaders").innerHTML = (L.rows.map((r) =>
    `<div class="leader"><span class="muted small">${h(r.label.toUpperCase())}</span><span class="lname">${pl(r.id, r.name)} <span class="muted small">${h(r.pos)}</span></span>
      <b>${h(r.value)}</b>${r.extra ? `<span class="muted small lx">${h(r.extra)}</span>` : ""}</div>`).join("") || '<span class="muted small">No stats yet.</span>');
  const g = d.program;
  if (g) {
    const pip = (v) => "■".repeat(v) + "□".repeat(10 - v);
    $("t-program").innerHTML = `<div class="list1">
      <div><span class="muted" style="width:78px">Prestige</span><b>${g.prestige}</b><span class="aside">budget ${h(g.budget)} · NIL free ${h(g.nil)}</span></div>
      ${g.facilities.map((f) => `<div><span class="muted" style="width:78px">${h(f.k)}</span><span class="pips">${pip(f.v)}</span><span class="aside">${f.v}/10</span></div>`).join("")}
      <div><span class="muted" style="width:78px">Stadium</span><span>${Number(g.capacity).toLocaleString()} seats · ${h(g.noise.toLowerCase())}</span><span class="aside">${g.tough ? "No. " + g.tough + " toughest" : ""}</span></div>
      <div><span class="muted" style="width:78px">Fund</span><span>${h(g.fund)}</span><span class="aside">${g.project ? "🏗 " + h(g.project) : ""}</span></div></div>`;
  }
  const r = d.recruiting;
  if (r) {
    const hrs = r.hoursTotal ? `<div class="bars" style="margin:6px 0">${meterRow("Hours", Math.round(100 * r.hours / Math.max(1, r.hoursTotal))).replace(/<b>\d+<\/b>/, `<b>${r.hours}</b>`)}</div>` : "";
    $("t-rec").innerHTML = `<div class="trio"><div><b>${r.rank ? "#" + r.rank : "—"}</b><span>class rank</span></div><div><b>${r.commits}</b><span>commits</span></div><div><b>${r.stars || "—"}</b><span>avg ★</span></div></div>${hrs}
      ${r.board !== undefined ? `<div class="muted small">Board ${r.board}/40</div>` : ""}
      ${r.queue ? `<div class="label" style="margin-top:8px;cursor:default">STANDING ORDERS <span class="muted small">${r.queueRuns} run · ${r.queueCut ? `<span class="bad">${r.queueCut} cut</span>` : "none cut"}</span></div>
        <div class="list1">${r.queue.map((q, i) => `<div><span class="ix">${i + 1}</span><span class="${q.runs ? "" : "muted"}">${h(q.a)} — ${h(q.name)}</span><span class="aside ${q.runs ? "good" : q.status.startsWith("cut") ? "bad" : ""}">${q.runs ? "✔" : q.status.startsWith("cut") ? "✘ cut" : "·"}</span></div>`).join("") || '<span class="muted small">Empty — [Q] on a recruit card.</span>'}${r.queueLen > 8 ? `<div class="muted small">+${r.queueLen - 8} more</div>` : ""}</div>` : ""}
      ${r.visits && r.visits.length ? `<div class="label" style="margin-top:8px;cursor:default">OFFICIAL VISITS</div><div class="list1">${r.visits.map((v) => `<div>${h(v.name)} <span class="stars">${"★".repeat(v.stars)}</span><span class="aside">Week ${v.week}</span></div>`).join("")}</div>` : ""}
      <div class="list1">${r.top.map((x) => `<div><span class="lineup"><span class="pos">${x.pos}</span></span>${h(x.name)}<span class="aside stars">${"★".repeat(x.stars)}</span></div>`).join("")}</div>`;
  }
}

function drawNews(n, d) {
  const sc = d.scores;
  if (sc) {
    $("sc-label").textContent = sc.label;
    const rk = (r) => r ? `<span class="rk">${r}</span>` : "";
    $("sc-list").innerHTML = sc.rows.map((g) => sc.upcoming
      ? `<div class="${g.mine ? "me" : ""}"><span>${rk(g.ar)}${h(g.away)}</span><span class="muted">${g.neutral ? "vs" : "at"}</span><span>${rk(g.hr)}${h(g.home)}</span></div>`
      : `<div class="${g.mine ? "me" : ""}${g.upset ? " upset" : ""}" ${g.upset ? 'title="Upset"' : ""}><span class="${g.awayWon ? "win" : ""}">${rk(g.ar)}${h(g.away)} <b>${g.a}</b></span><span class="muted">${g.neutral ? "vs" : "at"}</span><span class="${g.awayWon ? "" : "win"}">${rk(g.hr)}${h(g.home)} <b>${g.h}</b></span></div>`
    ).join("") || '<span class="muted small">No games this week.</span>';
  }
  $("hs-list").innerHTML = `<div class="list1">` + (d.hotseats || []).map((c) => {
    const col = c.seat >= 70 ? "var(--bad)" : c.seat >= 50 ? "var(--accent)" : "var(--good)";
    return `<div class="${c.you ? "gold" : ""}"><span style="flex:1">${h(c.name)} <span class="muted small">${h(c.school)}</span></span>
      <span class="minimeter"><i style="width:${c.seat}%;background:${col}"></i></span></div>`;
  }).join("") + `</div>`;
  $("c-rnews").hidden = !(d.rnews || []).length;
  $("rn-list").innerHTML = (d.rnews || []).map((x) => `<li class="${x.mine ? "good" : x.stars >= 5 ? "gold" : "info"}">${h(x.text)}</li>`).join("");
  $("nw-heads").innerHTML = (n.headlines || []).map((x) => `<li class="${x.tone}">${h(x.text)}</li>`).join("");
  $("c-log").hidden = !(n.log || []).length;
  $("nw-log").innerHTML = (n.log || []).map((x) => `<li><b>${x.year}</b><span>${h(x.text)}</span></li>`).join("");
}

function toasts(d) {
  const t = d.team, l = d.last;
  const key = l ? `${t.year}|${l.label}|${l.us}-${l.them}` : null;
  const rank = t ? t.rank : null;
  if (S.last) {
    if (key && key !== S.last.key) toast(`${l.won ? "✔ Win" : "✘ Loss"} — ${l.us}-${l.them} ${l.site} ${l.opp}`, l.won ? "good" : "bad");
    if (t && t.year === S.last.year && rank !== S.last.rank && S.last.key !== null) {
      if (rank && (!S.last.rank || rank < S.last.rank)) toast(`▲ Up to No. ${rank} in the media poll`, "good");
      else if (!rank && S.last.rank) toast(`▼ Out of the Top 25`, "bad");
      else if (rank && S.last.rank && rank > S.last.rank) toast(`▼ Down to No. ${rank} in the media poll`, "bad");
    }
  }
  S.last = { key, rank, year: t ? t.year : null };
}

function toast(text, kind = "") {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.textContent = text;
  $("toasts").appendChild(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 400); }, 4200);
}

function setTab(tab) {
  if (!TABS.includes(tab)) tab = "home";
  S.prefs.tab = tab;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("on", p.dataset.pane === tab));
}

function applyCollapsed() {
  const shut = new Set(S.prefs.shut || []);
  document.querySelectorAll("[data-card]").forEach((c) => c.classList.toggle("shut", shut.has(c.dataset.card)));
}

function setPlayers(list) {
  const key = list.map((p) => p.id).join(",");
  if (key === S.nameKey) return;
  S.nameKey = key;
  S.players = list;
  S.byName = new Map();
  const shortCount = new Map();
  for (const p of list) shortCount.set(p.short, (shortCount.get(p.short) || 0) + 1);
  const names = [];
  for (const p of list) {
    if (!S.byName.has(p.name)) { S.byName.set(p.name, p.id); names.push(p.name); }
    if (shortCount.get(p.short) === 1 && !S.byName.has(p.short)) { S.byName.set(p.short, p.id); names.push(p.short); }
  }
  names.sort((a, b) => b.length - a.length);
  const reEsc = (s) => esc(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  S.nameRe = names.length ? String.raw`(?<![A-Za-z])(` + names.map(reEsc).join("|") + String.raw`)(?![A-Za-z])` : null;
  try { new RegExp(S.nameRe); } catch (e) { S.nameRe = names.length ? `\\b(${names.map(reEsc).join("|")})\\b` : null; }
  rosterList();
  S.dirty = true;
}

const POS_ORDER = ["QB","RB","WR","TE","OL","DL","LB","CB","S","K","P"];
function rosterList() {
  const q = $("rsearch").value.trim().toLowerCase();
  const chip = S.rchip;
  const mine = S.players.filter((p) => p.mine && (!chip || p.pos === chip) &&
    (!q || p.name.toLowerCase().includes(q) || p.pos.toLowerCase() === q));
  mine.sort((a, b) => POS_ORDER.indexOf(a.pos) - POS_ORDER.indexOf(b.pos));
  $("rchips").innerHTML = ["", ...POS_ORDER].map((p) =>
    `<button class="${p === chip ? "on" : ""}" data-chip="${p}">${p || "ALL"}</button>`).join("");
  $("rlist").innerHTML = mine.map((p) =>
    `<div data-p="${p.id}"><span class="pos">${p.pos}</span><span class="num">${p.num}</span><span>${esc(p.name)}</span></div>`
  ).join("") || `<span class="muted">Nobody by that name.</span>`;
}

// ═══ Player card ════════════════════════════════════════════════════════════

async function openCard(id, back = false) {
  const d = await api("/card", { id });
  let text = d.text || "";
  text = text.split("\n").filter((l) => !/Press Enter to continue|▶\s+Select:|Enter to go back/.test(strip(l)))
    .join("\n").replace(/\s+$/, "");
  if (!back && !$("modal").hidden && S.cardCur) S.cardStack.push(S.cardCur);
  if ($("modal").hidden) S.cardStack = [];
  S.cardCur = id;
  $("mbody").innerHTML = renderAnsi(text, { names: true, keys: false });
  $("mback").hidden = !S.cardStack.length;
  $("modal").hidden = false;
  $("modal").querySelector(".sheet").scrollTop = 0;
  $("mclose").focus();
}
function cardBack() { const id = S.cardStack.pop(); if (id) openCard(id, true); }
function closeCard() { $("modal").hidden = true; S.cardStack = []; S.cardCur = null; focusLine(); }

// ═══ Sounds (made on the fly — no files) ════════════════════════════════════

let actx = null;
function tone(freq, start, dur, vol = 0.06, type = "triangle") {
  actx = actx || new (window.AudioContext || window.webkitAudioContext)();
  const o = actx.createOscillator(), g = actx.createGain();
  o.type = type; o.frequency.value = freq;
  const t = actx.currentTime + start;
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(vol, t + 0.02);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(actx.destination);
  o.start(t); o.stop(t + dur + 0.05);
}
function chime(kind) {
  if (!S.prefs.sound) return;
  try {
    if (kind === "td") { [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.09, 0.35)); }
    else if (kind === "mail") { tone(880, 0, 0.18, 0.04, "sine"); tone(1175, 0.1, 0.25, 0.04, "sine"); }
  } catch (e) { /* no audio here */ }
}
function sounds(text) {
  if (/TOUCHDOWN/.test(text) && Date.now() - S.lastTD > 4000) { S.lastTD = Date.now(); chime("td"); }
}

// ═══ Preferences ════════════════════════════════════════════════════════════

function applyPrefs() {
  document.documentElement.dataset.theme = S.prefs.theme === "light" ? "light" : "dark";
  $("sound").classList.toggle("off", !S.prefs.sound);
  $("sound").textContent = S.prefs.sound ? "🔊" : "🔈";
  $("sidebar").classList.toggle("hide", !S.prefs.sidebar);
  if (S.prefs.sbw) document.documentElement.style.setProperty("--sbw", S.prefs.sbw + "px");
  setTab(S.prefs.tab || "home");
  applyCollapsed();
  fit();
  S.dirty = true;
}
function savePrefs() { applyPrefs(); api("/prefs", S.prefs).catch(() => {}); }
function zoom(step) {
  if (MOBILE) { S.prefs.mzoom = Math.max(0.8, Math.min(3, +((S.prefs.mzoom || 1) + step * 2).toFixed(2))); savePrefs(); return; }
  S.prefs.zoom = Math.max(0.6, Math.min(1.8, +(S.prefs.zoom + step).toFixed(2))); savePrefs();
}

// ═══ History ════════════════════════════════════════════════════════════════

function goBack() {
  const last = S.screens.length - 1;
  const v = S.view === null ? last : S.view;
  if (v > 0) { S.view = v - 1; S.dirty = true; wrapEl.scrollTop = 0; }
}
function goForward() {
  if (S.view === null) return;
  S.view = S.view + 1 >= S.screens.length - 1 ? null : S.view + 1;
  S.dirty = true;
  if (S.view === null) requestAnimationFrame(() => (wrapEl.scrollTop = wrapEl.scrollHeight));
}
function goLive() { S.view = null; S.dirty = true; requestAnimationFrame(() => (wrapEl.scrollTop = wrapEl.scrollHeight)); }

// ═══ Wiring ═════════════════════════════════════════════════════════════════

barEl.addEventListener("submit", (e) => { e.preventDefault(); const v = lineEl.value; lineEl.value = ""; send(v); });

document.addEventListener("click", (e) => {
  const k = e.target.closest("[data-k]");
  if (k && !k.closest(".dead") && !k.closest("#modal")) {
    if (window.getSelection().toString()) return;             // selecting text, not clicking
    send(k.dataset.k === "Enter" ? "" : k.dataset.k);
    focusLine();
    return;
  }
  const p = e.target.closest("[data-p]");
  if (p) { if (!window.getSelection().toString()) openCard(p.dataset.p); return; }
});

$("modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeCard(); });
$("mclose").onclick = closeCard;
$("mback").onclick = cardBack;
$("hprev").onclick = goBack;
$("hnext").onclick = goForward;
$("golive").onclick = goLive;
$("zin").onclick = () => zoom(0.1);
$("zout").onclick = () => zoom(-0.1);
$("theme").onclick = () => { S.prefs.theme = S.prefs.theme === "light" ? "dark" : "light"; savePrefs(); };
$("sound").onclick = () => { S.prefs.sound = !S.prefs.sound; savePrefs(); if (S.prefs.sound) chime("mail"); };
$("side").onclick = () => { S.prefs.sidebar = !S.prefs.sidebar; savePrefs(); };
$("rsearch").addEventListener("input", rosterList);
$("rchips").addEventListener("click", (e) => { const b = e.target.closest("[data-chip]"); if (!b) return; S.rchip = b.dataset.chip; rosterList(); });
$("tabs").addEventListener("click", (e) => { const b = e.target.closest("[data-tab]"); if (b) { setTab(b.dataset.tab); savePrefs(); } });
$("p-more").addEventListener("click", (e) => { e.stopPropagation(); S.pollAll = !S.pollAll; refreshState(); });
document.getElementById("sb").addEventListener("click", (e) => {
  if (e.target.closest("#a-more")) { S.moreActs = !S.moreActs; S.actKey = null; refreshState(); return; }
  const act = e.target.closest("[data-act]");
  if (act && !act.disabled) { runAction(act.dataset.act); return; }
  const lab = e.target.closest(".card > .label");
  if (lab && !e.target.closest("button")) {
    const card = lab.parentElement, id = card.dataset.card;
    if (!id) return;
    const shut = new Set(S.prefs.shut || []);
    shut.has(id) ? shut.delete(id) : shut.add(id);
    S.prefs.shut = [...shut];
    applyCollapsed(); savePrefs();
  }
});
(function grip() {
  const g = $("sbgrip");
  let x0 = 0, w0 = 0;
  const move = (e) => {
    const w = Math.max(250, Math.min(560, w0 + (x0 - e.clientX)));
    S.prefs.sbw = w; document.documentElement.style.setProperty("--sbw", w + "px"); fit(); S.dirty = true;
  };
  const up = () => { g.classList.remove("drag"); document.removeEventListener("mousemove", move);
    document.removeEventListener("mouseup", up); savePrefs(); };
  g.addEventListener("mousedown", (e) => { x0 = e.clientX; w0 = $("sidebar").getBoundingClientRect().width;
    g.classList.add("drag"); document.addEventListener("mousemove", move); document.addEventListener("mouseup", up); e.preventDefault(); });
})();
$("copy").onclick = async () => {
  const idx = S.view === null ? S.screens.length - 1 : S.view;
  const text = strip(S.screens[idx] || "").split("\n").map((l) => l.replace(/\s+$/, "")).join("\n").trim() + "\n";
  let ok = false;
  try { await navigator.clipboard.writeText(text); ok = true; } catch (e) { /* fall back to the game's copier */ }
  if (!ok) { try { ok = (await api("/copy", { text })).ok; } catch (e) { ok = false; } }
  const b = $("copy"); const was = b.textContent;
  b.textContent = ok ? "Copied ✓" : "Saved to last_screen.txt";
  setTimeout(() => (b.textContent = was), 1600);
};

document.addEventListener("keydown", (e) => {
  if (!$("modal").hidden) {
    if (e.key === "Backspace" || (e.altKey && e.key === "ArrowLeft")) { e.preventDefault(); cardBack(); return; }
    if (e.key === "Escape" || e.key === "Enter") { e.preventDefault(); closeCard(); }
    return;
  }
  if ((e.ctrlKey || e.metaKey) && (e.key === "=" || e.key === "+")) { e.preventDefault(); zoom(0.1); return; }
  if ((e.ctrlKey || e.metaKey) && e.key === "-") { e.preventDefault(); zoom(-0.1); return; }
  if (e.altKey && e.key === "ArrowLeft") { e.preventDefault(); goBack(); return; }
  if (e.altKey && /^[1-5]$/.test(e.key)) { e.preventDefault(); if (!S.prefs.sidebar) { S.prefs.sidebar = true; } setTab(TABS[+e.key - 1]); savePrefs(); return; }
  if (e.altKey && e.key === "ArrowRight") { e.preventDefault(); goForward(); return; }
  if (e.key === "PageUp" || e.key === "PageDown") {
    wrapEl.scrollBy(0, (e.key === "PageUp" ? -1 : 1) * wrapEl.clientHeight * 0.85); e.preventDefault(); return;
  }
  const inField = e.target === lineEl || e.target === $("rsearch");
  if (!inField && e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) lineEl.focus();
  if (!inField && e.key === "Enter") { e.preventDefault(); lineEl.focus(); barEl.requestSubmit(); }
});
lineEl.addEventListener("keydown", (e) => {
  if (e.key === "ArrowUp" && S.sent.length) {
    S.sentIdx = S.sentIdx < 0 ? S.sent.length - 1 : Math.max(0, S.sentIdx - 1);
    lineEl.value = S.sent[S.sentIdx]; e.preventDefault();
  } else if (e.key === "ArrowDown" && S.sentIdx >= 0) {
    S.sentIdx = Math.min(S.sent.length, S.sentIdx + 1);
    lineEl.value = S.sent[S.sentIdx] || ""; if (S.sentIdx >= S.sent.length) S.sentIdx = -1; e.preventDefault();
  }
});

window.addEventListener("resize", () => { fit(); S.dirty = true; });
setInterval(refreshState, 2000);

(async function start() {
  try { Object.assign(S.prefs, await api("/prefs")); } catch (e) { /* first run */ }
  if (MOBILE) S.prefs.sidebar = false;
  applyPrefs();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { charW = null; fit(); });
  focusLine();
  poll();
  refreshState();
  requestAnimationFrame(draw);
})();


// ═══ Copy box (Settings → Copy team context) ═══════════════════════════════
// Browsers (iPhone Safari especially) only allow copying from a tap, so the game hands the text over
// and this box gives you the button to tap.
function showClip(text) {
  let box = document.getElementById("clipbox");
  if (!box) {
    box = document.createElement("div");
    box.id = "clipbox";
    box.innerHTML = '<div class="clipsheet"><div class="cliphead"><b>Team context</b><span id="clipn" class="muted"></span></div>' +
      '<textarea id="cliptext" readonly></textarea>' +
      '<div class="clipbtns"><button id="clipgo" class="primary">Copy</button><button id="clipclose">Close</button></div></div>';
    document.body.appendChild(box);
    document.getElementById("clipclose").onclick = () => { box.style.display = "none"; };
    document.getElementById("clipgo").onclick = async () => {
      const ta = document.getElementById("cliptext"), t = ta.value, b = document.getElementById("clipgo");
      let ok = false;
      try { if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(t); ok = true; } } catch (e) { ok = false; }
      if (!ok) {
        try { ta.removeAttribute("readonly"); ta.focus(); ta.setSelectionRange(0, t.length); ok = document.execCommand("copy"); }
        catch (e) { ok = false; } finally { ta.setAttribute("readonly", ""); }
      }
      b.textContent = ok ? "Copied \u2713" : "Select all and copy";
      if (ok) setTimeout(() => { box.style.display = "none"; b.textContent = "Copy"; }, 900);
    };
  }
  document.getElementById("cliptext").value = text;
  document.getElementById("clipn").textContent = " \u00b7 " + text.split("\n").length.toLocaleString() + " lines";
  document.getElementById("clipgo").textContent = "Copy";
  box.style.display = "flex";
}
