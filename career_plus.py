"""
career_plus.py — The season around your games (Coach Career).

  weekly(league, games)    after every week (played or simmed): storylines, alerts, achievements
  before(league)           a snapshot before you play the week …
  wrap(league, snap, g)    … and the Weekly Wrap after it: what your result changed
  report_card(league)      the AD's end-of-season report card
  selection_show(league)   Selection Day: the playoff field and the bowls, revealed
  bowl_week(league, g)     your bowl's week: the site, the lore, the opt-outs
  legacy_screen(league)    your legacy: trophy case, stops, achievements, jerseys, statues, your tree
  tree_screen(league)      your coaching tree: the assistants who worked for you, and where they are now
  nonconf_screen(league)   next season's non-conference schedule: philosophy, a marquee game, opponents
  story_start(...)         the story starts: The Rebuild, The Hot Seat, Replace a Legend
"""

from ui import (
    WIDTH,
    C,
    ask,
    clear,
    clip,
    columns,
    footer,
    key,
    pad,
    paint,
    panel,
    section,
    title_bar,
    truncate,
)


def mine(league):
    return getattr(league, "mode", None) == "career" and getattr(league, "user_team", None) is not None \
        and getattr(league, "user_coach", None) is not None


def _log(league, entry):
    league.__dict__.setdefault("career_log", []).append(entry)


def state(league):
    st = league.__dict__.setdefault("cplus", {})
    for k, v in (("stories", []), ("alerts", []), ("ach", {}), ("top3", {}), ("tree", {}), ("jerseys", []),
                 ("statues", []), ("nonconf", {}), ("seen", []), ("ovr_start", {}), ("flags", {})):
        st.setdefault(k, v)
    return st


def _story(league, kind, text, p=None):
    st = state(league)
    row = {"year": league.year, "week": league.week, "kind": kind, "text": text}
    if p is not None:
        row.update(who=p.name, pos=p.position)
    st["stories"].append(row)
    del st["stories"][:-1500]
    if p is not None:
        p.events[league.year].append(text)


def stories(league, year=None, week=None):
    return [s for s in state(league)["stories"] if (year is None or s["year"] == year)
            and (week is None or s["week"] == week)]


# ═══ Player storylines ═══════════════════════════════════════════════════════

BIG = (("pass_yds", 350, "throws for {v} yards"), ("pass_td", 5, "throws {v} touchdowns"),
       ("rush_yds", 175, "runs for {v} yards"), ("rush_td", 4, "runs for {v} touchdowns"),
       ("rec_yds", 170, "catches {n} balls for {v} yards"), ("rec_td", 3, "catches {v} touchdowns"),
       ("tkl", 14, "makes {v} tackles"), ("sack", 3, "gets to the quarterback {v} times"),
       ("int", 2, "picks off {v} passes"))
MILESTONES = (("pass_yds", 3000, "3,000 passing yards"), ("pass_td", 30, "30 touchdown passes"),
              ("rush_yds", 1000, "1,000 rushing yards"), ("rec_yds", 1000, "1,000 receiving yards"),
              ("rec", 75, "75 catches"), ("sack", 10, "10 sacks"), ("tkl", 100, "100 tackles"), ("int", 6, "6 interceptions"))


def _starters(team, pos):
    try:
        from models import STARTING_LINEUP
        return STARTING_LINEUP.get(pos, 1)
    except Exception:                                   # noqa: BLE001 — a lineup count never stops a story
        return 1


def _is_starter(team, p):
    room = list(team.players_at(p.position))
    return p in room and room.index(p) < _starters(team, p.position)


def _player_stories(league, team, games):
    st = state(league)
    flags = st["flags"]
    for g in games:
        if team not in (g.home, g.away) or not g.played or getattr(g, "box", None) is None:
            continue
        opp = g.opponent_of(team)
        told = 0
        for p, c in sorted(g.box.stats.items(), key=lambda kv: -(kv[1].get("pass_yds", 0) + kv[1].get("rush_yds", 0)
                                                                    + kv[1].get("rec_yds", 0) + 20 * kv[1].get("tkl", 0))):
            if p not in team.roster or told >= 2:
                continue
            for k, cut, how in BIG:
                v = c.get(k, 0)
                if v >= cut:
                    first = not flags.get(f"big:{p.name}:{team.school}")
                    flags[f"big:{p.name}:{team.school}"] = league.year
                    kind = "breakout" if first and (p.year <= 1 or not _is_starter(team, p)) else "big day"
                    lead = "Breakout: " if kind == "breakout" else ""
                    _story(league, kind, f"{lead}{p.position} {p.name} {how.format(v=v, n=c.get('rec', 0))} "
                                         f"{'vs' if g.home is team else 'at'} {opp.school}.", p)
                    told += 1
                    break
            # season milestones crossed this week
            s = getattr(p, "season_stats", None) or {}
            for k, cut, label in MILESTONES:
                now = s.get(k, 0)
                if now >= cut > now - c.get(k, 0):
                    _story(league, "milestone", f"Milestone: {p.position} {p.name} goes over {label} for the season.", p)
        # Senior Day: the last regular-season home game
        if g.home is team and not g.neutral and g.game_type == "Regular Season":
            later = [x for x in league.team_games(team) if x.week > g.week and x.home is team and not x.neutral
                     and x.game_type == "Regular Season"]
            if not later:
                seniors = sorted((p for p in team.roster if p.year >= 3), key=lambda p: -p.overall)
                if seniors:
                    won = g.winner is team
                    names = ", ".join(f"{p.position} {p.name}" for p in seniors[:3])
                    _story(league, "senior day",
                           f"Senior Day: {len(seniors)} seniors honored, then {'a win over' if won else 'a loss to'} "
                           f"{opp.school}. Leading the class: {names}.")
                    for p in seniors:
                        p.events[league.year].append("Honored on Senior Day")


