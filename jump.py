"""
jump.py — Go to anything from the dashboard.

Type / (or just start typing a name) on the dashboard: a screen ("depth chart", "standings",
"board"), a team ("Texas", "Texas schedule"), a player, or a coach. One clear match opens
straight away; otherwise you pick from a short list.
"""
from ui import C, ask, clear, pad, paint, pause, title_bar, truncate


def _screens(league):
    """(words people would type, label, what it opens). Your team's screens first."""
    import screens as sc
    team = getattr(league, "user_team", None) or getattr(league, "follow_team", None)
    career = getattr(league, "mode", None) == "career" and getattr(league, "user_coach", None) is not None

    def m(mod, fn, *a):
        return lambda: getattr(__import__(mod), fn)(*a)
    out = []
    if team is not None:
        out += [
            ("roster players", "Your roster", lambda: sc.roster_view(league, team)),
            ("depth chart lineup starters", "Depth chart", lambda: sc.depth_chart(league, team)),
            ("schedule results my schedule games", "Your schedule & results", lambda: sc.schedule_view(league, team)),
            ("team page program", "Your team page", lambda: sc.team_view(league, team)),
            ("team stats statistics", "Team statistics", m("team_stats", "screen", league, team)),
            ("budget nil money payroll", "Budget & NIL", m("finance_screens", "budget_screen", league, team)),
            ("facilities stadium", "Facilities", m("finance_screens", "facilities_screen", league, team)),
            ("transfer watch portal risk", "Transfer watch", m("transfer_watch", "screen", league, team)),
            ("locker room chemistry captains", "Locker room", m("personalities", "locker_room", league, team)),
            ("rivalries rival", "Rivalries", m("rivalries", "team_rivalries", league, team)),
        ]
        if career:
            out += [("practice report battles", "Practice report", m("practice", "screen", league, team))]
    out += [
        ("scores scoreboard around the country week", "Scores around the country", lambda: sc.schedule_menu(league)),
        ("standings conference", "Conference standings", lambda: sc.standings_menu(league)),
        ("top 25 poll ap rankings media", "Media Top 25", lambda: sc.top_25(league)),
        ("playoff rankings committee np cfp", "NP Playoff Rankings", m("committee_screens", "playoff_rankings", league)),
        ("heisman golden helmet award race", "Golden Helmet race", lambda: sc.heisman_race(league)),
        ("strength of schedule sos", "Strength of schedule", m("sos", "screen", league)),
        ("program history team history full history seasons all time", "Program history (any team)",
         m("history_book", "pick_team_history", league)),
        ("coach career full career coach history", "Coach career (any coach)", m("history_book", "pick_coach_career", league)),
        ("national champions history titles", "National champions", lambda: sc.champions_history(league)),
        ("record book records", "Record book", m("record_screens", "hub", league)),
        ("hall of fame hof", "Hall of Fame", m("halloffame", "hub", league)),
        ("toughest venues places to play stadiums", "Toughest places to play", m("stadium_screens", "toughest_screen", league)),
        ("recruiting hub recruits", "Recruiting hub", m("recruiting_screens", "recruiting_menu", league)),
        ("recruiting news commits wire", "Recruiting news", m("recruiting_screens", "news_screen", league)),
        ("transfer portal", "Transfer portal", lambda: sc.portal_screen(league)),
        ("media center wire stat leaders injuries awards", "Media center", m("media_center", "media_menu", league)),
        ("recap weekly week curate stories story kit podcast article", "Weekly Recap & story kit",
         m("recap", "screen", league)),
        ("upsets thrillers statements results", "Upsets & thrillers", m("media_hub", "upsets_screen", league)),
        ("games to watch big games next week matchups", "Games to watch", m("media_hub", "big_games_screen", league)),
        ("conference races title race", "Conference races", m("media_hub", "conf_races_screen", league)),
        ("coaches carousel hot seat candidates coordinators", "Coaches & carousel", m("coach_screens", "coaches_menu", league)),
        ("athletic directors ad market ads", "Athletic directors", m("ad_market", "screen", league)),
        ("weather forecast", "Weather center", m("weather_screens", "center", league, team)),
        ("settings options", "Settings", m("settings", "settings_menu", league)),
        ("manual help guide", "The manual", m("manual", "manual_screen", league)),
        ("edit rankings poll edit", "Edit the rankings", m("ranking_editor", "menu", league)),
    ]
    if career and team is not None:
        import recruiting_screens as rs
        out += [
            ("board recruiting board targets", "Recruiting board", lambda: rs.board_screen(league, team)),
            ("finder recruit finder search recruits", "Recruit finder", lambda: rs.finder(league, team)),
            ("class commits signees", "Your recruiting class", lambda: rs.class_view(league, team)),
            ("inbox messages mail email", "Inbox", m("people", "inbox_screen", league)),
            ("career my career contract goals", "My career", m("career", "career_screen", league)),
            ("staff coordinators assistants staff room", "My staff", m("staff_room", "manage", league)),
            ("develop coach upgrade", "Develop your coach", m("coach_dev", "develop_screen", league)),
            ("jobs pursue agent", "Pursue a job", m("job_market", "pursue_screen", league)),
            ("legacy trophy case achievements statue jerseys", "Legacy & trophy case", m("career_plus", "legacy_screen", league)),
            ("coaching tree assistants former", "Coaching tree (your assistants)", m("career_plus", "tree_screen", league)),
            ("storylines stories breakouts", "Storylines", m("career_plus", "storylines_screen", league)),
            ("report card grades ad", "Report cards from your AD", m("career_plus", "cards_screen", league)),
            ("non-conference nonconference scheduling next year schedule opener", "Next year's non-conference",
             m("career_plus", "nonconf_screen", league)),
            ("skill tree points", "Skill tree", m("skills", "tree_screen", league)),
            ("heads up alerts warnings", "Heads Up (alerts)", m("cp_alerts", "screen", league)),
            ("achievements trophies legacy score hall of fame", "Achievements", m("cp_ach", "screen", league)),
            ("story chapters start epilogue", "Your story (chapters)", m("cp_starts", "screen", league)),
        ]
    return out


