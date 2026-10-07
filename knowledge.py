"""
knowledge.py — What each person on the league website is allowed to know (Commissioner Mode).

THE RULE: the site never shows an individual player rating. Ever.

  Everyone (public)      standings, scores, polls, schedules, stats; every roster with an
                         APPROXIMATE tier word per player ("rotation player", "starter"...)
                         and his traits; every recruit's public profile, every school that
                         has offered him, his top schools and his public commitment.
  One team (private)     its own players as its staff sees them: the staff's read (a word),
                         the week's practice line, the staff's comments, the trend, traits,
                         the potential the staff can see; its recruiting board with what the
                         staff has learned (projection from scouting, the priorities uncovered,
                         where it stands); its coach (hot seat, goals, contract); its standing
                         orders; and its signing key for building codes.

Nothing here changes the world: it only reads. (Commissioner Mode clears the recruiting caches
before every import and cycle, so reading can't nudge results either.)
"""
import random

OFFSEASON_NOTE = "The offseason runs as one cycle for now: the coaching market runs in it, so set your jobs and contract answers now. Recruiting and game orders open again in fall camp."
CONF_PALETTE = ["#1F6B43", "#2D5DA8", "#9A3B2E", "#6B4FA0", "#B07A12", "#1E7F86", "#8A3C6E", "#44617B",
                "#5D7A1F", "#A0522D", "#3F3F8F", "#6E6E6E"]


def slug(school):
    import re
    return re.sub(r"[^a-z0-9]+", "-", school.lower()).strip("-")


def _pid(lg, p):
    import orders
    return orders.pid(lg, p)


def _ht(inches):
    return f"{inches // 12}'{inches % 12}\"" if inches else ""


def _trait_labels(p):
    import traits
    return [traits.PLAYER_TRAITS[k][0] for k in getattr(p, "traits", []) if k in traits.PLAYER_TRAITS]


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:                                   # noqa: BLE001 — one bad read must not sink the export
        return default


ANSI = __import__("re").compile(r"\x1b\[[0-9;?]*[A-Za-z]")
CLEAR = "\033[H\033[2J\033[3J"
MENU = __import__("re").compile(r"^\s*(\[[A-Z0-9#/]+\]|Enter|Select|\(\s*Enter)")


class _Done(Exception):
    pass


class words_only:
    """Inside this block every rating the game prints comes out as its Coach Career word, with no
    Scout's Eye ranges and no face art: what a coach sees, never a number."""
    def __enter__(self):
        import faces
        import scout
        self.old = (scout._FORCE[0], faces.enabled)
        scout._FORCE[0] = True
        faces.enabled = lambda: False
        return self

    def __exit__(self, *exc):
        import faces
        import scout
        scout._FORCE[0], faces.enabled = self.old
        return False


def capture(lg, team, fn, *args):
    """Run one of the game's own screens for this team and keep what it printed (its first page),
    as plain text. Any prompt is answered with Enter; the screen is read, never acted on."""
    import builtins
    import io
    import sys
    calls = [0]

    def feed(prompt=""):
        calls[0] += 1
        if calls[0] > 3:
            raise _Done
        return ""
    buf, old_in, old_out = io.StringIO(), builtins.input, sys.stdout
    old_user = lg.__dict__.get("user_team")
    builtins.input, sys.stdout = feed, buf
    lg.user_team = team
    try:
        with words_only():
            fn(*args)
    except _Done:
        pass
    except Exception:                                   # noqa: BLE001, S110 — a screen that can't draw is left out
        pass
    finally:
        builtins.input, sys.stdout = old_in, old_out
        lg.user_team = old_user
    frames = [f for f in buf.getvalue().split(CLEAR) if f.strip()]
    if not frames:
        return ""
    lines = [ANSI.sub("", ln).rstrip() for ln in frames[0].splitlines()]
    lines = [ln for ln in lines if not MENU.match(ln) and "Press Enter" not in ln]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


# ═══ League-wide (public) ═══════════════════════════════════════════════════

def conf_colors(lg):
    confs = sorted({t.conference for t in lg.teams}, key=lambda c: (c == "Independent", c))
    return {c: CONF_PALETTE[i % len(CONF_PALETTE)] for i, c in enumerate(confs)}


def teams_index(lg):
    import commissioner as cm
    colors = conf_colors(lg)
    return [{"id": slug(t.school), "school": t.school, "nick": t.nickname, "conf": t.conference,
             "confName": lg.conference_full_name(t.conference) or t.conference, "color": colors[t.conference],
             "owner": cm.owner(lg, t), "record": t.record, "confRecord": t.conf_record}
            for t in sorted(lg.teams, key=lambda t: t.school)]


def open_sections(lg):
    import comm_offseason
    off = comm_offseason.sections(lg) if getattr(lg, "mode", None) == "commissioner" else None
    if off is not None:
        return off
    if lg.season_complete:
        return ["jobs", "staff", "money", "nil"]
    return ["rec", "depth", "plan", "calls", "jobs", "staff", "money"]


def manifest(lg):
    import commissioner as cm
    st = cm.state(lg)
    links = st.setdefault("links", {})
    nxt = st["cycle"]["n"] + 1
    sections = open_sections(lg)
    return {"league": st["league_id"], "title": links.get("title") or "Console College League",
            "cycle": nxt, "label": cm.cycle_label(lg), "year": lg.year, "week": lg.week,
            "status": lg.status, "sections": sections,
            "note": links.get("note") or ("" if sections else OFFSEASON_NOTE),
            "formUrl": links.get("form_url") or "", "siteUrl": links.get("site_url") or "",
            "gameBuild": __import__("title").VERSION, "schema": cm.SCHEMA,
            "teams": teams_index(lg)}