def _room_stories(league, team):
    st = state(league)
    flags = st["flags"]
    # walk-on to starter
    for p in team.roster:
        if getattr(p, "walk_on", False) and _is_starter(team, p) and not flags.get(f"wo:{p.name}:{team.school}"):
            flags[f"wo:{p.name}:{team.school}"] = league.year
            _story(league, "walk-on", f"Walk-on to starter: {p.position} {p.name} came with no scholarship. "
                                      f"Now he's first on the depth chart.", p)
    # the quarterback job
    qbs = list(team.players_at("QB"))
    if qbs:
        cur = qbs[0].name
        last = flags.get(f"qb:{team.school}")
        if league.week == 1 and len(qbs) > 1 and abs(qbs[0].overall - qbs[1].overall) <= 3 \
                and flags.get(f"qbbattle:{team.school}") != league.year:
            flags[f"qbbattle:{team.school}"] = league.year
            _story(league, "qb battle", f"QB battle: {qbs[0].name} won the job in camp, but {qbs[1].name} "
                                        f"pushed him every day. The staff says it's close.")
        elif last and last != cur and league.week > 1:
            _story(league, "qb change", f"QB change: {cur} takes over from {last}.", qbs[0])
        flags[f"qb:{team.school}"] = cur
    # captains
    if league.week == 1 and getattr(team, "captains_year", None) == league.year \
            and flags.get(f"capt:{team.school}") != league.year:
        flags[f"capt:{team.school}"] = league.year
        caps = [p for p in (team.captains or []) if p in team.roster]
        if caps:
            _story(league, "captains", "The team votes its captains: "
                   + ", ".join(f"{p.position} {p.name} ({p.class_label})" for p in caps) + ".")
    # starters hurt this week
    for p in team.roster:
        if getattr(p, "inj_games", 0) > 0 and getattr(p, "inj_week", None) == league.week and _is_starter(team, p) \
                and "opted out" not in str(getattr(p, "inj_desc", "")):
            n = p.inj_games
            _story(league, "injury", f"Injury: starting {p.position} {p.name} is out "
                                     f"{'for the season' if n >= 99 else f'{n} game' + ('s' if n != 1 else '')}"
                                     f" ({getattr(p, 'inj_desc', 'injured')}).")


# ═══ Alerts: what you'd want to know before it's too late ═══════════════════

def _alerts(league, team):
    st = state(league)
    out = []
    top3 = st["top3"]
    cyc = league.recruiting
    for r in list(team.recruiting_targets) + [r for r in cyc.pool if r.committed_to is team]:
        rid = f"{r.name}:{r.position}"
        try:
            now = team in r.top_schools(3)
        except Exception:                               # noqa: BLE001, S112 — an alert is never worth a crash
            continue
        before = top3.get(rid)
        if r.committed_to is not None and r.committed_to is not team:
            if before != "gone":
                out.append((f"{r.stars}★ {r.position} {r.name} committed to {r.committed_to.school}", "4→B"))
                top3[rid] = "gone"
            continue
        if r.committed_to is team:
            others = [(t, a) for t, a in r.interest.items() if t is not team]
            if others:
                t, a = max(others, key=lambda x: x[1])
                if a >= r.interest.get(team, 0) - 8 and not r.signed:
                    out.append((f"Commit {r.name} is wavering: {t.school} is close", "4→B"))
            top3[rid] = True
            continue
        if before is not None and before != "gone" and now != before:
            out.append((f"{r.name} {'put you in his top 3' if now else 'dropped you from his top 3'}", "4→B"))
        top3[rid] = now
    import cp_alerts
    cp_alerts.scan(league, team, out[:8])               # + the roster, your job, the schedule, the money


def alerts(league):
    import cp_alerts
    return cp_alerts.alerts(league)


# ═══ Achievements ═══════════════════════════════════════════════════════════

from cp_ach import ACH_BY


def unlock(league, k, note=""):
    st = state(league)
    if k in st["ach"] or k not in ACH_BY:
        return False
    st["ach"][k] = {"year": league.year, "note": note}
    name, _ = ACH_BY[k]
    _log(league, (league.year, f"Achievement: {name}{' — ' + note if note else ''}."))
    _story(league, "achievement", f"Achievement unlocked: {name}{' — ' + note if note else ''}.")
    import cp_ach
    st["stories"][-1]["w"] = {"B": 12, "S": 22, "G": 40, "P": 70}.get(cp_ach.BY.get(k, ("",) * 5)[4], 15)
    return True


def _career_wins(league):
    coach = league.user_coach
    w = sum(s["w"] for s in coach.history)
    t = coach.team
    if t is not None and t.coach is coach and not (coach.history and coach.history[-1].get("year") == league.year):
        w += t.wins
    return w


def _game_achievements(league, team, games):
    for g in games:
        if team not in (g.home, g.away) or not g.played or g.winner is not team:
            continue
        opp = g.opponent_of(team)
        if _career_wins(league) == 1:
            unlock(league, "first_win", f"{g.score_for(team)}-{g.score_for(opp)} over {opp.school}")
        rk = (getattr(g, "ranks", None) or {}).get(opp)
        if rk == 1:
            unlock(league, "beat_no1", f"over No. 1 {opp.school}")
        if rk and rk <= 5 and g.away is team and not g.neutral:
            unlock(league, "road_top5", f"at No. {rk} {opp.school}")
        box = getattr(g, "box", None)
        if box is not None:
            run_me = run_them = 0
            worst = 0
            for q in range(len(box.line.get(team, []))):
                run_me += box.line[team][q]
                run_them += box.line.get(opp, [0] * 9)[q]
                worst = max(worst, run_them - run_me)
            if worst >= 17:
                unlock(league, "comeback", f"down {worst}, beat {opp.school}")
        if g.game_type in ("NP First Round", "NP Quarterfinal", "NP Semifinal", "National Championship"):
            unlock(league, "playoff_win", f"{g.game_type.replace('NP ', '')} over {opp.school}")
    w = _career_wins(league)
    if w >= 100:
        unlock(league, "wins_100")
    if w >= 200:
        unlock(league, "wins_200")


