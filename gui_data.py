"""
gui_data.py — Everything the desktop window's sidebar shows, as plain data.

play.py serves this as JSON; gui/app.js draws it. Each section is built on its
own and fails on its own (the game may be mid-update), so one bad read never
blanks the sidebar. Coach Career keeps its no-numbers rule: ratings and odds
come through as words.
"""
import re

TAB_KEYS = {"home": "1", "schedule": "2", "team": "3", "recruiting": "4", "rankings": "5", "coach": "6",
            "media": "7", "system": "8"}


def _ansi(code):
    """An ANSI color code as something the window can map: {"c": 93} or {"x": 214}."""
    m = re.search(r"38;5;(\d+)", code or "")
    if m:
        return {"x": int(m.group(1))}
    m = re.search(r"\[(\d+)m", code or "")
    return {"c": int(m.group(1))} if m else {"c": 97}


def _safe(out, key, fn):
    try:
        v = fn()
        if v is not None:
            out[key] = v
    except Exception as e:                               # mid-update: skip this section this time
        out.setdefault("_errors", []).append(f"{key}: {e}")


def _rank(lg, t):
    try:
        return lg.rankings.rank_of(t)
    except Exception:
        return None


def _cfp(lg, t):
    c = getattr(lg, "committee", None)
    if c is not None and getattr(c, "released", False) and getattr(c, "year", None) == lg.year:
        try:
            return c.rank_of(t)
        except Exception:
            return None
    return None


def _words(lg, who=None):
    """Words, not numbers? (Coach Career; in spectator mode, the team you follow.)"""
    import scout
    if who is None:
        import dashboard
        who = dashboard.focus_team(lg)
    return scout.hidden(lg, who)


def _team_word(lg, v, who=None):
    import scout
    return scout._w(scout.TEAM, v) if _words(lg, who) else v


# ═══ Sections ═══════════════════════════════════════════════════════════════

def team_card(lg, team):
    played = [g for g in lg.team_games(team) if g.played]
    form = []
    for g in played[-5:]:
        form.append({"r": "W" if g.winner is team else "L", "s": f"{g.score_for(team)}-{g.score_for(g.opponent_of(team))}",
                     "o": g.opponent_of(team).school})
    streak = ""
    if played:
        last = played[-1].winner is team
        n = 0
        for g in reversed(played):
            if (g.winner is team) == last:
                n += 1
            else:
                break
        streak = f"{'W' if last else 'L'}{n}"
    pf = sum(g.score_for(team) for g in played)
    pa = sum(g.score_for(g.opponent_of(team)) for g in played)
    ranks = []
    for g in played:
        r = (getattr(g, "ranks", None) or {}).get(team)
        ranks.append(r)
    now = _rank(lg, team)
    import scout
    mode = getattr(lg, "mode", None)
    total = 13
    return {
        "school": team.school, "nickname": team.nickname, "conference": team.conference,
        "confName": lg.conference_full_name(team.conference) or team.conference,
        "color": _ansi(lg.conference_color(team.conference)), "rank": now, "cfp": _cfp(lg, team),
        "record": team.record, "confRecord": team.conf_record, "streak": streak, "form": form,
        "pf": pf, "pa": pa, "games": len(played), "rankHistory": ranks + ([now] if not lg.season_complete else []),
        "year": lg.year, "when": lg.week_name(lg.week) if lg.week else "Preseason",
        "progress": min(1.0, lg.week / total) if not lg.season_complete else 1.0,
        "complete": lg.season_complete,
        "mode": "Coach Career" if mode == "career" else "Athletic Director" if mode == "ad" else "Spectator",
        "stadium": team.stadium, "chant": team.chant,
        "ovr": _team_word(lg, team.team_ovr), "off": _team_word(lg, team.offense_ovr),
        "def": _team_word(lg, team.defense_ovr), "words": _words(lg),
        "prestige": round(team.prestige),
    }


