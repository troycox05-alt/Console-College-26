"""
tabletview.py — The game on a tablet: scoreboard on top, the field in the middle, the play-by-play and
the info down the side, the team stats along the bottom.

WIDE (124 columns)                                        COMPACT (100 columns)
  ┌─ scoreboard ──────────────────────────────┐             ┌─ scoreboard ─────────────┐
  │ the field, centered      │ PLAY BY PLAY   │             │ the field, centered      │
  │ line score · this drive  │ (newest first) │             │ PLAY BY PLAY │ THIS DRIVE│
  │ coach's clipboard / top  │ scoring        │             │ clipboard / top players  │
  ├─ team stats ──────────────────────────────┤             ├─ team stats ─────────────┤
  └────────────────────────────────────────────┘             └──────────────────────────┘

Drawn before every snap of a game you watch or coach (the broadcast's ticker and the coach's call header
both use it; once per snap). In a coached game, the side panels carry what the sideline tablet always did
(momentum, orders, what's working, hot and cold, the staff's whisper). It changes nothing about the game.

Settings [F]: Tablet (auto size) · Tablet, wide · Tablet, compact · Field only · Slim field · Off.
Auto picks WIDE when the terminal reports 124 columns or more, COMPACT otherwise.
"""
import re
import shutil
import textwrap

import fieldview as fv
from ui import BAR_BG, C, MUTED, bg, on, paint

RESET = "\033[0m"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
WIDE_W, COMPACT_W = 124, 100
PANEL = C.GRAY                      # panel borders
TITLE = C.BYELLOW


# ═══ Little text tools that know about colors ═══════════════════════════════

def vlen(s):
    return len(ANSI.sub("", s))


def rpad(s, w):
    return s + " " * max(0, w - vlen(s))