def _score(words, q):
    """How well a query matches: every query word must start some word of the entry."""
    ws = words.lower().split()
    qs = q.lower().split()
    if not qs:
        return 0
    hit = 0
    for x in qs:
        if any(w.startswith(x) for w in ws):
            hit += 2 if any(w == x for w in ws) else 1
        else:
            return 0
    return hit


def results(league, q):
    """[(kind, label, open)] best first."""
    import screens as sc
    q = q.strip()
    low = q.lower()
    out = []
    for words, label, fn in _screens(league):
        s = _score(words + " " + label, q)
        if s:
            out.append((10 + s, "screen", label, fn))
    # teams: "texas", "texas schedule", "texas roster"
    tail = None
    for t_ in ("schedule", "roster", "depth", "history"):
        if low.endswith(" " + t_):
            tail, low = t_, low[: -len(t_) - 1].strip()
    if len(low) >= 3:
        for t in league.teams:
            name = f"{t.school} {t.nickname}".lower()
            if name.startswith(low) or t.school.lower() == low or low in name.split() or (len(low) >= 4 and low in name):
                exact = t.school.lower() == low
                rk = league.rankings.rank_of(t)
                tag = f"#{rk} " if rk else ""
                if tail == "schedule" or tail is None:
                    out.append((30 if exact else 18, "schedule", f"{tag}{t.school} schedule", lambda t=t: sc.schedule_view(league, t)))
                if tail == "history":
                    out.append((30 if exact else 18, "history", f"{tag}{t.school} program history",
                                lambda t=t: __import__("history_book").program_history(league, t)))
                if tail in ("roster", "depth"):
                    out.append((30 if exact else 18, "roster", f"{tag}{t.school} roster", lambda t=t: sc.roster_view(league, t)))
                if tail is None:
                    out.append((31 if exact else 19, "team", f"{tag}{t.school} {t.nickname}", lambda t=t: sc.team_view(league, t)))
    # people: players and coaches, by name
    if len(low) >= 4 and tail is None:
        mine = getattr(league, "user_team", None)
        for t in league.teams:
            for p in t.roster:
                if low in p.name.lower():
                    bonus = 6 if t is mine else 0
                    out.append((14 + bonus + (4 if p.name.lower() == low else 0), "player",
                                f"{p.position} {p.name} · {t.school}", lambda p=p: sc.player_card(league, p)))
            for c in (t.coach, getattr(t, "oc", None), getattr(t, "dc", None)):
                if c is not None and low in c.name.lower():
                    role = "HC" if c is t.coach else "OC" if c is getattr(t, "oc", None) else "DC"
                    out.append((15, "coach", f"{c.name} · {t.school} {role}",
                                lambda c=c: __import__("coach_screens").coach_view(league, c)))
    out.sort(key=lambda r: (-r[0], r[2]))
    seen, uniq = set(), []
    for r in out:
        if r[2] not in seen:
            seen.add(r[2])
            uniq.append(r)
    return uniq


KIND = {"screen": C.BCYAN, "team": C.BYELLOW, "schedule": C.BYELLOW, "roster": C.BYELLOW, "history": C.BYELLOW,
        "player": C.BGREEN, "coach": C.BMAGENTA}


def go(league, q=None):
    """The Go To box. Returns True when something was opened."""
    while True:
        if not q:
            clear()
            print(title_bar("GO TO"))
            print(paint("\n   A screen, a team, a player or a coach. Examples:", C.GRAY))
            for ex in ("depth chart", "board", "standings", "Texas", "Ohio State schedule", "a player's name", "hot seat"):
                print(paint(f"     · {ex}", C.GRAY))
            q = ask("Go to (Enter = back):")
            if not q:
                return False
        rows = results(league, q)
        if not rows:
            print(paint(f"\n   Nothing matches '{q}'. Try a screen ('roster', 'standings'), a school or a name.", C.BYELLOW))
            pause()
            q = None
            continue
        top = rows[0]
        if len(rows) == 1 or (top[0] >= 30 and (len(rows) < 2 or rows[1][0] < top[0])):
            top[3]()
            return True
        clear()
        print(title_bar(f"GO TO · {truncate(q.upper(), 40)}"))
        print()
        shown = rows[:18]
        for i, (_, kind, label, _fn) in enumerate(shown, 1):
            print(f"   {paint(f'[{i:>2}]', C.BYELLOW, C.BOLD)}  {paint(pad(kind, 9), KIND.get(kind, C.GRAY))}{label}")
        if len(rows) > len(shown):
            print(paint(f"\n   …and {len(rows) - len(shown)} more. Type more of the name to narrow it.", C.GRAY))
        c = ask("Open # (or type a new search, Enter = back):").strip()
        if not c:
            return False
        if c.isdigit() and 1 <= int(c) <= len(shown):
            shown[int(c) - 1][3]()
            return True
        q = c