def next_card(lg, team):
    import dashboard
    g = dashboard.next_game(lg, team)
    if g is None:
        return None
    opp = g.opponent_of(team)
    home = g.home is team
    site = "vs" if home or g.neutral else "at"
    out = {"site": site, "opp": opp.school, "oppNick": opp.nickname, "oppRank": _rank(lg, opp),
           "oppRecord": opp.record, "oppConf": "FCS" if getattr(opp, "fcs", False) else opp.conference,
           "oppColor": _ansi(lg.conference_color(opp.conference)),
           "label": g.game_type if g.game_type != "Regular Season" else lg.week_name(g.week),
           "venue": (g.venue.split(",")[0] if g.neutral and getattr(g, "venue", None) else g.home.stadium)}
    try:
        import broadcast
        out["kick"] = broadcast.when(g)
    except Exception:
        pass
    import carousel as cz
    import scout
    wp = cz.win_prob(team, opp, 0 if g.neutral else (1 if home else -1))
    wp = min(0.99, max(0.01, wp))
    out["wp"] = None if _words(lg) else round(wp, 3)
    out["wpBand"] = round(wp, 2)                        # drives the gauge color, even in words mode
    out["odds"] = scout.odds(wp, lg, team).replace("you're ", "").replace("you win this ", "").replace(" of the time", "")
    from commentary import rivalry_name
    out["rivalry"] = rivalry_name(team, opp) or ""
    try:
        import rivalries
        s = rivalries.series(lg, team, opp)
        if s.n:
            out["series"] = s.record_str()
            m = s.last
            out["lastMeeting"] = f"{m.year}: {m.winner} {m.wscore}-{m.lscore}"
        if s.trophy:
            out["trophy"] = s.trophy
    except Exception:
        pass
    if not g.neutral:
        import stadium
        out["toughRank"] = stadium.rank_of(lg, g.home)
        out["noise"] = stadium.noise_word(stadium.noise_rating(g.home))
    out["us"] = _team_word(lg, team.team_ovr)
    out["them"] = _team_word(lg, opp.team_ovr, opp)
    try:
        import weather
        f = weather.forecast(g, lg)
        if f["lead"] <= 2:
            if f["indoor"]:
                out["forecast"] = "🏟 Indoors"
            else:
                icon = ("❄" if f["ptype"] in ("snow", "mix") else "⛈" if f["ptype"] == "storms" else "🌧") \
                    if f["pop"] >= 40 else "💨" if f["wind"][1] >= 20 else "☁" if f["pop"] >= 20 else \
                    "🌙" if f["sky"] == "clear" else "☀"
                out["forecast"] = f"{icon} {f['temp']}° · {f['headline']} · {f['pop']}%"
            out["forecastSev"] = f["severity"]
    except Exception:
        pass
    return out


def last_card(lg, team):
    import dashboard
    g = dashboard.last_game(lg, team)
    if g is None:
        return None
    opp = g.opponent_of(team)
    return {"won": g.winner is team, "us": g.score_for(team), "them": g.score_for(opp), "opp": opp.school,
            "oppRank": (getattr(g, "ranks", None) or {}).get(opp), "site": "vs" if g.home is team or g.neutral else "at",
            "label": g.game_type if g.game_type != "Regular Season" else lg.week_name(g.week)}


def coach_card(lg, team):
    import carousel as cz
    import finance as fi
    c = team.coach
    if c is None:
        return {"open": True}
    out = {"name": c.name, "age": c.age, "interim": cz.is_interim(c), "you": getattr(c, "is_user", False)}
    heat = round(getattr(c, "seat", 0))
    out.update(seat=heat, seatLabel=cz.seat_label(heat), seatMove=heat - round(getattr(c, "seat_prev", heat)))
    k = fi.contract(c)
    if k:
        out["contract"] = f"{fi.money(k['salary'])}/yr through {k['end']}"
    out["ad"] = f"{team.ad['name']} · {cz.AD_STYLES[team.ad['style']][0]}"
    goals = []
    for g in getattr(team, "goals", [])[:5]:
        status, x = cz.goal_status(team, c, g, lg.year)
        goals.append({"text": g.short, "status": status or "open",
                      "note": (f"met {x}" if status == "met" else "missed" if status == "failed"
                               else f"{x} season{'s' if x != 1 else ''} left" if isinstance(x, int) else "")})
    out["goals"] = goals
    if out["you"]:
        import people
        import skills
        out["inbox"] = people.unread(lg)
        out["replies"] = len(people.waiting(lg))
        out["points"] = skills._st(c).get("points", 0)
        out["bank"] = fi.money(getattr(c, "bank", 0))
        want = {id(m) for m in people.waiting(lg)}
        out["mail"] = [{"from": people.sender_label(m, short=True), "subject": m["subject"], "unread": not m["read"],
                        "reply": id(m) in want}
                       for m in list(reversed(people.inbox(lg)))[:4]]
    return out