def rules(lg):
    import orders
    import promises
    import recruit_plus
    import recruiting_data as rd
    import sideline
    import week
    from models import POSITIONS
    return {
        "actions": {k: {"label": v[0], "cost": v[1]} for k, v in rd.ACTIONS.items()},
        "queueRules": recruit_plus.QUEUE_RULES,
        "priorities": rd.PRIORITY_LABELS,
        "focus": {k: {"label": v[0], "blurb": v[1], "hours": v[4]} for k, v in week.FOCUS.items()},
        "offKeys": {k: {"label": v[0], "blurb": v[1]} for k, v in sideline.OFF_KEYS.items()},
        "defKeys": {k: {"label": v[0], "blurb": v[1]} for k, v in sideline.DEF_KEYS.items()},
        "promises": {k: {"label": v[0], "cost": v[3]} for k, v in promises.KINDS.items()},
        "ovCost": recruit_plus.OV_COST, "ovMax": recruit_plus.OV_MAX, "pwoMax": recruit_plus.PWO_MAX,
        "boardMax": orders.BOARD_MAX, "queueMax": orders.MAX_QUEUE, "positions": list(POSITIONS),
        "prefix": orders.PREFIX, "version": orders.VERSION,
        "scales": {"player": [w for _, w in __import__("scout").OVR], "skill": ["horrible", "bad", "below average", "average",
                                                                        "good", "great", "elite"],
                   "athlete": [w for _, w in __import__("scout").FUND], "team": ["rebuilding", "below average", "average", "good",
                                                                                "very good", "elite"]},
        "offseason": [{"key": k, "label": v, "sections": __import__("comm_offseason").SECTIONS.get(k, [])}
                      for k, v in __import__("comm_offseason").STAGES],
    }


def scores(lg):
    out = []
    for wk in sorted(lg.schedule):
        games = lg.schedule.get(wk) or []
        if not games:
            continue
        rows = []
        for gi, g in enumerate(games):
            ranks = getattr(g, "ranks", None) or {}
            row = {"w": wk, "gi": gi, "box": bool(g.played and getattr(g, "box", None) is not None), "home": slug(g.home.school), "away": slug(g.away.school), "hs": g.home.school, "as": g.away.school,
                   "neutral": bool(g.neutral), "played": bool(g.played), "name": getattr(g, "bowl_name", None) or "",
                   "hr": ranks.get(g.home), "ar": ranks.get(g.away)}
            if g.played:
                row.update(h=g.home_score, a=g.away_score)
            rows.append(row)
        out.append({"week": wk, "label": lg.week_name(wk), "games": rows})
    return out


# ── box scores and game logs ──
_BOX_TEAM = (("First downs", lambda s: s["first_downs"]), ("Total yards", lambda s: s["total_yds"]),
             ("Passing yards", lambda s: s["pass_yds"]), ("Rushing yards", lambda s: s["rush_yds"]),
             ("Plays", lambda s: s["plays"]),
             ("Yards per play", lambda s: f"{s['total_yds'] / s['plays']:.1f}" if s["plays"] else "0.0"),
             ("Third down", lambda s: f"{s['third_conv']}-{s['third_att']}"),
             ("Fourth down", lambda s: f"{s['fourth_conv']}-{s['fourth_att']}"),
             ("Red zone TDs", lambda s: f"{s['red_zone_td']}-{s['red_zone_att']}"),
             ("Turnovers", lambda s: s["turnovers"]), ("Penalties", lambda s: f"{s['penalties']}-{s['pen_yds']}"),
             ("Plays of 20+", lambda s: s["plays_20_plus"]),
             ("Possession", lambda s: f"{int(s['top']) // 60}:{int(s['top']) % 60:02d}"))

# column header, then how to read each player's line; a player shows up in a table when `has` is true
_BOX_CATS = (
    ("Passing", ("C/ATT", "YDS", "TD", "INT", "SCK"), lambda c: c["pass_att"],
     lambda c: (f"{c['pass_cmp']}/{c['pass_att']}", c["pass_yds"], c["pass_td"], c["pass_int"], c["sacked"])),
    ("Rushing", ("CAR", "YDS", "AVG", "TD", "LONG"), lambda c: c["rush_att"],
     lambda c: (c["rush_att"], c["rush_yds"], f"{c['rush_yds'] / c['rush_att']:.1f}", c["rush_td"], c["rush_long"])),
    ("Receiving", ("REC", "TGT", "YDS", "TD", "LONG"), lambda c: c["rec"] or c["targets"],
     lambda c: (c["rec"], c["targets"], c["rec_yds"], c["rec_td"], c["rec_long"])),
    ("Defense", ("TKL", "TFL", "SACK", "INT", "PBU", "FF"), lambda c: any(c[k] for k in ("tkl", "ast", "tfl", "sack", "int", "pbu", "ff")),
     lambda c: (c["tkl"] + c["ast"], c["tfl"], c["sack"], c["int"], c["pbu"], c["ff"])),
    ("Kicking", ("FG", "LONG", "XP"), lambda c: c["fg_att"] or c["xp_att"],
     lambda c: (f"{c['fg_made']}/{c['fg_att']}", c["fg_long"], f"{c['xp_made']}/{c['xp_att']}")),
    ("Punting", ("PUNTS", "YDS", "AVG"), lambda c: c["punts"],
     lambda c: (c["punts"], c["punt_yds"], f"{c['punt_yds'] / c['punts']:.1f}")),
    ("Returns", ("KR", "KR YDS", "PR", "PR YDS"), lambda c: c["kr"] or c["pr"],
     lambda c: (c["kr"], c["kr_yds"], c["pr"], c["pr_yds"])),
)


def _points(text):
    if text.startswith("Safety"):
        return 2
    if text.endswith("FG") or " yd FG" in text:
        return 3
    return 6 + (1 if text.endswith("(kick)") else 2 if "2-pt good" in text else 0)