def season_achievements(league):
    """At the end of the season (the champion is crowned)."""
    import carousel as cz
    team, coach = league.user_team, league.user_coach
    s = cz.season_line(league, team)
    st = state(league)
    if s["w"] >= 10:
        unlock(league, "ten_wins", f"{s['w']}-{s['l']} in {league.year}")
    reg = [g for g in league.team_games(team) if g.game_type == "Regular Season" and g.played]
    if len(reg) >= 12 and all(g.winner is team for g in reg):
        unlock(league, "undefeated", str(league.year))
    if s["conf_champ"]:
        unlock(league, "conf_title", f"{team.conference}, {league.year}")
    if s["title"]:
        unlock(league, "natl_title", str(league.year))
        if any(h.get("title") and h.get("year") == league.year - 1 for h in coach.history):
            unlock(league, "repeat", f"{league.year - 1} and {league.year}")
    try:
        rk = league.recruiting.class_rank(team)
        if rk and rk <= 5:
            unlock(league, "top5_class", f"No. {rk} class")
    except Exception:                                   # noqa: BLE001, S110
        pass
    # the rivalry
    from commentary import rivalry_name
    for g in league.team_games(team):
        opp = g.opponent_of(team)
        if g.played and rivalry_name(team, opp):
            key_ = f"rival:{team.school}:{opp.school}"
            streak = st["flags"].get(key_, 0)
            streak = streak + 1 if g.winner is team else 0
            st["flags"][key_] = streak
            if streak >= 3:
                unlock(league, "rival3", f"{streak} straight over {opp.school}")
    seasons = {}
    for h in coach.history + ([s] if not (coach.history and coach.history[-1].get("year") == league.year) else []):
        if h["w"] > h["l"]:
            seasons.setdefault(h["school"], 0)
            seasons[h["school"]] += 1
    if len(seasons) >= 3:
        unlock(league, "three_schools", ", ".join(seasons))
    yrs = league.year - (coach.hired_year or league.year) + 1
    if yrs >= 10:
        unlock(league, "decade", f"{yrs} seasons at {team.school}")


def awards_achievements(league):
    """After the awards and the draft (the offseason)."""
    team = league.user_team
    aw = getattr(league, "awards", {}).get(league.year - 1) or getattr(league, "awards", {}).get(league.year)
    if aw and aw.get("heisman") and aw["heisman"][1].school == team.school:
        unlock(league, "heisman", aw["heisman"][0].name)
    for yr, picks in (getattr(league, "drafts", {}) or {}).items():
        for x in picks:
            if x.get("school") == team.school and x.get("round") == 1 and yr >= (league.user_coach.hired_year or 0):
                unlock(league, "first_rounder", f"{x.get('name')}, {yr}")
                return


# ═══ Every week ═════════════════════════════════════════════════════════════

def weekly(league, games):
    """After every week, played or simmed (league.finish_week)."""
    if not mine(league):
        return
    team = league.user_team
    st = state(league)
    if league.week == 1 and league.year not in st["ovr_start"]:
        st["ovr_start"][league.year] = team.team_ovr
        _record_staff(league)
        try:
            import cp_tree
            cp_tree.news(league)
        except Exception as e:                          # noqa: BLE001
            league.__dict__.setdefault("error_log", []).append(f"cp_tree.news: {e!r}")
        try:
            awards_achievements(league)                 # last winter's awards and draft
        except Exception:                               # noqa: BLE001, S110
            pass
    try:
        _player_stories(league, team, games)
        _room_stories(league, team)
        import cp_stories
        cp_stories.weekly(league, team, games)
        _alerts(league, team)
        _game_achievements(league, team, games)
        import cp_ach
        import cp_wrap
        cp_wrap.track_pulse(league, team)
        cp_ach.weekly(league)
        cp_ach.evaluate(league)
    except Exception as e:                              # noqa: BLE001 — the season goes on regardless
        league.__dict__.setdefault("error_log", []).append(f"career_plus.weekly: {e!r}")


# ═══ The Weekly Wrap ════════════════════════════════════════════════════════

def before(league):
    """Everything the wrap compares against, taken before the week is played."""
    if not mine(league):
        return None
    team, coach = league.user_team, league.user_coach
    try:
        import ad_trust
        trust = ad_trust.get(coach, team)
    except Exception:                                   # noqa: BLE001
        trust = None
    recs = {}
    for r in list(team.recruiting_targets) + [r for r in league.recruiting.pool if r.committed_to is team]:
        recs[id(r)] = (r, r.interest.get(team, 0), r.leader() is team, r.committed_to)
    return {"week": league.week + 1, "rank": league.rankings.rank_of(team), "seat": getattr(coach, "seat", 0),
            "trust": trust, "class_rank": league.recruiting.class_rank(team), "recs": recs,
            "hurt": {id(p) for p in team.roster if getattr(p, "inj_games", 0) > 0},
            "commits": len(league.recruiting.commitments(team))}


def _arrow(before, after, lower_is_better=True):
    if before is None and after is None:
        return paint("—", C.GRAY)
    if before is None:
        return paint("new", C.BGREEN, C.BOLD)
    if after is None:
        return paint("out", C.BRED, C.BOLD)
    d = before - after if lower_is_better else after - before
    if d > 0:
        return paint(f"▲{abs(d)}", C.BGREEN, C.BOLD)
    if d < 0:
        return paint(f"▼{abs(d)}", C.BRED, C.BOLD)
    return paint("—", C.GRAY)