def ad_card(lg):
    if getattr(lg, "mode", None) != "ad" or not getattr(lg, "ad_user", None):
        return None
    au = lg.ad_user
    return {"name": au["name"], "board": round(au["board"]), "fans": round(au["fans"]), "boosters": round(au["boosters"])}


def _book_rank(lg, b):
    import regulars as rg
    if not b.__dict__.get("regulars"):
        return ""
    rk, n = rg.your_rank(b, lg)
    from book_screens import _ord
    return f"{_ord(rk)} of {n} at the table"


def book_card(lg):
    """The Window (spectator mode): bankroll, trend, what's live."""
    if getattr(lg, "mode", None) != "spectator":
        return None
    import sportsbook as sb
    b = sb.get(lg, create=False)
    if b is None or not b.welcomed:
        return {"fresh": True}
    d = b.bank - b.start - b.reloads * sb.RELOAD
    op = sorted(b.open_bets, key=lambda x: (x.kind == "future", x.id))
    return {"bank": sb.money(b.bank), "delta": sb.money(d, sign=True), "up": d >= 0,
            "spark": [round(x[2], 2) for x in b.ledger[-30:]] + [round(b.bank, 2)],
            "open": len(op), "risk": sb.money(b.at_risk()), "toWin": sb.money(b.to_win_open()),
            "unseen": len(b.unseen),
            "rank": _book_rank(lg, b),
            "bets": [{"t": x.title(), "o": sb.fmt_odds(x.odds), "s": sb.money(x.stake)} for x in op[:5]],
            "more": max(0, len(op) - 5)}


def program_card(lg, team):
    import facilities as fa
    import finance as fi
    import stadium
    f = fa.ensure(team)
    stadium.ensure(team)
    return {"prestige": round(team.prestige), "budget": fi.money(fi.budget(team)),
            "nil": fi.money(fi.available(lg, team)),
            "facilities": [{"k": "Recruiting", "v": f["recruiting"]}, {"k": "Training", "v": f["training"]},
                           {"k": "Stadium", "v": f["stadium"]}],
            "capacity": team.capacity, "noise": stadium.noise_word(stadium.noise_rating(team)),
            "noiseV": stadium.noise_rating(team), "tough": stadium.rank_of(lg, team),
            "fund": fi.money(stadium.fund(team)),
            "project": (stadium.tier_name(team.stad["project"]["key"], team.stad["project"]["tier"])
                        + f" · opens {team.stad['project']['done'] + 1}") if team.stad.get("project") else ""}


def recruiting_card(lg, team):
    cyc = lg.recruiting
    commits = cyc.commitments(team)
    out = {"rank": cyc.class_rank(team), "commits": len(commits),
           "stars": round(sum(r.stars for r in commits) / len(commits), 1) if commits else 0,
           "top": [{"name": r.name, "pos": r.position, "stars": r.stars}
                   for r in sorted(commits, key=lambda r: r.national_rank)[:6]]}
    if getattr(lg, "mode", None) == "career" and team is getattr(lg, "user_team", None):
        out["hours"] = cyc.remaining_hours(team)
        out["hoursTotal"] = cyc.hours_for(team)
        out["board"] = len(getattr(team, "recruiting_targets", []))
        import recruit_plus as rp
        steps, _ = rp.plan(cyc, team)
        out["queue"] = [{"a": rp.ACTIONS[e["a"]][0], "name": e["r"].player.name, "runs": run,
                         "status": st} for e, st, c, run in steps[:8]]
        out["queueLen"] = len(steps)
        out["queueRuns"] = sum(1 for *_, run in steps if run)
        out["queueCut"] = sum(1 for _, st, _, _ in steps if st.startswith("cut"))
        out["visits"] = sorted(({"name": r.player.name, "week": w, "stars": r.stars} for r in cyc.pool
                                for t, w in rp.ov_of(r).items() if t is team and w >= lg.week and not r.signed),
                               key=lambda x: x["week"])[:5]
    for x, r in zip(out["top"], sorted(commits, key=lambda r: r.national_rank)[:6]):
        import recruit_plus as rp
        x["kind"] = rp.commit_word(r)
    return out


def injuries(lg, team):
    from injuries import status_text
    import scout
    out = []
    for p in team.injured()[:10]:
        out.append({"id": str(id(p)), "name": p.name, "pos": p.position, "status": status_text(p, short=True),
                    "starter": p in [x for grp in team.starters().values() for x in grp]})
    return out