def _game_line(c):
    """One game for one player, in a line: what a box-score glance would tell you."""
    bits = []
    if c["pass_att"]:
        bits.append(f"{c['pass_cmp']}/{c['pass_att']}, {c['pass_yds']} pass yds" + (f", {c['pass_td']} TD" if c["pass_td"] else "")
                    + (f", {c['pass_int']} INT" if c["pass_int"] else ""))
    if c["rush_att"]:
        bits.append(f"{c['rush_att']} car, {c['rush_yds']} yds" + (f", {c['rush_td']} TD" if c["rush_td"] else ""))
    if c["rec"]:
        bits.append(f"{c['rec']} rec, {c['rec_yds']} yds" + (f", {c['rec_td']} TD" if c["rec_td"] else ""))
    tk = c["tkl"] + c["ast"]
    d = [f"{tk} tkl"] if tk else []
    d += [f"{c['tfl']:g} TFL"] if c["tfl"] else []
    d += [f"{c['sack']:g} sack"] if c["sack"] else []
    d += [f"{c['int']} INT"] if c["int"] else []
    d += [f"{c['pbu']} PBU"] if c["pbu"] else []
    if d:
        bits.append(", ".join(d))
    if c["fg_att"] or c["xp_att"]:
        bits.append(f"FG {c['fg_made']}/{c['fg_att']}, XP {c['xp_made']}/{c['xp_att']}")
    if c["punts"]:
        bits.append(f"{c['punts']} punts, {c['punt_yds'] / c['punts']:.1f} avg")
    if c["kr"] or c["pr"]:
        bits.append(f"{c['kr'] + c['pr']} returns, {c['kr_yds'] + c['pr_yds']} yds")
    return "; ".join(bits)


def _box(lg, wk, i, g, b, logs):
    from collections import Counter

    import models
    order = {pos: n for n, pos in enumerate(models.POSITIONS)}
    ranks = getattr(g, "ranks", None) or {}
    sides = (g.away, g.home)
    home_ids = getattr(b, "_home_ids", set())
    per = {t: [] for t in sides}
    for p, line in b.stats.items():
        c = Counter(line)
        if not any(c.values()):
            continue
        t = g.home if id(p) in home_ids else g.away
        per[t].append((p, c))
        opp = g.opponent_of(t)
        mine, theirs = g.score_for(t), g.score_for(opp)
        logs.setdefault(id(p), []).append(
            [wk, lg.week_name(wk) if wk <= 13 else (getattr(g, "game_type", "") or lg.week_name(wk)), i, slug(opp.school),
             "vs" if g.home is t or g.neutral else "at", f"{'W' if mine > theirs else 'L'} {mine}-{theirs}", _game_line(c)])
    cats = []
    for name, cols, has, row in _BOX_CATS:
        teams = []
        for t in sides:
            rows = [[_pid(lg, p), p.name, p.position, *row(c)] for p, c in
                    sorted(per[t], key=lambda x: (order.get(x[0].position, 99), x[0].name)) if has(c)]
            if name == "Passing":
                rows.sort(key=lambda r: -int(str(r[3]).split("/")[1]))
            elif name in ("Rushing", "Receiving"):
                rows.sort(key=lambda r: -r[4 if name == "Rushing" else 5])
            elif name == "Defense":
                rows.sort(key=lambda r: -(r[3] + 2 * r[5] + 3 * r[6]))
            teams.append(rows)
        if any(teams):
            cats.append({"name": name, "cols": list(cols), "rows": teams})
    run = {g.away: 0, g.home: 0}
    scoring = []
    for q, clock, t, text in b.scoring:
        run[t] = run.get(t, 0) + _points(text)
        scoring.append([q, f"{int(clock) // 60}:{int(clock) % 60:02d}", slug(t.school), text, run[g.away], run[g.home]])
    if (run[g.away], run[g.home]) != (g.away_score, g.home_score):          # a scoring play we can't price: no running score
        for s in scoring:
            s[4] = s[5] = None
    ts = {t: b.team_stats.get(t) or {} for t in sides}
    team_rows = []
    for label, fn in _BOX_TEAM:
        try:
            team_rows.append([label, *(fn(Counter(ts[t])) for t in sides)])
        except (KeyError, ZeroDivisionError, TypeError, ValueError):
            continue
    drives = [[slug(d["team"].school), d.get("q"), f"{int(d.get('clock', 0)) // 60}:{int(d.get('clock', 0)) % 60:02d}",
               d.get("start"), d.get("plays"), d.get("yards"), f"{int(d.get('time', 0)) // 60}:{int(d.get('time', 0)) % 60:02d}",
               d.get("result", "")] for d in (b.drives or []) if d.get("team") in sides]
    return {"w": wk, "i": i, "label": lg.week_name(wk) if wk <= 13 else (getattr(g, "game_type", "") or lg.week_name(wk)),
            "name": getattr(g, "bowl_name", None) or "", "neutral": bool(g.neutral), "att": getattr(g, "attendance", None),
            "teams": [{"id": slug(t.school), "school": t.school, "rank": ranks.get(t), "score": g.score_for(t),
                       "line": list(b.line.get(t, []))} for t in sides],
            "team": team_rows, "scoring": scoring, "cats": cats, "drives": drives}


def box_scores(lg):
    """Every played game's box score, by week (same order as scores.json), and each player's game log."""
    out, logs = {}, {}
    for wk in sorted(lg.schedule):
        rows = []
        for i, g in enumerate(lg.schedule.get(wk) or []):
            b = getattr(g, "box", None)
            rows.append(_safe(lambda g=g, b=b, i=i, wk=wk: _box(lg, wk, i, g, b, logs), None) if g.played and b is not None else None)
        if any(rows):
            out[wk] = rows
    return out, logs


def standings(lg):
    out = []
    for conf in sorted({t.conference for t in lg.teams}, key=lambda c: (c == "Independent", c)):
        ts = [t for t in lg.teams if t.conference == conf]
        ts.sort(key=lambda t: (-t.conf_win_pct, -t.conf_wins, -t.win_pct, -t.prestige))
        out.append({"conf": conf, "name": lg.conference_full_name(conf) or conf,
                    "rows": [{"id": slug(t.school), "school": t.school, "conf": t.conf_record, "all": t.record,
                              "rank": lg.rankings.rank_of(t)} for t in ts]})
    return out


