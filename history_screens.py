"""
history_screens.py — The History Lookup (Media Center [16], or [H] on the dashboard's MEDIA tab).

  LOOK UP   a team, a head coach, a conference or a player — and, for a coach or player, "only at this school";
            for a team, "only while this man coached it"; and the subject's own poll tier.
  AGAINST   a team, a head coach, a conference, a poll tier (Top 25 / Top 10 / unranked) — any mix.
  GAMES     seasons from–to · regular season / conference / non-conference / postseason / bowls / playoff /
            conference title games · home / away / neutral · close games · wins or losses.

[Enter] shows the games (record, streaks, best and worst, every game with both head coaches — or, for a player, his
line in every game); [G] breaks them down by opponent, opposing coach, conference, season, school or coach; [P] has
ready-made lookups; a game's number opens its box score.
"""
import history as H
import ui
from ui import C, ask, chip, clear, columns, pad, paint, panel, pause, rule, title_bar, truncate

GRAY = C.GRAY
PER_PAGE = 15


def _acc():
    return ui.ACCENT


def _k(k):
    return paint(f"[{k}]", _acc(), C.BOLD)


def _val(v, none="any"):
    return paint(v, C.BWHITE, C.BOLD) if v else paint(none, GRAY)


# ═══ Picking a value ════════════════════════════════════════════════════════
def _pick(prompt, options, info=None, order=None):
    """Type part of a name. Returns (changed, value); value None = 'any' (typed '-' or 'any')."""
    c = ask(f"{prompt} (part of a name · - = any · Enter = keep):").strip()
    if not c:
        return False, None
    if c.lower() in ("-", "any", "none", "clear"):
        return True, None
    low = c.lower()
    exact = [o for o in options if o.lower() == low]
    hits = exact or [o for o in options if low in o.lower()]
    if order:
        hits.sort(key=order)
    if not hits:
        print(paint(f"   Nothing on record matches '{c}'.", C.BYELLOW))
        pause()
        return False, None
    if len(hits) == 1:
        return True, hits[0]
    shown = hits[:18]
    print()
    for i, o in enumerate(shown, 1):
        print(f"   {_k(i):>14} {paint(pad(truncate(o, 30), 31), C.BWHITE)}" + (paint(info(o), GRAY) if info else ""))
    if len(hits) > len(shown):
        print(paint(f"   …and {len(hits) - len(shown)} more — type more of the name.", GRAY))
    n = ask("Which one?").strip()
    if n.isdigit() and 1 <= int(n) <= len(shown):
        return True, shown[int(n) - 1]
    return False, None


def _coach_info(league):
    games, _ = H.index(league)
    d = {}
    for r in games:
        for school, coach in ((r.h, r.hhc), (r.a, r.ahc)):
            if coach:
                e = d.setdefault(coach, [set(), r.year, r.year, 0])
                e[0].add(school)
                e[1], e[2], e[3] = min(e[1], r.year), max(e[2], r.year), e[3] + 1
    return d


def _player_info(players):
    def info(name):
        rows = players.get(name, [])
        schools = []
        for r, home, *_ in rows:
            s = r.h if home else r.a
            if s not in schools:
                schools.append(s)
        yrs = sorted({r.year for r, *_ in rows})
        pos = rows[-1][2] if rows else ""
        return f"{pos:<3} {', '.join(schools)[:30]:<31}{yrs[0]}–{yrs[-1]}  {len(rows)} g" if rows else ""
    return info


# ═══ The filter screen ══════════════════════════════════════════════════════
def _default(league):
    import dashboard
    t = dashboard.focus_team(league)
    return H.Query(subj_type="team", subj=t.school if t is not None else None)


def _cycle(seq, cur):
    return seq[(seq.index(cur) + 1) % len(seq)]