def _potg(team, g):
    box = getattr(g, "box", None)
    if box is None:
        return None
    best, score = None, -1
    for p, c in box.stats.items():
        if p not in team.roster:
            continue
        v = (c.get("pass_yds", 0) * 0.05 + c.get("pass_td", 0) * 4 - c.get("pass_int", 0) * 3 + c.get("rush_yds", 0) * 0.1
             + c.get("rush_td", 0) * 6 + c.get("rec_yds", 0) * 0.1 + c.get("rec_td", 0) * 6 + c.get("tkl", 0)
             + c.get("sack", 0) * 4 + c.get("int", 0) * 5 + c.get("ff", 0) * 3)
        if v > score:
            best, score = (p, c), v
    return best


def _line(c):
    bits = []
    if c.get("pass_att", 0) >= 8:
        bits.append(f"{c['pass_cmp']}/{c['pass_att']}, {c['pass_yds']} yds, {c['pass_td']} TD")
    if c.get("rush_att", 0) >= 6:
        bits.append(f"{c['rush_att']} car, {c['rush_yds']} yds" + (f", {c['rush_td']} TD" if c.get("rush_td") else ""))
    if c.get("rec", 0) >= 3:
        bits.append(f"{c['rec']} rec, {c['rec_yds']} yds" + (f", {c['rec_td']} TD" if c.get("rec_td") else ""))
    if c.get("tkl", 0) >= 5 or c.get("sack", 0) or c.get("int", 0):
        bits.append(", ".join(x for x in (f"{c.get('tkl', 0)} tkl", f"{c.get('sack', 0):g} sk" if c.get("sack") else "",
                                          f"{c.get('int', 0)} INT" if c.get("int") else "") if x))
    return "; ".join(bits[:2])