def polls(lg):
    import gui_data
    d = _safe(lambda: gui_data.top25(lg, None), {}) or {}
    for row in d.get("poll", []):
        row["id"] = slug(row["school"])
        row.pop("color", None)
        row.pop("me", None)
    return {"label": d.get("label", ""), "poll": d.get("poll", []),
            "cfp": [{"rank": r["rank"], "school": r["school"], "id": slug(r["school"])} for r in d.get("cfp", [])],
            "heisman": [{"name": h["name"], "pos": h["pos"], "school": h["school"]} for h in d.get("heisman", [])]}


def news(lg):
    import re

    import dashboard
    heads = _safe(lambda: dashboard.headlines(lg, None, n=14), []) or []
    strip = re.compile(r"\x1b\[[0-9;]*m")
    rec = [strip.sub("", t) for _, _, t in list(getattr(lg.recruiting, "news", []))[:20]]
    return {"headlines": [strip.sub("", t) for _, t in heads], "recruiting": rec}


# ── recruits ──

def _pos_ranks(pool):
    out, seen = {}, {}
    for r in sorted(pool, key=lambda r: (r.national_rank or 99999)):
        seen[r.position] = seen.get(r.position, 0) + 1
        out[id(r)] = seen[r.position]
    return out


def recruits_public(lg):
    import recruit_plus as rp
    pool = lg.recruiting.pool
    pr = _pos_ranks(pool)
    out = []
    for r in sorted(pool, key=lambda r: (r.national_rank or 99999)):
        commit = rp.public_commit(r, None)
        out.append({"id": _pid(lg, r.player), "n": r.player.name, "p": r.position, "s": r.stars,
                    "r": r.national_rank, "pr": pr.get(id(r)), "st": r.home_state, "hs": rp.g(r, "hs") or "",
                    "k": rp.g(r, "kind", "hs") or "hs", "ht": _ht(r.player.height), "wt": r.player.weight,
                    "of": sorted(slug(t.school) for t in r.offers),
                    "top": [slug(t.school) for t in r.top_schools(5) if r.interest.get(t, 0) > 0],
                    "c": slug(commit.school) if commit is not None else None, "sg": bool(r.signed)})
    return out


def recruit_details(lg):
    """What the Coach Career recruit card shows anyone: where he's from, his senior season, his official
    visits, the experts' crystal ball and the kind of commitment. Split into small files by id."""
    import recruit_plus as rp
    cyc = lg.recruiting
    out = {}
    for r in cyc.pool:
        rid = _pid(lg, r.player)
        commit = rp.public_commit(r, None)
        _, line = _safe(lambda r=r: rp.senior_season(r, lg.week), ("", ""))
        cb = _safe(lambda r=r: rp.crystal(r, cyc), None)
        d = {"or": rp.origin_line(r), "ss": line, "hsk": rp.g(r, "kind", "hs") or "hs",
             "ov": [[slug(t.school), w] for t, w in sorted(rp.ov_of(r).items(), key=lambda x: x[1])],
             "gen": bool(getattr(r.player, "generational", False))}
        if cb:
            d["cb"] = [slug(cb[0].school), cb[1]]
        if commit is not None:
            d["cw"] = rp.commit_word(r).replace(" · silent", "")
        out.setdefault(rid % 16, {})[rid] = d
    return out


def classes(lg):
    """National recruiting class rankings, the way the class screen lists them."""
    cyc = lg.recruiting
    rows = []
    for t in lg.teams:
        k = cyc.commitments(t)
        if not k:
            continue
        rows.append({"id": slug(t.school), "rank": cyc.class_rank(t), "n": len(k),
                     "avg": round(sum(r.stars for r in k) / len(k), 2),
                     "five": sum(1 for r in k if r.stars == 5), "four": sum(1 for r in k if r.stars == 4)})
    rows.sort(key=lambda x: (x["rank"] or 999, -x["avg"]))
    return rows


# ── public team page ──

def _approx_word(lg, p):
    import scout
    rng = random.Random(f"pubtier:{lg.seed}:{_pid(lg, p)}:{lg.year}:{max(0, lg.week) // 4}")
    return scout.ovr_word(p.overall + rng.gauss(0, 3.0))


def _team_word(v):
    for cut, word in ((86, "elite"), (80, "very good"), (74, "good"), (68, "average"), (62, "below average")):
        if v >= cut:
            return word
    return "rebuilding"


def _card(lg, t, drop=("color", "mode", "words", "rankHistory")):
    """The team card without exact ratings: overall/offense/defense become fuzzy staff words."""
    import gui_data
    card = _safe(lambda: gui_data.team_card(lg, t), {}) or {}
    for k in drop:
        card.pop(k, None)
    rng = random.Random(f"pubteam:{lg.seed}:{t.school}:{lg.year}:{max(0, lg.week) // 4}")
    words = {}
    for k, label in (("ovr", "team"), ("off", "offense"), ("def", "defense")):
        v = card.pop(k, None)
        if isinstance(v, (int, float)):
            words[label] = _team_word(v + rng.gauss(0, 2.5))
    card["looks"] = words
    return card


def _stat_line(p):
    s = getattr(p, "season_stats", None) or {}
    bits = []
    for key, word in (("pass_yds", "pass yds"), ("pass_td", "pass TD"), ("rush_yds", "rush yds"), ("rush_td", "rush TD"),
                      ("rec", "rec"), ("rec_yds", "rec yds"), ("rec_td", "rec TD"), ("tkl", "tkl"), ("sack", "sacks"),
                      ("int", "INT"), ("fg_made", "FG")):
        v = s.get(key, 0)
        if v:
            bits.append(f"{v:g} {word}")
    return ", ".join(bits[:4])


def _public_stats(p, logs):
    """What anyone can look up about a player: this season, his career, year by year and his game log. No ratings."""
    from collections import Counter

    import screens
    career = screens._career_line(p) + Counter(p.season_stats or {})
    for k in [k for k in career if k.endswith("_long")]:
        career[k] = max(career[k] - (p.season_stats or {}).get(k, 0), (p.season_stats or {}).get(k, 0))
    cg = (p.career_games or 0) + (p.games_played or 0)
    years = []
    for y, line in sorted((getattr(p, "yearly_stats", None) or {}).items()):
        c = Counter(line)
        if any(c.values()):
            years.append([y, _game_line(c)])
    return {"gp": p.games_played or 0, "cgp": cg,
            "season": _stat_rows(p.season_stats, p.games_played) if p.games_played else [],
            "career": _stat_rows(career, cg) if cg and (p.career_games or 0) else [],
            "years": years, "log": (logs or {}).get(id(p), [])}