def lookup_screen(league, q=None):
    q = q or _default(league)
    while True:
        clear()
        print(title_bar("HISTORY LOOKUP", sub="MEDIA CENTER"))
        games, players = H.index(league)
        if not games:
            print(paint("\n   No games on record yet. Come back after the first week.", GRAY))
            pause()
            return
        yrs = sorted({r.year for r in games})
        print(paint(f"   {len(games):,} games on record  ·  seasons {yrs[0]}–{yrs[-1]}  ·  {len(players):,} players  ·  "
                    "head coaches on every game", GRAY))
        print()
        st = q.subj_type
        extra = ("At school", q.subj_school) if st in ("coach", "player") else \
            ("With coach", q.subj_coach) if st == "team" else (None, None)
        nxt = H.SUBJECTS[(H.SUBJECTS.index(st) + 1) % len(H.SUBJECTS)]
        left = [f"{_k(1)} {pad('Look up', 11)}" + paint(H.SUBJECT_NAMES[st], C.BWHITE, C.BOLD)
                + paint(f"   (next: {H.SUBJECT_NAMES[nxt].lower()})", GRAY),
                f"{_k(2)} {pad('Who', 11)}{_val(q.subj, 'pick one')}"]
        if extra[0]:
            left.append(f"{_k(3)} {pad(extra[0], 11)}{_val(extra[1])}")
        left.append(f"{_k('R')} {pad('Their rank', 11)}{_val(H.RANK_NAMES[q.subj_rank] if q.subj_rank != 'any' else None)}")
        right = [f"{_k(4)} {pad('Team', 11)}{_val(q.opp_school)}",
                 f"{_k(5)} {pad('Head coach', 11)}{_val(q.opp_coach)}",
                 f"{_k(6)} {pad('Conference', 11)}{_val(q.opp_conf)}",
                 f"{_k(7)} {pad('Rank', 11)}{_val(H.RANK_NAMES[q.opp_rank] if q.opp_rank != 'any' else None)}"]
        h = max(len(left), len(right))
        for ln in columns(panel("LOOK UP", left, 49, color=_acc(), title_color=_acc(), height=h),
                          panel("AGAINST", right, 50, color=_acc(), title_color=_acc(), height=h)):
            print(ln)
        span = f"{q.year_from or yrs[0]}–{q.year_to or yrs[-1]}"
        gl = [f"{_k(8)} Seasons {_val(span)}    {_k(9)} {_val(H.KIND_NAMES[q.kind])}    "
              f"{_k('S')} Site {_val(q.site if q.site != 'any' else None)}    "
              f"{_k('C')} Close games {_val('only' if q.close else None, 'off')}    "
              f"{_k('W')} Result {_val(q.result if q.result != 'any' else None)}"]
        for ln in panel("GAMES", gl, 100, color=_acc(), title_color=_acc()):
            print(ln)
        hits = H.run(league, q)
        s = H.summary(hits)
        if not q.subj:
            preview = paint("Pick who to look up with [2] — or try a ready-made lookup with [P].", C.BYELLOW)
        elif not hits:
            preview = paint("No games match. Loosen a filter.", C.BYELLOW)
        else:
            last = s["last"]
            preview = (paint(f"{s['g']} game{'s' if s['g'] != 1 else ''}", C.BWHITE, C.BOLD) + paint("  ·  ", GRAY)
                       + paint(f"{s['w']}-{s['l']}", C.BGREEN if s["w"] >= s["l"] else C.BRED, C.BOLD)
                       + paint(f"  ·  last: {last.r.year} {'W' if last.won else 'L'} {last.pf}-{last.pa} vs {last.opp}", GRAY))
        print(f"\n   {paint('→', _acc(), C.BOLD)} {preview}")
        print(rule())
        print(f"   {paint('[Enter]', C.BGREEN, C.BOLD)} show the games   {_k('G')} breakdown   {_k('P')} ready-made lookups   "
              f"{_k('X')} clear   {paint('[B]', GRAY, C.BOLD)} back")
        c = ask("Set a filter:").strip().lower()
        if c == "b":
            return
        if c == "":
            if q.subj and hits:
                results_screen(league, q)
            continue
        if c == "1":
            q = H.Query(subj_type=_cycle(H.SUBJECTS, st), **{k: v for k, v in q.__dict__.items()
                                                              if k.startswith("opp_") or k in ("year_from", "year_to",
                                                                                               "kind", "site", "close",
                                                                                               "result")})
        elif c == "2":
            q = _pick_subject(league, q)
        elif c == "3" and st in ("coach", "player"):
            schools, *_ = H.names(league)
            ok, v = _pick("At which school", schools)
            if ok:
                q.subj_school = v
        elif c == "3" and st == "team":
            info = _coach_info(league)
            mine = sorted(k for k, v in info.items() if q.subj in v[0]) if q.subj else sorted(info)
            ok, v = _pick("Only while which head coach was there", mine,
                          info=lambda n: f"{min(info[n][1], info[n][2])}–{info[n][2]}")
            if ok:
                q.subj_coach = v
        elif c == "r":
            q.subj_rank = _cycle(H.RANKS, q.subj_rank)
        elif c == "4":
            schools, *_ = H.names(league)
            ok, v = _pick("Against which team", schools)
            if ok:
                q.opp_school = v
        elif c == "5":
            info = _coach_info(league)
            ok, v = _pick("Against which head coach", sorted(info),
                          info=lambda n: f"{', '.join(sorted(info[n][0]))[:34]:<35}{info[n][1]}–{info[n][2]}")
            if ok:
                q.opp_coach = v
        elif c == "6":
            _, _, confs, _ = H.names(league)
            ok, v = _pick("Against which conference", confs)
            if ok:
                q.opp_conf = v
        elif c == "7":
            q.opp_rank = _cycle(H.RANKS, q.opp_rank)
        elif c == "8":
            a = ask(f"From which season? ({yrs[0]}–{yrs[-1]}, Enter = the first):").strip()
            b = ask("Through which season? (Enter = the latest):").strip()
            q.year_from = int(a) if a.isdigit() else None
            q.year_to = int(b) if b.isdigit() else None
        elif c == "9":
            q.kind = _cycle(H.KINDS, q.kind)
        elif c == "s":
            q.site = _cycle(H.SITES, q.site)
        elif c == "c":
            q.close = not q.close
        elif c == "w":
            q.result = _cycle(H.RESULTS, q.result)
        elif c == "x":
            q = H.Query(subj_type=q.subj_type, subj=q.subj)
        elif c == "g" and q.subj and hits:
            breakdown_screen(league, q)
        elif c == "p":
            q = presets(league, q)