def wrap(league, snap, games):
    """The Weekly Wrap: one screen with everything your week changed."""
    if snap is None or not mine(league):
        return
    import settings
    if not settings.load().get("weekly_wrap", True):
        import cp_cards
        cp_cards.midterm(league)
        return
    team, coach = league.user_team, league.user_coach
    g = next((x for x in games if team in (x.home, x.away) and x.played), None)

    def front():
        clear()
        wk = league.week_name(league.week) if league.week <= 13 else (g.game_type if g else league.week_name(league.week))
        print(title_bar(f"{wk.upper()} WRAP · {team.school.upper()}", league.team_color(team)))
        # the result
        if g is not None:
            opp = g.opponent_of(team)
            won = g.winner is team
            ork = (getattr(g, "ranks", None) or {}).get(opp)
            res = paint(" WIN " if won else " LOSS ", "\033[38;5;16m", "\033[102m" if won else "\033[101m", C.BOLD)
            print(f"\n   {res}  {paint(f'{g.score_for(team)}-{g.score_for(opp)}', C.BWHITE, C.BOLD)}  "
                  f"{'vs' if g.home is team or g.neutral else 'at'} {'#' + str(ork) + ' ' if ork else ''}{opp.school}"
                  f"   {paint(team.record + (' · ' + team.conf_record + ' conf' if team.conf_wins + team.conf_losses else ''), C.GRAY)}")
            pg = _potg(team, g)
            if pg:
                print(f"   {paint('Player of the game', C.GRAY)}  {paint(pg[0].name, C.BWHITE, C.BOLD)} "
                      f"{paint(pg[0].position, C.BCYAN)}  {paint(_line(pg[1]), C.GRAY)}")
            import cp_wrap
            ug = cp_wrap.grades_line(team, g)
            if ug:
                print(f"   {paint('Unit grades', C.GRAY)}        {ug}")
        else:
            print(paint(f"\n   No game for {team.school} this week.", C.GRAY))
        print()
        # the poll and the job
        rk = league.rankings.rank_of(team)
        left = [(f"{paint('Poll', C.GRAY)}  {('#' + str(snap['rank'])) if snap['rank'] else 'NR'} → "
                 f"{paint(('#' + str(rk)) if rk else 'NR', C.BWHITE, C.BOLD)}  {_arrow(snap['rank'], rk)}")]
        try:
            import committee
            c = committee.get(league)
            if c.released and c.year == league.year:
                cr = c.rank_of(team)
                left.append(f"{paint('Playoff', C.GRAY)}  {paint(('#' + str(cr)) if cr else 'outside the top 25', C.BWHITE)}")
        except Exception:                                   # noqa: BLE001, S110
            pass
        import week as _wk
        nxt = _wk.next_game(league, team)
        if nxt is not None:
            o = nxt.opponent_of(team)
            ork = league.rankings.rank_of(o)
            left.append(f"{paint('Next', C.GRAY)}  {'vs' if nxt.home is team or nxt.neutral else 'at'} "
                        f"{'#' + str(ork) + ' ' if ork else ''}{o.school} ({o.record})")
        seat = getattr(coach, "seat", 0)
        import carousel as cz
        d = seat - snap["seat"]
        job = [(f"{paint('Hot seat', C.GRAY)}  {snap['seat']} → {paint(str(seat), C.BWHITE, C.BOLD)}  "
                f"{paint(f'{d:+d}', C.BRED if d > 0 else C.BGREEN, C.BOLD) if d else paint('—', C.GRAY)}  "
                f"{paint(cz.seat_label(seat).lower(), C.GRAY)}")]
        try:
            import ad_trust
            tv = ad_trust.get(coach, team)
            if snap["trust"] is not None:
                dt = round(tv - snap["trust"])
                job.append(f"{paint('AD trust', C.GRAY)}  {snap['trust']:.0f} → {paint(f'{tv:.0f}', C.BWHITE, C.BOLD)}  "
                           f"{paint(f'{dt:+d}', C.BGREEN if dt > 0 else C.BRED, C.BOLD) if dt else paint('—', C.GRAY)}  "
                           f"{paint(ad_trust.word(tv), C.GRAY)}")
        except Exception:                                   # noqa: BLE001, S110
            pass
        word = cz.seat_word(coach)
        if word:
            job.append(paint(truncate(word[:1].upper() + word[1:], 44), C.GRAY))
        for ln in columns(panel("THE POLL", left, 50, height=3), panel("YOUR JOB", job, 49, height=3)):
            print(ln)
        # recruiting
        rec = []
        cyc = league.recruiting
        commits_now = cyc.commitments(team)
        new_commits = [r for r in commits_now if snap["recs"].get(id(r), (None, 0, False, None))[3] is not team]
        for r in new_commits[:3]:
            rec.append(paint("◆ ", C.BGREEN) + f"{r.stars}★ {r.position} {r.name} committed to you")
        moves = []
        for r, was, led, cto in snap["recs"].values():
            if r.committed_to is not None and r.committed_to is not team and cto is not r.committed_to:
                rec.append(paint("✕ ", C.BRED) + f"{r.name} committed to {r.committed_to.school}")
                continue
            now = r.interest.get(team, 0)
            lead_now = r.leader() is team
            if lead_now and not led:
                rec.append(paint("▲ ", C.BGREEN) + f"You now lead for {r.stars}★ {r.position} {r.name}")
            elif led and not lead_now and r.committed_to is None:
                lt = r.leader()
                rec.append(paint("▼ ", C.BRED) + f"{lt.school if lt else 'Someone'} passed you for {r.name}")
            elif abs(now - was) >= 4:
                moves.append((now - was, r))
        for d, r in sorted(moves, key=lambda x: -abs(x[0]))[:3]:
            rec.append((paint("▲ ", C.BGREEN) if d > 0 else paint("▼ ", C.BRED)) + f"{r.name} {'warming to' if d > 0 else 'cooling on'} you")
        if not team.recruiting_targets and not commits_now:
            rec.append(paint("Your board is empty. 4 → F finds recruits who fit.", C.BYELLOW))
        cr = cyc.class_rank(team)
        rec.append(paint(f"Class: {len(commits_now)} commit{'s' if len(commits_now) != 1 else ''} · "
                         f"{('No. ' + str(cr)) if cr else 'unranked'}"
                         + (f" (was {('No. ' + str(snap['class_rank'])) if snap['class_rank'] else 'unranked'})"
                            if snap["class_rank"] != cr else ""), C.GRAY))
        hurt = [p for p in team.roster if getattr(p, "inj_games", 0) > 0 and id(p) not in snap["hurt"]
                and "opted out" not in str(getattr(p, "inj_desc", ""))]
        inj = [paint("+ ", C.BRED) + f"{p.position} {p.name}: {'season' if p.inj_games >= 99 else str(p.inj_games) + ' wk'}"
               for p in sorted(hurt, key=lambda p: -p.overall)[:4]] or [paint("No new injuries.", C.BGREEN)]
        back = [p for p in team.roster if id(p) in snap["hurt"] and getattr(p, "inj_games", 0) == 0]
        if back:
            inj.append(paint("Back: " + ", ".join(p.last_name for p in back[:4]), C.GRAY))
        for ln in columns(panel("RECRUITING", rec[:6] or [paint("Quiet week on the trail.", C.GRAY)], 62, height=6),
                          panel("INJURIES", inj[:6], 37, height=6)):
            print(ln)
        # storylines
        told = [s for s in stories(league, league.year, league.week) if s["kind"] != "achievement"]
        ach = [s for s in stories(league, league.year, league.week) if s["kind"] == "achievement"]
        if told or ach:
            print(section("STORYLINES", C.BMAGENTA))
            for s in ach[:2]:
                print(clip("   " + paint("★ ", C.BYELLOW, C.BOLD) + paint(s["text"], C.BYELLOW), WIDTH))
            for s in told[:5]:
                print(clip("   " + paint("• ", C.BMAGENTA) + s["text"], WIDTH))
        al = alerts(league)
        if al:
            print(section("HEADS UP", C.BYELLOW))
            for a in al[:3]:
                print(clip("   " + paint("● ", C.BYELLOW) + a["text"] + paint(f"   {a['keys']}", C.GRAY), WIDTH))
        try:
            import dashboard
            heads = dashboard.headlines(league, team, n=4)
            if heads:
                print(section("AROUND THE SPORT", C.BCYAN))
                for col, text in heads[:3]:
                    print(clip("   " + paint("● ", col) + text, WIDTH))
        except Exception:                                   # noqa: BLE001, S110
            pass
    import cp_wrap
    page = None
    while True:
        if page is None:
            front()
            footer(key("Enter", "continue", C.BGREEN), *[key(k.upper(), lab) for k, lab in cp_wrap.PAGES.items()],
                   key("L", "storylines"), key("H", "heads up"))
        else:
            cp_wrap.open_page(league, team, games, page)
            footer(key("Enter", "back to the wrap", C.BGREEN),
                   *[key(k.upper(), lab) for k, lab in cp_wrap.PAGES.items() if k != page])
        c = ask("Select:").strip().lower()
        if c == "l":
            storylines_screen(league)
            page = None
        elif c == "h":
            import cp_alerts
            cp_alerts.screen(league)
            page = None
        elif c in cp_wrap.PAGES:
            page = c
        elif page is not None:
            page = None
        else:
            break
    import cp_cards
    cp_cards.midterm(league)


def storylines_screen(league, year=None):
    import cp_stories
    cp_stories.screen(league, year)


# ═══ The AD's report card ═══════════════════════════════════════════════════