def team_public(lg, t, logs=None):
    import gui_data
    import recruit_plus as rp
    card = _card(lg, t)
    coach = t.coach
    roster = []
    for pos in __import__("models").POSITIONS:
        for i, p in enumerate(t.players_at(pos)):
            roster.append({"id": _pid(lg, p), "n": p.name, "num": p.number, "p": pos, "yr": p.class_label,
                           "ht": _ht(p.height), "wt": p.weight, "home": getattr(p, "home_state", None) or "",
                           "stars": getattr(p, "hs_stars", None), "tier": _approx_word(lg, p),
                           "traits": _trait_labels(p), "inj": (p.inj_desc or "injured") if getattr(p, "inj_games", 0) > 0 else "",
                           "stats": _stat_line(p), "depth": i + 1, **_public_stats(p, logs)})
    sched = _safe(lambda: gui_data.schedule(lg, t), []) or []
    for row, g in zip(sched, lg.team_games(t)):
        wk_games = lg.schedule.get(g.week) or []
        row["w"] = g.week
        row["gi"] = next((k for k, x in enumerate(wk_games) if x is g), None)
        row["box"] = bool(g.played and getattr(g, "box", None) is not None)
    commits = [_pid(lg, r.player) for r in lg.recruiting.pool if rp.public_commit(r, None) is t]
    return {"id": slug(t.school), "card": card,
            "coach": {"name": coach.name if coach else "Vacant", "record": _safe(lambda: __import__("carousel")._record(coach), ""),
                      "age": getattr(coach, "age", None)} if coach else {"name": "Vacant"},
            "schedule": sched, "roster": roster, "commits": commits}


# ═══ One team (private) ═════════════════════════════════════════════════════

def _star_range(r, team):
    import recruit_plus as rp
    if r.scout.get(team, 0) <= 0:
        return None
    lo, hi = r.scouting_range(team)

    def stars(v):
        return next(s for cut, s in rp.TRUTH_STARS if v >= cut)
    a, b = stars(lo), stars(hi)
    return f"{a}★" if a == b else f"{a}★–{b}★"


def _recruit_private(lg, team, r):
    """Everything the Coach Career recruit card shows this staff about one recruit."""
    import finance
    import promises
    import recruit_plus as rp
    import recruiting as rc
    import recruiting_data as rd
    from recruiting_data import PERSONALITIES
    cyc = lg.recruiting
    ov = rp.ov_of(r)
    ok_ov, why_ov = _safe(lambda: rp.can_invite(cyc, team, r, enforce=False), (False, ""))
    prom = promises.of(r) or {}
    mine = prom if prom.get("school") == team.school else {}
    why_prom = _safe(lambda: promises.precheck(lg, team, r), None)
    ok_pwo, why_pwo = _safe(lambda: rp.can_pwo(cyc, team, r), (False, ""))
    log = []
    for e in rp.log_of(cyc, team, r)[-6:]:
        if isinstance(e, (list, tuple)) and len(e) == 2:
            log.append(f"{'Wk ' + str(e[0]) if e[0] else 'Summer'}: {e[1]}")
        elif isinstance(e, dict):
            log.append(e.get("result") or "")
        else:
            log.append(str(e))
    lo, hi = r.scouting_range(team)
    known = rp.known(r, team)
    wants = [rd.PRIORITY_LABELS.get(k, k) if k in known else None for k in r.priorities]
    tops = r.top_schools(5)
    race = [[slug(t.school), round(r.interest.get(t, 0))] for t in tops if r.interest.get(t, 0) > 0]
    others = {t: a for t, a in finance.offers_for(cyc, r).items() if t is not team}
    best = max(others, key=others.get) if others else None
    nil = {"market": finance.market(r.stars), "yours": round(finance.market(r.stars) * finance.pay_scale(team)),
           "others": len(others), "high": others[best] if best else 0, "highBy": slug(best.school) if best else None,
           "appetite": finance.appetite_word(r) if r.scout.get(team, 0) >= 1 else ""}
    warn = ""
    if not r.signed and r.committed_to is not team and r.interest.get(team, 0) >= 30:
        blocked = _safe(lambda: rc.block_reason(lg, team, r, cyc._class_of(team)), None)
        if blocked:
            warn = f"You can't sign him right now: {blocked}"
        elif r.committed_to is None and r.leader() is team:
            left = rp.room_left(cyc, team, r.position)
            ahead = sum(1 for k in rp._leaning(cyc).get((team, r.position), ()) if k < r.national_rank)
            if ahead >= left:
                warn = (f"Room is tight at {r.position}: {left} spot{'s' if left != 1 else ''} left, {ahead} higher-ranked "
                        f"uncommitted kid{'s' if ahead != 1 else ''} leaning your way pick first on signing day")
    pv = rp.pipeline_of(team, r)
    with words_only():
        room = _safe(lambda: promises.room_line(team, r), "")
        pitches = _safe(lambda: [[k, w] for k, w in rp.pitch_options(cyc, team, r, n=10)], [])
    return {"id": _pid(lg, r.player), "standing": r.standing(team) if r.interest.get(team, 0) > 0 else "No contact yet",
            "proj": _star_range(r, team), "projWords": _proj_words(lo, hi), "scout": r.scout.get(team, 0),
            "wants": wants, "reads": PERSONALITIES[r.personality]["label"] if r.scout.get(team, 0) >= 2 else "",
            "knows": [rd.PRIORITY_LABELS.get(k, k) for k in known],
            "knowsKeys": known, "offered": team in r.offers, "offersOut": len(r.offers), "race": race,
            "mine": r.committed_to is team, "ov": ov.get(team), "ovN": len(ov), "canOv": bool(ok_ov), "whyOv": why_ov or "",
            "nil": finance.offer_to(cyc, team, r), "nilPanel": nil, "promise": (mine.get("kind") if mine else None),
            "whyPromise": why_prom or "", "room": room, "pwo": r in rp.pwo_list(cyc, team), "canPwo": bool(ok_pwo),
            "whyPwo": why_pwo or "", "pipeline": rp.pipe_word(pv) if pv else "", "warn": warn, "pitches": pitches,
            "log": [x for x in log if x]}