def _pick_subject(league, q):
    schools, coaches, confs, players = H.names(league)
    if q.subj_type == "team":
        ok, v = _pick("Which team", schools)
    elif q.subj_type == "coach":
        info = _coach_info(league)
        ok, v = _pick("Which head coach", sorted(info),
                      info=lambda n: f"{', '.join(sorted(info[n][0]))[:34]:<35}{info[n][1]}–{info[n][2]}")
    elif q.subj_type == "conf":
        ok, v = _pick("Which conference", confs)
    else:
        ok, v = _pick("Which player", list(players), info=_player_info(players),
                      order=lambda n: -len(players.get(n, [])))
    if ok:
        q.subj = v
        q.subj_school = q.subj_coach = None
    return q


# ═══ Ready-made lookups ═════════════════════════════════════════════════════
def presets(league, q):
    import dashboard
    from collections import Counter
    t = dashboard.focus_team(league)
    if t is None:
        return q
    games, players = H.index(league)
    opp = Counter(r.a if r.h == t.school else r.h for r in games if t.school in (r.h, r.a))
    import rivalries
    rivals = [o for o in opp if rivalries.is_rivalry(t.school, o)]          # a named rivalry first (the Iron Bowl...)
    rival = max(rivals, key=lambda o: opp[o]) if rivals else (opp.most_common(1)[0][0] if opp else None)
    coach = t.coach.name if t.coach is not None else None
    other = "Big Ten" if t.conference != "Big Ten" else "SEC"
    star = None
    for p in sorted(t.roster, key=lambda p: -p.overall):
        if players.get(p.name):
            star = p.name
            break
    items = [(f"{t.school}: the all-time record", H.Query(subj=t.school))]
    if rival:
        items.append((f"{t.school} vs {rival}" + (f" — {rivalries.rivalry_name(t.school, rival)}"
                                                  if rivalries.rivalry_name(t.school, rival) else " (the most-played series)"),
                      H.Query(subj=t.school, opp_school=rival)))
        if coach:
            items.append((f"{t.school} vs {rival}, only with {coach} coaching {t.school}",
                          H.Query(subj=t.school, subj_coach=coach, opp_school=rival)))
    if coach:
        items.append((f"Coach {coach} vs Top 25 teams, wherever he coached",
                      H.Query(subj_type="coach", subj=coach, opp_rank="top25")))
        items.append((f"Coach {coach} in the postseason", H.Query(subj_type="coach", subj=coach, kind="postseason")))
    items.append((f"{t.school} vs the {other}", H.Query(subj=t.school, opp_conf=other)))
    items.append((f"The {t.conference} vs the {other}", H.Query(subj_type="conf", subj=t.conference, opp_conf=other)))
    items.append((f"{t.school} in close games (8 points or fewer)", H.Query(subj=t.school, close=True)))
    items.append((f"{t.school} as a Top 10 team vs Top 25 teams", H.Query(subj=t.school, subj_rank="top10", opp_rank="top25")))
    if star:
        items.append((f"{star} vs Top 25 teams", H.Query(subj_type="player", subj=star, opp_rank="top25")))
    clear()
    print(title_bar("READY-MADE LOOKUPS", sub="HISTORY LOOKUP"))
    print()
    for i, (label, _) in enumerate(items, 1):
        print(f"   {_k(i):>14}  {label}")
    print(paint("\n   Each one fills in the filters — change any of them after.", GRAY))
    c = ask("Which one? (Enter = back)").strip()
    if c.isdigit() and 1 <= int(c) <= len(items):
        return items[int(c) - 1][1]
    return q


