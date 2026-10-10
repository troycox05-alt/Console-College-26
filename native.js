// Console College — native web screens (loaded by mobile_web.py after app.js).
// The game sends a screen's data (webview.py); this draws it as a real app screen. Every button
// sends the same key the terminal would, so the game itself doesn't change. Screens that haven't
// been converted yet keep the classic text view.
"use strict";
(function () {
  const nEl = document.createElement("div");
  nEl.id = "native";
  nEl.hidden = true;
  const wrap = document.getElementById("screenwrap");
  wrap.insertBefore(nEl, wrap.firstChild);

  const col = (c) => colorOf(c) || "var(--accent)";
  const rk = (r) => (r ? `<span class="nv-rk">#${r}</span>` : "");
  const btn = (k, label, cls = "") => `<button class="nv-btn ${cls}" data-k="${h(k)}">${label}</button>`;
  const card = (title, body, extra = "") => `<section class="nv-card"${extra}>${title ? `<div class="nv-ct">${title}</div>` : ""}${body}</section>`;
  const gaugeOk = typeof gauge === "function";

  // ═══ Main screen ══════════════════════════════════════════════════════════
  function hero(t) {
    if (!t) return "";
    const form = (t.form || []).map((g) => `<i class="${g.r}">${g.r}</i>`).join("");
    return `<div class="nv-hero" style="--tc:${col(t.color)}">
      <div class="nv-hmode">${h((t.mode || "").toUpperCase())} · ${h(t.year)} · ${h(t.complete ? "Season complete" : t.when)}</div>
      <div class="nv-hname">${t.rank ? `<span class="nv-hrank">#${t.rank}</span>` : ""}${h(t.school)}</div>
      <div class="nv-hsub">${h([t.nickname, t.confName].filter(Boolean).join(" · "))}${t.cfp ? ` · NP #${t.cfp}` : ""}</div>
      <div class="nv-hrow"><b class="nv-rec">${h(t.record)}</b><span class="muted">${h(t.confRecord || "")} ${h(t.conference || "")}</span>
        ${t.streak ? `<span class="chip ${t.streak[0].toLowerCase()}">${h(t.streak)}</span>` : ""}<span class="nv-form">${form}</span></div>
      <div class="nv-prog"><i style="width:${Math.round((t.progress || 0) * 100)}%"></i></div></div>`;
  }

  function nextCard(n) {
    if (!n) return "";
    const kv = [];
    if (n.kick) kv.push(["Kickoff", n.kick]);
    if (n.forecast) kv.push(["Forecast", n.forecast]);
    kv.push(["Where", n.venue + (n.noise ? ` · ${n.noise.toLowerCase()}` : "")]);
    if (n.us !== undefined) kv.push(["Matchup", `us ${n.us} · them ${n.them}`]);
    if (n.series) kv.push(["Series", n.series]);
    if (n.lastMeeting) kv.push(["Last met", n.lastMeeting]);
    const wb = n.wpBand ?? 0.5;
    return card(`NEXT GAME · ${h(n.label)}`, `
      <div class="nv-next"><div class="nv-g">${gaugeOk ? gauge(wb, n.wp === null) : ""}</div>
        <div><div class="nv-opp"><span class="muted">${h(n.site)}</span> ${rk(n.oppRank)}<b style="color:${col(n.oppColor)}">${h(n.opp)}</b></div>
        <div class="muted small">${h([n.oppRecord, n.oppConf].filter(Boolean).join(" · "))}</div>
        <div class="nv-odds ${wb >= 0.6 ? "good" : wb >= 0.4 ? "gold" : "bad"}">${h(n.odds ? n.odds[0].toUpperCase() + n.odds.slice(1) : "")}</div></div></div>
      ${n.rivalry ? `<div class="gold small">★ ${h(n.rivalry)}${n.trophy ? " — " + h(n.trophy) : ""}</div>` : ""}
      <div class="nv-kv">${kv.map(([k, v]) => `<b>${h(k)}</b><span>${h(v)}</span>`).join("")}</div>`);
  }

  function lastCard(l) {
    if (!l) return "";
    return card(`LAST GAME · ${h(l.label)}`, `<div class="nv-last"><span class="wl ${l.won ? "W" : "L"}">${l.won ? "W" : "L"}</span>
      <b class="nv-big">${l.us}-${l.them}</b><span>${h(l.site)} ${rk(l.oppRank)}${h(l.opp)}</span></div>`);
  }

  function coachCard(c, career) {
    if (!c || c.open) return "";
    const seat = Math.max(3, Math.min(100, c.seat || 0));
    const sc = c.seat >= 70 ? "var(--bad)" : c.seat >= 50 ? "var(--accent)" : "var(--good)";
    const mail = (c.mail || []).map((m) => `<div class="nv-row" data-k="i"><span>${m.unread ? "●" : "·"}</span><span class="nv-grow">${h(m.from)}: ${h(m.subject)}</span>${m.reply ? '<span class="gold small">reply</span>' : ""}</div>`).join("");
    return card(`${h(c.name.toUpperCase())}${c.interim ? " (INTERIM)" : ""}`, `
      <div class="nv-meter"><span class="muted small">Hot seat</span><div><i style="width:${seat}%;background:${sc}"></i></div><span class="small">${h(c.seatLabel || "")}</span></div>
      ${c.you ? `<div class="nv-chips"><button class="nv-btn sm" data-k="i">✉ Inbox${c.inbox ? ` (${c.inbox})` : ""}</button>${c.replies ? `<span class="gold small">${c.replies} want a reply</span>` : ""}</div>${mail}` : ""}
      ${(c.goals || []).length ? `<div class="nv-sub">AD GOALS</div>` + c.goals.map((g) => `<div class="nv-row"><span class="nv-grow">${h(g.text)}</span><span class="small ${g.status === "met" ? "good" : g.status === "failed" ? "bad" : "muted"}">${h(g.note || g.status)}</span></div>`).join("") : ""}`);
  }

  function pollCard(p) {
    if (!p) return "";
    const rows = p.poll.slice(0, 10);
    const me = p.poll.find((r) => r.me);
    if (me && me.rank > 10) rows.push(me);
    const mv = (r) => r.new ? '<span class="good small">NEW</span>' : r.move > 0 ? `<span class="good small">▲${r.move}</span>` : r.move < 0 ? `<span class="bad small">▼${-r.move}</span>` : '<span class="muted small">–</span>';
    return card(`MEDIA TOP 25 · ${h(p.label)}`, rows.map((r) => `<div class="nv-row ${r.me ? "me" : ""}"><span class="nv-ix">${r.rank}</span><i class="dot" style="background:${col(r.color)}"></i><span class="nv-grow">${h(r.school)}</span><span class="muted small">${h(r.record)}</span>${mv(r)}</div>`).join("")
      || '<span class="muted small">The first poll comes out in the preseason.</span>');
  }

  function standingsCard(s) {
    if (!s) return "";
    return card(`${h(s.conf.toUpperCase())} STANDINGS`, `<div class="nv-row muted small"><span class="nv-ix"></span><span class="nv-grow"></span><span class="nv-c">CONF</span><span class="nv-c">ALL</span></div>` +
      s.rows.map((r, i) => `<div class="nv-row ${r.me ? "me" : ""}"><span class="nv-ix">${i + 1}</span><span class="nv-grow">${rk(r.rank)}${h(r.school)}</span><span class="nv-c">${h(r.conf)}</span><span class="nv-c">${h(r.all)}</span></div>`).join(""));
  }

  function newsCard(n) {
    if (!n || !(n.headlines || []).length) return "";
    return card("HEADLINES", n.headlines.slice(0, 7).map((x) => `<div class="nv-news ${h(x.tone)}">${h(x.text)}</div>`).join(""));
  }

  function schedRows(rows) {
    return (rows || []).map((g) => {
      const res = g.played ? `<span class="${g.won ? "good" : "bad"}"><b>${g.won ? "W" : "L"}</b> ${h(g.score)}</span>` : g.next ? '<span class="gold">NEXT</span>' : '<span class="muted">—</span>';
      return `<div class="nv-row ${g.next ? "me" : ""}"><span class="nv-wk">${h(g.wk)}</span><span class="muted">${h(g.site)}</span><span class="nv-grow ${g.conf ? "" : ""}">${rk(g.oppRank)}${h(g.opp)}${g.conf ? ' <span class="muted small">conf</span>' : ""}</span>${res}</div>`;
    }).join("") || '<span class="muted small">No games yet.</span>';
  }

  function scoresCard(sc) {
    if (!sc || !sc.rows.length) return "";
    return card(h(sc.label.toUpperCase()), sc.rows.map((g) => sc.upcoming
      ? `<div class="nv-row ${g.mine ? "me" : ""}"><span class="nv-grow">${rk(g.ar)}${h(g.away)} <span class="muted">${g.neutral ? "vs" : "at"}</span> ${rk(g.hr)}${h(g.home)}</span></div>`
      : `<div class="nv-row ${g.mine ? "me" : ""}"><span class="nv-grow"><span class="${g.awayWon ? "nv-win" : ""}">${rk(g.ar)}${h(g.away)} ${g.a}</span> <span class="muted">${g.neutral ? "vs" : "at"}</span> <span class="${g.awayWon ? "" : "nv-win"}">${rk(g.hr)}${h(g.home)} ${g.h}</span></span>${g.upset ? '<span class="bad small">UPSET</span>' : ""}</div>`).join(""));
  }

  function lineupCard(list) {
    if (!list || !list.length) return "";
    return card("STARTING LINEUP", `<div class="nv-lineup">` + list.map((p) =>
      `<div data-p="${p.id}"><span class="nv-pos">${p.pos}</span><span class="nv-grow ${p.hurt ? "bad" : p.fill ? "gold" : ""}">${h(p.name)}${p.hurt ? " ✚" : p.fill ? " ↺" : ""}</span><b>${h(p.ovr)}</b></div>`).join("") + `</div>`);
  }

  function leadersCard(L) {
    if (!L || !L.rows.length) return "";
    return card(`TEAM LEADERS${L.lastYear ? " (last season)" : ""}`, L.rows.map((r) =>
      `<div class="nv-row" data-p="${r.id}"><span class="muted small nv-lbl">${h(r.label)}</span><span class="nv-grow">${h(r.name)} <span class="muted small">${h(r.pos)}</span></span><b>${h(r.value)}</b></div>`).join(""));
  }

  function injuriesCard(list) {
    return card("INJURIES", (list || []).length ? list.map((p) =>
      `<div class="nv-row" data-p="${p.id}"><span class="nv-pos">${p.pos}</span><span class="nv-grow">${h(p.name)}${p.starter ? ' <span class="gold small">starter</span>' : ""}</span><span class="bad small">${h(p.status)}</span></div>`).join("")
      : '<span class="muted small">Everybody\'s healthy. ✔</span>');
  }

  function programCard(g) {
    if (!g) return "";
    const pip = (v) => "■".repeat(v) + "□".repeat(10 - v);
    return card("PROGRAM", `<div class="nv-row"><span class="muted nv-lbl">Prestige</span><b class="nv-grow">${g.prestige}</b><span class="muted small">NIL free ${h(g.nil)}</span></div>` +
      (g.facilities || []).map((f) => `<div class="nv-row"><span class="muted nv-lbl">${h(f.k)}</span><span class="nv-grow nv-pips">${pip(f.v)}</span><span class="small">${f.v}/10</span></div>`).join(""));
  }

  function home(d) {
    const t = d.team || {};
    let out = hero(t);
    const acts = [];
    if (!d.online) acts.push(btn("m", "⏩ Sim", "sm"));
    if (d.career) acts.push(btn("i", "✉ Inbox" + (d.coach && d.coach.inbox ? ` (${d.coach.inbox})` : ""), "sm"), btn("c", "👤 Career", "sm"));
    acts.push(btn("v", "💾 Save", "sm"), btn("/", "🔎 Go to…", "sm"));
    out += `<div class="nv-acts">${btn("a", "▶ " + h(d.adv), "primary")}</div><div class="nv-tabs">${acts.join("")}</div>`;
    out += `<div class="nv-tabs">${d.tabs.map((n, i) => `<button data-k="${i + 1}" class="${d.tab === i + 1 ? "on" : ""}">${h(n)}</button>`).join("")}</div>`;
    if (d.tab === 1) {
      out += nextCard(d.next) + lastCard(d.last) + coachCard(d.coach, d.career) + newsCard(d.news) + pollCard(d.top25) + standingsCard(d.standings);
    } else if (d.tab === 2) {
      const so = d.sos;
      out += card("SCHEDULE", (so ? `<div class="muted small" style="margin-bottom:6px">SOS No. ${so.rank} (${h(so.word)})</div>` : "") + schedRows(d.schedule));
      out += `<div class="nv-acts">${btn("s", "📅 Full schedule")}${btn("w", "▦ Scoreboard")}${btn("t", "≡ Standings")}${btn("f", "☂ Weather")}</div>`;
      out += scoresCard(d.scores) + standingsCard(d.standings);
    } else if (d.tab === 3) {
      out += `<div class="nv-acts">${btn("r", "☰ Roster")}${d.career ? btn("h", "▤ Depth chart") + btn("p", "⏱ Practice") : ""}${btn("t", "🏈 Team page")}${btn("$", "$ Budget")}</div>`;
      out += lineupCard(d.lineup) + leadersCard(d.leaders) + injuriesCard(d.injuries) + programCard(d.program);
    }
    return out;
  }

  // ═══ Roster & schedule ════════════════════════════════════════════════════
  let rosterPos = "";
  function roster(d) {
    const chips = ["", ...d.groups.map((g) => g.pos)].map((p) => `<button class="${p === rosterPos ? "on" : ""}" data-rpos="${p}">${p || "ALL"}</button>`).join("");
    let out = `<div class="nv-title">${h(d.school)} <span class="muted">· ${d.count} players</span></div>
      <div class="muted small" style="margin:-4px 2px 8px">NIL ${h(d.nil)}/yr · budget ${h(d.budget)}</div>
      <div class="nv-acts">${d.mine ? btn("h", "▤ Depth chart") : ""}${btn("$", "$ Payroll")}${btn("s", "📅 Schedule")}${btn("Enter", "← Back")}</div>
      <div class="nv-tabs nv-pchips">${chips}</div>`;
    for (const g of d.groups) {
      if (rosterPos && g.pos !== rosterPos) continue;
      out += card(h(g.name.toUpperCase()), g.players.map((p, i) => `<div class="nv-prow" data-p="${p.id}">
        <span class="nv-num">${p.num}</span>
        <span class="nv-grow"><b>${h(p.name)}</b>${p.tr ? ' <span class="info small">⇄</span>' : ""}${p.hurt ? ` <span class="bad small">✚ ${h(p.status || "")}</span>` : ""}
          <span class="muted small nv-pmeta">${h(p.yr)}${p.ht ? " · " + h(p.ht) + " " + h(p.wt) : ""}${p.stars ? " · " + "★".repeat(p.stars) : ""}${p.best ? ` · best: ${h(p.best)} · worst: ${h(p.worst)}` : ""}${p.nil ? ` · <span class="good">${h(p.nil)}</span>` : ""}</span></span>
        <span class="nv-ovr ${i === 0 ? "top" : ""}">${h(p.ovr)}</span></div>`).join(""));
    }
    return out;
  }

  function schedule(d) {
    const rows = d.rows.map((r) => {
      if (r.bye) return `<div class="nv-row muted"><span class="nv-wk">${h(r.wk)}</span><span class="nv-grow">BYE</span></div>`;
      const res = r.played ? `<span class="${r.won ? "good" : "bad"}"><b>${r.won ? "W" : "L"}</b> ${h(r.score)}</span>`
        : `<span class="${r.wpv >= 0.6 ? "good" : r.wpv >= 0.4 ? "gold" : r.wpv !== undefined ? "bad" : "muted"}">${h(r.wp || "—")}</span>`;
      const tags = (r.tags || []).filter(Boolean).map((t) => `<span class="nv-tag">${h(t)}</span>`).join("");
      return `<div class="nv-srow" ${r.played && r.box ? `data-k="${r.n}"` : ""}>
        <span class="nv-wk">${h(r.wk)}</span><span class="nv-grow"><b>${h(r.opp)}</b>
        <span class="muted small nv-pmeta">${h(r.them || "")}${r.look ? " · " + h(r.look) : ""} ${tags}</span></span>${res}</div>`;
    }).join("");
    return `<div class="nv-title">${h(d.school)} <span class="muted">· ${d.year}</span></div>
      <div class="nv-hrow" style="margin:0 2px 8px"><b class="nv-rec">${h(d.record)}</b><span class="muted">${h(d.confRecord ? d.confRecord + " conf" : "")}</span></div>
      ${d.sos ? `<div class="muted small" style="margin:0 2px 8px">${h(d.sos)}</div>` : ""}
      ${card("", rows + '<div class="muted small" style="margin-top:6px">Tap a played game for its box score.</div>')}
      <div class="nv-acts">${btn("s", "SOS")}${btn("o", "Another team")}${btn("b", "← Back")}</div>`;
  }

  // ═══ Game week ════════════════════════════════════════════════════════════
  function week(d) {
    const us = d.us, th = d.them, wb = d.wpBand ?? 0.5;
    const routines = (d.routines || []).map((r) => `<button class="${r.on ? "on" : ""}" data-k="${r.key}">${h(r.name)}${r.default ? " ★" : ""}</button>`).join("");
    return `<div class="nv-title">${h(d.week)}${d.rivalry ? ' <span class="gold">· RIVALRY WEEK</span>' : ""}</div>
      <div class="nv-match">
        <div class="nv-team" style="--tc:${col(us.color)}">${rk(us.rank)}<b>${h(us.school)}</b><span>${h(us.record)}</span><span class="muted small">${h(String(us.ovr))}</span></div>
        <div class="nv-vs"><span class="muted">${h(d.site)}</span><div class="nv-g sm">${gaugeOk ? gauge(wb, d.wp === null) : ""}</div></div>
        <div class="nv-team" style="--tc:${col(th.color)}">${rk(th.rank)}<b>${h(th.school)}</b><span>${h(th.record)}</span><span class="muted small">${h(String(th.ovr))}</span></div>
      </div>
      <div class="nv-odds center ${wb >= 0.6 ? "good" : wb >= 0.4 ? "gold" : "bad"}">${h(d.odds)}</div>
      <div class="muted small center">HC ${h(th.coach)} · ${h(th.scheme)} · ${h(d.forecast)}</div>
      <button class="nv-btn primary wide" data-k="Enter">▶ Go to Saturday</button>
      ${card("ROUTINE", `<div class="nv-tabs nv-wrap">${routines}<button data-k="y">Manage…</button></div>
        <div class="small ${d.routine ? "good" : "muted"}">${h(d.routine || "None — set the week by hand or pick one")}</div>`)}
      ${card("GAME PLAN", `<div class="${d.plan ? "good" : "muted"}">${h(d.plan || "The staff's plan")}</div>`, ' data-k="g"')}
      ${card("PRACTICE", `<b class="good">${h(d.focus)}</b><div class="muted small">${h(d.focusBlurb)}</div>
        <div class="nv-acts">${btn("p", "Change focus")}${btn("r", d.battles ? `Report · ${d.battles} battle${d.battles !== 1 ? "s" : ""}` : "Practice report")}</div>`)}
      ${card("FILM", (d.film || []).map((x) => `<div class="nv-news">${h(x)}</div>`).join("") + `<div class="nv-acts">${btn("o", "Film on " + h(th.school))}</div>`)}
      ${card(`INBOX · ${d.inbox.unread} unread · ${d.inbox.waiting} want a reply`, (d.inbox.mail || []).map((m) => `<div class="nv-row"><span>${m.unread ? "●" : "·"}</span><span class="nv-grow">${h(m.text)}</span></div>`).join(""), ' data-k="i"')}
      ${card("PRESS CONFERENCE", `<div class="${d.presser ? "muted" : ""}">${d.presser ? "Done: " + h(d.presser) : "Optional. Two questions."}</div>${d.banked ? `<div class="good small">Banked for Saturday: ${h(d.banked)}</div>` : ""}`, d.presser ? "" : ' data-k="m"')}
      ${card("INJURIES", (d.injuries || []).map((x) => `<div class="${/OUT/.test(x) ? "bad" : "good"} small">${h(x)}</div>`).join(""), ' data-k="d"')}
      <div class="nv-acts">${btn("d", "Depth chart")}${btn("f", "Formation subs")}${btn("k", "Retention")}${btn("w", "Weather")}${btn("t", h(th.school) + " page")}${btn("s", "My schedule")}${btn("b", "← Back")}</div>`;
  }

  function matchup(d, adds) {
    const teams = d.teams.map((t) => `<div class="nv-mteam ${t.mine ? "mine" : ""}" style="--tc:${col(t.color)}">
      <div class="nv-mhead">${rk(t.rank)}<b>${h(t.full)}</b><span class="muted small">${h(t.conf)} · ${h(t.record)}</span></div>
      <div class="nv-trio"><div><b>${h(String(t.ovr))}</b><span>overall</span></div><div><b>${h(String(t.off))}</b><span>offense</span></div><div><b>${h(String(t.def))}</b><span>defense</span></div></div>
      <div class="muted small">HC ${h(t.coach)} · ${h(t.offScheme)} / ${h(t.defScheme)}</div>
      ${t.out.length ? `<div class="bad small">OUT: ${h(t.out.join(", "))}</div>` : ""}</div>`);
    const wb = d.wpBand;
    return `<div class="nv-title">${h(d.title)}${d.mine ? ' <span class="gold">· YOUR GAME</span>' : ""}</div>
      ${d.slot ? `<div class="center gold small" style="margin-bottom:6px">${h(d.slot)}</div>` : ""}
      ${teams[0]}<div class="center muted" style="margin:4px 0">${d.neutral ? "vs" : "at"}</div>${teams[1]}
      ${wb !== undefined ? `<div class="nv-g center">${gaugeOk ? gauge(wb, d.wp === null) : ""}</div>` : ""}
      ${card("", `<div class="small">${h(d.venue)} · ${h(d.kind)}</div>${d.rivalry ? `<div class="gold small">★ ${h(d.rivalry)}</div>` : ""}
        ${d.series ? `<div class="muted small">Series ${h(d.series)} · last ${h(d.last || "")}</div>` : ""}${d.trophy ? `<div class="gold small">${h(d.trophy)}</div>` : ""}`)}
      ${stream(adds || [])}
      <details class="nv-log"><summary>Full text</summary><div id="nv-tail"></div></details>`;
  }

  // ═══ Game Day ═════════════════════════════════════════════════════════════
  function field(d) {
    const W = 360, H = 120, EZ = 30, F = W - EZ * 2;
    const X = (y) => EZ + (F * y) / 100;
    let lines = "";
    for (let y = 10; y < 100; y += 10) {
      lines += `<line x1="${X(y)}" y1="0" x2="${X(y)}" y2="${H}" stroke="rgba(255,255,255,.35)" stroke-width="${y === 50 ? 1.6 : 1}"/>`;
      const n = y <= 50 ? y : 100 - y;
      lines += `<text x="${X(y)}" y="${H - 8}" class="nv-yn">${n}</text><text x="${X(y)}" y="16" class="nv-yn">${n}</text>`;
    }
    for (let y = 5; y < 100; y += 10) lines += `<line x1="${X(y)}" y1="${H / 2 - 5}" x2="${X(y)}" y2="${H / 2 + 5}" stroke="rgba(255,255,255,.25)"/>`;
    const off = d.offense === "home" ? d.home : d.away, def = off === d.home ? d.away : d.home;
    const leftTeam = d.right ? off : def, rightTeam = d.right ? def : off;     // each side's own end zone
    const ball = X(d.ball);
    const fd = d.first !== null && d.first !== undefined ? `<line x1="${X(d.first)}" y1="4" x2="${X(d.first)}" y2="${H - 4}" stroke="#f2c14e" stroke-width="2.5"/>` : "";
    const arrow = d.right ? `M${ball + 9},${H / 2} l-7,-6 v12 z` : `M${ball - 9},${H / 2} l7,-6 v12 z`;
    return `<svg class="nv-field" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
      <rect x="0" y="0" width="${W}" height="${H}" fill="#2f6b3a"/>
      <rect x="0" y="0" width="${EZ}" height="${H}" fill="${col(leftTeam.color)}" opacity=".85"/>
      <rect x="${W - EZ}" y="0" width="${EZ}" height="${H}" fill="${col(rightTeam.color)}" opacity=".85"/>
      <text x="${EZ / 2}" y="${H / 2}" class="nv-ez" transform="rotate(-90 ${EZ / 2} ${H / 2})">${h(leftTeam.abbr)}</text>
      <text x="${W - EZ / 2}" y="${H / 2}" class="nv-ez" transform="rotate(90 ${W - EZ / 2} ${H / 2})">${h(rightTeam.abbr)}</text>
      ${lines}${fd}
      <line x1="${ball}" y1="4" x2="${ball}" y2="${H - 4}" stroke="#58a6ff" stroke-width="2.5"/>
      <ellipse cx="${ball}" cy="${H / 2}" rx="7" ry="4.5" fill="#8a4b22" stroke="#fff" stroke-width="1"/>
      <path d="${arrow}" fill="#fff" opacity=".9"/></svg>`;
  }

  function sb(t, cls) {
    const to = "●".repeat(t.to) + "○".repeat(Math.max(0, 3 - t.to));
    return `<div class="nv-sbt ${cls}" style="--tc:${col(t.color)}"><div class="nv-sbn">${rk(t.rank)}${h(t.abbr)}${t.ball ? ' <span class="nv-pos-ball">🏈</span>' : ""}</div>
      <div class="nv-sbs">${t.score}</div><div class="nv-to">${to}</div></div>`;
  }

  function game(d, adds) {
    const st = d.stats;
    const stat = st ? `<table class="nv-stats"><tr><th></th><th>${h(d.away.abbr)}</th><th>${h(d.home.abbr)}</th></tr>
      ${[["Yards", "yds"], ["Rush", "rush"], ["Pass", "pass"], ["3rd down", "third"], ["Turnovers", "to"], ["Possession", "top"]].map(([l, k]) => `<tr><td>${l}</td><td>${h(st.away[k])}</td><td>${h(st.home[k])}</td></tr>`).join("")}</table>` : "";
    return `<div class="nv-sb">${sb(d.away, "l")}<div class="nv-sbc"><b>${h(d.q)} ${h(d.clock)}</b><div class="nv-dd">${h(d.dd)}</div><div class="muted small">${h(d.spot ? "ball on " + d.spot : "")}</div>${d.wx ? `<div class="info small">${h(d.wx)}</div>` : ""}</div>${sb(d.home, "r")}</div>
      ${field(d)}
      ${d.drive ? `<div class="nv-drive small"><b>Drive:</b> ${d.drive.plays} play${d.drive.plays !== 1 ? "s" : ""}, <span class="${d.drive.yds > 0 ? "good" : "bad"}">${d.drive.yds > 0 ? "+" : ""}${d.drive.yds} yds</span> · started at ${h(d.drive.start)}</div>` : ""}
      ${(d.plays || [])[0] ? `<div class="nv-lastplay"><span class="muted small">LAST PLAY · ${h(d.plays[0].q)} ${h(d.plays[0].clock)}${d.plays[0].off ? " · " + h(d.plays[0].off) : ""}</span><div>${h(d.plays[0].text)}</div></div>` : ""}
      ${stream(adds || [])}
      ${d.clip ? card(`COACH'S CLIPBOARD · ${h(d.clipSide)}`, d.clip.map((x) => `<div class="small">${h(x)}</div>`).join("")) : ""}
      ${card("PLAY BY PLAY", (d.plays || []).slice(1).map((p, i) => `<div class="nv-play"><div class="muted small">${h(p.q)} ${h(p.clock)} ${p.dd ? "· " + h(p.dd) : ""} ${p.off ? "· " + h(p.off) : ""}</div><div>${h(p.text)}</div></div>`).join("") || '<span class="muted small">Kickoff. The first snap is coming.</span>')}
      ${(d.scoring || []).length ? card("SCORING", d.scoring.map((s) => `<div class="nv-row"><span class="muted small">${h(s.q)} ${h(s.clock)}</span><b>${h(s.team)}</b><span class="nv-grow good small">${h(s.what)}</span></div>`).join("")) : ""}
      ${stat ? card("TEAM STATS", stat) : ""}
      <details class="nv-log"><summary>Full broadcast text</summary><div id="nv-tail"></div></details>`;
  }

  // ═══ The Saturday show ════════════════════════════════════════════════════
  const WHO = { host: "#e6edf3", film: "#39c5cf", coach: "#f2c14e", boom: "#d2a8ff", defender: "#57ab5a", crowd: "#ff7b72", reporter: "#8b949e", guest: "#f2c14e", player: "#e6edf3" };
  function show(d, adds) {
    let out = `<div class="nv-show"><div class="nv-showname">📺 ${h(d.name.toUpperCase())}</div><div class="muted small">${h(d.week)} · ${h(d.town)}</div>
      <div class="nv-showgame">${h(d.matchup)}</div><div class="muted small">${h(d.stadium)}</div></div>`;
    for (const a of adds) {
      if (a.kind === "say") {
        const c = WHO[a.data.who] || "var(--accent)";
        out += `<div class="nv-say ${a.data.who === "crowd" ? "crowd" : ""}" style="--sc:${c}"><b>${h(a.data.label)}</b><span>${h(a.data.text)}</span></div>`;
      } else if (a.kind === "picks") {
        const p = a.data;
        out += card("THE PICKS", `<div class="nv-scroll"><table class="nv-picks"><tr><th></th>${p.names.map((n) => `<th>${h(n)}</th>`).join("")}</tr>
          ${p.rows.map((r) => `<tr><td><div>${h(r.game)}</div><div class="muted small">${h(r.kick)}</div></td>${r.picks.map((x) => `<td><b>${h(x)}</b></td>`).join("")}</tr>`).join("")}</table></div>
          <div class="muted small">${h(p.note)}</div>`);
      }
    }
    return out;
  }

  // ═══ Recruiting ═══════════════════════════════════════════════════════════
  const stars = (n) => `<span class="nv-stars">${"★".repeat(n || 0)}</span>`;
  const stTone = (st) => /LEADING|GOOD SHAPE/.test(st) ? "good" : /MIX/.test(st) ? "gold" : /FRINGE/.test(st) ? "warn" : "muted";
  const msgLine = (m) => m ? `<div class="nv-msg">${h(m)}</div>` : "";
  const bar = (v, max = 100, cls = "") => `<span class="nv-bar ${cls}"><i style="width:${Math.max(2, Math.min(100, 100 * v / (max || 1)))}%"></i></span>`;

  function rhub(d) {
    const ro = d.readonly;
    const needs = (d.needs || []).map((n) => `<div class="nv-need ${n.got >= n.want ? "done" : n.got ? "part" : ""}"><b>${h(n.pos)}</b><span>${n.got}/${n.want}</span>${n.board ? `<i>${n.board}●</i>` : ""}</div>`).join("") || '<span class="muted small">Every room is full.</span>';
    const top = (d.top || []).map((r) => `<div class="nv-row"><span class="nv-pos">${h(r.pos)}</span><span class="nv-grow">${h(r.name)} ${stars(r.stars)}</span><span class="small ${stTone(r.standing)}">${h(r.standing)}</span></div>`).join("")
      || '<span class="muted small">Your board is empty — open the Recruit Finder.</span>';
    const tools = ro ? "" : `<div class="nv-acts">${btn("q", "⟳ Standing orders")}${btn("v", "🏟 Official visits")}${btn("w", "⚔ War room")}${btn("h", "Hit or bust")}${d.week === 0 ? btn("c", "⛺ Summer camp") : ""}${d.week >= 8 ? btn("l", "Walk-ons") : ""}</div>
      <div class="nv-acts">${btn("o", "Overtime (+10 hrs, risky)", "risky")}${btn("t", "Back channel (tampering)", "risky")}</div>`;
    return `<div class="nv-hero" style="--tc:${col(d.color)}"><div class="nv-hmode">RECRUITING · ${d.classYear} CLASS · ${h(d.status)}</div>
        <div class="nv-hname">${h(d.school)}</div>
        <div class="nv-trio light"><div><b>${d.rank ? "#" + d.rank : "—"}</b><span>class rank</span></div><div><b>${d.commits}/${d.cap}</b><span>commits</span></div><div><b>${d.avg ? d.avg.toFixed(2) + "★" : "—"}</b><span>avg stars</span></div></div></div>
      ${ro ? '<div class="nv-msg">View only — this board belongs to another staff.</div>' : ""}
      ${card("THIS WEEK", `${d.contact && !d.hoursTotal ? '<div class="gold">Contact period</div>' : `<div class="nv-meter"><span class="small">Hours <b>${d.hours}/${d.hoursTotal}</b></span>${bar(d.hours, d.hoursTotal)}</div>`}
        <div class="muted small">${h(d.hoursWhy)}</div>
        <div class="nv-row"><span class="muted nv-lbl">NIL free</span><b class="good nv-grow">${h(d.nil)}</b><span class="muted small">Board ${d.board}/40</span></div>
        ${d.orders ? `<div class="info small">Standing orders: ${d.orders.queued} queued · ${d.orders.run} run this week${d.orders.cut ? ` · <span class="bad">${d.orders.cut} cut</span>` : ""}</div>` : ""}
        ${d.contact ? '<div class="gold small">Contact period — evaluation, calls/texts and offers only.</div>' : ""}`)}
      <div class="nv-grid2">${btn("f", "🔎 Recruit finder", "big")}${btn("g", "✨ Suggested for you", "big")}${btn("1", "★ My board", "big")}${btn("2", "🎓 My class", "big")}</div>
      ${card("POSITION NEEDS · signed / needed", `<div class="nv-needs">${needs}</div>`)}
      ${card("TOP OF YOUR BOARD", top, ' data-k="1"')}
      ${tools}
      ${card("RECRUITING WIRE", (d.news || []).map((n) => `<div class="nv-news ${n.kind === "commit" ? "good" : n.kind === "decommit" ? "bad" : "info"}">● ${h(n.text)}</div>`).join("") || '<span class="muted small">No news yet.</span>')}
      <div class="nv-acts">${btn("3", "National rankings")}${btn("4", "News")}${btn("5", "Final class rankings")}${btn("6", "$ Budget & NIL")}${btn("b", "← Back")}</div>`;
  }

  function rrow(r, extra = "") {
    const status = r.mine ? '<span class="good small">◆ YOURS</span>' : r.commit ? `<span class="bad small">◆ ${h(r.commit)}</span>` : "";
    return `<div class="nv-rrow" data-k="${r.i}"><span class="nv-ix">${r.rank}</span>
      <span class="nv-grow"><b>${h(r.name)}</b> ${r.board ? '<span class="gold">●</span>' : ""}
        <span class="muted small nv-pmeta"><span class="nv-pos">${h(r.pos)}</span>${stars(r.stars)} · ${h(r.home)} · proj ${h(r.proj)}${r.offer ? ' · <span class="good">offered</span>' : ""}</span>
        ${extra}</span>
      <span class="nv-rside"><span class="small ${stTone(r.standing)}">${h(r.standing)}</span>${status}</span></div>`;
  }

  function rlist(d) {
    const rows = d.rows.map((r) => {
      const why = r.why && r.why.length ? `<span class="nv-why">${r.why.map((w) => `<i>${h(w)}</i>`).join("")}</span>` : "";
      const add = !d.readonly && !r.board ? `<button class="nv-add" data-k="a${r.i}">＋ Board</button>` : "";
      return rrow(r, why + add);
    }).join("") || '<div class="muted">Nobody matches. Loosen a filter or reset.</div>';
    return `<div class="nv-title">${h(d.title)} <span class="muted">· ${d.count.toLocaleString()}</span></div>
      <div class="muted small" style="margin:-4px 2px 8px">${h(d.filters)} · sorted by ${h(d.sort)} · ${d.hours} hrs · board ${d.board}/40</div>
      ${msgLine(d.msg)}
      <div class="nv-tabs">${btn("f", "Filters", "sm")}${btn("s", "Sort", "sm")}${btn("g", "Suggested", "sm")}${btn("r", "Reset", "sm")}${btn("b", "← Back", "sm")}</div>
      ${card("", rows)}
      <div class="nv-pager">${btn("p", "‹ Prev")}<span class="muted">page ${d.page}/${d.pages}</span>${btn("n", "Next ›")}</div>`;
  }

  function rboard(d) {
    const rows = d.rows.map((r) => {
      const ex = `<span class="nv-bline">${bar(r.interest, 100, stTone(r.standing))}<span class="small muted">${r.leader ? (r.leaderMe ? '<span class="good">you lead</span>' : "leader " + h(r.leader)) : "open"}</span>
        ${r.nil && r.nil !== "—" ? `<span class="good small">${h(r.nil)}</span>` : ""}${r.queued ? '<span class="info small">Q</span>' : ""}${r.visit ? '<span class="info small">visit</span>' : ""}</span>
        ${d.readonly ? "" : `<span class="nv-rowacts"><button data-k="$${r.i}">$ NIL</button><button data-k="q${r.i}">⟳ Order</button><button data-k="d${r.i}">✕ Drop</button></span>`}`;
      return rrow(r, ex);
    }).join("") || '<div class="muted">Nobody on your board yet — open the Recruit Finder.</div>';
    return `<div class="nv-title">${h(d.school)} · Board <span class="muted">${d.rows.length}/40</span></div>
      <div class="nv-meter" style="margin:0 2px 4px"><span class="small">Hours <b>${d.hours}/${d.hoursTotal}</b></span>${bar(d.hours, d.hoursTotal)}<span class="good small">NIL ${h(d.nil)}</span></div>
      <div class="muted small" style="margin:0 2px 8px">${h(d.needs)}</div>${msgLine(d.msg)}
      <div class="nv-tabs">${btn("f", "🔎 Find", "sm")}${btn("g", "✨ Suggested", "sm")}${btn("s", "Sort: " + h(d.sort), "sm")}${btn("b", "← Back", "sm")}</div>
      ${card("", rows)}`;
  }

  function rcard(d) {
    const race = (d.race || []).map((t) => `<div class="nv-race ${t.me ? "me" : ""}"><span class="nv-grow">${h(t.school)}${t.commit ? " ◆" : ""}</span>
      <span class="nv-bar ${t.me ? "good" : ""}"><i style="width:${Math.max(2, 100 * t.v / (d.raceMax || 1))}%;${t.me ? "" : `background:${col(t.color)}`}"></i></span><b>${t.v}</b></div>`).join("") || '<span class="muted small">Nobody\'s in on him yet.</span>';
    const acts = (d.actions || []).map((a) => `<button class="nv-act" data-k="${a.key}" ${a.ok ? "" : "disabled"}><b>${h(a.label)}</b><span>${a.cost}h</span></button>`).join("");
    return `<div class="nv-title">${h(d.name)} <span class="muted">· ${h(d.pos)}</span></div>
      <div style="margin:-6px 2px 8px">${stars(d.stars)} <span class="muted small">National #${d.rank} · ${h(d.state)} · ${h(d.size)}</span></div>
      ${(d.tags || []).map((t) => `<span class="nv-tag big">${h(t)}</span>`).join(" ")}
      ${msgLine(d.msg)}
      ${card("THE RACE", `<div class="nv-row"><span class="nv-grow">You: <b class="${stTone(d.standing)}">${h(d.standing)}</b></span><span class="small">${d.offered ? '<span class="good">Offered ✔</span>' : '<span class="bad">No offer</span>'} · ${d.offers} out</span></div>${race}`)}
      ${d.readonly ? "" : card(`STAFF HOURS LEFT · ${d.hours}`, `<div class="nv-actgrid">${acts}</div>`)}
      ${card("SCOUTING", `<div><span class="muted">Projection</span> <b>${h(d.proj)}</b> <span class="muted small">· scouted ${d.scouted}/3</span></div>
        <div class="nv-sub">WHAT HE WANTS</div>${d.wants.map((w, i) => `<div class="${w ? "" : "muted small"}">${i + 1}. ${w ? `<b>${h(w)}</b>` : "??? — evaluate, or pitch it and see"}</div>`).join("")}
        ${d.reads ? `<div class="muted small" style="margin-top:4px">Reads as: ${h(d.reads)}</div>` : ""}`)}
      ${(d.extras || []).length ? card("", d.extras.map((x) => `<div class="small ${/⚠/.test(x) ? "bad" : ""}">${h(x)}</div>`).join("")) : ""}
      ${card("NIL", (d.nil || []).filter(Boolean).map((x) => `<div class="small">${h(x)}</div>`).join(""))}
      ${card("", `${d.promise ? `<div><span class="muted">Your promise</span> <b class="gold">${h(d.promise)}</b></div>` : ""}<div class="small muted">His room: ${h(d.room)}</div>
        ${(d.story || []).map((s) => `<div class="small"><span class="muted">${s.wk ? "Wk " + s.wk : "Summer"}</span> ${h(s.text)}</div>`).join("")}`)}
      ${d.readonly ? `<div class="nv-acts">${btn("b", "← Back")}</div>` : `<div class="nv-acts">${btn("n", "$ NIL offer")}${btn("q", "⟳ Queue order" + (d.queued ? ` (${d.queued})` : ""))}${d.visit ? "" : btn("v", "🏟 Official visit")}${d.promise ? "" : btn("m", "🤝 Make a promise")}${btn("t", d.onBoard ? "Remove from board" : "＋ Add to board")}${btn("b", "← Back")}</div>`}`;
  }

  function rclass(d) {
    return `<div class="nv-title">${h(d.school)} · ${d.year} class</div>
      <div class="nv-trio" style="margin-bottom:10px"><div><b>${d.commits}/${d.cap}</b><span>commits</span></div><div><b>${d.avg ? d.avg.toFixed(2) + "★" : "—"}</b><span>average</span></div><div><b>${d.rank ? "#" + d.rank : "—"}</b><span>national rank</span></div></div>
      <div class="small" style="margin:0 2px 8px">Momentum <b class="${d.momentum >= 38 ? "good" : "gold"}">${h(d.momWord)}</b> ${d.momentum}/100 · <span class="muted">${h(d.needs)}</span></div>
      ${card("COMMITMENTS", (d.groups || []).map((g) => `<div class="nv-row"><span class="nv-pos">${h(g.pos)}</span><span class="nv-grow">${g.players.map((p) => `${h(p.name)} <span class="nv-stars">${p.stars}★</span> <span class="muted small">${h(p.state)}</span>`).join("<br>")}</span></div>`).join("") || '<span class="muted">No commitments yet.</span>')}
      ${card("NATIONAL CLASS RANKINGS", d.top.map((t, i) => `<div class="nv-row ${t.me ? "me" : ""}"><span class="nv-ix">${i + 1}</span><span class="nv-grow">${h(t.school)}</span><span class="small">${t.n} commits · ${t.avg.toFixed(2)}★</span></div>`).join(""))}`;
  }

  // ═══ Transfer portal ══════════════════════════════════════════════════════
  const whoTag = (r) => {
    if (!r.known) return `<span class="muted small">? · ${h((r.heat || "").toLowerCase())}</span>`;
    const tone = r.place === 1 ? "good" : r.ratio >= 0.9 ? "gold" : "bad";
    const word = r.place === 1 ? (r.ratio >= 1.12 ? "Leader — clear" : "Leader — barely") : `#${r.place} of ${r.of}${r.ratio >= 0.9 ? " — close" : " — behind"}`;
    return `<span class="small ${tone}"><b>${word}</b>${r.timeline === "deciding THIS week" ? " ⏱" : ""}</span>`;
  };

  function portal(d) {
    const rows = d.rows.map((r) => `<div class="nv-rrow" data-k="${r.i}"><span class="nv-ovr">${h(r.ovr)}</span>
      <span class="nv-grow"><b>${h(r.name)}</b>${r.offered ? ' <span class="good">✓</span>' : ""}
        <span class="muted small nv-pmeta"><span class="nv-pos">${h(r.pos)}</span>${h(r.yr)} · from ${h(r.from)}${r.nil ? ` · <span class="good">${h(r.nil)}</span>` : ""}</span>
        <span class="gold small nv-pmeta">wants ${h(r.wants)}</span></span>
      <span class="nv-rside">${whoTag(r)}${r.known && r.place > 1 && r.leader ? `<span class="muted small">${h(r.leader)} leads</span>` : ""}</span></div>`).join("")
      || '<div class="muted">Nobody on the board matches that view.</div>';
    return `<div class="nv-hero" style="--tc:#3b5bdb"><div class="nv-hmode">TRANSFER PORTAL · ${h(d.window.toUpperCase())}</div><div class="nv-hname">${h(d.school)}</div>
        <div class="nv-trio light"><div><b>${d.hours}</b><span>hours</span></div><div><b>${d.slots}</b><span>spots open</span></div><div><b>${h(d.nil)}</b><span>NIL free</span></div></div>
        <div class="small" style="opacity:.85;margin-top:6px">${d.signed} signed · ${d.offers} offers out · ${d.leaving} leaving you</div></div>
      ${d.holes.length ? `<div class="nv-msg">Starting holes: ${h(d.holes.join(", "))}</div>` : ""}
      ${d.short.length ? card("STAFF SHORT LIST", d.short.map((x) => `<div class="small">${h(x)}</div>`).join("")) : ""}
      <div class="nv-tabs"><button class="${d.targets ? "on" : ""}" data-k="t">My targets</button><button class="${d.fits ? "on" : ""}" data-k="h">Fits my needs</button>
        <button data-k="s">Sort: ${h(d.sort)}</button><button data-k="f">Position</button><button data-k="y">My players (${d.leaving})</button></div>
      ${card("", rows)}
      <div class="nv-pager">${btn("p", "‹ Prev")}<span class="muted">page ${d.page}/${d.pages}</span>${btn("n", "Next ›")}</div>
      <button class="nv-btn primary wide" data-k="d">✓ Done for this week</button>`;
  }

  function pcard(d) {
    const ang = d.angles.map((a) => `<button class="nv-angle g${a.grade}" data-k="${a.key}" ${d.known && d.hours >= d.cost.pitch ? "" : "disabled"}>
      <span>${a.star ? "★ " : a.second ? "☆ " : ""}${h(a.label)}</span><b>${a.grade}</b>${a.used ? `<i>×${a.used}</i>` : ""}</button>`).join("");
    const you = d.known ? `<div class="nv-row"><span class="nv-grow">You: ${whoTag(d)} ${d.leader ? `<span class="muted small">· ${h(d.leader)} ${d.place > 1 ? "leads" : "is next"}</span>` : ""}</span></div>
        <div class="nv-row"><span class="nv-grow small">Timeline: <b class="${d.timeline === "deciding THIS week" ? "bad" : d.timeline === "deciding next week" ? "gold" : "good"}">${h(d.timeline)}</b></span><span class="small">Your work: <b class="info">${h(d.work)}</b>${d.visited ? ' · <span class="purple">visited</span>' : ""}</span></div>`
      : `<div class="muted small">Market: ${h(d.heat)} — ${d.serious} serious. Contact him to learn where you stand.</div>`;
    return `<div class="nv-title">${h(d.name)} <span class="muted">· ${h(d.pos)} · ${h(d.from)}</span></div>
      <div style="margin:-6px 2px 8px" class="small"><b>${h(d.ovr)}</b> <span class="muted">· ${h(d.yr)}${d.home ? " · from " + h(d.home) : ""} · left because: ${h(d.reason)}</span></div>
      ${(d.msgs || []).map((m) => `<div class="nv-msg">${h(m)}</div>`).join("")}
      ${card("WHAT HE WANTS", `<div><b class="gold">★ ${h(d.wants)}</b></div><div class="${d.also ? "" : "muted"} small">☆ ${d.also ? h(d.also) : "second priority unknown — contact him"}</div>
        <div class="small" style="margin-top:4px">${h(d.fit)}</div>`)}
      ${card("WHERE YOU STAND", you)}
      ${card(`YOUR CASE · pitch ${d.cost.pitch}h · ${d.hours} hrs left`, `<div class="nv-angles">${ang}</div><div class="muted small" style="margin-top:6px">Pitch where you're strong and he cares (★ ☆). Weak pitches on what he wants backfire.</div>`)}
      ${card("NIL", `<div class="small">Market ~${h(d.market)}/yr · yours <b class="${d.mine ? "good" : "muted"}">${h(d.mine || "none")}</b> · free ${h(d.free)}</div>`)}
      <div class="nv-grid2">
        ${d.known ? btn("1", "Contacted ✓", "big") : btn("1", `📞 Contact (${d.cost.contact}h)`, "big")}
        ${d.visited ? btn("v", "Visited ✓", "big") : btn("v", `🏟 Visit (${d.cost.visit}h)`, "big")}
        ${btn("o", d.offered ? "Withdraw offer" : `✓ Offer a spot (${d.slots})`, "big")}
        ${btn("n", "$ NIL offer", "big")}</div>
      <button class="nv-btn primary wide" data-k="c" ${d.offered && !d.pushedThisWeek ? "" : "disabled"}>✍ Push to commit (${d.cost.push}h)</button>
      <div class="nv-acts">${btn("b", "← Back to board")}</div>`;
  }

  function pkeep(d) {
    return `<div class="nv-title">Your players in the portal</div>
      <div class="muted small" style="margin:-4px 2px 8px">${d.cost} hrs a talk · ${d.hours} hrs left · once a week each</div>
      ${card("STILL IN THE PORTAL", d.out.map((p) => `<div class="nv-rrow" data-k="${p.i}"><span class="nv-ovr">${h(p.ovr)}</span>
        <span class="nv-grow"><b>${h(p.name)}</b> <span class="muted small">${h(p.pos)} · ${h(p.yr)}</span>
        <span class="muted small nv-pmeta">${h(p.reason)}</span><span class="gold small nv-pmeta">wants ${h(p.wants)}</span></span>
        <span class="nv-rside">${p.talked ? '<span class="muted small">talked this week</span>' : '<span class="info small">Talk ›</span>'}</span></div>`).join("") || '<span class="muted small">Nobody left to talk to.</span>')}
      ${d.kept.length ? card("STAYING", d.kept.map((n) => `<div class="good">✓ ${h(n)}</div>`).join("")) : ""}
      ${d.gone.length ? card("GONE", d.gone.map((g) => `<div class="bad small">✗ ${h(g.name)} → ${h(g.to)}</div>`).join("")) : ""}
      <div class="nv-acts">${btn("Enter", "← Back")}</div>`;
  }

  // ═══ Player card (full screen and the pop-up) ═════════════════════════════
  function playerHTML(d, full) {
    const nilLine = d.nil ? `<span class="good">${h(d.nil)}/yr NIL</span>` : "";
    const hero = `<div class="nv-hero" style="--tc:${col(d.color)}"><div class="nv-hmode">${h(d.team.toUpperCase())}</div>
      <div class="nv-hname"><span class="nv-hrank">#${d.num}</span>${h(d.name)}</div>
      <div class="nv-hsub">${h(d.posName)} · ${h(d.yr)} · ${h(d.ht)}, ${h(d.wt)} lbs</div>
      <div class="nv-trio light"><div><b>${h(String(d.ovr))}</b><span>${d.hide ? "looks like" : "overall"}</span></div><div><b>${"★".repeat(d.hs || 0) || "—"}</b><span>HS recruit</span></div><div><b>${h(d.dev)}</b><span>development</span></div></div></div>`;
    const tags = [d.generational ? '<span class="nv-tag big purple">✦ Generational talent</span>' : "", d.transfer ? `<span class="nv-tag big">⇄ from ${h(d.transfer)}</span>` : "",
      d.injury ? `<span class="nv-tag big bad">✚ ${h(d.injury)}</span>` : ""].join("");
    const mor = d.morale ? `<div class="nv-row"><span class="muted nv-lbl">Morale</span><b class="nv-grow ${d.morale.v >= 65 ? "good" : d.morale.v >= 45 ? "gold" : "bad"}">${d.morale.v} · ${h(d.morale.word)}</b></div>${d.morale.log.length ? `<div class="muted small">lately: ${h(d.morale.log.join("; "))}</div>` : ""}` : "";
    const info = card("", `<div class="nv-row"><span class="muted nv-lbl">Durability</span><span class="nv-grow">${h(d.durability)}</span></div>
      <div class="nv-row"><span class="muted nv-lbl">Ceiling</span><span class="nv-grow">${h(d.ceiling)}</span></div>
      ${d.classroom ? `<div class="nv-row"><span class="muted nv-lbl">Classroom</span><span class="nv-grow">${h(d.classroom)}</span></div>` : ""}
      <div class="nv-row"><span class="muted nv-lbl">NIL</span><span class="nv-grow">${nilLine || '<span class="muted">none</span>'}</span></div>${mor}`);
    const traits = (d.traits || []).length ? card("PERSONALITY", d.traits.map((t) => `<div style="margin:3px 0"><b class="gold">${h(t.name)}</b> <span class="muted small">${h(t.why)}</span></div>`).join("")) : "";
    const st = d.stats ? card(`${h(d.stats.label.toUpperCase())} · ${d.stats.games} games`, d.stats.rows.map((r) => `<div class="nv-statg"><span class="info small">${h(r.group)}</span><div>${r.cells.map(([k, v]) => `<span><i>${h(k)}</i><b>${h(v)}</b></span>`).join("")}</div></div>`).join("")) : "";
    const max = d.skillMax || 1.2;
    const skills = (d.skills || []).length ? card(`${h(d.posName.toUpperCase())} SKILLS`, d.skills.map((k) => `<div class="nv-race"><span class="nv-grow small">${h(k.label)}</span>${d.hide ? `<span class="small">${h(k.word)}</span>` : `<span class="nv-bar ${k.v / max >= 0.8 ? "good" : k.v / max >= 0.6 ? "gold" : "warn"}"><i style="width:${Math.round(100 * k.v / max)}%"></i></span><b class="small">${k.v.toFixed(2)}</b>`}</div>`).join("")
      + (d.report ? `<div class="muted small" style="margin-top:6px">Staff report: ${h(d.report)}</div>` : "") + (d.practice ? `<div class="info small">This week: ${h(d.practice)}</div>` : "")) : "";
    const fund = card(d.hide ? "ATHLETE" : "FUNDAMENTALS", (d.fund || []).map((f) => d.hide ? `<div class="nv-row"><span class="nv-grow small">${h(f.name)}</span><span class="small">${h(f.word)}</span></div>`
      : `<div class="nv-race"><span class="nv-grow small">${h(f.name)}</span><span class="nv-bar"><i style="width:${f.raw}%"></i></span><b class="small">${f.raw}</b><span class="muted small">→ ${f.applied}</span></div>`).join(""));
    const alts = card(d.hide ? "OTHER POSITIONS" : "POSITION FIT", (d.alts || []).map((a) => `<div class="nv-row"><span class="nv-pos">${h(a.pos)}</span><span class="nv-grow">${h(String(a.ovr))}</span>${a.prof !== undefined ? `<span class="muted small">${a.prof.toFixed(2)}</span>` : ""}</div>`).join(""));
    const tl = (d.timeline || []).length ? card("CAREER", d.timeline.map((y) => `<div class="nv-tl"><b class="gold">${y.year}</b> <span class="small">${h(String(y.ovr))}${y.delta !== null && y.delta !== undefined ? ` <span class="${y.delta >= 0 ? "good" : "bad"}">(${y.delta >= 0 ? "+" : ""}${y.delta})</span>` : ""}</span>
      ${y.events.map((e) => `<div class="small">• ${h(e)}</div>`).join("")}${y.stats ? `<div class="muted small">↳ ${h(y.stats)}</div>` : ""}</div>`).join("")) : "";
    const nav = full && d.room ? `<div class="nv-pager">${btn("p", "‹ Prev")}<span class="muted">${h(d.pos)} ${d.room.i} of ${d.room.n}</span>${btn("n", "Next ›")}</div>` : "";
    return hero + (tags ? `<div style="margin:0 0 8px">${tags}</div>` : "") + nav + info + st + skills + traits + tl + fund + alts
      + (full ? `<div class="nv-acts">${btn("Enter", "← Back")}</div>` : "");
  }
  function player(d) { return playerHTML(d, true); }

  if (typeof openCard === "function") {
    const plainOpen = openCard;
    openCard = async function (id, back = false) {
      if (S.prefs.native === false || !/^\d+$/.test(String(id))) return plainOpen(id, back);
      let d;
      try { d = await api("/card", { id }); } catch (e) { return plainOpen(id, back); }
      if (!d || !d.data) return plainOpen(id, back);
      if (!back && !$("modal").hidden && S.cardCur) S.cardStack.push(S.cardCur);
      if ($("modal").hidden) S.cardStack = [];
      S.cardCur = id;
      $("mbody").innerHTML = `<div class="nvm">${playerHTML(d.data, false)}</div>`;
      $("mtitle") && ($("mtitle").textContent = `#${d.data.num} ${d.data.name}`);
      $("mback").hidden = !S.cardStack.length;
      $("modal").hidden = false;
      $("modal").querySelector(".sheet").scrollTop = 0;
    };
  }

  // ═══ Depth chart ══════════════════════════════════════════════════════════
  function depth(d) {
    const rows = d.rows.map((r, k) => {
      const cut = k === d.n ? `<div class="nv-cut">CUT LINE · rotation / development</div>` : "";
      const mv = r.move > 0 ? `<span class="good small">staff ▲</span>` : r.move < 0 ? `<span class="bad small">staff ▼</span>` : "";
      const form = d.camp ? `Camp ${(r.camp || []).map((x) => `<span class="${x > 0 ? "good" : x < 0 ? "bad" : ""}">${x > 0 ? "+" : ""}${x}</span>`).join(" ") || "—"} · ${h(r.formWord)}`
        : `Film ${(r.film || []).map((x) => `<span class="${x >= 75 ? "good" : x >= 65 ? "gold" : "bad"}">${x}</span>`).join(" ") || "—"} · ${h(r.filmWord)}`;
      return cut + `<div class="nv-drow ${r.starter ? "start" : ""}">
        <div class="nv-dmove"><button data-k="u${r.i}" ${r.i === 1 ? "disabled" : ""}>▲</button><span>${r.i}</span><button data-k="d${r.i}" ${r.i === d.rows.length ? "disabled" : ""}>▼</button></div>
        <div class="nv-grow" data-p="${r.id}"><b>#${r.num} ${h(r.name)}</b>${r.hurt ? ' <span class="bad">✚</span>' : ""} <span class="muted small">${h(r.yr)} · ${h(r.ovr)}</span>
          <div class="small">Staff #${r.staff} ${mv} · coord #${r.coord} · pos #${r.posc}${r.split ? ' · <span class="gold">split</span>' : ""} · morale ${r.morale}</div>
          <div class="small muted">${form}</div>
          <details class="small"><summary class="muted">Staff read</summary><div>Coordinator: ${h(r.coordNote)}</div><div>Position coach: ${h(r.posNote)}</div>${r.traits.length ? `<div class="gold">${h(r.traits.join(" · "))}</div>` : ""}</details></div></div>`;
    }).join("");
    return `<div class="nv-title">${h(d.posName)} <span class="muted">· ${d.n} starter${d.n !== 1 ? "s" : ""}</span></div>
      <div class="muted small" style="margin:-4px 2px 8px">Coordinator ${h(d.coord.name)} (${h(d.coord.lean)}) · Position coach ${h(d.posCoach.name)} (${h(d.posCoach.lean)})</div>
      ${msgLine(d.msg)}
      <div class="nv-tabs">${d.camp ? "" : btn("prev", "‹ Prev room", "sm") + btn("n", "Next room ›", "sm")}${btn("l", "Let staff set it", "sm")}${btn("c", "Coordinator's board", "sm")}${btn("p", "Position coach's board", "sm")}</div>
      ${card("", rows)}
      ${d.ideas.length ? card("POSITION MOVE IDEAS", d.ideas.map((x) => `<div class="small">${x.i}. <b>${h(x.name)}</b> ${h(x.old)} → <b class="info">${h(x.new)}</b> · <span class="muted">${h(x.why)}</span></div>`).join("") + `<div class="nv-acts" style="margin-top:6px">${btn("x", "Change a position…", "sm")}</div>`) : ""}
      <div class="nv-acts">${btn("s", "Switch two players")}${btn("Enter", d.camp ? "✓ Done" : "← Back")}</div>`;
  }

  function depth2(d) {
    const rows = d.rows.map((r, k) => `${k === d.starts ? '<div class="nv-cut">BACKUPS</div>' : ""}<div class="nv-drow ${r.starter ? "start" : ""}">
      <div class="nv-dmove"><button data-k="m ${r.i} ${r.i - 1}" ${r.i === 1 ? "disabled" : ""}>▲</button><span>${r.i}</span><button data-k="m ${r.i} ${r.i + 1}" ${r.i === d.rows.length ? "disabled" : ""}>▼</button></div>
      <div class="nv-grow" data-p="${r.id}"><b>#${r.num} ${h(r.name)}</b>${r.hurt ? ` <span class="bad small">✚ ${h(r.hurt)}</span>` : ""}
        <div class="small muted">${h(r.yr)} · ${h(String(r.ovr))}${r.alt ? " · next best " + h(r.alt) : ""}</div>${r.practice ? `<div class="small info">${h(r.practice)}</div>` : ""}</div></div>`).join("")
      || '<div class="muted">Nobody plays here right now.</div>';
    return `<div class="nv-title">Depth chart · ${h(d.posName)}</div>
      <div class="muted small" style="margin:-4px 2px 8px">${h(d.base)} · ${d.starts} starter${d.starts !== 1 ? "s" : ""}</div>${msgLine(d.msg)}
      <div class="nv-tabs">${d.positions.map((p) => `<button class="${p === d.pos ? "on" : ""}" data-k="${p}">${p}</button>`).join("")}</div>
      ${d.ideas.length ? card("STAFF IDEAS", d.ideas.map((x) => `<div class="nv-row" data-k="${x.key}"><span class="nv-grow small">${h(x.text)}</span><span class="info small">Do it ›</span></div>`).join("")) : ""}
      ${card("", rows)}
      <div class="nv-acts">${btn("r", d.hide ? "Use staff recommendation" : "Reset to overall")}${d.hide ? btn("w", "Practice report") : ""}${btn("b", "← Back")}</div>`;
  }

  // ═══ Inbox & press ════════════════════════════════════════════════════════
  function inbox(d) {
    const row = (m) => `<div class="nv-rrow" data-k="${m.i}"><span>${m.unread ? '<b class="gold">●</b>' : '<span class="muted">·</span>'}</span>
      <span class="nv-grow"><b>${h(m.from)}</b> <span class="muted small">${h(m.kind)}</span><span class="nv-pmeta">${h(m.subject)}</span></span>
      <span class="nv-rside"><span class="muted small">${h(m.when)}</span>${m.reply ? '<span class="purple small"><b>REPLY</b></span>' : m.missed ? '<span class="muted small">missed</span>' : m.said ? `<span class="muted small">→ ${h(m.said)}</span>` : ""}</span></div>`;
    return `<div class="nv-title">Inbox <span class="muted">· ${d.unread} unread · ${d.waiting} waiting on you</span></div>
      ${d.waiting ? `<button class="nv-btn primary wide" data-k="a">✉ Answer the next one (${d.waiting})</button>` : ""}
      ${d.todo.length ? card("NEEDS YOUR REPLY", d.todo.map(row).join("")) : ""}
      ${d.rest.length ? card("EARLIER", d.rest.map(row).join("")) : ""}
      ${!d.todo.length && !d.rest.length ? '<div class="muted">Nothing yet.</div>' : ""}
      <div class="nv-acts">${btn("Enter", "← Back")}</div>`;
  }

  function message(d) {
    const opts = d.options.map((o) => `<button class="nv-reply" data-k="${o.key}"><b>${h(o.label)}</b>${o.hint ? `<span>${h(o.hint)}</span>` : ""}</button>`).join("");
    return `<div class="nv-title">${h(d.subject)}</div>
      <div class="nv-say" style="--sc:var(--accent)"><b>${h(d.from)} <span class="muted">· ${h(d.role)}</span></b><span>${h(d.body)}</span></div>
      ${d.last ? '<div class="bad small" style="margin:0 2px 8px">Last chance to answer this one.</div>' : ""}
      ${opts ? `<div class="nv-sub">YOUR REPLY</div>${opts}<div class="nv-acts" style="margin-top:8px">${btn("Enter", "Answer later")}</div>`
        : `<div class="muted" style="margin:6px 2px">${d.missed ? "You never answered. " + h(d.missedText) : d.said ? "You replied: " + h(d.said) : ""}</div><div class="nv-acts">${btn("Enter", "← Back")}</div>`}
      ${d.queue ? `<div class="muted small">${d.queue} more waiting after this one.</div>` : ""}`;
  }

  const TONE = { measured: "muted", confident: "good", fiery: "bad", humble: "info", deflect: "gold", bold: "gold", joke: "purple" };
  function presser(d, adds) {
    let out = `<div class="nv-show"><div class="nv-showname">🎙 ${h(d.title.toUpperCase())}</div><div class="muted small">${h(d.intro)}</div>${d.half ? `<div class="small" style="margin-top:4px">${h(d.half)}</div>` : ""}</div>`;
    const last = adds.length - 1;
    adds.forEach((a, k) => {
      if (a.kind === "q") {
        out += `<div class="nv-say" style="--sc:#f2c14e"><b>${a.data.follow ? "FOLLOW-UP" : "REPORTER"}</b><span>${h(a.data.q.replace(/^Follow-up:\s*/, ""))}</span></div>`;
        if (k === last) out += a.data.options.map((o) => `<button class="nv-reply" data-k="${o.key}"><b><span class="${TONE[o.tone] || "info"}">${h(o.tone.toUpperCase())}</span>${o.default ? ' <span class="muted small">(default)</span>' : ""}</b><span>“${h(o.ans)}”</span>${o.hint ? `<span class="muted">${h(o.hint)}</span>` : ""}</button>`).join("");
      } else if (a.kind === "a") {
        out += `<div class="nv-say me" style="--sc:#58a6ff"><b>YOU · ${h(a.data.tone)}</b><span>“${h(a.data.ans)}”</span></div><div class="info small" style="margin:-4px 2px 10px">→ ${h(a.data.line)}</div>`;
      } else if (a.kind === "sum") {
        out += card("TODAY AT THE PODIUM", `<div class="small">${h(a.data.text.replace(/^Today at the podium:\s*/, ""))}</div>`);
      }
    });
    return out;
  }

  // ═══ After the game ═══════════════════════════════════════════════════════
  function box(d) {
    const t = (x) => `<div class="nv-sbt" style="--tc:${col(x.color)}"><div class="nv-sbn">${h(x.school)}</div><div class="nv-sbs">${x.score}</div></div>`;
    return `${d.banner ? `<div class="center gold small" style="margin-bottom:6px">${h(d.banner)}</div>` : ""}
      <div class="nv-sb">${t(d.away)}<div class="nv-sbc"><b>FINAL</b><span class="muted small">${h(d.at)}</span></div>${t(d.home)}</div>
      ${card("BOX SCORE", `<div class="nv-scroll"><pre class="nv-pre">${renderAnsi(d.lines.join("\n"), { names: true })}</pre></div>`)}`;
  }

  function results(d) {
    const rk2 = (r) => (r ? `<span class="nv-rk">${r}</span>` : "");
    const mine = d.rows.find((r) => r.mine);
    const row = (g) => `<div class="nv-res ${g.mine ? "me" : ""}" ${g.box ? `data-k="${g.n}"` : ""}>
      <div class="${g.awayWon ? "w" : ""}"><span>${rk2(g.ar)}${h(g.away)}</span><b>${g.a}</b></div>
      <div class="${g.awayWon ? "" : "w"}"><span>${rk2(g.hr)}${h(g.home)}</span><b>${g.h}</b></div>${g.tag ? `<div class="muted small">${h(g.tag)}</div>` : ""}</div>`;
    return `<div class="nv-title">${h(d.title)} results</div>
      ${mine ? card("YOUR GAME", row(mine)) : ""}
      ${(d.classics || []).length ? card("★ FOR THE BOOK", d.classics.map((c) => `<div class="gold small">${h(c)}</div>`).join("")) : ""}
      <div class="nv-resgrid">${d.rows.filter((r) => !r.mine).map(row).join("")}</div>
      ${(d.injuries || []).length ? card("INJURIES", d.injuries.map((x) => `<div class="small muted">${h(x)}</div>`).join("")) : ""}
      <div class="muted small" style="margin:0 2px 8px">Tap a game for its box score.</div>
      <button class="nv-btn primary wide" data-k="Enter">Continue ›</button>`;
  }

  function report(d) {
    return `<div class="nv-title">The week's work <span class="muted">· ${h(d.title)}</span></div>
      ${d.routine ? `<div class="muted small" style="margin:-4px 2px 8px">Routine: ${h(d.routine)}</div>` : ""}
      ${card("WHAT EACH DECISION PUT ON THE FIELD", d.rows.map((r) => `<div class="nv-row"><span class="nv-wk">${h(r.day)}</span><span class="nv-grow">${h(r.what)}${r.notes.map((n) => `<div class="muted small">· ${h(n)}</div>`).join("")}</span>
        <b class="${r.lift > 0.005 ? "good" : r.lift < -0.005 ? "bad" : "muted"}">${r.lift >= 0 ? "+" : ""}${r.lift.toFixed(2)}</b><span class="muted small">${r.pts >= 0 ? "+" : ""}${r.pts.toFixed(1)} pts</span></div>`).join(""))}
      ${(d.plan || []).length ? card(`GAME PLAN (${h(d.whose)})`, d.plan.map((p) => `<div class="nv-row"><span class="nv-grow info">${h(p.name)}</span><span class="small">${h(p.verdict)}</span></div>`).join("")) : ""}
      ${card("", `<div><span class="muted">The week in all:</span> <b class="${d.total > 0 ? "good" : d.total < 0 ? "bad" : ""}">${d.total >= 0 ? "+" : ""}${d.total.toFixed(2)} form ≈ ${d.pts >= 0 ? "+" : ""}${d.pts.toFixed(1)} points</b></div><div style="margin-top:4px">${h(d.line)}</div>`)}
      <button class="nv-btn primary wide" data-k="Enter">Continue ›</button>`;
  }

  // ═══ Offseason ════════════════════════════════════════════════════════════
  function offhub(d) {
    const wk = d.weeks.map((w) => `<div class="nv-oweek ${w.now ? "now" : w.done ? "done" : ""}"><span>${w.n}</span><i>${h(w.mon)}</i><b>${h(w.label)}</b>${w.done ? "<em>✓</em>" : ""}</div>`).join("");
    const list = (xs) => xs.map((x) => `<div class="small" style="margin:2px 0">${h(x)}</div>`).join("") || '<span class="muted small">—</span>';
    return `<div class="nv-hero" style="--tc:${col(d.color)}"><div class="nv-hmode">OFFSEASON · ${h(d.season)} · ${h(d.mon)}</div>
        <div class="nv-hname">Week ${d.week}/17 · ${h(d.label)}</div><div class="nv-hsub">${h(d.blurb)}</div>
        <div class="small" style="margin-top:6px;color:#f2c14e"><b>Next deadline:</b> ${h(d.deadline)}</div></div>
      ${msgLine(d.msg)}
      <button class="nv-btn primary wide" data-k="a">▶ This week's agenda</button>
      ${(d.desk || []).length ? card("ON YOUR DESK", d.desk.map((x) => `<div class="gold small" style="margin:3px 0">• ${h(x)}</div>`).join("")) : ""}
      <div class="nv-tabs">${btn("i", "✉ Inbox", "sm")}${btn("r", "☰ Roster", "sm")}${btn("c", "🎓 Recruiting class", "sm")}${btn("t", "⇄ Transfer class", "sm")}${btn("$", "$ Budget", "sm")}${btn("s", "☷ Staff", "sm")}${btn("v", "💾 Save", "sm")}</div>
      ${card("PROGRAM STATUS", list(d.program))}
      ${card("NATIONAL BOARD", list(d.national))}
      ${card("OFFSEASON CALENDAR", `<div class="nv-oweeks">${wk}</div>`)}
      ${card("LAST SEASON", list(d.last))}`;
  }

  function agenda(d) {
    const tone = d.status === "done" ? "good" : d.status === "required" ? "bad" : "info";
    return `<div class="nv-title">Week ${d.week} agenda <span class="muted">· ${h(d.label)}</span></div>
      ${d.task ? card("MUST / SHOULD HANDLE", `<div class="nv-row"><b class="nv-grow">${h(d.task)}</b><span class="small ${tone}"><b>${h(d.status.toUpperCase())}</b></span></div>
        <button class="nv-btn wide" data-k="1">${d.status === "done" ? "Re-enter this task" : "▶ Handle it now"}</button>`) : card("", '<div class="muted">No required action this week.</div>')}
      ${(d.watch || []).length ? card("WATCH BEFORE YOU ADVANCE", d.watch.map((x) => `<div class="small">• ${h(x)}</div>`).join("")) : ""}
      <button class="nv-btn primary wide" data-k="a" ${d.status === "required" ? "" : ""}>⏭ Advance the week</button>
      <div class="nv-acts">${btn("Enter", "← Back to hub")}</div>`;
  }

  // ═══ Auto: any screen that hasn't been converted, laid out app-style ══════
  // Reads the screen's own text: the title bar becomes a header, sections and boxed panels become
  // cards, menu rows become buttons, tables stay aligned in a scrollable block, prose wraps.
  const ESC_RE = /\x1b\[[0-9;?]*[A-Za-z]/g;
  const vis = (s) => s.replace(ESC_RE, "").replace(/\u2063/g, "");
  function sliceVis(s, a, b) {               // columns a..b of the visible text, keeping the colour codes
    let out = "", col = 0, i = 0;
    while (i < s.length) {
      if (s[i] === "\x1b") { const m = /^\x1b\[[0-9;?]*[A-Za-z]/.exec(s.slice(i)); if (m) { out += m[0]; i += m[0].length; continue; } }
      if (col >= a && col < b) out += s[i];
      col++; i++;
    }
    return out;
  }
  const ITEM_RE = /^\s{0,8}([●○◆▶★✓✔►]\s*)?\[ ?([^\]\s]{1,5})\]\s{1,4}(\S.*)$/;
  const KEYS_RE = /\[ ?([^\]\s]{1,5})\]\s*([^\[]*)/g;
  const isMono = (t) => /\S\s{3,}\S/.test(t.trim()) || /[│┃║]/.test(t);
  const ansiLine = (l) => renderAnsi(l.replace(/^\u2063/, ""), { names: true });

  function autoParse(lines) {
    const blocks = [];
    let i = 0;
    while (i < lines.length) {
      const L = lines[i], t = vis(L);
      if (L.charCodeAt(0) === 0x2063) { i++; continue; }                         // command strip → key row
      if (/^[\s─━═┄▀▄_]+$/.test(t) && t.trim()) { blocks.push({ k: "br" }); i++; continue; }
      if (!t.trim()) { blocks.push({ k: "gap" }); i++; continue; }
      if (/^\s*▌\s/.test(t)) {
        blocks.push({ k: "sec", text: t.replace(/^\s*▌\s*/, "").replace(/\s*─+\s*$/, "").trim(), raw: L.replace(/─+(\x1b\[[0-9;]*m)*\s*$/, "") });
        i++; continue;
      }
      if (t.includes("╭")) {                                                   // one or more boxed panels side by side
        const starts = [], ends = [];
        for (let c = 0; c < t.length; c++) { if (t[c] === "╭") starts.push(c); if (t[c] === "╮") ends.push(c); }
        const panels = starts.map((a, n) => ({ a, b: ends[n] !== undefined ? ends[n] : t.length - 1,
          title: t.slice(a, ends[n]).replace(/[╭─╮]/g, " ").trim(), body: [] }));
        let j = i + 1;
        for (; j < lines.length; j++) {
          const tj = vis(lines[j]);
          if (panels.every((p) => tj[p.a] === "╰" || tj[p.a] === undefined)) { j++; break; }
          for (const p of panels) {
            if (tj[p.a] === "│") p.body.push(sliceVis(lines[j], p.a + 2, p.b - 1));
          }
        }
        for (const p of panels) blocks.push({ k: "panel", title: p.title, inner: autoParse(p.body.map((x) => x.replace(/\s+$/, ""))) });
        i = j; continue;
      }
      const keys = [...t.matchAll(KEYS_RE)];
      const m = ITEM_RE.exec(t);
      if (m && keys.length === 1) {                                              // a menu row: [K] Label   what it does
        const parts = m[3].split(/\s{2,}/);
        const it = { k: "item", key: m[2], label: parts[0], desc: parts.slice(1).join(" · "), on: !!m[1] && /[●◆▶★✓✔►]/.test(m[1]) };
        const ind = t.search(/\S/);
        let j = i + 1;
        while (j < lines.length) {
          const tj = vis(lines[j]);
          if (!tj.trim() || tj.search(/\S/) <= ind + 4 || /\[ ?[^\]\s]{1,5}\]/.test(tj) || lines[j].charCodeAt(0) === 0x2063) break;
          it.desc += (it.desc ? " " : "") + tj.trim(); j++;
        }
        blocks.push(it); i = j; continue;
      }
      if (keys.length >= 2 && t.replace(KEYS_RE, "").trim().length < 6) {       // a row of commands
        blocks.push({ k: "keys", keys: keys.map((x) => ({ key: x[1], label: x[2].trim().replace(/\s{2,}.*/, "") })) });
        i++; continue;
      }
      if (isMono(t)) {
        const grp = [L];
        let j = i + 1;
        while (j < lines.length) {
          const tj = vis(lines[j]);
          if (!tj.trim() || lines[j].charCodeAt(0) === 0x2063 || /^\s*▌\s/.test(tj) || tj.includes("╭")) break;
          if (ITEM_RE.test(tj) && [...tj.matchAll(KEYS_RE)].length === 1) break;
          if (!isMono(tj) && tj.search(/\S/) !== t.search(/\S/)) break;
          grp.push(lines[j]); j++;
        }
        const prev = blocks[blocks.length - 1];
        if (prev && prev.k === "text" && prev.lines.length === 1 && prev.ind === t.search(/\S/)) { blocks.pop(); grp.unshift(prev.raw); }
        const ind = Math.min(...grp.map((x) => vis(x).search(/\S/)).filter((x) => x >= 0));
        blocks.push({ k: "mono", lines: grp.map((x) => sliceVis(x, ind, 9999)) });
        i = j; continue;
      }
      const para = [L.replace(/^\s+/, "")];
      let j = i + 1;
      while (j < lines.length) {                                                 // wrapped prose continues on indented lines
        const tj = vis(lines[j]);
        if (!tj.trim() || isMono(tj) || /\[ ?[^\]\s]{1,5}\]/.test(tj) || /^\s*[▌╭•·◆▶⏎]/.test(tj) || lines[j].charCodeAt(0) === 0x2063) break;
        if (tj.search(/\S/) < t.search(/\S/) + 2) break;
        para.push(lines[j].replace(/^\s+/, "")); j++;
      }
      blocks.push({ k: "text", lines: para, ind: t.search(/\S/), raw: L });
      i = j;
    }
    return blocks;
  }

  function autoHTML(blocks) {
    let out = "", open = false;
    const close = () => { if (open) { out += "</section>"; open = false; } };
    for (const b of blocks) {
      if (b.k === "sec") { close(); out += `<section class="nv-card"><div class="nv-ct">${h(b.text)}</div>`; open = true; continue; }
      if (b.k === "panel") { close(); out += card(h(b.title), autoHTML(b.inner)); continue; }
      if (b.k === "br") { close(); continue; }
      if (b.k === "gap") { out += '<div class="nv-gap"></div>'; continue; }
      if (b.k === "item") {
        out += `<button class="nv-item ${b.on ? "on" : ""}" data-k="${h(b.key)}"><span class="nv-ik">${h(b.key)}</span><span class="nv-grow"><b>${ansiLine(b.label)}</b>${b.desc ? `<span>${h(b.desc)}</span>` : ""}</span></button>`;
        continue;
      }
      if (b.k === "keys") { out += `<div class="nv-acts">${b.keys.map((x) => btn(x.key, `<b class="gold">${h(x.key)}</b> ${h(x.label)}`, "sm")).join("")}</div>`; continue; }
      if (b.k === "mono") { out += `<div class="nv-scroll"><pre class="nv-pre">${b.lines.map(ansiLine).join("\n")}</pre></div>`; continue; }
      if (b.k === "text") { out += `<div class="nv-p">${b.lines.map(ansiLine).join(" ")}</div>`; continue; }
    }
    close();
    return out.replace(/(<div class="nv-gap"><\/div>)+/g, '<div class="nv-gap"></div>');
  }

  let autoKey = "";
  function autoRender(raw, idx, live) {
    const key = idx + ":" + raw.length + ":" + live;
    nEl.hidden = false;
    if (key === autoKey) return;
    const fresh = !autoKey.startsWith(idx + ":");
    autoKey = key;
    shown = null; shownAdds = -1;
    const lines = raw.replace(/\r\n/g, "\n").split("\n");
    let title = "", sub = "", start = 0;
    for (let k = 0; k < Math.min(4, lines.length); k++) {
      if (/\x1b\[(4[0-7]|48;)/.test(lines[k]) && vis(lines[k]).trim()) {
        const t = vis(lines[k]).trim().split(/\s{2,}/);
        title = t[0]; sub = t.slice(1).join(" · ").replace(/^◂\s*/, "");
        start = k + 1;
        if (lines[k + 1] && /^[▀\s]+$/.test(vis(lines[k + 1]))) start = k + 2;
        break;
      }
    }
    let html = "";
    try { html = autoHTML(autoParse(lines.slice(start))); } catch (e) { console.warn(e); html = `<pre class="nv-pre">${renderAnsi(raw)}</pre>`; }
    nEl.className = "nvk-auto" + (live ? "" : " dead");
    nEl.innerHTML = (title ? `<div class="nv-title">${h(title)}${sub && !/Console College/i.test(sub) ? ` <span class="muted small">· ${h(sub)}</span>` : ""}</div>` : "") + html;
    if (fresh) wrap.scrollTop = 0;
  }

  function title(d) {
    return `<div class="nv-logo"><div>CONSOLE</div><div>COLLEGE</div><span>RECRUIT · COACH · BUILD A DYNASTY</span></div>
      ${msgLine(d.msg)}
      ${d.cont ? `<button class="nv-cont" data-k="1"><b>▶ Continue</b><span>${h(d.cont.who)}</span><i>${h(d.cont.status)} · saved ${h(d.cont.ago)}</i></button>` : ""}
      ${d.items.map((x) => `<button class="nv-item" data-k="${x.key}" ${x.off ? "disabled" : ""}><span class="nv-ik">${x.key}</span><span class="nv-grow"><b>${h(x.label)}</b><span>${h(x.desc)}</span></span></button>`).join("")}
      <div class="muted small center" style="margin-top:10px">${h(d.version)} · 138 FBS programs · every snap simulated</div>`;
  }

  function plan(d) {
    const tone = (w) => /real edge|should help/.test(w) ? "good" : /uphill/.test(w) ? "gold" : /says no/.test(w) ? "bad" : "muted";
    return `<div class="nv-title">Friday · Game plan <span class="muted">vs ${h(d.opp)}</span></div>
      ${card("WHAT THE FILM SHOWS", d.film.map((x) => `<div class="info small" style="margin:3px 0">· ${h(x)}</div>`).join(""))}
      ${d.sides.map((sd) => card(h(sd.title.toUpperCase()), sd.options.map((o) => `<button class="nv-item ${o.on ? "on" : ""}" data-k="${o.key}">
        <span class="nv-ik">${o.on ? "●" : h(o.key.toUpperCase())}</span><span class="nv-grow"><b>${h(o.label)}${o.staff ? ' <span class="info small">← staff</span>' : ""}</b>
        <span>${h(o.blurb)}</span><span class="${tone(o.worth)}">${h(o.worth)}</span></span></button>`).join(""))).join("")}
      ${card("SCRIPT THE OPENERS", `<div class="nv-row"><span class="nv-grow small">Sharp first ten snaps (+${d.lift}) · costs a practice period (−${d.cost} Saturday)</span>
        <button class="nv-btn sm ${d.script ? "primary" : ""}" data-k="s" style="flex:none">${d.script ? "ON" : "OFF"}</button></div>`)}
      <div class="nv-acts">${btn("r", "Take the staff's plan")}</div>
      <button class="nv-btn primary wide" data-k="Enter">✓ Done</button>`;
  }

  function half(d, adds) {
    const st = (x) => `<div class="nv-row"><b class="nv-grow">${h(x.school)}</b><span class="small">${x.stats.rush_yds} rush · ${x.stats.pass_yds} pass · ${x.stats.first_downs} 1st · ${x.stats.turnovers} TO</span></div>`;
    let out = `<div class="nv-show"><div class="nv-showname">HALFTIME</div><div class="nv-showgame">${h(d.us.school)} ${d.us.score}, ${h(d.them.school)} ${d.them.score}</div></div>
      ${card("FIRST HALF", st(d.us) + st(d.them))}
      ${d.scoring.length ? card("FIRST-HALF SCORING", d.scoring.map((e) => `<div class="nv-row ${e.mine ? "" : "muted"}"><span class="small">Q${e.q} ${h(e.clock)}</span><b>${h(e.team)}</b><span class="nv-grow small">${h(e.what)}</span></div>`).join("")) : ""}
      ${d.plan.length ? card("THE GAME PLAN", d.plan.map((x) => `<div class="nv-row"><span class="nv-grow">${h(x.label)}</span><span class="small">${h(x.verdict)}</span></div>`).join("")) : ""}
      ${d.reads.length ? card("STAFF", d.reads.map((r) => `<div class="info small">${h(r)}</div>`).join("")) : ""}`;
    const last = adds.length - 1;
    adds.forEach((a, k) => {
      if (a.kind === "opts") {
        out += `<div class="nv-sub" style="margin:10px 2px 6px">${h(a.data.title.toUpperCase())}</div>`;
        if (k === last) out += a.data.options.map((o) => `<button class="nv-item" data-k="${o.key}"><span class="nv-ik">${o.key}</span><span class="nv-grow"><b>${h(o.label)}</b><span>${h(o.line)}</span></span></button>`).join("");
        else out += '<div class="muted small" style="margin:0 2px">✓ decided</div>';
      } else if (a.kind === "res") out += `<div class="nv-msg">→ ${h(a.data.text)}</div>`;
    });
    return out;
  }

  function final(d) {
    const t = (x) => `<div class="nv-sbt" style="--tc:${col(x.color)}"><div class="nv-sbn">${h(x.school)}</div><div class="nv-sbs">${x.score}</div></div>`;
    return `<div class="nv-final ${d.won ? "good" : "bad"}">${d.won ? "WIN" : "LOSS"}</div>
      <div class="nv-sb">${t(d.us)}<div class="nv-sbc"><b>FINAL</b></div>${t(d.them)}</div>
      ${d.scoring.length ? card("SCORING", d.scoring.map((e) => `<div class="nv-row ${e.mine ? "" : "muted"}"><span class="small">${h(e.q)} ${h(e.clock)}</span><b>${h(e.team)}</b><span class="nv-grow small">${h(e.what)}</span></div>`).join("")) : ""}
      <div class="nv-grid2">${d.box ? btn("b", "▦ Box score", "big") : ""}${btn("Enter", "Continue ›", "big primary")}</div>`;
  }

  // ═══ Money, team pages, standings ═════════════════════════════════════════
  function budget(d) {
    const secs = [];
    for (const r of d.rows) { let s = secs.find((x) => x.name === r.sec); if (!s) { s = { name: r.sec, rows: [] }; secs.push(s); } s.rows.push(r); }
    const rowH = (r) => `<div class="nv-mrow ${/AVAILABLE/.test(r.label) ? "total" : ""}"><span class="nv-grow"><b>${h(r.label)}</b><span class="muted small nv-pmeta">${h(r.who)}${r.note ? " · " + h(r.note) : ""}</span></span>
      <b class="${r.tone || (r.neg ? "bad" : "")}">${h(r.amount)}</b></div>`;
    return `<div class="nv-hero" style="--tc:${col(d.color)}"><div class="nv-hmode">FOOTBALL BUDGET · ${d.year}</div><div class="nv-hname">${h(d.budget)}</div>
        <div class="nv-hsub">${h(d.school)} · #${d.rank} of ${d.of} nationally</div>
        <div class="small" style="opacity:.85;margin-top:4px">AD ${h(d.ad)}: ${h(d.adBlurb)}</div>
        ${d.trend ? `<div class="small" style="margin-top:4px;color:${d.trendUp ? "#7ee787" : "#ff7b72"}">Last change ${h(d.trend)}</div>` : ""}</div>
      ${card("THIS SEASON", `<div class="nv-meter"><span class="small">Spent <b>${h(d.spent)}</b></span>${bar(Math.min(100, d.pct), 100, d.pct > 100 ? "warn" : "good")}<span class="small">${d.pct}%</span></div>
        <div class="small ${d.over ? "bad" : "good"}" style="margin:2px 0 6px">${d.over ? "OVER BUDGET" : "Unspent"} ${h(d.left)}</div>${(secs[0] || { rows: [] }).rows.map(rowH).join("")}`)}
      ${secs.slice(1).map((s) => card(h(s.name.toUpperCase()), s.rows.map(rowH).join(""))).join("")}
      ${d.top.length ? card("TOP NIL DEALS", d.top.map((p) => `<div class="nv-row" data-p="${p.id}"><span class="nv-pos">${h(p.pos)}</span><span class="nv-grow">${h(p.name)} <span class="muted small">${h(p.yr)} · ${h(p.ovr)}</span></span><b class="good">${h(p.nil)}</b></div>`).join("")) : ""}
      ${d.buyouts.length ? card("BUYOUTS OWED", d.buyouts.map((o) => `<div class="nv-row"><span class="nv-grow">${h(o.name)} <span class="muted small">${h(o.role)}</span></span><b class="bad">${h(o.per)}/yr</b><span class="muted small">${h(o.span)}</span></div>`).join("")) : ""}
      <div class="nv-grid2">${btn("p", "Full payroll", "big")}${btn("l", "Every program's budget", "big")}${btn("f", "Facilities", "big")}${btn("r", "Find money / rebalance", "big")}</div>
      <div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  function team(d) {
    const rbar = (x) => `<div class="nv-race"><span class="nv-grow small">${h(x.label)}</span><span class="nv-bar ${x.v >= 80 ? "good" : x.v >= 60 ? "gold" : "warn"}"><i style="width:${x.v}%"></i></span><b class="small">${x.v}</b></div>`;
    return `<div class="nv-hero" style="--tc:${col(d.color)}"><div class="nv-hmode">${d.rank ? `RANKED #${d.rank} THIS WEEK` : "TEAM PAGE"}</div>
        <div class="nv-hname">${d.rank ? `<span class="nv-hrank">#${d.rank}</span>` : ""}${h(d.full)}</div><div class="nv-hsub"><i>“ ${h(d.chant)} ”</i></div>
        <div class="nv-trio light">${d.summary.map(([l, v]) => `<div><b>${h(v.split(/\s+/)[0])}</b><span>${h(l.toLowerCase())}</span></div>`).slice(0, 3).join("")}</div></div>
      ${d.titles.length ? `<div class="gold center" style="margin:0 0 8px">🏆 National champions: ${h(d.titles.join(", "))}</div>` : ""}
      ${card("", d.info.map(([l, v]) => `<div class="nv-row"><span class="muted nv-lbl">${h(l)}</span><span class="nv-grow small">${ansiLine(v)}</span></div>`).join("") + (d.form ? `<div class="muted small" style="margin-top:4px">Season form: ${h(d.form)}</div>` : ""))}
      <div class="nv-grid2">${btn("r", "☰ Roster", "big")}${btn("s", "📅 Schedule", "big")}${d.mine ? btn("h", "▤ Depth chart", "big") + btn("a", "⚙ Sim strategy", "big") : btn("p", "Player card", "big") + btn("k", "Locker room", "big")}</div>
      ${card("FACILITIES", `<div class="nv-trio">${d.facilities.map((f) => `<div><b>${f.v}/10</b><span>${h(f.k)} · ${h(f.grade)}</span></div>`).join("")}</div>`, ' data-k="f"')}
      ${card("PROGRAM RATINGS", d.ratings.map(rbar).join(""))}
      ${d.coach ? card(`HEAD COACH · ${h(d.coach.name.toUpperCase())}`, d.coach.ratings.map(rbar).join("") + (d.coach.traits.length ? `<div class="gold small" style="margin-top:4px">${h(d.coach.traits.join(" · "))}</div>` : "") + `<div class="muted small">${h(d.coach.style)}</div>`, ' data-k="c"') : ""}
      ${d.history.length ? card("RECENT SEASONS", d.history.map((x) => `<div class="nv-row"><span class="nv-wk">${x.yr}</span><b>${h(x.rec)}</b><span class="nv-grow muted small">${h(x.conf)}</span>${x.ach.length ? `<span class="gold small">🏆 ${h(x.ach.join(", "))}</span>` : ""}</div>`).join(""), ' data-k="y"') : ""}
      ${d.injuries.length ? card("INJURY REPORT", d.injuries.map((p) => `<div class="nv-row" data-p="${p.id}"><span class="nv-pos">${h(p.pos)}</span><span class="nv-grow">${h(p.name)}</span><span class="bad small">${h(p.status)}</span></div>`).join("")) : ""}
      <div class="nv-tabs nv-wrap">${[["c", "Coach & program"], ["o", "OC"], ["d", "DC"], ["$", "Budget"], ["j", "Team builder"], ["y", "Program history"], ["v", "Rivalries"], ["i", "Instant classics"], ["e", "Record book"], ["g", "Hall of Fame"], ...(d.mine ? [["u", "Formation subs"], ["k", "Locker room"], ["p", "Player card"]] : [])].map(([k, l]) => `<button data-k="${k}">${l}</button>`).join("")}</div>
      <div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  function confs(d) {
    return `<div class="nv-title">Conference standings</div>
      ${d.rows.map((c) => `<button class="nv-item" data-k="${c.key}" style="border-left:5px solid ${col(c.color)}"><span class="nv-grow"><b>${h(c.name)}</b><span>${c.count} teams</span></span><span class="muted">›</span></button>`).join("")}
      <div class="nv-grid2">${btn("a", "All conferences", "big")}${btn("b", "← Back", "big")}</div>`;
  }

  function standings(d) {
    return d.confs.map((c) => `<div class="nv-title" style="border-left:5px solid ${col(c.color)};padding-left:8px">${h(c.name)}</div>` + c.divs.map((dv) => card(dv.name ? h(dv.name.toUpperCase()) + " DIVISION" : "",
      `<div class="nv-row muted small"><span class="nv-ix"></span><span class="nv-grow"></span><span class="nv-c">CONF</span><span class="nv-c">ALL</span><span class="nv-c">PRS</span></div>` +
      dv.rows.map((r, i) => `<div class="nv-row ${r.me ? "me" : ""}" data-k="${r.n}"><span class="nv-ix">${i + 1}</span><span class="nv-grow">${rk(r.rank)}${h(r.school)}</span><span class="nv-c">${h(r.conf)}</span><span class="nv-c"><b>${h(r.all)}</b></span><span class="nv-c muted">${r.prs}</span></div>`).join(""))).join("")).join("")
      + `${d.started ? "" : '<div class="muted small" style="margin:0 2px 8px">No games yet — ordered by prestige.</div>'}<div class="muted small" style="margin:0 2px 8px">Tap a team for its page.</div><div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  // ═══ Polls, races, scoreboards, payroll ═══════════════════════════════════
  const mvTag = (m, isNew) => isNew ? '<span class="good small">NEW</span>' : m > 0 ? `<span class="good small">▲${m}</span>` : m < 0 ? `<span class="bad small">▼${-m}</span>` : '<span class="muted small">–</span>';

  function rmenu(d) {
    return `<div class="nv-title">Poll & Golden Helmet race <span class="muted">· ${h(d.label)}</span></div>
      ${d.items.map(([k, l, x]) => `<button class="nv-item" data-k="${k}"><span class="nv-ik">${k}</span><span class="nv-grow"><b>${h(l)}</b><span>${h(x)}</span></span></button>`).join("")}
      <div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  function top25(d) {
    return `<div class="nv-title">${h(d.title)} <span class="muted">· ${h(d.label)}</span></div>
      ${card("", d.rows.map((r) => `<div class="nv-prow ${r.me ? "me" : ""}" data-k="${r.rank}"><span class="nv-trank ${r.rank <= 5 ? "gold" : ""}">${r.rank}</span>
        <span class="nv-grow"><b style="color:${col(r.color)}">${h(r.school)}</b> <span class="muted small">${h(r.record)}</span>
          <span class="muted small nv-pmeta">${h(r.conf)}${r.last ? ` · <span class="${r.won ? "good" : "bad"}">${r.won ? "W" : "L"}</span> ${h(r.last)}` : ""}</span></span>
        <span class="nv-rside">${mvTag(r.move, r.new)}${r.pts !== null && r.pts !== undefined ? `<span class="muted small">${r.pts} pts${r.first ? ` (${r.first})` : ""}</span>` : ""}</span></div>`).join(""))}
      ${d.others.length ? `<div class="muted small" style="margin:0 2px 8px">Also receiving votes: ${h(d.others.join(", "))}</div>` : ""}
      <div class="muted small" style="margin:0 2px 8px">${d.voters} voters · tap a team for its page</div><div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  function heisman(d) {
    return `<div class="nv-title">${h(d.title)} <span class="muted">· ${h(d.label)}</span></div>
      ${card("", d.rows.map((r) => `<div class="nv-prow" data-p="${r.id}"><span class="nv-trank ${r.rank === 1 ? "gold" : ""}">${r.rank}</span>
        <span class="nv-grow"><b>${h(r.name)}</b> <span class="info small">${h(r.pos)}</span> <span class="small" style="color:${col(r.color)}">${r.trank ? "#" + r.trank + " " : ""}${h(r.school)}</span>
          <span class="muted small nv-pmeta">${h(r.blurb)}</span></span>${mvTag(r.move, r.move === null)}</div>`).join(""))}
      <div class="muted small" style="margin:0 2px 8px">Voters weigh production, position, strength of schedule and how much his team wins.</div>
      <button class="nv-btn primary wide" data-k="Enter">Continue ›</button>`;
  }

  function champs(d) {
    return `<div class="nv-title">National champions</div>
      ${d.counts.length ? card("MOST TITLES", `<div class="nv-tabs nv-wrap">${d.counts.slice(0, 16).map(([s, n]) => `<span class="nv-tag big">${h(s)} <b>${n}</b></span>`).join("")}</div>`) : ""}
      ${card("", d.rows.map((c) => `<div class="nv-row ${c.mine ? "me" : ""}"><span class="nv-wk ${c.mine ? "gold" : ""}">${c.year}</span><span class="nv-grow"><b>${h(c.school)}</b> <span class="muted small">${h(c.record)} · ${h(c.coach)}</span><span class="muted small nv-pmeta">${h(c.game)}</span></span></div>`).join("")
        || '<span class="muted">No champion yet in this world.</span>')}
      <button class="nv-btn primary wide" data-k="Enter">Continue ›</button>`;
  }

  function scores(d) {
    const rk2 = (r) => (r ? `<span class="nv-rk">${r}</span>` : "");
    const res = (g) => `<div class="nv-res ${g.mine ? "me" : ""}" ${g.box ? `data-k="${g.n}"` : ""}>${g.bowl ? `<div class="muted small">${h(g.bowl)}</div>` : ""}
      <div class="${g.played && g.awayWon ? "w" : ""}"><span>${rk2(g.ar)}${h(g.away)}</span><b>${g.played ? g.a : ""}</b></div>
      <div class="${g.played && !g.awayWon ? "w" : ""}"><span>${g.neutral ? "" : "@ "}${rk2(g.hr)}${h(g.home)}</span><b>${g.played ? g.h : ""}</b></div></div>`;
    return `<div class="nv-title">${h(d.title)} <span class="muted">· ${h(d.scope)}</span></div>
      <div class="nv-pager">${btn("p", "‹ Prev week")}<span class="muted">Week ${d.week}</span>${btn("n", "Next week ›")}</div>
      ${d.done.length ? `<div class="nv-sub" style="margin:4px 2px 6px">RESULTS · tap for the box score</div><div class="nv-resgrid">${d.done.map(res).join("")}</div>` : ""}
      ${d.todo.length ? `<div class="nv-sub" style="margin:4px 2px 6px">SCHEDULED</div><div class="nv-resgrid">${d.todo.map(res).join("")}</div>` : ""}
      ${!d.done.length && !d.todo.length ? '<div class="muted">No games scheduled.</div>' : ""}
      <div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  function payroll(d) {
    return `<div class="nv-title">${h(d.school)} · NIL payroll <span class="good">${h(d.total)}/yr</span></div>
      ${card("", d.rows.map((p) => `<div class="nv-prow" data-p="${p.id}"><span class="nv-pos">${h(p.pos)}</span>
        <span class="nv-grow"><b>${h(p.name)}</b>${p.tr ? ' <span class="info small">⇄</span>' : ""} <span class="muted small">#${p.num} · ${h(p.yr)} · ${h(p.ovr)}</span>
          ${p.nil ? `<span class="muted small nv-pmeta">${h(p.share)} of payroll · paid through ${h(p.thru)}</span>` : `<span class="muted small nv-pmeta">${p.walkon ? "walk-on" : "no deal"}</span>`}</span>
        <b class="${p.nil ? "good" : "muted"}">${h(p.nil || "—")}</b></div>`).join(""))}
      <div class="nv-pager">${btn("p", "‹ Prev")}<span class="muted">page ${d.page}/${d.pages}</span>${btn("n", "Next ›")}</div>
      <div class="muted small" style="margin:0 2px 8px">NIL deals are fixed once signed. Seniors' deals come off after the season.</div>
      <div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  // ═══ Career, playoff rankings, practice, recruiting news ══════════════════
  function career(d) {
    const r = d.rec || {};
    const meter = (v, max, cls) => `<span class="nv-bar ${cls}"><i style="width:${Math.max(3, Math.min(100, 100 * v / max))}%"></i></span>`;
    return `<div class="nv-hero" style="--tc:${col(d.color)}"><div class="nv-hmode">MY CAREER · ${h(d.difficulty.toUpperCase())}</div>
        <div class="nv-hname">Coach ${h(d.name)}</div><div class="nv-hsub">${h(d.where)}${d.bg ? " · " + h(d.bg) : ""} · age ${d.age}</div>
        <div class="nv-trio light"><div><b>${r.w ?? 0}-${r.l ?? 0}</b><span>career${d.live ? " (incl. now)" : ""}</span></div><div><b>${d.ovr}</b><span>coach ovr</span></div><div><b>${r.titles ?? 0}</b><span>national titles</span></div></div></div>
      ${d.hasTeam ? card("JOB SECURITY", `<div class="nv-meter"><span class="small">Hot seat <b>${d.seat}/100</b></span>${meter(d.seat, 100, d.seat >= 70 ? "warn" : d.seat >= 50 ? "gold" : "good")}<span class="small">${h(d.seatWord)}</span></div>
        <div class="nv-meter" style="margin-top:6px"><span class="small">AD trust <b>${d.trust}/100</b></span>${meter(d.trust, 100, d.trust >= 60 ? "good" : d.trust >= 40 ? "gold" : "warn")}<span class="small">${h(d.trustWord)}</span></div>
        <div class="muted small" style="margin-top:4px">AD ${h(d.ad)}${d.trustLog && d.trustLog.length ? " · lately: " + h(d.trustLog.join("; ")) : ""}</div>
        ${d.contract ? `<div class="small" style="margin-top:6px"><span class="good">${h(d.contract)}</span> <span class="muted">· owed if fired ${h(d.owed)}</span></div>` : ""}`) : ""}
      ${(d.goals || []).length ? card("AD GOALS", d.goals.map((g) => `<div class="nv-row"><span class="nv-grow small">${h(g.text)}</span><span class="small ${g.status === "met" ? "good" : g.status === "failed" ? "bad" : "muted"}">${h(g.note || g.status)}</span></div>`).join("")) : ""}
      ${card("CAREER", `<div class="nv-statg"><div>${[["vs Top 25", `${r.t25w ?? 0}-${r.t25l ?? 0}`], ["NP trips", r.cfp ?? 0], ["Conf titles", r.confs ?? 0], ["Bowls", r.bowls ?? 0]].map(([k, v]) => `<span><i>${k}</i><b>${h(String(v))}</b></span>`).join("")}</div></div>
        <div class="small"><span class="muted">Reputation:</span> ${h(d.rep.join(", ") || "—")}</div>`)}
      <div class="nv-grid2">${btn("t", `🌳 Coaching tree${d.points ? ` (${d.points})` : ""}`, "big")}${btn("d", "📈 Develop your coach", "big")}${btn("p", "👤 Full profile", "big")}${btn("s", "☷ My staff", "big")}</div>
      ${d.hasTeam ? `<button class="nv-item" data-k="k"><span class="nv-ik">K</span><span class="nv-grow"><b>Change my schemes</b><span>${h(d.schemes || "")}</span>${(d.installs || []).map((x) => `<span class="gold">${h(x)}</span>`).join("")}</span></button>` : ""}
      <div class="muted small" style="margin:-4px 2px 8px">${h(d.bank)} in the bank · ${d.points} skill point${d.points !== 1 ? "s" : ""} to spend, ${d.spent} spent</div>
      ${card("YOUR STORY", d.story.map(([y, t]) => `<div class="nv-row"><span class="nv-wk">${y}</span><span class="nv-grow small">${h(t)}</span></div>`).join("") || '<span class="muted small">Nothing written yet.</span>')}
      <div class="nv-tabs nv-wrap">${btn("m", "$ Budget & NIL", "sm")}${btn("f", "Facilities", "sm")}${btn("l", "Difficulty", "sm")}${btn("r", "Retire", "sm risky")}${btn("b", "← Back", "sm")}</div>`;
  }

  function cfp(d) {
    return `<div class="nv-title">${h(d.title)} <span class="muted">· ${h(d.label)}</span></div>
      <div class="muted small" style="margin:-4px 2px 8px">Committee ${d.weight}% · media poll ${100 - d.weight}% · ${d.tag === "SEED" ? "seeded field" : "projected field if the season ended today"} · * automatic bid</div>
      ${card("", d.rows.map((r) => `<div class="nv-prow ${r.me ? "me" : ""}" data-k="${r.rank}"><span class="nv-trank ${r.rank <= 4 ? "gold" : ""}">${r.rank}</span>
        <span class="nv-grow"><b style="color:${col(r.color)}">${h(r.school)}</b> <span class="muted small">${h(r.record)}</span>
          <span class="muted small nv-pmeta">${h(r.conf)} · comm avg ${r.avg}${r.firsts ? ` · ${r.firsts} first-place` : ""} · poll ${r.poll ? "#" + r.poll : "NR"}</span></span>
        <span class="nv-rside">${r.seed ? `<span class="nv-seed">${d.tag === "SEED" ? "SEED" : "PROJ"} ${r.seed}${r.auto ? "*" : ""}</span>` : ""}${mvTag(r.move, r.new)}</span></div>`).join(""))}
      ${d.next.length ? `<div class="muted small" style="margin:0 2px 8px">Next up: ${h(d.next.join(", "))}</div>` : ""}
      <div class="muted small" style="margin:0 2px 8px">Tap a team to see how every committee member ranked it.</div>
      <div class="nv-acts">${btn("m", "The committee")}${btn("e", "Edit these rankings")}${btn("b", "← Back")}</div>`;
  }

  function practice(d) {
    return `<div class="nv-title">Practice report <span class="muted">· ${h(d.when)}</span></div>${msgLine(d.msg)}
      ${card("POSITION BATTLES", d.battles.map((b) => `<div class="nv-row"><span class="nv-pos">${h(b.pos)}</span><span class="nv-grow small">${h(b.text)}</span></div>`).join("") || '<span class="muted small">No real battles this week — the depth chart is settled.</span>')}
      ${card("POSITION ROOMS", `<div class="muted small" style="margin-bottom:6px">See who's coming on. To act on it, open the depth chart.</div><div class="nv-tabs nv-wrap">${d.groups.map((g) => `<button data-k="${g.key}">${h(g.label)}</button>`).join("")}</div>`)}
      <div class="nv-grid2">${btn("d", "▤ Depth chart", "big")}${btn("Enter", "← Back", "big")}</div>`;
  }

  function proom(d) {
    return `<div class="nv-title">${h(d.label)} <span class="muted">· practice</span></div>
      ${card("", d.rows.map((r) => `<div class="nv-tl" data-p="${r.id}"><div class="nv-row"><span class="nv-ix">${r.i}</span><b class="nv-grow">${h(r.name)} <span class="muted small">${h(r.yr)} · ${h(r.ovr)}</span></b>
        <span class="small ${r.form >= 0.8 ? "good" : r.form <= -0.8 ? "bad" : "muted"}">${r.form >= 0.8 ? "good week" : r.form <= -0.8 ? "rough week" : h(r.trend)}</span></div>
        ${r.text ? `<div class="info small">${h(r.text)}</div>` : ""}${r.report ? `<div class="muted small">${h(r.report)}</div>` : ""}</div>`).join(""))}
      <button class="nv-btn primary wide" data-k="Enter">Continue ›</button>`;
  }

  function rnews(d) {
    const tag = { commit: ["COMMIT", "good"], flip: ["FLIP", "bad"], visit: ["VISIT", "info"], rating: ["RATING", "gold"], cb: ["CRYSTAL BALL", "purple"] };
    return `<div class="nv-title">${h(d.title)}</div>
      ${card("", d.rows.map((r) => { const t = tag[r.kind] || ["NEWS", "muted"]; return `<div class="nv-row"><span class="nv-wk">Wk ${r.wk}</span><span class="nv-grow small"><b class="${t[1]}">${t[0]}</b> ${h(r.text.replace(/^CRYSTAL BALL:\s*/i, ""))}</span></div>`; }).join("") || '<span class="muted">Quiet so far.</span>')}
      <button class="nv-btn primary wide" data-k="Enter">Continue ›</button>`;
  }

  // ═══ Awards, the draft, signing day, the staff room ═══════════════════════
  function awards(d) {
    const me = (x) => (x.me ? ' <span class="purple">★</span>' : "");
    const allam = (rows) => rows.map((x) => `<div class="nv-row" data-p="${x.id}"><span class="nv-pos">${h(x.grp)}</span><span class="nv-grow">${h(x.name)}${me(x)}</span><span class="muted small">${h(x.school)}</span></div>`).join("");
    return `<div class="nv-title">${d.year} awards season</div>
      ${d.heisman ? `<div class="nv-hero" style="--tc:${col(d.heisman.color)}" data-p="${d.heisman.id}"><div class="nv-hmode">🏆 THE TROPHY</div><div class="nv-hname">${h(d.heisman.name)}${me(d.heisman)}</div>
        <div class="nv-hsub">${h(d.heisman.pos)} · ${h(d.heisman.school)}</div><div class="small" style="margin-top:4px;opacity:.9">${h(d.heisman.line)}</div></div>` : ""}
      ${d.extra.length ? card("", d.extra.map((x) => `<div class="nv-row"><span class="gold small nv-lbl">${h(x.award)}</span><span class="nv-grow"><b>${h(x.name)}</b>${me(x)} <span class="muted small">${h(x.school)} · ${h(x.line)}</span></span></div>`).join("")) : ""}
      ${card("THE BEST AT EVERY POSITION", d.positional.map((x) => `<div class="nv-tl" data-p="${x.id}"><div class="gold small">${h(x.award)}</div><b>${h(x.name)}</b>${me(x)} <span class="muted small">${h(x.school)}</span><div class="muted small">${h(x.line)}</div></div>`).join(""))}
      ${card("FIRST-TEAM ALL-AMERICA", allam(d.first))}
      ${card("SECOND-TEAM ALL-AMERICA", allam(d.second))}
      <button class="nv-btn primary wide" data-k="Enter">Continue ›</button>`;
  }

  function draft(d) {
    let body = "";
    if (d.picks) body = card(`ROUND ${d.round}`, d.picks.map((x) => `<div class="nv-prow ${x.me ? "me" : ""}"><span class="nv-trank">${x.pick}</span>
      <span class="nv-grow"><b>${h(x.name)}</b> <span class="info small">${h(x.pos)}</span>${x.me ? ' <span class="purple">★</span>' : ""}<span class="muted small nv-pmeta">${h(x.school)} · ${h(x.cls)}${x.early ? " · early" : ""}</span></span>
      <span class="small">${h(x.nfl)}</span></div>`).join("") || '<span class="muted">No picks.</span>');
    else if (d.bySchool) body = card("PICKS BY SCHOOL", d.bySchool.map((x) => `<div class="nv-row ${x.me ? "me" : ""}"><span class="nv-grow">${h(x.school)}</span><b>${x.n}</b><span class="muted small">${x.r1} in round 1</span></div>`).join(""));
    else if (d.mine) body = card(`${h(d.you.toUpperCase())} PICKS`, (d.mine.map((x) => `<div class="nv-row"><span class="nv-wk">R${x.round} #${x.pick}</span><span class="nv-grow"><b>${h(x.name)}</b> <span class="info small">${h(x.pos)}</span></span><span class="small">${h(x.nfl)}</span></div>`).join("") || '<span class="muted">None this year.</span>') + `<div class="muted small" style="margin-top:6px">Draft prestige bonus: +${d.bonus}</div>`);
    return `<div class="nv-title">${d.year} pro draft</div><div class="muted small" style="margin:-4px 2px 8px">${d.n} drafted · ${d.early} underclassmen · ${d.schools} schools</div>
      <div class="nv-tabs">${[1, 2, 3, 4, 5, 6, 7].map((r) => `<button class="${d.round === r ? "on" : ""}" data-k="${r}">Round ${r}</button>`).join("")}<button class="${d.bySchool ? "on" : ""}" data-k="s">By school</button>${d.you ? `<button class="${d.mine ? "on" : ""}" data-k="y">Your picks</button>` : ""}</div>
      ${body}<div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  function signing(d, adds) {
    let out = `<div class="nv-show"><div class="nv-showname">✍ NATIONAL SIGNING DAY</div><div class="nv-showgame">${d.year}</div></div>`;
    let sec = null;
    for (const a of adds) {
      if (a.kind === "pick") {
        const x = a.data;
        const s2 = x.yours ? "YOUR BOARD" : "AROUND THE COUNTRY";
        if (s2 !== sec) { out += `<div class="nv-sub" style="margin:8px 2px 6px">${s2}</div>`; sec = s2; }
        const tone = x.mineWin ? "good" : x.mineLoss ? "bad" : "gold";
        out += `<div class="nv-card nv-sign ${tone}"><div><b>${x.stars}★ ${h(x.pos)} ${h(x.name)}</b> <span class="muted small">${h(x.origin)}</span></div>
          ${x.kind === "signed" ? `<div class="small ${x.mineWin ? "good" : "muted"}">Signs with ${h(x.pick)}, as expected.</div>`
          : `<div class="muted small">On the table: ${h(x.hats.join(" · "))}${x.kind === "flip" && x.fav ? ` · was committed to ${h(x.fav)}` : ""}</div>
             <div class="nv-hat ${tone}">${x.kind === "flip" ? "FLIPS TO " : ""}${h(x.pick.toUpperCase())}!</div>
             ${x.why && x.fav && x.fav !== x.pick ? `<div class="small ${x.favMe ? "bad" : "muted"}">${x.favMe ? "You were" : h(x.fav) + " was"} his first choice — but ${h(x.why)}.</div>` : ""}`}</div>`;
      } else if (a.kind === "sdend") {
        const x = a.data;
        if (x.nflips) out += card(`${x.nflips} SIGNING-DAY FLIP${x.nflips !== 1 ? "S" : ""}`, x.flips.map((f) => `<div class="purple small">${h(f)}</div>`).join(""));
        if (x.lost.length) out += card("WHO YOU COULDN'T TAKE", x.lost.map((f) => `<div class="bad small">${h(f)}</div>`).join(""));
      }
    }
    return out;
  }

  function staff(d) {
    const rows = d.rows.map((r) => !r.name
      ? `<div class="nv-drow"><span class="nv-grow"><span class="muted small">${h(r.role)}</span><div class="bad"><b>— open —</b></div></span><button class="nv-btn sm primary" data-k="h${r.n}" style="flex:none">Hire</button></div>`
      : `<div class="nv-drow"><span class="nv-grow"><span class="muted small">${h(r.role)}${r.calls ? ' · <span class="info">calls plays</span>' : ""}${r.ahc ? ' · <span class="gold">AHC</span>' : ""}</span>
          <div><b>${h(r.name)}</b>${r.unhappy ? ' <span class="bad">!</span>' : ""} <span class="muted small">age ${r.age} · ${h(r.pot)}${r.yrs !== undefined ? ` · ${r.yrs} yr${r.yrs !== 1 ? "s" : ""}` : ""}</span></div>
          <div class="small">OVR <b>${r.ovr}</b> · DEV <b>${r.dev}</b> · REC <b>${r.rec}</b>${r.eye !== undefined ? ` · EVAL <b>${r.eye}</b>` : ""} · <span class="good">${h(r.pay || "—")}</span></div>
          ${r.kind ? `<div class="small"><span class="info">${h(r.kind)}</span> <span class="gold">· ${h(r.spec)}</span></div>` : ""}
          <div class="nv-rowacts"><button data-k="v${r.n}">Profile</button>${r.coord ? `<button data-k="n${r.n}">Negotiate</button>` : `<button data-k="p${r.n}">Promote</button>`}<button data-k="f${r.n}" class="bad">Fire</button></div></span></div>`).join("");
    return `<div class="nv-title">Staff room <span class="muted">· ${h(d.school)} · HC ${h(d.hc)}</span></div>
      ${card("", rows)}
      <div class="small ${d.over ? "gold" : "good"}" style="margin:0 2px 8px">Position coach payroll: ${h(d.payroll)}.</div>
      <div class="muted small" style="margin:0 2px 8px">DEV: how much his players improve · REC: pull with recruits at his positions · EVAL: how well he reads his room · ! unsettled, may walk.</div>
      <div class="nv-grid2">${btn("c", "Play-calling & autopilot", "big")}${btn("Enter", "✓ Done", "big")}</div>`;
  }

  // ═══ Coaching tree, spring ball, A-Day ════════════════════════════════════
  const PERK = { have: ["●", "good"], buy: ["○", "gold"], poor: ["○", "muted"], locked: ["✕", "bad"], gated: ["·", "muted"] };
  function tree(d) {
    return `<div class="nv-hero" style="--tc:#2ea043"><div class="nv-hmode">COACHING TREE · COACH ${h(d.name.toUpperCase())}</div>
        <div class="nv-trio light"><div><b>${d.points}</b><span>to spend</span></div><div><b>${d.spent}</b><span>spent</span></div><div><b>${d.branches.reduce((a, b) => a + b.perks.filter((p) => p.status === "have").length, 0)}</b><span>perks learned</span></div></div></div>
      ${msgLine(d.msg)}${d.free ? '<div class="nv-msg">New job: your next reset is free.</div>' : ""}
      <div class="muted small" style="margin:0 2px 8px">Earn points with results. Each branch opens tier by tier; tier 2 is a fork.${d.born.length ? " Starting trait: " + h(d.born.join(", ")) + "." : ""}</div>
      ${d.branches.map((b) => `<button class="nv-item" data-k="${b.key}"><span class="nv-ik">${b.key}</span><span class="nv-grow"><b>${h(b.label)} <span class="muted small">· ${b.spent} spent</span></b>
        <span class="nv-perks">${b.perks.map((p) => { const [m, t] = PERK[p.status] || ["·", "muted"]; return `<i class="${t}">${p.ranks > 1 ? "●".repeat(p.have) + "○".repeat(p.ranks - p.have) : m} ${h(p.name)}</i>`; }).join("")}</span></span></button>`).join("")}
      ${d.recent.length ? `<div class="muted small" style="margin:0 2px 8px">Lately: ${h(d.recent.slice().reverse().join("; "))}</div>` : ""}
      <div class="muted small" style="margin:0 2px 8px">● have · ○ can buy (gray: not enough points) · ✕ locked by your fork · needs more points in the branch</div>
      <div class="nv-grid2">${btn("r", "Reset the tree", "big risky")}${btn("Enter", "← Back", "big")}</div>`;
  }

  function branch(d) {
    const tag = (r) => r.ranks > 1 ? `rank ${r.have}/${r.ranks} · ${r.status === "have" ? "maxed" : r.cost + " pts"}` :
      ({ have: "learned", buy: `${r.cost} pts`, poor: `${r.cost} pts (need more)`, locked: "locked — you took the other fork", gated: `opens at ${r.gate} spent here` })[r.status];
    return `<div class="nv-title">${h(d.label)} <span class="muted">· ${d.spent} spent here · ${d.points} to spend</span></div>
      ${[1, 2, 3, 4].map((t) => { const rs = d.rows.filter((r) => r.tier === t); return rs.length ? card(`TIER ${t}${t === 2 ? " · FORK" : ""}`, rs.map((r) => `<button class="nv-item ${r.status === "have" ? "on" : ""}" data-k="${r.key}" ${["buy"].includes(r.status) || (r.ranks > 1 && r.status !== "have" && r.status !== "gated" && r.status !== "locked") ? "" : "disabled"}>
        <span class="nv-ik">${(PERK[r.status] || ["·"])[0]}</span><span class="nv-grow"><b>${h(r.name)}${r.fork ? ' <span class="purple small">FORK</span>' : ""}</b><span>${h(r.what)}</span><span class="${(PERK[r.status] || ["", "muted"])[1]}">${h(tag(r))}</span></span></button>`).join("")) : ""; }).join("")}
      <div class="nv-acts">${btn("Enter", "← Back")}</div>`;
  }

  function spring(d) {
    return `<div class="nv-hero" style="--tc:#3b82f6"><div class="nv-hmode">SPRING BALL PLAN · ${d.year}</div><div class="nv-hname">${h(d.school)}</div>
      <div class="nv-hsub">Two practice blocks and A-Day. The emphasis changes development, evaluation and risk.</div></div>
      ${d.options.map((o) => `<button class="nv-item" data-k="${o.key}"><span class="nv-ik">${o.key}</span><span class="nv-grow"><b>${h(o.name)}</b><span>${h(o.desc)}</span></span></button>`).join("")}`;
  }

  function aday(d) {
    return `<div class="nv-show"><div class="nv-showname">A-DAY · SPRING GAME</div><div class="muted small">${h(d.school)} · ${h(d.stadium)}</div></div>
      <div class="nv-sb"><div class="nv-sbt" style="--tc:#2563eb"><div class="nv-sbn">BLUE</div><div class="nv-sbs">${d.blue}</div></div><div class="nv-sbc"><b>FINAL</b></div><div class="nv-sbt r" style="--tc:#9ca3af"><div class="nv-sbn">WHITE</div><div class="nv-sbs">${d.white}</div></div></div>
      <div class="muted small" style="margin:0 2px 8px">First team on Blue, second team on White, alternating down every room.</div>
      ${card("SNAPSHOT", d.snap.map((x) => `<div class="nv-row"><b class="nv-grow">${h(x.label)}</b><span class="small">${x.yds} yds · ${x.first} 1st · ${x.explosive} explosive · ${x.to} TO</span></div>`).join(""))}
      ${card("STANDOUTS", d.standouts.map((p) => `<div class="nv-row" data-p="${p.id}"><span class="nv-pos">${h(p.pos)}</span><span class="nv-grow">${h(p.name)}</span>${p.battle ? '<span class="gold small">★ spring battle</span>' : ""}</div>`).join(""))}
      <div id="nv-tail"></div>
      <div class="nv-grid2">${btn("y", "▦ Full box score", "big")}${btn("n", "Continue ›", "big primary")}</div>`;
  }

  // ═══ Live game: the call, the booth, the choices ══════════════════════════
  function optsHTML(o, live) {
    if (!live) return `<div class="muted small nv-done">✓ ${h(o.title)}</div>`;
    const many = o.options.length > 5 && o.options.every((x) => !x.detail);
    return `<div class="nv-opts"><div class="nv-sub">${h(o.title.toUpperCase())}</div>${o.note ? `<div class="muted small" style="margin:-2px 0 6px">${h(o.note)}</div>` : ""}
      ${many ? `<div class="nv-tabs nv-wrap">${o.options.map((x) => `<button data-k="${h(x.key)}">${h(x.label)}</button>`).join("")}</div>`
        : o.options.map((x) => `<button class="nv-item" data-k="${h(x.key)}"><span class="nv-ik">${h(x.key === "Enter" ? "⏎" : x.key.toUpperCase())}</span><span class="nv-grow"><b>${h(x.label)}</b>${x.detail ? `<span>${h(x.detail)}</span>` : ""}</span></button>`).join("")}</div>`;
  }

  function callHTML(c) {
    const sit = `<div class="nv-callhd"><b>YOUR CALL · ${c.side.toUpperCase()}</b><span>${h(c.down)} & ${h(String(c.togo))} · ${c.side === "offense" ? "at " : ""}${h(c.spot)}</span></div>
      <div class="muted small">${c.timeouts} timeouts${c.side === "offense" ? ` · tempo ${h(c.tempo)}` : ` · they're in ${h(c.personnel)} personnel`} · ${h(c.scheme)}${c.wx ? " · " + h(c.wx) : ""}</div>`;
    if (c.side === "defense") {
      return `<div class="nv-call def">${sit}
        <button class="nv-btn primary wide" data-k="Enter">✓ Staff's call: ${h(c.rec)}</button>
        <div class="nv-calls">${(c.calls || []).map((x) => `<button data-k="${x.key}" class="${x.name === c.rec ? "rec" : ""}"><b>${x.star ? "★ " : ""}${h(x.name)}</b><span>${h(x.desc)}</span></button>`).join("")}</div>
        <div class="nv-tabs nv-wrap">${[["t", "Timeout"], ["s", "Sim ahead"], ["b", "Substitutions"], ["g", "Orders"], ["c", "Get the crowd up"], ["o", "Let the DC call the rest"]].map(([k, l]) => `<button data-k="${k}">${l}</button>`).join("")}</div></div>`;
    }
    const x = c.extra || {};
    return `<div class="nv-call">${sit}
      <div class="nv-grid2" style="margin:8px 0">${btn("r", "🏃 Run", "big")}${btn("p", "🎯 Pass", "big")}</div>
      <button class="nv-btn primary wide" data-k="Enter" style="margin-top:0">✓ Staff's call: ${h(c.rec)}</button>
      ${c.fourth ? `<div class="nv-sub" style="margin:6px 0">FOURTH DOWN${x.chart ? ` · <span class="info">the chart says: ${h(x.chart)}</span>` : ""}</div>
        <div class="nv-grid2">${btn("u", "Punt", "big")}${btn("f", `Field goal (${c.fg} yds)`, "big")}</div>
        ${(x.fakes || []).length ? `<div class="nv-tabs nv-wrap">${x.fakes.map((f) => `<button data-k="${f.key}">${h(f.label)} · ${h(f.odds)}</button>`).join("")}</div>` : ""}` : ""}
      <div class="nv-tabs nv-wrap">${[["k", "Kneel"], ["t", "Timeout"], ["h", "Hurry-up"], ["n", "Normal tempo"], ["m", "Milk the clock"], ["s", "Sim ahead"], ["b", "Substitutions"], ["g", "Orders"]].map(([k, l]) => `<button data-k="${k}" class="${(k === "h" && c.tempo === "hurry-up") || (k === "n" && c.tempo === "normal") || (k === "m" && c.tempo === "milk the clock") ? "on" : ""}">${l}</button>`).join("")}</div></div>`;
  }

  function stream(adds) {
    let lastI = -1;
    adds.forEach((a, i) => { if (a.kind === "opts" || a.kind === "call") lastI = i; else if (a.kind === "booth" && lastI >= 0 && i > lastI) lastI = -2; });
    let out = "", booth = [];
    const flush = () => { if (booth.length) { out += `<div class="nv-booth">${booth.join("")}</div>`; booth = []; } };
    adds.forEach((a, i) => {
      const x = a.data;
      if (a.kind === "booth") { booth.push(`<div class="nv-bline2 ${x.pbp ? "pbp" : "an"}"><b>${h(x.who)}</b> ${h(x.text)}</div>`); return; }
      if (a.kind === "note") { booth.push(`<div class="nv-bline2 note">${h(x.text)}</div>`); return; }
      flush();
      if (a.kind === "qbreak") out += `<div class="nv-qbreak"><b>${h(x.label)}</b><span>${h(x.score)}</span></div>`;
      else if (a.kind === "opts") out += optsHTML(x, i === lastI);
      else if (a.kind === "call") out += i === lastI ? callHTML(x) : `<div class="muted small nv-done">✓ called</div>`;
    });
    flush();
    return out;
  }

  function plays(d, adds) {
    return `<div class="nv-title">${d.kind === "run" ? "Run plays" : "Pass plays"} <span class="muted">· ${h(d.down)} & ${d.togo} at ${h(d.spot)}</span></div>
      <div class="muted small" style="margin:-4px 2px 8px">${h(d.us)} ${d.su} · ${h(d.them)} ${d.so} · ★ in your scheme's playbook</div>
      ${adds.length ? stream(adds) : `<div class="nv-calls">${d.plays.map((p) => `<button data-k="${p.key}"><b>${p.star ? "★ " : ""}${h(p.name)}</b><span>${h(p.desc)}</span></button>`).join("")}</div>
      <div class="nv-acts">${btn("Enter", "← Back to the call")}</div>`}`;
  }

  function schemes(d) {
    return `<div class="nv-title">Change your schemes</div>
      ${card("RIGHT NOW", `<div class="nv-row"><span class="muted nv-lbl">Offense</span><b class="nv-grow">${h(d.off)}</b><span class="muted small">calls: ${h(d.offBy)}</span></div>
        <div class="nv-row"><span class="muted nv-lbl">Defense</span><b class="nv-grow">${h(d.def)}</b><span class="muted small">calls: ${h(d.defBy)}</span></div>
        ${d.installs.map((x) => `<div class="gold small" style="margin-top:4px">${h(x)}</div>`).join("")}`)}
      ${card("WHAT A SWITCH COSTS", `<div class="small">An ${h(d.when)} install takes <b>${d.games} games</b>. It starts at about <b class="bad">−${d.start.toFixed(1)} form</b> (≈ ${(d.start * 1.7).toFixed(1)} points a game) and fades every game.</div>
        <div class="muted small" style="margin-top:4px">Only the side you call plays for pays the full price — a coordinator's side costs a quarter. One switch per side per season.</div>`)}
      <button class="nv-item" data-k="o" ${d.offDone ? "disabled" : ""}><span class="nv-ik">O</span><span class="nv-grow"><b>Change my offense</b><span>${d.offDone ? "already switched this season" : "now: " + h(d.off)}</span></span></button>
      <button class="nv-item" data-k="d" ${d.defDone ? "disabled" : ""}><span class="nv-ik">D</span><span class="nv-grow"><b>Change my defense</b><span>${d.defDone ? "already switched this season" : "now: " + h(d.def)}</span></span></button>
      <div class="nv-acts">${btn("b", "← Back")}</div>`;
  }

  function schemepick(d, adds) {
    return `<div class="nv-title">New ${d.side === "off" ? "offense" : "defense"}</div>
      ${d.options.map((o) => `<button class="nv-item ${o.current ? "on" : ""}" data-k="${o.key}" ${o.current ? "disabled" : ""}><span class="nv-ik">${o.key}</span><span class="nv-grow"><b>${h(o.name)}</b>${o.current ? "<span>current</span>" : ""}</span></button>`).join("")}
      <div id="nv-tail"></div>
      <div class="nv-grid2">${btn("y", "✓ Yes, switch", "big primary")}${btn("Enter", "Cancel", "big")}</div>`;
  }

  const R = { home, roster, schedule, week, matchup, game, show, rhub, rlist, rboard, rcard, rclass, portal, pcard, pkeep,
    player, depth, depth2, inbox, message, presser, box, results, report, offhub, agenda, title, plan, half, final,
    budget, team, confs, standings, rmenu, top25, heisman, champs, scores, payroll,
    career, cfp, practice, proom, rnews, awards, draft, signing, staff,
    tree, branch, spring, aday, plays, schemes, schemepick };
  let shown = null, shownAdds = -1;

  window.NATIVE = {
    has(kind) { return !!R[kind]; },
    render(nv, live) {
      nEl.hidden = false;
      nEl.classList.toggle("dead", !live);
      const fresh = shown !== nv;
      autoKey = "";
      if (!fresh && shownAdds === nv.adds.length) return false;
      const near = wrap.scrollHeight - wrap.scrollTop - wrap.clientHeight < 80;
      try { nEl.innerHTML = R[nv.kind](nv.data, nv.adds); }
      catch (e) { console.warn(e); nEl.innerHTML = ""; }
      nEl.className = "nvk-" + nv.kind + (live ? "" : " dead");
      shown = nv; shownAdds = nv.adds.length;
      if (fresh && !["show", "presser", "half", "signing"].includes(nv.kind)) wrap.scrollTop = 0;
      else if (["matchup", "plays"].includes(nv.kind) && !fresh) {
        const o = nEl.querySelector(".nv-opts, .nv-call");
        if (o) requestAnimationFrame(() => o.scrollIntoView({ block: "nearest" }));
      }
      else if (near || fresh) requestAnimationFrame(() => (wrap.scrollTop = wrap.scrollHeight));
      return fresh;
    },
    hide() { if (!nEl.hidden) { nEl.hidden = true; nEl.innerHTML = ""; shown = null; shownAdds = -1; autoKey = ""; } },
    auto(raw, idx, live) { autoRender(raw, idx, live); },
  };

  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-rpos]");
    if (!b || !shown || shown.kind !== "roster") return;
    rosterPos = b.dataset.rpos;
    shownAdds = -1; shown = null; S.dirty = true;
  });
})();