def _proj_words(lo, hi):
    import scout
    a, b = scout.ovr_word(lo), scout.ovr_word(hi)
    return a if a == b else f"{a} to {b}"


def _scan(lg, team):
    """The recruit finder's columns for every recruit still on the market: your staff's projection,
    where you stand, and the suggested-fit score with its reasons."""
    import recruiting_screens as rs
    import scout
    cyc = lg.recruiting
    needs = cyc._needs(team)
    commits = cyc.commitments(team)
    real_needs, real_commits = cyc._needs, cyc.commitments
    cyc._needs = lambda t, _n=needs, _f=real_needs: _n if t is team else _f(t)           # one read per team, not per recruit
    cyc.commitments = lambda t, _c=commits, _f=real_commits: _c if t is team else _f(t)
    out = []
    try:
        for r in cyc.pool:
            if r.signed:
                continue
            lo, hi = r.scouting_range(team)
            a, b = scout.OVR_SHORT[scout.ovr_word(lo)], scout.OVR_SHORT[scout.ovr_word(hi)]
            score, why = _safe(lambda r=r: rs.suggestion(lg, team, r), (0, []))
            out.append([_pid(lg, r.player), a if a == b else f"{a}-{b}",
                        r.standing(team) if r.interest.get(team, 0) > 0 else "", round(score, 1), [w for w, _ in why]])
    finally:
        cyc._needs, cyc.commitments = real_needs, real_commits
    return out


def _hours_next(lg, team):
    """The staff hours the coming week will have (before any recruiting-week bonus from the plan)."""
    cyc = lg.recruiting
    real = lg.week
    try:
        lg.week = real + 1
        phase, base, bonus = cyc.hours_parts(team)
        total = cyc.hours_for(team) - bonus
    finally:
        lg.week = real
    return {"phase": phase, "base": base, "total": max(0, total), "used": int(cyc.hours_used.get(team, 0))}


FORM_WORDS = ((0.75, "hot"), (0.20, "up"), (-0.20, "steady"), (-0.75, "down"), (-99, "cold"))
FILM_WORDS = ((4, "outplaying his grade"), (1, "trending up"), (-1, "on expectation"), (-4, "trending down"), (-99, "under his grade"))


def _band(v, scale):
    return next(w for cut, w in scale if v >= cut)


def _stat_rows(line, games):
    import screens
    return [[g, [[k, (round(v, 1) if isinstance(v, float) else v)] for k, v in cells]]
            for g, cells in _safe(lambda: screens._stat_rows(line, games), []) or []]


def _player_private(lg, t, p, pos, i, ctx):
    """One of your own players, the way the Coach Career player card, practice report and depth room
    show him: words for every rating, numbers only where the game shows numbers too."""
    import compliance
    import depth_staff
    import finance
    import injuries
    import morale
    import practice
    import scout
    import screens
    import subprof
    import traits
    from models import FUNDAMENTAL_NAMES, FUNDAMENTALS, POSITIONS
    from recruiting_data import STATES
    hurt = getattr(p, "inj_games", 0) > 0
    text, form = ctx["prac"].get(id(p), ("", 0.0))
    mv = morale.get(p)
    subs = subprof.all_values(p)
    ranked = sorted(subs, key=lambda x: -x[2])
    timeline = []
    for yr in sorted(set(p.events.keys()) | set(p.yearly_stats.keys()) | {y for y, _ in p.history}):
        if yr < 2026:
            continue
        o = next((o for y, o in p.history if y == yr), None)
        st = p.yearly_stats.get(yr) or {}
        bits = []
        if st.get("pass_yds"):
            bits.append(f"{st['pass_yds']} pass yds, {st.get('pass_td', 0)} TD")
        if st.get("rush_yds"):
            bits.append(f"{st['rush_yds']} rush yds, {st.get('rush_td', 0)} TD")
        if st.get("rec_yds"):
            bits.append(f"{st['rec_yds']} rec yds, {st.get('rec_td', 0)} TD")
        if st.get("tkl"):
            bits.append(f"{st['tkl']} tkl, {st.get('sack', 0)} sack, {st.get('int', 0)} INT")
        timeline.append({"y": yr, "looked": scout.ovr_word(o) if o else "", "events": list(p.events.get(yr, [])),
                         "stats": ", ".join(bits), "gp": getattr(p, "yearly_games", {}).get(yr)})
    personas = []
    try:
        pk = traits.persona(p)
        if pk in traits.PERSONAS:
            personas.append([traits.PERSONAS[pk][0], traits.PERSONAS[pk][1]])
    except Exception:                                   # noqa: BLE001, S110 — no personality on file
        pass
    staff = {}
    if ctx["depth"]:
        cr, ct = _safe(lambda: depth_staff.take(lg, t, p, pos, "coord"), (None, ""))
        prr, pt = _safe(lambda: depth_staff.take(lg, t, p, pos, "pos"), (None, ""))
        order = ctx["staffOrder"].get(pos, [])
        film = depth_staff.recent(p)
        delta = depth_staff.recent_delta(p)
        cform = depth_staff.camp_form(lg, t, p)
        staff = {"board": order.index(p) + 1 if p in order else None, "coord": cr, "coordNote": ct, "pos": prr, "posNote": pt,
                 "split": bool(cr and prr and abs(cr - prr) >= 2), "film": [round(x) for x in film],
                 "filmWord": _band(delta, FILM_WORDS) if film else "", "camp": [round(x[1], 1) for x in
                                                                                  depth_staff.camp(lg, t).get(id(p), [])],
                 "campWord": _band(cform, FORM_WORDS)}
    season = _stat_rows(p.season_stats, p.games_played) if p.games_played else []
    career = _stat_rows(screens._career_line(p), p.career_games) if p.career_games else []
    return {"id": _pid(lg, p), "n": p.name, "num": p.number, "p": pos, "yr": p.class_label,
            "ht": _ht(p.height), "wt": p.weight, "home": getattr(p, "home_state", None) or "",
            "homeName": (STATES.get(getattr(p, "home_state", None)) or [""])[0],
            "stars": getattr(p, "hs_stars", None), "depth": i + 1, "starter": i < ctx["starts"].get(pos, 1),
            "eval": scout.ovr_word(p.overall), "dev": p.potential_grade, "durability": p.durability,
            "developed": p.seasons_developed, "potential": "looks " + subprof.word(p.prof_ceiling),
            "gen": bool(getattr(p, "generational", False)), "transfer": screens._transfer_from(p) or "",
            "practice": text, "week": "good week" if form >= 0.8 else "rough week" if form <= -0.8 else "",
            "comments": _safe(lambda: practice.report(p, lg.week), ""), "trend": _safe(lambda: practice.trend(p)[0], ""),
            "best": [x[1] for x in ranked[:2]], "worst": [x[1] for x in ranked[-2:]] if len(ranked) > 2 else [],
            "skills": [[label, subprof.word(v)] for _, label, v in subs],
            "athlete": [[FUNDAMENTAL_NAMES[f], scout._w(scout.FUND, p.fundamentals[f])] for f in FUNDAMENTALS],
            "alt": [[x, scout.ovr_word(p.overall_at(x))] for x in sorted((x for x in POSITIONS if x != p.position),
                                                                      key=p.overall_at, reverse=True)[:3]],
            "traits": _trait_labels(p), "explain": [list(x) for x in _safe(lambda: traits.explain(p), [])], "persona": personas,
            "morale": round(mv), "mood": morale.word(mv),
            "lately": [f"{why} ({d:+d})" for _, d, why in p.__dict__.get("mood_log", [])[-3:] if d][::-1],
            "school": compliance.gpa_word(compliance.gpa(p)),
            "inj": injuries.status_text(p) if hurt else "", "nil": finance.player_nil(p),
            "portal": ctx["portal"].get(id(p), ["", ""]), "staff": staff,
            "stats": _stat_line(p), "season": season, "career": career, "gp": p.games_played,
            "cgp": p.career_games, "timeline": timeline}


