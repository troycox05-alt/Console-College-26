"""
webview.py — The web app's native screens.

The game still prints every screen exactly as before (terminal, desktop window, phone). When it
runs behind the web app (mobile_web.py / play.py set HOOK), the screens below ALSO send their
data as JSON, and the page draws a real app screen from it instead of the text. Buttons on those
screens send the same keys the terminal uses, so the game can't tell the difference.

  view  — the screen that was just printed, as data (replaces the text above it)
  add   — something added to that screen (a line of the Saturday show, the picks table)

Text printed after a view (prompts, staff notes, play-by-play calls) still shows under it.
Nothing here may ever break the game: every builder swallows its own errors.
"""
import json
import re

HOOK = [None]                    # set by play.install(): fn(event_kind, json_text)
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def on():
    return HOOK[0] is not None


def plain(s):
    return _ANSI.sub("", str(s if s is not None else "")).replace("\u2063", "").strip()


def emit(kind, data, add=False):
    if HOOK[0] is None:
        return
    try:
        HOOK[0]("add" if add else "view", json.dumps({"kind": kind, "data": data}, default=str))
    except Exception:
        pass


def _lg():
    try:
        import scout
        return scout._LG[0]
    except Exception:
        return None


def _color(lg, team):
    try:
        import gui_data
        return gui_data._ansi(lg.conference_color(team.conference))
    except Exception:
        return None