def leaders(lg, team):
    fresh = not any(p.season_stats.get(k, 0) for p in team.roster for k in ("pass_yds", "rush_yds", "rec_yds", "tkl"))
    stat = (lambda p, k: (p.yearly_stats.get(lg.year - 1) or {}).get(k, 0)) if fresh else \
        (lambda p, k: p.season_stats.get(k, 0))
    rows = []
    for label, key, unit in (("Passing", "pass_yds", "yds"), ("Rushing", "rush_yds", "yds"),
                             ("Receiving", "rec_yds", "yds"), ("Tackles", "tkl", ""), ("Sacks", "sack", ""),
                             ("Interceptions", "int", "")):
        best = max(team.roster, key=lambda p: stat(p, key), default=None)
        if best is None or not stat(best, key):
            continue
        extra = ""
        if key == "pass_yds":
            extra = f"{stat(best, 'pass_td')} TD, {stat(best, 'pass_int')} INT"
        elif key == "rush_yds":
            extra = f"{stat(best, 'rush_td')} TD"
        elif key == "rec_yds":
            extra = f"{stat(best, 'rec')} rec, {stat(best, 'rec_td')} TD"
        v = stat(best, key)
        rows.append({"label": label, "id": str(id(best)), "name": best.name, "pos": best.position,
                     "value": f"{v:,}" + (f" {unit}" if unit else ""), "extra": extra})
    return {"rows": rows, "lastYear": fresh}


def lineup(lg, team):
    import scout
    import depth
    counts = depth.starters(team)
    out = []
    for pos in ("QB", "RB", "WR", "TE", "OL", "DL", "LB", "CB", "S", "K", "P"):
        ranked = team.players_at(pos)
        n = counts.get(pos, 1)
        healthy = [p for p in ranked if getattr(p, "inj_games", 0) <= 0]
        starters_on_chart = {id(p) for p in ranked[:n]}
        for p in (healthy + [p for p in ranked if p not in healthy])[:n]:
            out.append({"id": str(id(p)), "pos": pos, "name": p.short_name, "num": p.number,
                        "yr": p.class_label,
                        "ovr": scout.OVR_SHORT[scout.ovr_word(p.overall)] if _words(lg) else p.overall,
                        "ovrLong": scout.ovr_word(p.overall) if _words(lg) else "",
                        "hurt": getattr(p, "inj_games", 0) > 0,
                        "fill": id(p) not in starters_on_chart})         # filling in for a hurt starter
    return out


def schedule(lg, team):
    rows = []
    nxt = None
    for g in lg.team_games(team):
        opp = g.opponent_of(team)
        row = {"wk": lg.week_name(g.week) if g.week <= 13 else g.game_type, "site": "vs" if g.home is team or g.neutral else "at",
               "opp": opp.school, "oppRank": (getattr(g, "ranks", None) or {}).get(opp) if g.played else _rank(lg, opp),
               "played": g.played, "conf": bool(getattr(g, "conference_game", False))}
        if g.played:
            row.update(won=g.winner is team, score=f"{g.score_for(team)}-{g.score_for(opp)}")
        elif nxt is None:
            row["next"] = True
            nxt = g
        rows.append(row)
    return rows


def sos_card(lg, team):
    import sos
    row = sos.of(lg, team)
    if not row or not row.get("rank_full"):
        return None
    return {"rank": row["rank_full"], "word": sos.word(row["rank_full"])[0],
            "played": row.get("rank_played"), "ahead": row.get("rank_ahead"), "opp": sos.opp_record(row)}


def standings(lg, team):
    conf = [t for t in lg.teams if t.conference == team.conference]
    conf.sort(key=lambda t: (-t.conf_win_pct, -t.conf_wins, -t.win_pct, -t.prestige))
    return {"conf": team.conference, "rows": [{"school": t.school, "conf": t.conf_record, "all": t.record,
                                               "rank": _rank(lg, t), "me": t is team} for t in conf]}