def _roster_private(lg, t):
    import depth_staff
    import practice
    import transfer_watch as tw
    from models import POSITIONS
    ctx = {"prac": _safe(lambda: practice.run(lg, t), {}) or {}, "starts": _safe(lambda: practice.starter_counts(t), {}) or {},
           "depth": True, "portal": {}}
    ctx["staffOrder"] = {pos: _safe(lambda pos=pos: depth_staff.order(lg, t, pos), []) for pos in POSITIONS}
    for _, p, name, _c in _safe(lambda: tw._rows(lg, t, True), []):
        ctx["portal"][id(p)] = [name, _safe(lambda p=p: tw._why(t, p), "")]
    out = []
    for pos in POSITIONS:
        for i, p in enumerate(t.players_at(pos)):
            out.append(_player_private(lg, t, p, pos, i, ctx))
    return out


def _film(lg, t, opp):
    """The opponent film screen as data: tendencies, the staff's tips, and their best players in words."""
    import playbook as pb
    import practice
    import scout
    import staff as sf
    from career import MAN_CALLS, PRESSURE_CALLS, _tempo_word
    oc_, dc_ = sf.play_caller(opp, "off"), sf.play_caller(opp, "def")
    off_s, def_s = oc_.offense_scheme, dc_.defense_scheme
    spec = pb.OFFENSE_SCHEMES.get(off_s, {"run": 0.5, "tempo": 26})
    calls = pb.DEFENSE_SCHEMES.get(def_s, {})
    tot = sum(calls.values()) or 1
    press = sum(v for kk, v in calls.items() if kk in PRESSURE_CALLS) / tot
    man = sum(v for kk, v in calls.items() if kk in MAN_CALLS) / tot
    aggr = sf.aggression(opp, "off")
    tips = []
    if spec["run"] >= 0.6:
        tips.append("they'll run it: an extra man in the box")
    elif spec["run"] <= 0.4:
        tips.append("they'll throw it: keep two safeties deep")
    if press >= 0.3:
        tips.append("they bring pressure: quick game and hot routes")
    elif man >= 0.5:
        tips.append("they play man: rub routes and your best receiver on their worst corner")
    else:
        tips.append("they sit in zone: take the underneath stuff and stay patient")
    starters = [p for grp in opp.starters().values() for p in grp if p.position not in ("K", "P")]
    best = [{"p": p.position, "n": p.name, "yr": p.class_label, "looks": scout.ovr_word(p.overall),
             "film": _safe(lambda p=p: practice.report(p, lg.week, film=True), "")}
            for p in sorted(starters, key=lambda x: -x.overall)[:8]]
    return {"team": scout._w(scout.TEAM, opp.team_ovr),
            "offense": f"{off_s}: runs about {spec['run'] * 100:.0f}% of the time, {_tempo_word(spec['tempo'])}, "
                       + ("goes for it on fourth down" if aggr >= 65 else "punts it away" if aggr <= 35 else "picks its fourth downs"),
            "defense": f"{def_s}: pressure on about {press * 100:.0f}% of snaps, {'man' if man >= 0.5 else 'zone'}-first ({man * 100:.0f}% man)",
            "tips": tips, "best": best}