# ═══ Results ════════════════════════════════════════════════════════════════
def _subject_face(league, q, hits):
    import faces
    if not faces.enabled() or q.subj_type not in ("coach", "player"):
        return None
    if q.subj_type == "coach":
        pool = [t.coach for t in league.teams if t.coach is not None] + list(getattr(league, "coach_pool", []) or []) \
            + list(getattr(league, "retired_coaches", []) or [])
        c = next((c for c in pool if c.name == q.subj), None)
        if c is not None:
            return faces.coach_portrait(c, mini=True)
        return faces.name_portrait(q.subj, school=hits[-1].school if hits else None, role="coach", mini=True)
    p = next((p for t in league.teams for p in t.roster if p.name == q.subj), None)
    if p is not None:
        return faces.player_portrait(p, mini=True)
    last = hits[-1] if hits else None
    return faces.name_portrait(q.subj, school=last.school if last else None,
                               year=faces.class_year(last.cls) if last else 3, mini=True)


def _summary_lines(q, hits, s):
    w, l, g_, pf, pa = s["w"], s["l"], s["g"], s["pf"], s["pa"]
    pct = w / g_ if g_ else 0
    rec = paint(f"{w}-{l}", C.BGREEN if w >= l else C.BRED, C.BOLD)
    lines = []
    if q.subj_type == "player":
        t = H.totals(hits)
        g = s["g"]
        schools = []
        for h in hits:
            if h.school not in schools:
                schools.append(h.school)
        lines.append(paint(q.subj, C.BWHITE, C.BOLD) + paint(f"   {hits[-1].pos} · {', '.join(schools)}", GRAY))
        lines.append(paint(f"{g} games", C.BWHITE, C.BOLD) + "   " + paint("his team went", GRAY) + " " + rec)
        lines.append(paint("TOTALS  ", GRAY) + truncate(H.statline(t), 74))
        per = []
        if t.get("pass_att"):
            per.append(f"{t['pass_yds'] / g:.0f} pass yds")
        if t.get("rush_att"):
            per.append(f"{t['rush_yds'] / g:.0f} rush yds")
        if t.get("rec"):
            per.append(f"{t['rec_yds'] / g:.0f} rec yds")
        if t.get("tkl"):
            per.append(f"{t['tkl'] / g:.1f} tkl")
        if per:
            lines.append(paint("PER GAME  ", GRAY) + " · ".join(per))
        best = max(hits, key=lambda h: H.impact(h.line))
        rk = f"#{best.opp_rank} " if best.opp_rank else ""
        lines.append(paint("BEST GAME  ", GRAY) + f"{best.r.year} vs {rk}{best.opp}: " + truncate(H.statline(best.line), 50))
        return lines
    lines.append(paint("RECORD", GRAY) + " " + rec + " " + paint(f"({pct:.3f})", GRAY) + "   "
                 + paint("POINTS", GRAY) + f" {pf}-{pa} " + paint(f"(avg {pf / g_:.1f}-{pa / g_:.1f})", GRAY))
    lines.append(f"{paint('STREAK', GRAY)} {s['streak']}   {paint('longest win streak', GRAY)} {s['best_streak']}   "
                 f"{paint('vs Top 25', GRAY)} {s['ranked_w']}-{s['ranked_g'] - s['ranked_w']}   "
                 f"{paint('close games', GRAY)} {s['close_w']}-{s['close_g'] - s['close_w']}")
    f_, l_ = s["first"], s["last"]
    lines.append(f"{paint('FIRST', GRAY)} {f_.r.year} {'W' if f_.won else 'L'} {f_.pf}-{f_.pa} vs {f_.opp}   "
                 f"{paint('LAST', GRAY)} {l_.r.year} {'W' if l_.won else 'L'} {l_.pf}-{l_.pa} vs {l_.opp}")
    bw, bl = s["big_win"], s["bad_loss"]
    lines.append((f"{paint('BIGGEST WIN', GRAY)} +{bw.pf - bw.pa} vs {bw.opp} ({bw.r.year})   " if bw else "")
                 + (f"{paint('WORST LOSS', GRAY)} -{bl.pa - bl.pf} vs {bl.opp} ({bl.r.year})" if bl else ""))
    return lines