def top25(lg, team):
    r = lg.rankings
    rows = []
    for i, t in enumerate(r.order[:25], 1):
        before = r.previous_rank(t)
        rows.append({"rank": i, "school": t.school, "record": t.record, "me": t is team,
                     "move": (before - i) if before else None, "new": before is None and r.week > 0,
                     "color": _ansi(lg.conference_color(t.conference))})
    c = getattr(lg, "committee", None)
    cfp = []
    if c is not None and getattr(c, "released", False) and getattr(c, "year", None) == lg.year:
        cfp = [{"rank": i, "school": t.school, "me": t is team} for i, t in enumerate(c.order[:12], 1)]
    heis = [{"id": str(id(p)), "name": p.name, "pos": p.position, "school": p.team.school}
            for p, _, _ in lg.rankings.heisman[:5]]
    import stadium
    tough = [{"school": t.school, "stadium": t.stadium, "score": s, "me": t is team}
             for t, s, _ in stadium.ranking(lg)[:5]]
    return {"poll": rows, "label": "Preseason" if r.week == 0 else f"After week {r.week}", "cfp": cfp,
            "heisman": heis, "tough": tough}


def news(lg, team):
    import dashboard
    col = {"\x1b[92m": "good", "\x1b[91m": "bad", "\x1b[93m": "gold", "\x1b[96m": "info", "\x1b[95m": "purple"}
    heads = [{"text": t, "tone": col.get(c, "muted")} for c, t in dashboard.headlines(lg, team, n=10)]
    log = [{"year": y, "text": t} for y, t in list(getattr(lg, "career_log", []))[-8:]][::-1]
    return {"headlines": heads, "log": log}


def scores(lg, team):
    """The week's biggest results around the country (or next week's biggest games, before they're played)."""
    wk = lg.week
    games = [g for g in lg.schedule.get(wk, []) if g.played]
    upcoming = False
    if not games:
        games = [g for g in lg.schedule.get(wk + 1, [])]
        upcoming = True
    def rk(g, t):
        return (getattr(g, "ranks", None) or {}).get(t) if not upcoming else _rank(lg, t)
    def weight(g):
        r = [x for x in (rk(g, g.home), rk(g, g.away)) if x]
        return (0 if team in (g.home, g.away) else 1, min(r) if r else 99, -(len(r)))
    rows = []
    for g in sorted(games, key=weight)[:8]:
        row = {"away": g.away.school, "home": g.home.school, "ar": rk(g, g.away), "hr": rk(g, g.home),
               "neutral": bool(g.neutral), "mine": team in (g.home, g.away)}
        if not upcoming:
            row.update(a=g.away_score, h=g.home_score, awayWon=g.winner is g.away)
            wr, lr = rk(g, g.winner), rk(g, g.loser)
            row["upset"] = bool(lr and (not wr or wr > lr + 5))
        rows.append(row)
    return {"label": (lg.week_name(wk + 1) + " — coming up") if upcoming else lg.week_name(wk), "rows": rows,
            "upcoming": upcoming}


def hot_seats(lg, team):
    import carousel as cz
    cs = [t.coach for t in lg.teams if t.coach is not None and not cz.is_interim(t.coach)]
    cs.sort(key=lambda c: -getattr(c, "seat", 0))
    return [{"name": c.name, "school": c.team.school, "seat": round(c.seat), "label": cz.seat_label(round(c.seat)),
             "you": getattr(c, "is_user", False)} for c in cs[:6]]


def recruit_news(lg, team):
    meta = getattr(lg.recruiting, "news_meta", {})
    out = []
    for week, kind, text in getattr(lg.recruiting, "news", [])[:40]:
        m = meta.get(text)
        stars = m[2] if m else None
        mine = bool(m and m[1] == team.school)
        if mine or (stars or 0) >= 4 or m is None:
            out.append({"text": text, "mine": mine, "stars": stars or 0})
        if len(out) >= 7:
            break
    return out