def team_private(lg, t):
    import coach_screens
    import commissioner as cm
    import depth
    import finance
    import finance_screens
    import gui_data
    import orders
    import personalities
    import practice
    import recruit_plus as rp
    import recruiting_screens as rs
    import sideline
    import staff
    import staff_room
    import transfer_watch
    import week
    cyc = lg.recruiting
    row = cm.team_row(lg, t)
    stand = orders.standing(lg, t)
    # recruits this staff knows something about
    known = {id(r) for r in t.recruiting_targets}
    for r in cyc.pool:
        if t in r.offers or r.scout.get(t, 0) > 0 or r.committed_to is t:
            known.add(id(r))
    for e in rp.queue(cyc, t):
        known.add(id(e["r"]))
    recruits = [_recruit_private(lg, t, r) for r in cyc.pool if id(r) in known]
    queue = [{"rid": _pid(lg, e["r"].player), "act": e["a"], "rule": e["rule"], "n": e.get("n", 0), "pitch": e.get("pitch") or "auto",
              "last": list(e["last"]) if e.get("last") else None, "runs": e.get("runs", 0)} for e in rp.queue(cyc, t)]
    summ = rp.S(cyc)["summary"].get(t) or {}
    last_week = {"week": summ.get("week"), "ran": [list(x[:3]) for x in summ.get("ran", [])],
                 "cut": [list(x) for x in summ.get("cut", [])], "done": [list(x) for x in summ.get("done", [])]}
    homes = [{"week": g.week, "opp": g.away.school} for wk in range(lg.week + 1, 14)
             for g in lg.schedule.get(wk, []) if g.home is t and not g.played]
    g = week.next_game(lg, t)
    nxt = None
    if g is not None:
        opp = g.opponent_of(t)
        rec_off, rec_def, lines = _safe(lambda: sideline.recommend(t, opp), ("balanced", "balanced", []))
        with words_only():
            card = _safe(lambda: gui_data.next_card(lg, t), {}) or {}
        card.pop("oppColor", None)
        card.pop("wp", None)
        card.pop("wpBand", None)
        nxt = {"week": g.week, "opp": opp.school, "oppId": slug(opp.school), "site": "home" if g.home is t else
               ("neutral" if g.neutral else "away"), "recOff": rec_off, "recDef": rec_def,
               "film": [str(x) for x in (lines or [])][:4], "card": card,
               "scout": _safe(lambda: _film(lg, t, opp), None)}
    calls = _safe(lambda: staff.calls(t), {"off": "HC", "def": "HC"})
    starters = _safe(lambda: depth.starters(t), {})
    depth_now = {pos: [_pid(lg, p) for p in t.players_at(pos)] for pos in __import__("models").POSITIONS}
    costs = {a: rp.action_cost(t, a) for a in __import__("recruiting_data").ACTIONS}
    commits = cyc.commitments(t)
    battles = [[pos, txt] for pos, _a, _b, txt in _safe(lambda: practice.battles(lg, t), [])]
    rec = _safe(lambda: practice.recommend(lg, t), {}) or {}
    starts = _safe(lambda: practice.starter_counts(t), {}) or {}
    ideas = []
    for pos, room in rec.items():
        n = starts.get(pos, 1)
        cur = t.players_at(pos)[:n]
        outs = [q for q in cur if q not in room[:n]]
        for p in room[:n]:
            if p not in cur:
                o = outs.pop(0) if outs else None
                ideas.append(f"{pos}: start {p.name}" + (f" over {o.last_name}" if o else ""))
    reports = {
        "program": capture(lg, t, coach_screens.program_view, lg, t),
        "staff": capture(lg, t, staff_room._show, lg, t),
        "budget": capture(lg, t, finance_screens.budget_screen, lg, t),
        "facilities": capture(lg, t, finance_screens.facilities_screen, lg, t),
        "locker": capture(lg, t, personalities.locker_room, lg, t),
        "portal": capture(lg, t, transfer_watch.screen, lg, t),
    }
    return {
        "team": t.school, "id": slug(t.school), "owner": row.get("owner"), "cycle": cm.state(lg)["cycle"]["n"] + 1,
        "league": cm.state(lg)["league_id"], "secret": row["secret"],
        "coach": _safe(lambda: gui_data.coach_card(lg, t), {}),
        "card": _card(lg, t, drop=("color", "mode", "words")),
        "program": _safe(lambda: gui_data.program_card(lg, t), {}),
        "roster": _roster_private(lg, t),
        "practice": {"battles": battles, "ideas": ideas},
        "reports": reports,
        "recruiting": {"hours": _hours_next(lg, t), "costs": costs, "board": [_pid(lg, r.player) for r in t.recruiting_targets],
                       "known": recruits, "queue": queue, "auto": rp.autopilot(cyc, t), "lastWeek": last_week,
                       "homeGames": homes, "nilLeft": _safe(lambda: finance.available(lg, t), 0),
                       "pwoOpen": lg.week + 1 >= 8, "classSize": len(commits),
                       "class": {"rank": cyc.class_rank(t), "cap": _safe(lambda: __import__("compliance").class_cap(t, lg), None),
                                 "avg": round(sum(r.stars for r in commits) / len(commits), 2) if commits else 0,
                                 "needs": _safe(lambda: rs._needs_line(lg, t), ""),
                                 "commits": [_pid(lg, r.player) for r in commits]},
                       "scan": _scan(lg, t)},
        "gameday": {"next": nxt, "plan": stand.get("plan"), "calls": calls,
                    "oc": getattr(getattr(t, "oc", None), "name", None), "dc": getattr(getattr(t, "dc", None), "name", None),
                    "depth": depth_now, "locks": stand.get("depth") or {}, "starters": starters},
        "jobs": _safe(lambda: __import__("job_market").private_jobs(lg, t), {}),
        "staff": _safe(lambda: __import__("member_offseason").staff_view(lg, t), {}),
        "money": _safe(lambda: __import__("member_offseason").money_view(lg, t), {}),
        "seasonEnd": _safe(lambda: __import__("member_offseason").nil_view(lg, t), {}),
        "portal": _safe(lambda: __import__("comm_offseason").portal_view(lg, t), {}),
        "rosterWeek": _safe(lambda: __import__("comm_offseason").roster_view(lg, t), {}),
        "spring": t.__dict__.get("spring_report") if (t.__dict__.get("spring_report") or {}).get("year") == lg.year else None,
        "missed": row.get("missed", 0),
    }