def results_screen(league, q):
    import faces_ui
    hits = H.run(league, q)
    order = "newest"
    page = 0
    while True:
        s = H.summary(hits)
        view = list(reversed(hits)) if order == "newest" else list(hits) if order == "oldest" else \
            sorted(hits, key=lambda h: -(abs(h.pf - h.pa)))
        pages = max(1, (len(view) + PER_PAGE - 1) // PER_PAGE)
        page = min(page, pages - 1)
        clear()
        print(title_bar("HISTORY · " + truncate(q.describe(), 84), sub=None))
        lines = _summary_lines(q, hits, s)
        face = _subject_face(league, q, hits)
        body = faces_ui.beside(face, lines, indent=0, gap=2) if face else lines
        for ln in panel("THE RECORD", body, 100, color=_acc(), title_color=_acc()):
            print(ln)
        player = q.subj_type == "player"
        show_school = q.subj_type in ("coach", "conf", "player")
        if player:
            print(paint(f"   {'#':>2}  {'YEAR':<5}{'GAME':<16}{'':<3}{'OPPONENT':<22}{'RESULT':<10}HIS LINE", GRAY, C.BOLD))
        else:
            print(paint(f"   {'#':>2}  {'YEAR':<5}{'GAME':<16}{'':<3}" + (f"{'TEAM':<16}" if show_school else "")
                        + f"{'OPPONENT':<22}{'RESULT':<10}HEAD COACHES", GRAY, C.BOLD))
        chunk = view[page * PER_PAGE:(page + 1) * PER_PAGE]
        for i, h in enumerate(chunk, 1):
            site = {"home": "vs", "away": "at", "neutral": "n"}[h.site]
            rk = paint(f"#{h.opp_rank} ", C.BYELLOW) if h.opp_rank else ""
            res = paint(f"{'W' if h.won else 'L'} {h.pf}-{h.pa}", C.BGREEN if h.won else C.BRED, C.BOLD)
            label = truncate(h.r.label.replace("Week ", "Wk "), 15)
            row = f"   {paint(f'{i:>2}', _acc())}  {h.r.year:<5}{pad(label, 16)}{paint(pad(site, 3), GRAY)}"
            if player:
                row += f"{pad(rk + truncate(h.opp, 18), 22)}{pad(res, 10)}{paint(truncate(H.statline(h.line), 40), C.BWHITE)}"
            else:
                if show_school:
                    srk = paint(f"#{h.rank} ", C.BYELLOW) if h.rank and q.subj_type != "team" else ""
                    row += pad(srk + truncate(h.school, 14), 16)
                row += f"{pad(rk + truncate(h.opp, 18), 22)}{pad(res, 10)}"
                hc = f"{(h.coach or '—').split()[-1]} vs {(h.opp_coach or '—').split()[-1]}"
                row += paint(truncate(hc, 26 if show_school else 40), GRAY)
            print(row)
        print(rule())
        print(f"   {paint(f'Page {page + 1}/{pages}', GRAY)}  {_k('N')} next  {_k('P')} prev  {_k('O')} order: "
              f"{paint(order, C.BWHITE)}  {_k('#')} box score  {_k('G')} breakdown  {paint('[B]', GRAY, C.BOLD)} back")
        c = ask("Select:").strip().lower()
        if c in ("b", ""):
            return
        if c == "n":
            page = (page + 1) % pages
        elif c == "p":
            page = (page - 1) % pages
        elif c == "o":
            order = {"newest": "oldest", "oldest": "margin", "margin": "newest"}[order]
            page = 0
        elif c == "g":
            breakdown_screen(league, q)
        elif c.isdigit() and 1 <= int(c) <= len(chunk):
            g = chunk[int(c) - 1].r.src
            if getattr(g, "box", None) is not None:
                import screens
                screens.show_box_score(league, g)


def breakdown_screen(league, q):
    hits = H.run(league, q)
    opts = [("O", "opp", "opponent"), ("H", "opp_coach", "opposing coach"), ("F", "opp_conf", "opp. conference"),
            ("Y", "season", "season")]
    if q.subj_type in ("coach", "player", "conf"):
        opts.append(("S", "school", "school"))
    if q.subj_type in ("team", "conf"):
        opts.append(("C", "coach", "head coach"))
    by = opts[0][1]
    while True:
        rows = H.group(hits, by)
        name = next(n for k, b, n in opts if b == by)
        clear()
        print(title_bar(f"BREAKDOWN BY {name.upper()}", sub="HISTORY LOOKUP"))
        print(paint("   " + truncate(q.describe(), 94), GRAY))
        print()
        print(paint(f"   {name.upper():<34}{'G':>4}{'W-L':>9}{'PCT':>8}{'PF':>7}{'PA':>7}{'AVG MARGIN':>12}", GRAY, C.BOLD))
        for label, w, l, pf, pa in rows[:24]:
            g = w + l
            col = C.BGREEN if w > l else C.BRED if l > w else C.BWHITE
            print(f"   {pad(truncate(label, 32), 34)}{g:>4}{paint(f'{w}-{l}'.rjust(9), col, C.BOLD)}{w / g:>8.3f}"
                  f"{pf:>7}{pa:>7}{(pf - pa) / g:>+12.1f}")
        if len(rows) > 24:
            print(paint(f"   …and {len(rows) - 24} more", GRAY))
        print(rule())
        print("   " + "  ".join(f"{_k(k)} {n}" for k, b, n in opts) + f"  {paint('[B]', GRAY, C.BOLD)} back")
        c = ask("Break down by:").strip().lower()
        hit = next((b for k, b, n in opts if k.lower() == c), None)
        if hit:
            by = hit
        else:
            return