def _grade(score):
    """score: -1 (disaster) … +1 (beyond hopes) → a letter."""
    cuts = ((0.55, "A+"), (0.35, "A"), (0.2, "A-"), (0.1, "B+"), (0.0, "B"), (-0.1, "B-"), (-0.2, "C+"),
            (-0.3, "C"), (-0.42, "C-"), (-0.55, "D"), (-9, "F"))
    return next(g for c, g in cuts if score >= c)


GRADE_COLOR = {"A": C.BGREEN, "B": C.GREEN, "C": C.BYELLOW, "D": C.BRED, "F": C.BRED}


def report_card(league):
    import cp_cards
    cp_cards.report_card(league)


# ═══ Selection Day and bowl week ════════════════════════════════════════════

def selection_show(league):
    import cp_post
    cp_post.selection_show(league)


def bowl_week(league, g):
    """Before your bowl or playoff game's week (cp_post.trip_week)."""
    import cp_post
    cp_post.trip_week(league, g)


# ═══ The coaching tree ══════════════════════════════════════════════════════

def _record_staff(league):
    """Week 1 every year: who's on your staff goes into your tree."""
    team = league.user_team
    st = state(league)
    rows = [(getattr(team, "oc", None), "OC"), (getattr(team, "dc", None), "DC")]
    try:
        import poscoach
        rows += [(c, g) for g, c in poscoach.staff_of(team).items()]
    except Exception:                                   # noqa: BLE001, S110
        pass
    for c, role in rows:
        if c is None:
            continue
        st["tree"].setdefault(c.name, [])
        entry = [league.year, team.school, role]
        if entry not in st["tree"][c.name]:
            st["tree"][c.name].append(entry)


def _all_coaches(league):
    seen, out = set(), []

    def add(c):
        if c is not None and id(c) not in seen:
            seen.add(id(c))
            out.append(c)
    for t in league.teams:
        add(t.coach)
        add(getattr(t, "oc", None))
        add(getattr(t, "dc", None))
        try:
            import poscoach
            for c in poscoach.staff_of(t).values():
                add(c)
        except Exception:                               # noqa: BLE001, S110
            pass
    for c in getattr(league, "coach_pool", []) + getattr(league, "retired_coaches", []) + getattr(league, "pos_pool", []):
        add(c)
    return out


def tree(league):
    """[(coach object or None, name, [(year, school, role)], where now, record line)]"""
    me = league.user_coach
    st = state(league)
    _record_staff(league) if mine(league) and league.week >= 1 else None
    served = {name: [tuple(x) for x in v] for name, v in st["tree"].items()}
    mine_years = {(h["year"], h["school"]) for h in me.history}
    if me.team is not None:
        for y in range(me.hired_year or league.year, league.year + 1):
            mine_years.add((y, me.team.school))
    by_name = {}
    for c in _all_coaches(league):
        if c is me:
            continue
        for e in getattr(c, "coord_history", []) or []:
            if isinstance(e, dict) and e.get("hc") == me.name:
                served.setdefault(c.name, [])
                x = (e.get("year"), e.get("school"), e.get("role"))
                if x not in served[c.name]:
                    served[c.name].append(x)
        for e in getattr(c, "history", []) or []:
            if isinstance(e, tuple) and len(e) == 3 and (e[0], e[1]) in mine_years:
                served.setdefault(c.name, [])
                if e not in served[c.name]:
                    served[c.name].append(e)
        by_name.setdefault(c.name, c)
    where = {}
    for t_ in league.teams:
        try:
            import poscoach
            for grp, pc in poscoach.staff_of(t_).items():
                if pc is not None:
                    where[id(pc)] = (t_, grp)
        except Exception:                               # noqa: BLE001, S110
            pass
    out = []
    for name, roles in served.items():
        c = by_name.get(name)
        now, rec = "out of coaching", ""
        if c is not None and id(c) in where:
            t_, grp = where[id(c)]
            now = f"{grp} coach at {t_.school}"
        elif c is not None:
            t = getattr(c, "team", None)
            if t is not None and t.coach is c:
                now = f"head coach at {t.school}"
                hist = [h for h in getattr(c, "history", []) if isinstance(h, dict)]
                w = sum(h["w"] for h in hist) + t.wins
                l_ = sum(h["l"] for h in hist) + t.losses
                rec = f"{w}-{l_} as a head coach"
            elif t is not None and getattr(t, "oc", None) is c:
                now = f"offensive coordinator at {t.school}"
            elif t is not None and getattr(t, "dc", None) is c:
                now = f"defensive coordinator at {t.school}"
            elif t is not None:
                now = f"assistant at {t.school}"
            elif getattr(c, "status", "") == "retired" or c in getattr(league, "retired_coaches", []):
                now = "retired"
            else:
                now = "between jobs"
        out.append((c, name, sorted(roles, key=lambda r: (r[0] or 0)), now, rec))
    out.sort(key=lambda r: (not r[3].startswith("head coach"), not r[3].endswith("coordinator") and "coordinator" not in r[3], r[1]))
    return out


def head_to_head(league, other):
    me = league.user_coach.name
    w = l_ = 0
    import archive
    games = []
    for y in archive.seasons(league):
        games += archive.games_for(league, y)
    games += [g for wk in league.schedule.values() for g in wk if g.played]
    for g in games:
        hc = getattr(g, "hc", None) or {}
        if me in hc.values() and other in hc.values():
            win = getattr(g, "winner", None)
            if win is None:
                continue
            if hc.get(win) == me:
                w += 1
            else:
                l_ += 1
    return w, l_


def tree_screen(league):
    import cp_tree
    cp_tree.screen(league)


# ═══ Legacy and the trophy case ═════════════════════════════════════════════