def _try(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def pid(p):
    return str(id(p))


# ═══ The main screen ══════════════════════════════════════════════════════════

TAB_NAMES = ("Home", "Schedule", "Team", "Recruiting", "Rankings", "Coach", "Media", "System")
NATIVE_TABS = (1, 2, 3)


def home(league, team, tab):
    if not on() or tab not in NATIVE_TABS:
        return
    try:
        import gui_data as gd
        import preseason
        d = {"tab": tab, "tabs": TAB_NAMES}
        for k, fn in (("team", gd.team_card), ("next", gd.next_card), ("last", gd.last_card),
                      ("coach", gd.coach_card), ("standings", gd.standings), ("top25", gd.top25),
                      ("news", gd.news), ("schedule", gd.schedule), ("scores", gd.scores),
                      ("lineup", gd.lineup), ("leaders", gd.leaders), ("injuries", gd.injuries),
                      ("program", gd.program_card), ("recruiting", gd.recruiting_card), ("sos", gd.sos_card)):
            d[k] = _try(lambda fn=fn: fn(league, team))
        d["adv"] = "Advance to offseason" if league.season_complete else \
            "Preseason week" if preseason.needed(league) else f"Play {league.week_name(league.week + 1)}"
        d["career"] = getattr(league, "mode", None) == "career" and getattr(league, "user_coach", None) is not None
        try:
            from netplay import lobby
            d["online"] = bool(lobby.active(league))
        except Exception:
            d["online"] = False
        emit("home", d)
    except Exception:
        pass


# ═══ Roster and schedule ══════════════════════════════════════════════════════

def roster(league, team):
    if not on():
        return
    try:
        import finance as fi
        import scout
        from models import POSITIONS, POSITION_NAMES
        hide = scout.hidden(league)
        groups = []
        for pos in POSITIONS:
            players = team.players_at(pos)
            if not players:
                continue
            rows = []
            for i, p in enumerate(players):
                r = {"id": pid(p), "num": p.number, "name": p.name, "yr": p.class_label,
                     "ovr": plain(scout.ovr(p)) if hide else p.overall, "hurt": p.inj_games > 0,
                     "nil": fi.money(fi.player_nil(p)) if fi.player_nil(p) else "",
                     "tr": bool(getattr(p, "transfer_from", None)), "stars": getattr(p, "hs_stars", 0),
                     "ht": getattr(p, "height_str", ""), "wt": getattr(p, "weight", "")}
                if hide:
                    try:
                        import subprof
                        subs = sorted(subprof.all_values(p), key=lambda x: -x[2])
                        if subs:
                            r["best"], r["worst"] = subs[0][1].lower(), subs[-1][1].lower()
                    except Exception:
                        pass
                if p.inj_games > 0:
                    r["status"] = _try(lambda p=p: plain(__import__("injuries").status_text(p, short=True)), "hurt")
                rows.append(r)
            groups.append({"pos": pos, "name": POSITION_NAMES.get(pos, pos), "players": rows})
        emit("roster", {"school": team.full_name, "count": len(team.roster), "hide": hide,
                        "nil": fi.money(fi.roster_nil(team)), "budget": fi.money(fi.budget(team)),
                        "mine": getattr(league, "user_team", None) is team, "groups": groups})
    except Exception:
        pass


def schedule(league, team, year, rows, record, conf_record, sos_line):
    if not on():
        return
    emit("schedule", {"school": team.full_name, "year": year, "record": record, "confRecord": conf_record,
                      "sos": plain(sos_line), "rows": rows})


# ═══ The week before the game ═════════════════════════════════════════════════

def week(league, team, g, focus_label, focus_blurb, routine, routines, presser, film, inbox, injuries,
         plan, forecast, battles, banked):
    if not on():
        return
    try:
        import carousel as cz
        import scout
        opp = g.opponent_of(team)
        site = 0 if g.neutral else (1 if g.home is team else -1)
        wp = _try(lambda: min(0.99, max(0.01, cz.win_prob(team, opp, site, league))), 0.5)
        hide = scout.hidden(league)
        d = {"week": league.week_name(league.week + 1), "site": "vs" if g.home is team or g.neutral else "at",
             "us": {"school": team.school, "rank": league.rankings.rank_of(team), "record": team.record,
                    "color": _color(league, team), "ovr": plain(scout._w(scout.TEAM, team.team_ovr)) if hide else team.team_ovr},
             "them": {"school": opp.school, "rank": league.rankings.rank_of(opp), "record": opp.record,
                      "color": _color(league, opp), "ovr": plain(scout._w(scout.TEAM, opp.team_ovr)) if hide else opp.team_ovr,
                      "coach": opp.coach.name if opp.coach else "", "scheme": opp.coach.offense_scheme if opp.coach else ""},
             "wp": None if hide else round(wp, 3), "wpBand": round(wp, 2), "odds": plain(scout.odds(wp)),
             "rivalry": cz.PRIMARY_RIVAL.get(team.school) == opp.school,
             "forecast": plain(forecast), "film": [plain(x) for x in film], "inbox": inbox,
             "focus": focus_label, "focusBlurb": focus_blurb, "battles": battles,
             "presser": presser, "banked": banked, "injuries": [plain(x) for x in injuries],
             "plan": plain(plan), "routine": routine, "routines": routines}
        emit("week", d)
    except Exception:
        pass


def matchup(league, g, mine):
    if not on():
        return
    try:
        import broadcast
        import scout
        from commentary import rivalry_name
        teams = []
        for t in (g.away, g.home):
            hurt = [p for p in t.injured() if p in t.players_at(p.position)[:2]][:3]
            c = t.coach
            hide = scout.hidden(league, t)
            teams.append({"school": t.school, "full": t.full_name, "rank": league.rankings.rank_of(t),
                          "record": t.record, "conf": t.conference, "color": _color(league, t),
                          "ovr": plain(scout.team(t.team_ovr, who=t)) if hide else t.team_ovr,
                          "off": plain(scout.team_short(t.offense_ovr, who=t)) if hide else t.offense_ovr,
                          "def": plain(scout.team_short(t.defense_ovr, who=t)) if hide else t.defense_ovr,
                          "coach": c.name if c else "", "offScheme": c.offense_scheme if c else "",
                          "defScheme": c.defense_scheme if c else "",
                          "out": [f"{p.position} {p.last_name}" for p in hurt],
                          "mine": t is getattr(league, "user_team", None)})
        d = {"title": f"{league.year} · {league.week_name(league.week)}", "teams": teams,
             "neutral": bool(g.neutral), "slot": plain(_try(lambda: broadcast.when(g), "")),
             "venue": g.venue if g.neutral else f"{g.home.stadium} ({g.home.capacity:,})",
             "kind": g.game_type if g.game_type != "Regular Season" else
             ("Conference game" if g.conference_game else "Non-conference"),
             "rivalry": _try(lambda: rivalry_name(g.home, g.away), "") or "", "mine": bool(mine)}
        try:
            import rivalries
            s = rivalries.series(league, g.away, g.home)
            if s.n:
                d["series"] = s.record_str()
                d["last"] = f"{s.last.year}: {s.last.winner} {s.last.wscore}-{s.last.lscore}"
            if s.trophy:
                d["trophy"] = s.trophy
        except Exception:
            pass
        try:
            import carousel as cz
            me = getattr(league, "user_team", None)
            if me in (g.home, g.away):
                opp = g.opponent_of(me)
                wp = cz.win_prob(me, opp, 0 if g.neutral else (1 if g.home is me else -1))
                d["wpBand"] = round(min(0.99, max(0.01, wp)), 2)
                d["wp"] = None if scout.hidden(league) else d["wpBand"]
        except Exception:
            pass
        emit("matchup", d)
    except Exception:
        pass


# ═══ Game Day: the field ══════════════════════════════════════════════════════

def _clock(sec):
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def _dd(down, togo, yl):
    d = ("", "1st", "2nd", "3rd", "4th")[max(1, min(4, down or 1))]
    return f"{d} & Goal" if togo >= 100 - yl else f"{d} & {togo}"


def game(sim, ctl=None, side=None, narr=None):
    if not on():
        return
    try:
        import fieldview as fv
        lg = _lg()
        away, home, off = sim.away, sim.home, getattr(sim, "offense", None)

        def side_of(t):
            return {"school": t.school, "abbr": t.abbr, "score": sim.score[t],
                    "to": _try(lambda: sim.timeouts[t], 3), "color": _color(lg, t) if lg else None,
                    "rank": _try(lambda: lg.rankings.rank_of(t)) if lg else None, "ball": t is off}
        right = _try(lambda: fv.drives_right(sim, off), True)
        yl = sim.yardline
        d = {"away": side_of(away), "home": side_of(home),
             "q": f"Q{sim.quarter}" if sim.quarter <= 4 else f"OT{sim.quarter - 4}", "clock": _clock(sim.clock),
             "dd": _dd(sim.down, sim.togo, yl) if off is not None else "",
             "spot": _try(lambda: fv._spot_word(sim, yl, off), ""),
             "ball": yl if right else 100 - yl,
             "first": (min(100, yl + sim.togo) if right else max(0, 100 - yl - sim.togo)) if sim.togo < 100 - yl else None,
             "right": bool(right), "offense": "home" if off is home else "away"}
        dr = getattr(sim, "drive", None) or {}
        if dr.get("plays"):
            d["drive"] = {"plays": dr["plays"], "yds": yl - dr.get("start", yl),
                          "start": _try(lambda: fv._spot_word(sim, dr["start"], off), "")}
        log = list(getattr(narr if narr is not None else getattr(sim, "narr", None), "play_log", []) or [])
        d["plays"] = [{"q": f"Q{e['q']}" if e["q"] <= 4 else "OT", "clock": _clock(e["clock"]),
                       "dd": _dd(e["down"], e["togo"], e["yl"]) if e.get("down") is not None else "",
                       "off": e.get("off", ""), "text": plain(e["text"])} for e in log[-8:]][::-1]
        d["scoring"] = [{"q": f"Q{e[0]}" if e[0] <= 4 else "OT", "clock": _clock(e[1]), "team": e[2].abbr,
                         "what": plain(e[3])} for e in list(getattr(sim, "scoring", []))[-4:]][::-1]
        try:
            ts = sim.team_stats

            def st(t):
                s = ts[t]
                return {"yds": s["total_yds"], "rush": s["rush_yds"], "pass": s["pass_yds"],
                        "third": f"{s['third_conv']}/{s['third_att']}", "to": s["turnovers"], "top": _clock(s["top"])}
            d["stats"] = {"away": st(away), "home": st(home)}
        except Exception:
            pass
        try:
            import weather
            c = weather.now(sim)
            d["wx"] = "indoors" if c is None else f"{c['temp']}°" + (f" · wind {c['wind']}" if c["wind"] >= 8 else "")
        except Exception:
            pass
        if ctl is not None:
            try:
                import sideline
                d["clip"] = [x for x in (plain(ln) for ln in sideline.tablet_rows(sim, ctl, side)) if x][:9]
                d["clipSide"] = "Offense" if side == "off" else "Defense"
            except Exception:
                pass
        emit("game", d)
    except Exception:
        pass


# ═══ Game Day: the Saturday show ══════════════════════════════════════════════

def show_open(show_name, week, town, matchup, stadium):
    emit("show", {"name": show_name, "week": week, "town": town, "matchup": matchup, "stadium": stadium})


def say(who, label, text):
    emit("say", {"who": who, "label": label, "text": plain(text)}, add=True)


def picks(names, rows, note):
    emit("picks", {"names": names, "rows": rows, "note": plain(note)}, add=True)


# ═══ The player card ══════════════════════════════════════════════════════════

def player_data(league, p):
    """Everything on a player's card, as data (the pop-up card and the full-screen card)."""
    import scout
    import screens as sc
    from models import FUNDAMENTALS, FUNDAMENTAL_NAMES, POSITIONS, POSITION_NAMES
    hide = scout.hidden(league)
    team = p.team
    d = {"id": pid(p), "num": p.number, "name": p.name, "pos": p.position,
         "posName": POSITION_NAMES.get(p.position, p.position), "team": team.full_name if team else "",
         "color": _color(league, team) if team else None, "yr": p.class_label, "ht": p.height_str, "wt": p.weight,
         "hide": hide, "ovr": plain(scout.ovr(p)) if hide else p.overall, "hs": p.hs_stars,
         "dev": plain(sc._dev_grade(p)), "durability": p.durability.lower(),
         "generational": bool(getattr(p, "generational", False)), "transfer": sc._transfer_from(p) or ""}
    d["ceiling"] = _try(lambda: __import__("subprof").word(p.prof_ceiling) if hide else f"{p.prof_ceiling:.2f}", "")
    try:
        import finance as fi
        amt = fi.player_nil(p)
        d["nil"] = fi.money(amt) if amt else ""
    except Exception:
        pass
    try:
        import morale
        mv = morale.get(p)
        d["morale"] = {"v": round(mv), "word": morale.word(mv),
                       "log": [f"{why} ({dd:+d})" for _, dd, why in p.__dict__.get("mood_log", [])[-3:] if dd][::-1]}
    except Exception:
        pass
    try:
        import compliance
        gv = compliance.gpa(p)
        d["classroom"] = compliance.gpa_word(gv) + ("" if hide else f" ({gv:.2f} GPA)")
    except Exception:
        pass
    if p.inj_games > 0:
        d["injury"] = _try(lambda: plain(__import__("injuries").status_text(p)), "injured")
    d["traits"] = _try(lambda: [{"name": n, "why": plain(w)} for n, w in __import__("traits").explain(p)], [])
    # this season (or career) stats
    try:
        line, games, label = p.season_stats, p.games_played, f"{league.year} season"
        if not games and p.career_games:
            line, games, label = sc._career_line(p), p.career_games, "Career"
        if games:
            d["stats"] = {"label": label, "games": games,
                          "rows": [{"group": g, "cells": [[k, f"{v:g}" if isinstance(v, float) else str(v)] for k, v in cells]}
                                   for g, cells in sc._stat_rows(line, games)]}
    except Exception:
        pass
    # timeline
    try:
        years = sorted(set(p.events.keys()) | set(p.yearly_stats.keys()) | {y for y, _ in p.history})
        prev = next((o for y, o in reversed(p.history) if y < 2026), None)
        tl = []
        for yr in [y for y in years if y >= 2026]:
            ovr = next((o for y, o in p.history if y == yr), prev)
            delta = (ovr - prev) if (prev is not None and ovr is not None) else None
            prev = ovr or prev
            st = p.yearly_stats.get(yr) or {}
            bits = []
            if st.get("pass_yds"):
                bits.append(f"{st['pass_yds']} pass yds, {st['pass_td']} TD")
            if st.get("rush_yds"):
                bits.append(f"{st['rush_yds']} rush yds, {st['rush_td']} TD")
            if st.get("rec_yds"):
                bits.append(f"{st['rec_yds']} rec yds, {st['rec_td']} TD")
            if st.get("tkl"):
                bits.append(f"{st['tkl']} tkl, {st['sack']} sack, {st['int']} INT")
            tl.append({"year": yr, "ovr": (plain(scout.ovr(ovr)) if hide else ovr) if ovr else "",
                       "delta": None if hide else delta, "events": [plain(e) for e in p.events.get(yr, [])],
                       "stats": ", ".join(bits)})
        d["timeline"] = tl[::-1]
    except Exception:
        pass
    # skills
    try:
        import subprof
        d["skills"] = [{"label": lab, "v": round(v, 2), "word": plain(scout.sub(v, seed=p.name + k, width=1)).strip() if hide else ""}
                       for k, lab, v in subprof.all_values(p)]
        d["skillMax"] = __import__("models").PROFICIENCY_MAX if hasattr(__import__("models"), "PROFICIENCY_MAX") else 1.2
    except Exception:
        pass
    if hide:
        try:
            import practice
            d["report"] = plain(practice.report(p, league.week) or "")
            if p.team is getattr(league, "user_team", None):
                d["practice"] = plain(practice.run(league, p.team).get(id(p), ("", 0))[0])
        except Exception:
            pass
        d["fund"] = [{"name": FUNDAMENTAL_NAMES[f], "word": plain(scout.fund(p.fundamentals[f], width=1)).strip()} for f in FUNDAMENTALS]
        d["alts"] = [{"pos": x, "ovr": plain(scout.ovr(p.overall_at(x)))}
                     for x in sorted((x for x in POSITIONS if x != p.position), key=p.overall_at, reverse=True)[:3]]
    else:
        d["fund"] = [{"name": FUNDAMENTAL_NAMES[f], "raw": p.fundamentals[f], "applied": p.applied(f)} for f in FUNDAMENTALS]
        d["alts"] = [{"pos": x, "ovr": p.overall_at(x), "prof": round(p.proficiency_at(x), 2)}
                     for x in sorted(POSITIONS, key=p.proficiency_at, reverse=True)[:5]]
    return d


def player(league, p, room=None):
    if not on():
        return
    try:
        d = player_data(league, p)
        if room:
            d["room"] = room
        emit("player", d)
    except Exception:
        pass


def opts(title, options, note="", kind="opts"):
    """A set of choices on the current screen: [(key, label, detail)] → buttons."""
    emit(kind, {"title": plain(title), "note": plain(note),
                "options": [{"key": str(k), "label": plain(l), "detail": plain(d) if d else ""} for k, l, d in options]}, add=True)