def center(s, w):
    v = vlen(s)
    left = max(0, (w - v) // 2)
    return " " * left + s + " " * max(0, w - v - left)


def clip(text, w):
    return text if len(text) <= w else text[:max(0, w - 1)] + "…"


def wrap_ansi(s, w, max_lines=None):
    """Word-wrap a colored string; the color in force at a break carries onto the next line."""
    toks = re.findall(r"\x1b\[[0-9;]*m|[^\x1b\s]+|\s+", s)
    lines, cur, cur_len, active = [], "", 0, ""
    pending_space = False
    for t in toks:
        if t.startswith("\x1b"):
            cur += t
            active = "" if t == RESET else active + t
        elif t.isspace():
            pending_space = t if cur_len > 0 else False
        else:
            need = len(t) + (len(pending_space) if pending_space else 0)
            if cur_len and cur_len + need > w:
                lines.append(cur + RESET)
                cur, cur_len = active, 0
                pending_space = False
            if pending_space:
                cur += pending_space
                cur_len += len(pending_space)
                pending_space = False
            while len(t) > w:                                    # a word longer than the column
                cur += t[:w - cur_len]
                lines.append(cur + RESET)
                t = t[w - cur_len:]
                cur, cur_len = active, 0
            cur += t
            cur_len += len(t)
    if cur_len or not lines:
        lines.append(cur + (RESET if active else ""))
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = ANSI.sub("", lines[-1])
        lines[-1] = paint(clip(last, w - 1).rstrip(".,;: ") + "…", C.GRAY)
    return lines


def panel(title, rows, w, height=None, color=None):
    """A box, exactly w columns wide. rows: colored strings, each already <= w-4 visible columns."""
    color = color or PANEL
    t = f" {title} "
    top = paint("┌─", color) + paint(t, TITLE, C.BOLD) + paint("─" * max(0, w - 3 - len(t)) + "┐", color)
    out = [top]
    for r in rows:
        out.append(paint("│ ", color) + rpad(r, w - 4) + paint(" │", color))
    while height and len(out) < height - 1:
        out.append(paint("│", color) + " " * (w - 2) + paint("│", color))
    out.append(paint("└" + "─" * (w - 2) + "┘", color))
    return out


def hstack(cols, gaps):
    """Lay out columns (lists of equal-width strings) side by side."""
    h = max(len(c) for c in cols)
    widths = [vlen(c[0]) if c else 0 for c in cols]
    out = []
    for i in range(h):
        parts = []
        for c, w in zip(cols, widths):
            parts.append(rpad(c[i], w) if i < len(c) else " " * w)
        out.append((" " * gaps).join(parts))
    return out


# ═══ Layout ═════════════════════════════════════════════════════════════════

def layout():
    """'wide' or 'compact', from the setting (and, in auto, the terminal)."""
    m = fv.mode()
    if m == "wide":
        return "wide"
    if m == "compact":
        return "compact"
    import ui
    cols = ui.display_cols()                       # the window says 100; a terminal says how wide it is
    return "wide" if cols >= WIDE_W else "compact"


def _conf_color(team):
    try:
        import league
        return league.League.conference_color(team.conference)
    except Exception:
        return C.BWHITE


def _clock(sec):
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def _qtxt(sim):
    return f"Q{sim.quarter}" if sim.quarter <= 4 else f"OT{sim.quarter - 4}"


def _dd(down, togo, yl):
    d = ("", "1st", "2nd", "3rd", "4th")[max(1, min(4, down))]
    return f"{d} & Goal" if togo >= 100 - yl else f"{d} & {togo}"


# ═══ Pieces ═════════════════════════════════════════════════════════════════

BIG = {"0": ("█▀█", "█ █", "▀▀▀"), "1": ("▄█ ", " █ ", "▄█▄"), "2": ("▀▀█", "█▀▀", "▀▀▀"),
       "3": ("▀▀█", " ▀█", "▀▀▀"), "4": ("█ █", "▀▀█", "  ▀"), "5": ("█▀▀", "▀▀█", "▀▀▀"),
       "6": ("█▀▀", "█▀█", "▀▀▀"), "7": ("▀▀█", "  █", "  ▀"), "8": ("█▀█", "█▀█", "▀▀▀"),
       "9": ("█▀█", "▀▀█", "▀▀▀")}


def big(n):
    """A score, three lines tall."""
    digits = [BIG[ch] for ch in str(max(0, int(n)))]
    return [" ".join(d[r] for d in digits) for r in range(3)]


def _bar(text, bgc=BAR_BG):
    """A full-width bar: the background survives every color reset inside it."""
    return bgc + text.replace(RESET, RESET + bgc) + RESET


def scoreboard(sim, W):
    """The score in big digits, the clock, and the situation, on a charcoal bar."""
    away, home = sim.away, sim.home
    off = getattr(sim, "offense", None)
    ca, ch = _conf_color(away), _conf_color(home)

    def name(team, left):
        col = _conf_color(team)
        badge = bg(col) + on(col) + C.BOLD + f" {team.abbr[:5]:^5} " + RESET
        nm = paint(team.school.upper(), C.BWHITE, C.BOLD)
        dot = paint("●", C.BWHITE, C.BOLD) if team is off else " "
        return f"{badge} {nm} {dot}" if left else f"{dot} {nm} {badge}"

    ga, gh = big(sim.score[away]), big(sim.score[home])
    q = _qtxt(sim)
    c0 = paint(f"{q}   {_clock(sim.clock)}" if sim.quarter <= 4 else f"{q}  OVERTIME", C.BYELLOW, C.BOLD)
    if off is not None:
        c1 = paint(_dd(sim.down, sim.togo, sim.yardline), C.BWHITE, C.BOLD)
        c2 = paint(f"ball on {fv._spot_word(sim, sim.yardline, off)}", C.BYELLOW)
    else:
        c1 = c2 = ""
    to = lambda t: paint("●" * sim.timeouts[t] + "○" * (3 - sim.timeouts[t]), C.BWHITE)
    wx = ""
    try:
        import weather
        c = weather.now(sim)
        if c is not None:
            pw = weather.precip_words(c)
            wx = paint(f"   {c['temp']}°" + (f" {pw}" if pw else "") + (f" · wind {c['wind']}" if c["wind"] >= 8 else " · calm"), C.BCYAN)
        else:
            wx = paint("   indoors", C.GRAY)
    except Exception:
        pass
    c3 = paint(f"{away.abbr[:4]} ", C.GRAY) + to(away) + paint(f"  ·  {home.abbr[:4]} ", C.GRAY) + to(home) + wx
    cen = [c0, c1, c2, c3]
    l0, r0 = name(away, True), name(home, False)
    rows = []
    for r in range(4):
        if r == 0:
            l, rr = l0, r0
        else:
            l = "  " + paint(ga[r - 1], C.BWHITE, C.BOLD)
            rr = paint(gh[r - 1], C.BWHITE, C.BOLD) + "  "
        room = W - 2 - vlen(l) - vlen(rr)
        if r == 0:
            line = " " + l + center(cen[r], room) + rr + " "
        else:                                       # big digits hug the edges: a fixed-width block on each side
            lw = 14
            line = " " + rpad(l, lw) + center(cen[r], W - 2 - lw * 2) + " " * (lw - vlen(rr)) + rr + " "
        rows.append(_bar(line))
    return rows


def linescore(sim, w):
    """By quarter: how the points came."""
    cum = {sim.home: [0] * 5, sim.away: [0] * 5}
    tl = getattr(sim, "timeline", [])
    for q in range(1, 5):
        last = None
        for e in tl:
            if e[0] <= q:
                last = e
        if last is not None:
            cum[sim.home][q], cum[sim.away][q] = last[2], last[3]
        elif q > 1:
            cum[sim.home][q], cum[sim.away][q] = cum[sim.home][q - 1], cum[sim.away][q - 1]
    rows = []
    hdr = paint(f"{'':<9}", C.GRAY) + "".join(paint(f"{h:>3}", C.GRAY) for h in ("1", "2", "3", "4")) \
        + (paint("  OT", C.GRAY) if sim.quarter > 4 else "") + paint("  TOT", C.GRAY)
    rows.append(hdr)
    for t in (sim.away, sim.home):
        by = []
        for q in range(1, 5):
            if q > sim.quarter:
                by.append("  ·")
                continue
            end = sim.score[t] if q == min(sim.quarter, 4) and sim.quarter <= 4 else cum[t][q]
            by.append(f"{end - cum[t][q - 1]:>3}")
        ot = f"{sim.score[t] - cum[t][4]:>4}" if sim.quarter > 4 else ""
        lead = sim.score[t] > sim.score[sim.other(t)]
        rows.append(paint(f"{t.abbr[:5]:<5}", C.BWHITE, C.BOLD) + "    " + "".join(by) + ot
                    + paint(f"{sim.score[t]:>5}", C.BWHITE if lead else C.GRAY, C.BOLD))
    return panel("SCORE BY QUARTER", rows, w)


def drive_panel(sim, w):
    d = sim.drive or {}
    off = sim.offense
    rows = []
    if not d or not d.get("plays"):
        rows.append(paint(f"{off.school} takes over at {fv._spot_word(sim, d.get('start', sim.yardline), off)}", C.BWHITE))
        rows.append(paint("first snap coming up", C.GRAY))
    else:
        yds = sim.yardline - d["start"]
        t = sim.team_stats[d["team"]]["top"] - d.get("top0", 0)
        rows.append(paint(off.school, C.BWHITE, C.BOLD) + paint(f"  {d['plays']} play{'s' if d['plays'] != 1 else ''}", C.GRAY))
        rows.append(paint(f"{yds:+d} yards", C.BGREEN if yds > 0 else C.BRED) + paint(f"  ·  {_clock(max(0, t))} off the clock", C.GRAY))
        rows.append(paint(f"started at {fv._spot_word(sim, d['start'], off)}", C.GRAY))
    need = sim.togo if sim.togo < 100 - sim.yardline else 100 - sim.yardline
    rows.append(paint(f"{_dd(sim.down, sim.togo, sim.yardline)}", C.BYELLOW, C.BOLD)
                + paint(f"  ·  {need} to move the chains" if sim.togo < 100 - sim.yardline else "  ·  score or bust", C.GRAY))
    return panel("THIS DRIVE", rows, w)


def pbp_panel(sim, narr, w, height):
    """The booth's calls, newest first, as many as fit."""
    log = list(getattr(narr, "play_log", []) or []) if narr is not None else []
    inner = w - 4
    budget = max(3, height - 2)
    rows = []
    for e in reversed(log):
        head = paint(f"{'Q' + str(e['q']) if e['q'] <= 4 else 'OT'} {_clock(e['clock'])}", C.GRAY)
        if e["down"] is not None:
            head += paint(f"  {_dd(e['down'], e['togo'], e['yl'])}", C.BYELLOW) + paint(f"  {e['off']}", C.GRAY)
        body = wrap_ansi(paint(e["text"], C.BWHITE if not rows else C.WHITE), inner - 1, 3)
        need = 1 + len(body) + (1 if rows else 0)
        if len(rows) + need > budget:
            break
        if rows:
            rows.append("")
        rows.append(head)
        rows += [" " + b for b in body]
    if not rows:
        rows = [paint("Kickoff. The first snap is coming.", C.GRAY)]
    return panel("PLAY BY PLAY", rows, w, height)


def scoring_panel(sim, w, n=4):
    rows = []
    inner = w - 4
    for e in list(reversed(sim.scoring))[:n]:
        q, clk, team, what = e[0], e[1], e[2], e[3]
        head = paint(f"{'Q' + str(q) if q <= 4 else 'OT'} {_clock(clk)} ", C.GRAY) + paint(team.abbr[:5], C.BWHITE, C.BOLD)
        rows.append(head)
        rows.append(" " + paint(clip(str(what), inner - 1), C.BGREEN))
    if not rows:
        rows = [paint("No scoring yet.", C.GRAY)]
    return panel("SCORING", rows, w)


def performers_panel(sim, w):
    """The best day so far for each team: passer, runner, receiver."""
    rows = []
    inner = w - 4
    for t in (sim.away, sim.home):
        plist = [(p, c) for p, c in sim.stats.items() if sim.team_of(p) is t]
        bits = []
        qb = max((x for x in plist if x[1]["pass_att"]), key=lambda x: x[1]["pass_yds"], default=None)
        if qb:
            p, c = qb
            bits.append(f"{p.last_name} {c['pass_cmp']}/{c['pass_att']}, {c['pass_yds']} yds" + (f", {c['pass_td']} TD" if c["pass_td"] else ""))
        rb = max((x for x in plist if x[1]["rush_att"] and x[0].position != "QB"), key=lambda x: x[1]["rush_yds"], default=None)
        if rb:
            p, c = rb
            bits.append(f"{p.last_name} {c['rush_att']} car, {c['rush_yds']} yds")
        wr = max((x for x in plist if x[1]["rec_yds"]), key=lambda x: x[1]["rec_yds"], default=None)
        if wr:
            p, c = wr
            bits.append(f"{p.last_name} {c['rec']} rec, {c['rec_yds']} yds" if "rec" in c else f"{p.last_name} {c['rec_yds']} rec yds")
        rows.append(paint(t.abbr[:5], C.BWHITE, C.BOLD))
        for b in bits or ["nothing yet"]:
            rows.append(" " + paint(clip(b, inner - 1), C.GRAY if b == "nothing yet" else C.WHITE))
    return panel("TOP PERFORMERS", rows, w)


def clipboard_panel(sim, ctl, side, w):
    """What the sideline tablet always showed, wrapped into a panel (a coached game only)."""
    import sideline
    raw = sideline.tablet_rows(sim, ctl, side)
    rows = []
    for ln in raw:
        ln = ln[3:] if ln.startswith("   ") else ln
        if not ANSI.sub("", ln).strip():
            continue
        rows += wrap_ansi(ln, w - 4, 3)
    if not rows:
        return []
    title = "COACH'S CLIPBOARD  ·  " + ("OFFENSE" if side == "off" else "DEFENSE")
    return panel(title, rows[:9], w)


def stats_footer(sim, W):
    """The team stats, side by side, along the bottom."""
    extra = 4 if W >= WIDE_W else 2
    cols = [(n, w + extra) for n, w in (("YARDS", 7), ("RUSH", 6), ("PASS", 6), ("EXP", 7), ("3RD DN", 7),
                                       ("TURNOVERS", 10), ("PENALTIES", 10), ("POSSESSION", 11))]

    def vals(t):
        s = sim.team_stats[t]
        return [s["total_yds"], s["rush_yds"], s["pass_yds"], s["explosive_plays"],
                (f"{s['third_conv']}/{s['third_att']}", s["third_conv"] / s["third_att"] if s["third_att"] else 0),
                s["turnovers"], (f"{s['penalties']}-{s['pen_yds']}", s["penalties"]), _clock(s["top"])]

    A, H = vals(sim.away), vals(sim.home)
    # which cell leads: True for the better side (turnovers and penalties: lower is better)
    def lead(i, a, b):
        ka = a[1] if isinstance(a, tuple) else (int(a.split(":")[0]) * 60 + int(a.split(":")[1]) if isinstance(a, str) else a)
        kb = b[1] if isinstance(b, tuple) else (int(b.split(":")[0]) * 60 + int(b.split(":")[1]) if isinstance(b, str) else b)
        if ka == kb:
            return 0
        better_low = i in (5, 6)
        return 1 if (ka < kb) == better_low else -1

    label_w = 18
    head = " " * label_w + "".join(paint(f"{n:>{w}}", C.GRAY) for n, w in cols)
    lines = [paint("─" * W, C.GRAY), center(paint("TEAM STATS", C.BYELLOW, C.BOLD), W), center(head, W)]
    for t, V, sgn in ((sim.away, A, 1), (sim.home, H, -1)):
        cells = ""
        for i, ((n, w), v) in enumerate(zip(cols, V)):
            txt = v[0] if isinstance(v, tuple) else str(v)
            ld = lead(i, A[i], H[i]) * sgn
            cells += paint(f"{txt:>{w}}", C.BWHITE if ld > 0 else C.GRAY, C.BOLD if ld > 0 else "")
        lines.append(center(paint(f"{t.abbr[:5]:<5}", C.BWHITE, C.BOLD) + paint(f" {clip(t.school, 12):<12}", C.GRAY) + cells, W))
    return lines


# ═══ The whole thing ════════════════════════════════════════════════════════

def render_lines(sim, ctl=None, side=None, narr=None, kind=None):
    """The tablet as printable lines (no ball in play: [])."""
    if getattr(sim, "offense", None) is None:
        return []
    kind = kind or layout()
    narr = narr if narr is not None else getattr(sim, "narr", None)
    out = []
    if kind == "wide":
        W, LW, RW, GAP = WIDE_W, 82, 40, 2
        geo = fv.Geo(70, 5)
        out += scoreboard(sim, W)
        fld = [rpad(" " + ln, LW) for ln in fv.lines(sim, indent=0, geo=geo, spot=False)]
        spot = fv.spot_line(sim, 0, LW)
        fld.append(spot)
        left = fld + [""] + hstack([linescore(sim, 40), drive_panel(sim, 40)], GAP)
        if ctl is not None:
            left += clipboard_panel(sim, ctl, side, LW)
        else:
            left += hstack([performers_panel(sim, 40), scoring_panel(sim, 40)], GAP)
        right = pbp_panel(sim, narr, RW, max(len(left), 27))
        body = hstack([left, right], GAP)
        out += [""] + body
        out += stats_footer(sim, W)
    else:
        W = COMPACT_W
        geo = fv.Geo(80, 6)
        out += scoreboard(sim, W)
        out.append("")
        out += [rpad(" " * 4 + ln, W) for ln in fv.lines(sim, indent=0, geo=geo, spot=False)]
        out.append(fv.spot_line(sim, 0, W))
        out.append("")
        colw = 49
        a = pbp_panel(sim, narr, colw, 12)
        b = drive_panel(sim, colw)
        b += linescore(sim, colw)
        if ctl is None:
            b += scoring_panel(sim, colw, 2)
        out += hstack([a, b], 2)
        if ctl is not None:
            cb = clipboard_panel(sim, ctl, side, W)
            if cb:
                out += cb
        out += stats_footer(sim, W)
    return out


def _key(sim):
    return (getattr(sim, "plays_run", None), sim.yardline, sim.down, sim.togo, id(sim.offense), sim.quarter)


def show(sim, ctl=None, side=None, narr=None, force=False):
    """Print the tablet for this snap (once per snap, whoever asks first). Returns True if it drew."""
    if fv.mode() not in fv.TABLET_MODES and not force:
        return False
    if getattr(sim, "offense", None) is None:
        return False
    k = _key(sim)
    if not force and getattr(sim, "_tv_key", None) == k:
        return False
    body = render_lines(sim, ctl, side, narr)
    if not body:
        return False
    sim._tv_key = k
    import ui
    ui.clear()                                     # one screen per snap: the tablet on top, the call below
    width = max(ui.visible_len(ANSI.sub("", ln)) for ln in body)
    with ui.allow_width(width):                    # the tablet is laid out to its width: never fold it
        for ln in body:
            print(ln)
    return True