def _statues_and_jerseys(league):
    """Season end: retire the numbers of your greats; a statue after 20 seasons or 3 titles at one school."""
    if not mine(league):
        return
    st = state(league)
    team, coach = league.user_team, league.user_coach
    aw = getattr(league, "awards", {}).get(league.year) or {}
    greats = {}
    if aw.get("heisman") and aw["heisman"][1] is team:
        greats[aw["heisman"][0]] = "won the Golden Helmet"
    for grp, p, t in aw.get("first", []) or []:
        if t is team and getattr(p, "all_american", 0) >= 2:
            greats.setdefault(p, "two-time All-American")
    for p, why in greats.items():
        if any(j["name"] == p.name and j["school"] == team.school for j in st["jerseys"]):
            continue
        if p.year >= 3 or why.startswith("won"):
            st["jerseys"].append({"school": team.school, "number": p.number, "name": p.name, "why": why, "year": league.year})
            _story(league, "jersey", f"{team.school} will retire No. {p.number}: {p.name} {why}.", p)
    seasons = [h for h in coach.history if h["school"] == team.school]
    yrs = league.year - (coach.hired_year or league.year) + 1
    titles = sum(1 for h in seasons if h.get("title"))
    if (yrs >= 20 or titles >= 3) and not any(s_["school"] == team.school for s_ in st["statues"]):
        st["statues"].append({"school": team.school, "year": league.year,
                              "why": f"{yrs} seasons" if yrs >= 20 else f"{titles} national titles"})
        _story(league, "statue", f"{team.school} will put up a statue of {coach.name} outside {team.stadium}.")
        unlock(league, "statue", team.school)


def season_end(league):
    """Called once the title game is over (season_wrap)."""
    if not mine(league):
        return
    st = state(league)
    if f"end:{league.year}" in st["seen"]:
        return
    st["seen"].append(f"end:{league.year}")
    try:
        import cp_ach
        import cp_stories
        cp_ach.season_record(league)
        season_achievements(league)
        _statues_and_jerseys(league)
        cp_stories.season_honors(league)
        import cp_starts
        import cp_tree
        cp_starts.season_end(league)
        cp_tree.news(league)
        cp_ach.evaluate(league, final=True)
    except Exception as e:                              # noqa: BLE001
        league.__dict__.setdefault("error_log", []).append(f"career_plus.season_end: {e!r}")