def actions(lg):
    """Shortcuts the sidebar can run — only while the game sits on the dashboard. Each is a list of keys."""
    career = getattr(lg, "mode", None) == "career" and getattr(lg, "user_coach", None) is not None
    ad = getattr(lg, "mode", None) == "ad" and getattr(lg, "ad_user", None)
    done = lg.season_complete
    label = "Advance to the offseason" if done else "Start the season" if lg.week == 0 else "Play next week"
    acts = [{"id": "advance", "label": label, "keys": ["a"],
             "icon": "▶", "primary": True},
            {"id": "save", "label": "Save", "keys": ["v"], "icon": "💾"}]
    if career:
        acts += [{"id": "inbox", "label": "Inbox", "keys": ["i"], "icon": "✉"},
                 {"id": "depth", "label": "Depth chart", "keys": ["3", "h"], "icon": "▤"},
                 {"id": "practice", "label": "Practice report", "keys": ["3", "p"], "icon": "⏱"},
                 {"id": "recruit", "label": "Recruiting hub", "keys": ["4", "r"], "icon": "★"},
                 {"id": "orders", "label": "Standing orders", "keys": ["4", "r", "q"], "icon": "⟳"},
                 {"id": "warroom", "label": "War room", "keys": ["4", "r", "w"], "icon": "⚔"},
                 {"id": "visits", "label": "Official visits", "keys": ["4", "r", "v"], "icon": "🏟"},
                 {"id": "tree", "label": "Coaching tree", "keys": ["6", "t"], "icon": "⚑"},
                 {"id": "staff", "label": "My staff", "keys": ["6", "s"], "icon": "☷"}]
    if ad:
        acts += [{"id": "office", "label": "AD office", "keys": ["c"], "icon": "🏛"}]
    if getattr(lg, "mode", None) == "spectator":
        acts += [{"id": "book", "label": "Sportsbook", "keys": ["1", "b"], "icon": "$", "primary": False}]
    acts += [{"id": "roster", "label": "Roster", "keys": ["3", "r"], "icon": "☰"},
             {"id": "teampage", "label": "Team page", "keys": ["3", "t"], "icon": "🏈"},
             {"id": "facilities", "label": "Facilities", "keys": ["3", "t", "f"], "icon": "🏟"},
             {"id": "budget", "label": "Budget & NIL", "keys": ["3", "$"], "icon": "$"},
             {"id": "schedule", "label": "Schedule", "keys": ["2", "s"], "icon": "📅"},
             {"id": "scores", "label": "Scoreboard", "keys": ["2", "w"], "icon": "▦"},
             {"id": "standings", "label": "Standings", "keys": ["2", "t"], "icon": "≡"},
             {"id": "poll", "label": "Media Top 25", "keys": ["5", "t"], "icon": "#"},
             {"id": "cfp", "label": "NP rankings", "keys": ["5", "p"], "icon": "◆"},
             {"id": "heisman", "label": "Golden Helmet race", "keys": ["5", "h"], "icon": "🏆"},
             {"id": "tough", "label": "Toughest places", "keys": ["5", "s"], "icon": "📣"},
             {"id": "portal", "label": "Transfer portal", "keys": ["4", "p"], "icon": "⇄"},
             {"id": "carousel", "label": "Coaching carousel", "keys": ["6", "k"], "icon": "↻"},
             {"id": "media", "label": "Media center", "keys": ["7", "m"], "icon": "🎙"},
             {"id": "weather", "label": "Weather center", "keys": ["2", "f"], "icon": "☂"},
             {"id": "manual", "label": "Manual", "keys": ["?"], "icon": "?"}]
    return acts


def snapshot(lg):
    """The whole sidebar."""
    import dashboard
    team = dashboard.focus_team(lg)
    out = {"ready": True}
    _safe(out, "team", lambda: team_card(lg, team))
    _safe(out, "next", lambda: next_card(lg, team))
    _safe(out, "last", lambda: last_card(lg, team))
    _safe(out, "coach", lambda: coach_card(lg, team))
    _safe(out, "ad", lambda: ad_card(lg))
    _safe(out, "book", lambda: book_card(lg))
    _safe(out, "program", lambda: program_card(lg, team))
    _safe(out, "recruiting", lambda: recruiting_card(lg, team))
    _safe(out, "injuries", lambda: injuries(lg, team))
    _safe(out, "leaders", lambda: leaders(lg, team))
    _safe(out, "lineup", lambda: lineup(lg, team))
    _safe(out, "schedule", lambda: schedule(lg, team))
    _safe(out, "sos", lambda: sos_card(lg, team))
    _safe(out, "standings", lambda: standings(lg, team))
    _safe(out, "top25", lambda: top25(lg, team))
    _safe(out, "news", lambda: news(lg, team))
    _safe(out, "scores", lambda: scores(lg, team))
    _safe(out, "hotseats", lambda: hot_seats(lg, team))
    _safe(out, "rnews", lambda: recruit_news(lg, team))
    _safe(out, "actions", lambda: actions(lg))
    out["atDash"] = bool(getattr(lg, "_gui_at_dash", False))
    return out