def legacy_screen(league):
    if getattr(league, "user_coach", None) is None:
        return
    import carousel as cz
    coach = league.user_coach
    st = state(league)
    awards_achievements(league) if mine(league) else None
    while True:
        hist = [h for h in coach.history if isinstance(h, dict)]
        live = None
        t = coach.team
        if t is not None and t.coach is coach and not (hist and hist[-1].get("year") == league.year) and (t.wins or t.losses):
            live = cz.season_line(league, t)
        seasons = hist + ([live] if live else [])
        tot = cz.splits(seasons) if seasons else {"w": 0, "l": 0, "titles": 0, "cfp": 0, "confs": 0, "bowls": 0}
        clear()
        print(title_bar(f"LEGACY · COACH {coach.name.upper()}"))
        yrs = len(seasons)
        print(f"\n   {paint(coach.name, C.BWHITE, C.BOLD)}  ·  {yrs} season{'s' if yrs != 1 else ''}  ·  "
              f"{paint(str(tot['w']) + '-' + str(tot['l']), C.BWHITE, C.BOLD)}"
              + (paint(f" ({tot['w'] / max(1, tot['w'] + tot['l']):.3f})", C.GRAY)))
        # trophy case
        print(section("TROPHY CASE", C.BYELLOW))
        titles = [h["year"] for h in seasons if h.get("title")]
        confs = [f"{h['conf']} {h['year']}" for h in seasons if h.get("conf_champ")]
        bowls = [f"{h['post'].replace('Won ', '')} {h['year']}" for h in seasons if h.get("bowl_win")]
        cfp = sum(1 for h in seasons if h.get("cfp"))
        coy = [y for y, a in (getattr(league, "awards", {}) or {}).items() if a.get("coach") and a["coach"][0] == coach.name]
        cases = [("National titles", ", ".join(map(str, titles)) or "—"),
                 ("Conference titles", ", ".join(confs) or "—"),
                 ("Playoff trips", str(cfp) if cfp else "—"),
                 ("Bowl wins", ", ".join(bowls[-6:]) + (f" (+{len(bowls) - 6})" if len(bowls) > 6 else "") or "—"),
                 ("Coach of the Year", ", ".join(map(str, coy)) or "—")]
        # players' honors under you
        years_at = {(h["year"], h["school"]) for h in seasons}
        helmets, aas, firsts = [], 0, []
        for y, a in (getattr(league, "awards", {}) or {}).items():
            if a.get("heisman") and (y, a["heisman"][1].school) in years_at:
                helmets.append(f"{a['heisman'][0].name} {y}")
            aas += sum(1 for _, p, tt in a.get("first", []) or [] if (y, tt.school) in years_at)
        for y, picks in (getattr(league, "drafts", {}) or {}).items():
            firsts += [x for x in picks if x.get("round") == 1 and (y, x.get("school")) in years_at]
        cases += [("Golden Helmets", ", ".join(helmets) or "—"), ("All-Americans", str(aas) if aas else "—"),
                  ("1st-round picks", str(len(firsts)) if firsts else "—")]
        for label, v in cases:
            print(clip(f"   {paint(pad(label, 19), C.GRAY)}{paint(v, C.BYELLOW if v != '—' else C.GRAY)}", WIDTH))
        # stops
        print(section("STOPS", C.BCYAN))
        stops = {}
        for h in seasons:
            s_ = stops.setdefault(h["school"], {"from": h["year"], "to": h["year"], "w": 0, "l": 0, "t": 0})
            s_["to"] = h["year"]
            s_["w"] += h["w"]
            s_["l"] += h["l"]
            s_["t"] += bool(h.get("title"))
        if not stops and t is not None:
            stops[t.school] = {"from": coach.hired_year or league.year, "to": league.year, "w": 0, "l": 0, "t": 0}
        for school, s_ in stops.items():
            print(f"   {pad(school, 22)}{s_['from']}–{s_['to']}   {s_['w']}-{s_['l']}"
                  + (paint(f"   {s_['t']} title{'s' if s_['t'] != 1 else ''}", C.BYELLOW) if s_["t"] else ""))
        # honors at the schools
        if st["statues"] or st["jerseys"]:
            print(section("IN BRONZE AND ON THE WALL", C.BMAGENTA))
            for s_ in st["statues"]:
                print(f"   {paint('Statue', C.BYELLOW, C.BOLD)}  outside the stadium at {s_['school']} ({s_['year']}, {s_['why']})")
            for j in st["jerseys"][-6:]:
                print(f"   {paint('No. ' + str(j['number']), C.BWHITE, C.BOLD)} retired at {j['school']}: {j['name']} ({j['why']}, {j['year']})")
        else:
            yrs_here = league.year - (coach.hired_year or league.year) + 1 if t is not None else 0
            import textwrap
            msg = (f"A statue comes after 20 seasons or 3 national titles at one school (you're at {yrs_here} season"
                   f"{'s' if yrs_here != 1 else ''} at {t.school if t else 'no school'}). Golden Helmet winners and "
                   "two-time All-Americans get their numbers retired.")
            print()
            for ln in textwrap.wrap(msg, 94):
                print(paint("   " + ln, C.GRAY))
        # achievements and the legacy score
        import cp_ach
        got = st["ach"]
        total, pts, res, label, col, nxt = cp_ach.legacy_score(league)
        print(section(f"ACHIEVEMENTS · {len(got)} OF {len(cp_ach.ALL)} · LEGACY SCORE {total}", C.BGREEN))
        from ui import bar
        top = nxt or total or 1
        print(f"   {paint(pad(label, 22), col, C.BOLD)}{bar(total, 30, top, col)}  "
              f"{paint(f'{total}' + (f' / {nxt} for the next step' if nxt else ''), C.GRAY)}")
        print(paint(f"   {pts} from achievements, {res} from the résumé (wins, titles, players, your tree)", C.GRAY))
        recent = sorted(got.items(), key=lambda kv: -kv[1]["year"])[:5]
        for k, v in recent:
            a_ = cp_ach.BY.get(k)
            if a_:
                tn, _tp, tc = cp_ach.TIER[a_[4]]
                print(clip(f"   {paint('★', C.BYELLOW, C.BOLD)} {paint(pad(a_[1], 30), C.BWHITE, C.BOLD)}{paint(pad(tn, 9), tc)}"
                           f"{paint(str(v['year']), C.GRAY)}  {paint(truncate(v.get('note') or '', 36), C.GRAY)}", WIDTH))
        tr = tree(league)
        heads = sum(1 for r in tr if r[3].startswith("head coach"))
        print(paint(f"\n   Coaching tree: {len(tr)} assistants, {heads} now head coaches.", C.GRAY))
        import cp_starts
        ch = cp_starts.status_line(league)
        if ch:
            print(paint("   " + ch, C.BMAGENTA))
        footer(key("A", "achievements"), key("T", "coaching tree"), key("L", "storylines"), key("R", "report cards"),
               *([key("S", "your story")] if ch else []), key("B", "back", C.GRAY))
        c = ask("Select:").strip().lower()
        if c == "a":
            cp_ach.screen(league)
        elif c == "t":
            tree_screen(league)
        elif c == "l":
            storylines_screen(league)
        elif c == "r":
            cards_screen(league)
        elif c == "s" and ch:
            cp_starts.screen(league)
        else:
            return


def cards_screen(league):
    import cp_cards
    cp_cards.cards_screen(league)


# ═══ Non-conference scheduling ══════════════════════════════════════════════

PLANS = {
    "cupcakes": ("Easy start", "two guarantee games (one FCS), and a Group of Five team. Wins in the bank, a weaker SoS"),
    "balanced": ("Balanced", "what most programs do: one marquee game, a Group of Five team, an FCS guarantee game"),
    "tough": ("Tough", "two Power opponents and no FCS game. The committee notices; so does your record"),
    "national": ("National", "three Power opponents, coast to coast. For programs that want every Saturday on TV"),
}


def nonconf_plan(league, year):
    return state(league)["nonconf"].get(str(year)) if mine(league) else None


def nonconf_screen(league):
    import cp_sched
    cp_sched.screen(league)


def apply_wish(league, team, wish, slots, already=()):
    """season.build_schedule: your philosophy instead of the AD's default."""
    plan = nonconf_plan(league, league.year)
    if not plan or team is not league.user_team:
        return wish
    style = plan.get("style", "balanced")
    if style == "balanced":
        return wish
    from season import schedule_tier
    have = sum(schedule_tier(o) == "power" for o in already)
    fcs = {"cupcakes": 1, "tough": 0, "national": 0}[style]
    power = max(0, {"cupcakes": 0, "tough": 2, "national": 3}[style] - have)
    fcs = min(fcs, slots)
    power = min(power, slots - fcs)
    wish["fcs"], wish["power"], wish["group"] = fcs, power, slots - fcs - power      # (a Counter: update() would add)
    return wish


# ═══ The story starts (cp_starts.py: fifteen of them, with chapters) ═════════

def story_start(league, coach, rng):
    import cp_starts
    return cp_starts.pick(league, coach, rng)


def apply_start(league, coach, team, kind):
    import cp_starts
    cp_starts.apply(league, coach, team, kind)
