"""
screens.py — Everything the player sees: main menu, conference standings,
team view, full roster, and player cards.
"""
from itertools import zip_longest

from commentary import rivalry_name
from injuries import status_text
from league import CONFERENCES, League
import recruiting_screens
import saves
from rankings import TOP_N
from traits import blurbs, labels
from season import REGULAR_SEASON_WEEKS
import postseason as ps
from playbook import signature_plays
from models import (FUNDAMENTALS, FUNDAMENTAL_ABBR, FUNDAMENTAL_NAMES, POSITIONS,
                    POSITION_NAMES, PROFICIENCY_MAX, Coach, Team)
from ui import (C, WIDTH, ask, bar, clear, pad, paint, pause, proficiency_color,
                rating, rule, section, stars, title_bar, title_screen_lines, truncate)

COMING_SOON = []
_LEAGUE = [None]                  # the league on screen (the results rows mark instant classics)
FIRST_SOON = 12


# ═══ Main menu ══════════════════════════════════════════════════════════════

def main_menu(league: League):
    _LEAGUE[0] = league
    import scout
    scout.bind(league)                       # Coach Career: words, not numbers
    """The dashboard: a header, eight tabs, and a grid of live panels."""
    import dashboard
    tab = 1
    import guide
    while True:
        import ui as _ui
        _ui.CRUMB[0] = None
        guide.tip(league, guide.welcome_key(league) if tab == 1 else f"tab{tab}")   # the guided first week
        team = dashboard.render(league, tab)
        league._gui_at_dash = tab                    # the window's sidebar shortcuts only run from here
        try:
            choice = ask("Select:").strip().lower()
        finally:
            league._gui_at_dash = None
        calendar = (league.year, league.week, getattr(league, "mode", None),
                    getattr(getattr(league, "user_coach", None), "team", None))
        career = getattr(league, "mode", None) == "career" and getattr(league, "user_coach", None) is not None
        if choice.isdigit() and 1 <= int(choice) <= len(dashboard.TABS):
            tab = int(choice)
            continue
        handled = True
        import ui as _ui
        _ui.CRUMB[0] = f"{dashboard.TABS[tab - 1]} TAB" if choice else None     # the way back, on every screen's header
        # ── this tab's commands first ─────────────────────────────────────
        if tab == 2 and choice == "s":
            schedule_view(league, team)
        elif tab == 2 and choice == "w":
            schedule_menu(league)
        elif tab == 2 and choice == "f":
            import weather_screens
            weather_screens.center(league, team)
        elif tab == 2 and choice == "t":
            standings_menu(league)
        elif tab == 2 and choice == "o":
            import sos
            sos.screen(league, focus=team)
        elif tab == 2 and choice == "n" and career:
            import career_plus
            career_plus.nonconf_screen(league)
        elif tab == 3 and choice == "n" and career:
            import career_plus
            career_plus.storylines_screen(league)
        elif tab == 6 and choice == "l" and career:
            import career_plus
            career_plus.legacy_screen(league)
        elif tab == 6 and choice == "w" and career:
            import career_plus
            career_plus.tree_screen(league)
        elif tab == 2 and choice == "g":
            other = pick_team(league)
            if other:
                schedule_view(league, other)
        elif tab == 3 and choice == "r":
            roster_view(league, team)
        elif tab == 3 and choice == "p" and _is_mine(league, team) and getattr(league, "mode", None) == "career":
            import practice
            practice.screen(league, team)
        elif tab == 3 and choice == "t":
            team_view(league, team)
        elif tab == 3 and choice == "s":
            import team_stats
            team_stats.screen(league, team)
        elif tab == 3 and choice == "$":
            import finance_screens
            finance_screens.budget_screen(league, team)
        elif tab == 3 and choice == "o":
            other = pick_team(league)
            if other:
                team_view(league, other)
        elif tab in (3, 6) and choice == "f" and getattr(league, "mode", None) == "spectator":
            dashboard.pick_follow(league)
        elif tab in (3, 6, 7) and choice == "y":
            import compliance_screens
            compliance_screens.hub(league)
        elif tab == 4 and choice in ("r", "f", "b", "k"):
            t, readonly = recruiting_screens._context(league)
            if t is not None:
                league._recruit_readonly = readonly
                {"r": lambda: recruiting_screens.recruiting_menu(league),
                 "f": lambda: recruiting_screens.finder(league, t),
                 "b": lambda: recruiting_screens.board_screen(league, t),
                 "k": lambda: recruiting_screens.class_view(league, t)}[choice]()
        elif tab == 4 and choice == "p":
            portal_screen(league)
        elif tab == 4 and choice == "w":
            import transfer_watch
            transfer_watch.screen(league, getattr(league, "user_team", None) or team)
        elif tab == 4 and choice == "n":
            recruiting_screens.news_screen(league)
        elif tab == 5 and choice == "t":
            top_25(league)
        elif tab == 5 and choice in ("p", "c"):
            import committee_screens
            (committee_screens.playoff_rankings if choice == "p" else committee_screens.members_screen)(league)
        elif tab == 5 and choice == "h":
            heisman_race(league)
        elif tab == 5 and choice == "n":
            champions_history(league)
        elif tab == 5 and choice == "s":
            import stadium_screens
            stadium_screens.toughest_screen(league)
        elif tab == 5 and choice == "r":
            import record_screens
            record_screens.hub(league)
        elif tab == 5 and choice == "f":
            import halloffame
            halloffame.hub(league)
        elif tab == 5 and choice == "o":
            import sos
            sos.screen(league)
        elif tab == 5 and choice == "e":
            import ranking_editor
            ranking_editor.menu(league)
        elif tab == 6 and choice == "c" and career:
            import career as career_mod
            career_mod.career_screen(league)
        elif tab == 6 and choice == "t" and career:
            import skills
            skills.tree_screen(league)
        elif tab == 6 and choice == "d" and career:
            import coach_dev
            coach_dev.develop_screen(league)
        elif tab == 6 and choice == "s" and career:
            import staff_screens
            import staff_room
            staff_room.manage(league)
        elif tab == 6 and choice == "p" and team.coach is not None:
            import coach_screens
            coach_screens.coach_view(league, team.coach)
        elif tab == 6 and choice == "k":
            import coach_screens
            coach_screens.coaches_menu(league)
        elif tab == 7 and choice == "h":
            import history_screens
            history_screens.lookup_screen(league)
        elif tab == 7 and choice == "m":
            import media_center
            media_center.media_menu(league)
        elif tab == 7 and choice == "n":
            recruiting_screens.news_screen(league)
        elif tab == 7 and choice == "k":
            import coach_screens
            coach_screens.carousel_news(league)
        elif tab == 8 and choice == "h":
            import manual
            manual.manual_screen(league)
        elif tab == 8 and choice == "s":
            import settings
            settings.settings_menu(league)
        elif tab == 8 and choice == "e":
            import export_sheets
            export_sheets.export_screen(league)
        elif tab == 8 and choice == "l" and league.__dict__.get("online_client"):
            print(paint("\n   You're in an online world. [Q] to the title screen first, then load.", C.BYELLOW))
            pause()
        elif tab == 8 and choice == "l":
            loaded = saves.load_screen()
            if loaded is not None:
                league = loaded                  # every screen takes the league it's handed
                continue
        else:
            handled = False
        # ── anywhere ──────────────────────────────────────────────────────
        if not handled and choice in ("a", "m", "x"):
            from netplay import lobby
            if lobby.active(league):                     # online: the week is everyone's
                if choice != "a":
                    print(paint("\n   Online, weeks move when everyone's ready: [A] plays your week.", C.BYELLOW))
                    pause()
                    continue
                from netplay import turn
                new = turn.play(league)
                if new is not None:
                    league = new                         # the host's world, with your week in it
                    from netplay import capture
                    capture.begin(league, league.user_team)
                continue
        if not handled:
            if choice == "a":
                import preseason
                if league.season_complete:
                    season_wrap(league)
                elif preseason.needed(league):
                    if preseason.hub(league):             # fall camp first, then straight into Week 1
                        gameday(league)
                else:
                    gameday(league)
            elif choice in ("m", "x"):
                if league.season_complete:
                    print(paint("\n   The season is over. Advance to the offseason first.", C.BYELLOW))
                    pause()
                else:
                    bulk_sim(league)
            elif choice == "c" and career:
                import career as career_mod
                career_mod.career_screen(league)
            elif choice == "c" and getattr(league, "mode", None) == "ad" and getattr(league, "ad_user", None):
                import ad_mode
                ad_mode.office(league)
            elif choice == "i" and career:
                import people
                people.inbox_screen(league)
            elif choice == "c" and getattr(league, "mode", None) == "spectator":
                import recap
                recap.screen(league)                      # the week's Recap and [C] curate stories
            elif choice == "b" and getattr(league, "mode", None) == "spectator":
                import book_screens
                book_screens.hub(league)                 # The Window: the sportsbook
            elif choice == "v":
                saves.save_screen(league)
            elif choice in ("?", "help", "manual"):
                import manual
                manual.manual_screen(league)
            elif choice.startswith("/") or choice in ("g", "go", "goto"):
                import jump
                jump.go(league, choice.lstrip("/").strip() or None)
            elif len(choice) >= 3 and choice not in ("q", "quit", "exit"):
                import jump
                jump.go(league, choice)
            elif choice in ("q", "quit", "exit"):
                clear()
                print(paint("\n   Saving and returning to the title screen…", C.GRAY), flush=True)
                saves.autosave(league)
                return "menu"
        _ui.CRUMB[0] = None
        # The calendar moved (a week, the offseason, a new job): keep the autosave current,
        # and land on HOME so the new poll, results and news are the first thing on screen.
        if calendar != (league.year, league.week, getattr(league, "mode", None),
                        getattr(getattr(league, "user_coach", None), "team", None)):
            saves.autosave(league)
            tab = 1


# ═══ Standings ══════════════════════════════════════════════════════════════

def standings_menu(league: League):
    while True:
        clear()
        print(title_bar("CONFERENCE STANDINGS"))
        print()
        for i, (short, full, color) in enumerate(CONFERENCES, start=1):
            count = len(league.conference_teams(short))
            print(f"   {paint(f'[{i:>2}]', C.BYELLOW)}  {pad(paint(full, color, C.BOLD), 34)}"
                  f"{paint(f'{count} teams', C.GRAY)}")
        print(f"   {paint('[ A]', C.BYELLOW)}  {paint('All Conferences', C.BWHITE, C.BOLD)}")
        print(f"   {paint('[ B]', C.GRAY, C.BOLD)}  Back")

        import webview
        if webview.on():
            webview.emit("confs", {"rows": [{"key": str(i), "name": full, "short": short,
                                             "count": len(league.conference_teams(short)),
                                             "color": webview._color(league, type("T", (), {"conference": short})())}
                                            for i, (short, full, color) in enumerate(CONFERENCES, start=1)]})
        choice = ask("Select a conference:").lower()
        if choice in ("b", "back", ""):
            return
        if choice == "a":
            show_standings(league, [c[0] for c in CONFERENCES])
        elif choice.isdigit() and 1 <= int(choice) <= len(CONFERENCES):
            show_standings(league, [CONFERENCES[int(choice) - 1][0]])


def _standings_header():
    return paint(
        f"   {'#':>3}  {'RK':<4}{'TEAM':<30}{'CONF':>6}{'ALL':>7}   {'PRS':>3}  {'OFF':>3}  {'DEF':>3}  "
        f"{'CCH':>3}  {'TM':>3}  STADIUM", C.GRAY, C.BOLD)


def _standings_row(idx, team, league=None):
    name = paint(truncate(team.full_name, 29), C.BWHITE)
    stadium = paint(truncate(f"{team.stadium} ({team.capacity:,})", 22), C.GRAY)
    rk = league.rankings.rank_of(team) if league is not None else None
    return (f"   {paint(f'{idx:>3}', C.GRAY)}  {paint(pad(f'#{rk}' if rk else '', 4), C.BYELLOW)}{pad(name, 30)}"
            f"{team.conf_record:>6}{team.record:>7}   "
            f"{rating(team.prestige)}  {rating(team.ratings['offense'])}  {rating(team.ratings['defense'])}  "
            f"{rating(team.ratings['coach'])}  {__import__('scout').team_short(team.team_ovr, who=team)}  {stadium}")


def show_standings(league: League, conferences):
    while True:
        clear()
        numbered = []
        for conf in conferences:
            color = league.conference_color(conf)
            print(title_bar(league.conference_full_name(conf).upper(), color))
            print(_standings_header())
            for div in league.divisions(conf):
                if div:
                    print(paint(f"   ── {div} Division ──", color, C.BOLD))
                for team in league.standings(conf, div):
                    numbered.append(team)
                    print(_standings_row(len(numbered), team, league))
            print()
        started = any(t.wins or t.losses for t in numbered)
        print(paint("   RK this week's poll · ALL overall record · PRS prestige · OFF/DEF/CCH program ratings · TM roster"
                    + ("" if started else " · no games yet: ordered by prestige"), C.GRAY))
        import ui as _u
        _u.footer(_u.key("#", "team page"), _u.key("S#", "that team's schedule"), _u.key("B", "back", C.GRAY))
        import webview
        if webview.on():
            try:
                me = getattr(league, "user_team", None)
                blocks, n = [], 0
                for conf in conferences:
                    divs = []
                    for div in league.divisions(conf):
                        rows = []
                        for team in league.standings(conf, div):
                            n += 1
                            rows.append({"n": n, "school": team.school, "rank": league.rankings.rank_of(team),
                                         "conf": team.conf_record, "all": team.record, "prs": team.prestige,
                                         "me": team is me})
                        divs.append({"name": div or "", "rows": rows})
                    blocks.append({"name": league.conference_full_name(conf),
                                   "color": webview._color(league, type("T", (), {"conference": conf})()), "divs": divs})
                webview.emit("standings", {"confs": blocks, "started": started})
            except Exception:
                pass
        choice = ask("Select:").strip().lower()
        if not choice or choice == "b":
            return
        if choice.startswith("s") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= len(numbered):
            schedule_view(league, numbered[int(choice[1:]) - 1])
        elif choice.isdigit() and 1 <= int(choice) <= len(numbered):
            team_view(league, numbered[int(choice) - 1])


# ═══ Team selection ═════════════════════════════════════════════════════════

def pick_team(league: League):
    query = ask("Team name (e.g. Ohio State, Auburn, Tigers — Enter = cancel):")
    if not query or query.lower() in ("b", "back"):
        return None
    matches = league.search(query)
    if not matches:
        print(paint(f"\n  No team matches '{query}'.", C.BRED))
        pause()
        return None
    if len(matches) == 1:
        return matches[0]

    print()
    for i, t in enumerate(matches[:25], start=1):
        print(f"   {paint(f'[{i:>2}]', C.BYELLOW)}  {pad(t.full_name, 32)}"
              f"{paint(t.conference, league.conference_color(t.conference))}")
    choice = ask("Which one?")
    if choice.isdigit() and 1 <= int(choice) <= min(25, len(matches)):
        return matches[int(choice) - 1]
    return None


# ═══ Team view ══════════════════════════════════════════════════════════════

def team_view(league: League, team: Team):
    while True:
        clear()
        _print_team_page(league, team)
        import team_momentum
        if team.wins + team.losses and not getattr(team, "fcs", False):
            print(paint(f"   Season form: {team_momentum.line(team)}", C.GRAY))
        print(rule())
        k = lambda x: paint(f"[{x}]", C.BYELLOW)
        print(f"   {paint('TEAM    ', C.GRAY)}{k('R')} Roster   {k('P')} Player card   {k('S')} Schedule & results   "
              + (f"{paint('[H]', C.BGREEN)} Depth chart   {paint('[U]', C.BGREEN)} Formation subs   {paint('[A]', C.BGREEN)} Sim strategy   " if _is_mine(league, team) else "")
              + f"{k('K')} Locker room")
        print(f"   {paint('PROGRAM ', C.GRAY)}{k('C')} Coach & program   {k('O')} OC   {k('D')} DC   {k('$')} Budget   "
              f"{k('F')} Facilities   {k('J')} Team builder")
        print(f"   {paint('HISTORY ', C.GRAY)}{paint('[Y]', C.BGREEN, C.BOLD)} Full program history   {k('V')} Rivalries   "
              f"{k('I')} Instant classics   {k('E')} Record book   {k('G')} Hall of Fame   {paint('[B]', C.GRAY, C.BOLD)} Back")
        _wv_team(league, team)
        choice = ask("Select:").lower()
        if choice in ("b", "back", ""):
            return
        if choice == "r":
            roster_view(league, team)
        elif choice == "h" and _is_mine(league, team):
            depth_chart(league, team)
        elif choice == "u" and _is_mine(league, team):
            import formation_subs
            formation_subs.screen(league, team)
        elif choice == "a" and _is_mine(league, team):
            import sim_strategy
            sim_strategy.screen(league, team)
        elif choice == "p":
            _open_player(league, team)
        elif choice == "s":
            schedule_view(league, team)
        elif choice == "c":
            import coach_screens
            coach_screens.program_view(league, team)
        elif choice in ("$", "m"):
            import finance_screens
            finance_screens.budget_screen(league, team)
        elif choice == "f":
            import finance_screens
            finance_screens.facilities_screen(league, team)
        elif choice == "y":
            import history_book
            history_book.program_history(league, team)
        elif choice == "v":
            import rivalries
            rivalries.team_rivalries(league, team)
        elif choice == "k":
            import personalities
            personalities.locker_room(league, team)
        elif choice == "i":
            import classics
            classics.classics_screen(league, team)
        elif choice == "e":
            import record_screens
            record_screens.hub(league, team.school)
        elif choice == "g":
            import halloffame
            halloffame.program_screen(league, team.school)
        elif choice == "j":
            import team_builder
            team_builder.team_menu(league, team)
        elif choice in ("o", "d") and getattr(team, "oc" if choice == "o" else "dc", None) is not None:
            import coach_screens
            coach_screens.coach_view(league, getattr(team, "oc" if choice == "o" else "dc"))


def _is_mine(league, team):
    """Your program in a career (or the one you run as AD): the depth chart is yours to set."""
    if getattr(league, "mode", None) == "career":
        return getattr(league, "user_team", None) is team
    return False


def depth_chart(league: League, team: Team):
    """Set the depth chart: who starts, who's next, and who changes positions.
    The order you set is the order the game uses — lineups, snaps, and the two-deep."""
    import guide
    if _is_mine(league, team):
        guide.tip(league, "depth")
    from models import STARTING_LINEUP
    import playbook as pb
    import staff as st
    order = team.__dict__.setdefault("depth_order", {})
    scheme = st.play_caller(team, "off").offense_scheme
    pers = pb.OFFENSE_SCHEMES.get(scheme, {}).get("personnel", {"11": 1})
    base = max(pers, key=pers.get)
    starts = dict(STARTING_LINEUP)
    starts.update(RB=int(base[0]), TE=int(base[1]), WR=5 - int(base[0]) - int(base[1]))
    pos_i = 0
    msg = ""
    while True:
        clear()
        color = league.conference_color(team.conference)
        pos = POSITIONS[pos_i]
        print(title_bar(f"{team.school.upper()} · DEPTH CHART · {POSITION_NAMES[pos].upper()}", color))
        staff_set = getattr(team, "depth_set", None) == league.year
        print(paint(f"   Base offense: {pb.PERSONNEL_NAMES.get(base, base)} ({scheme}). "
                    f"Starters at {pos}: {starts.get(pos, 1)}.  "
                    + (f"Set by your staff for {league.year} camp — yours to change."
                       if staff_set and order.get(pos) else "Your order." if order.get(pos) else
                       ("Sorted by your staff's grades" if __import__('scout').hidden(league) else "Sorted by overall")
                       + " (you haven't set this one)."), C.GRAY))
        ideas = [x for x in getattr(team, "depth_ideas", []) if x[4] == league.year and x[0] in team.roster
                 and x[0].position == x[1]]
        for i, (p, q, to, why, _) in enumerate(ideas, 1):
            print(paint(f"   {'Staff idea' if i == 1 else '          '} [S{i}] move #{p.number} {p.name} from {q} to {to} "
                        f"— {why}", C.BYELLOW))
        print("   " + "  ".join(paint(f"[{q}]", C.BYELLOW if q == pos else C.GRAY) for q in POSITIONS))
        print()
        players = team.players_at(pos)
        import scout
        hide = scout.hidden(league)
        if hide:
            import practice
            prac = practice.run(league, team)
            print(paint(f"   {'SLOT':<6}{'#':>3}  {'NAME':<22}{'YR':<7}{'LOOKS LIKE':<20}THIS WEEK IN PRACTICE", C.GRAY, C.BOLD))
        else:
            print(paint(f"   {'SLOT':<6}{'#':>3}  {'NAME':<22}{'YR':<7}{'OVR':>3}   {'NEXT BEST SPOT':<16}STATUS", C.GRAY, C.BOLD))
        for i, p in enumerate(players, 1):
            tag = paint("START", C.BGREEN, C.BOLD) if i <= starts.get(pos, 1) else paint(f"{i}", C.GRAY)
            alt_pos, alt_ovr = p.best_alternate()
            status = paint(status_text(p, short=True), C.BRED) if p.inj_games > 0 else ""
            if hide:
                text, form = prac.get(id(p), ("", 0))
                col = C.BGREEN if form >= 0.8 else C.BRED if form <= -0.8 else C.GRAY
                head = (f"   {pad(tag, 6)}{paint(f'{p.number:>3}', C.GRAY)}  {pad(truncate(p.name, 21), 22)}"
                        f"{p.class_label:<7}{pad(scout.ovr(p), 20)}")
                if len(text) <= 36:
                    print(head + paint(text, col) + status)
                else:                                          # long lines wrap under the practice column
                    import textwrap
                    wrapped = textwrap.wrap(text, 36)
                    print(head + paint(wrapped[0], col) + status)
                    for more in wrapped[1:]:
                        print(" " * 63 + paint(more, col))
                continue
            print(f"   {pad(tag, 6)}{paint(f'{p.number:>3}', C.GRAY)}  {pad(truncate(p.name, 21), 22)}"
                  f"{p.class_label:<7}{rating(p.overall)}   {paint(pad(f'{alt_pos} {alt_ovr}', 16), C.GRAY)}{status}")
        if not players:
            print(paint("   Nobody plays here right now.", C.BYELLOW))
        print(rule())
        print(paint("   [N]/[P] next/previous position · type a position (TE) to jump · [M a b] move slot a to slot b\n"
                    "   [C # POS] change a player's position (C 82 OL) · " + ("[S#] take a staff idea · " if ideas else "")
                    + ("[R] use the staff's recommendation here · [W] practice report" if hide else
                       "[R] reset this position to overall") + " · [B] back", C.GRAY))
        if msg:
            print(paint("   " + msg, C.BCYAN, C.BOLD))
        import webview
        if webview.on():
            try:
                rows = []
                for i, p in enumerate(players, 1):
                    r = {"i": i, "id": webview.pid(p), "num": p.number, "name": p.name, "yr": p.class_label,
                         "ovr": webview.plain(scout.ovr(p)) if hide else p.overall, "starter": i <= starts.get(pos, 1),
                         "hurt": webview.plain(status_text(p, short=True)) if p.inj_games > 0 else ""}
                    if hide:
                        r["practice"] = prac.get(id(p), ("", 0))[0]
                    else:
                        ap, ao = p.best_alternate()
                        r["alt"] = f"{ap} {ao}"
                    rows.append(r)
                webview.emit("depth2", {"school": team.school, "pos": pos, "posName": POSITION_NAMES[pos],
                                        "positions": list(POSITIONS), "starts": starts.get(pos, 1), "hide": hide,
                                        "base": f"{pb.PERSONNEL_NAMES.get(base, base)} ({scheme})", "rows": rows,
                                        "ideas": [{"key": f"s{i}", "text": f"Move #{p.number} {p.name} from {q} to {to} — {why}"}
                                                  for i, (p, q, to, why, _) in enumerate(ideas, 1)], "msg": msg})
            except Exception:
                pass
        msg = ""
        raw = ask("Depth chart:").strip()
        c = raw.lower()
        parts = raw.split()
        if c in ("", "b"):
            return
        if c == "n":
            pos_i = (pos_i + 1) % len(POSITIONS)
        elif c == "p":
            pos_i = (pos_i - 1) % len(POSITIONS)
        elif raw.upper() in POSITIONS:
            pos_i = POSITIONS.index(raw.upper())
        elif c == "w" and hide:
            import practice
            practice.screen(league, team)
        elif c == "r" and hide:
            import practice
            order[pos] = practice.recommend(league, team)[pos]
            msg = f"{pos} now follows the staff's recommendation."
        elif c == "r":
            order.pop(pos, None)
            msg = f"{pos} is back to best-overall order."
        elif parts and parts[0].lower() == "m" and len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
            a, b = int(parts[1]) - 1, int(parts[2]) - 1
            if 0 <= a < len(players) and 0 <= b < len(players):
                lst = list(players)
                who = lst.pop(a)
                lst.insert(b, who)
                order[pos] = lst
                msg = f"{who.name} moves to slot {b + 1} at {pos}."
            else:
                msg = "Those slots aren't on the chart."
        elif len(c) == 2 and c[0] == "s" and c[1].isdigit() and 1 <= int(c[1]) <= len(ideas):
            p, q, to, why, _ = ideas[int(c[1]) - 1]
            import depth
            depth.apply_move(league, team, p, to)
            import scout
            msg = (f"{p.name} moves from {q} to {to} ({scout.ovr_plain(p.overall)} there). The staff has him "
                   f"{'starting' if p in team.players_at(to)[:starts.get(to, 1)] else 'in the rotation'}.")
            import practice
            order[to] = practice.recommend(league, team)[to]
            pos_i = POSITIONS.index(to)
        elif parts and parts[0].lower() == "c" and len(parts) == 3 and parts[1].isdigit() \
                and parts[2].upper() in POSITIONS:
            who = team.find_player(int(parts[1]))
            new = parts[2].upper()
            if who is None:
                msg = f"Nobody wears #{parts[1]}."
            elif who.position == new:
                msg = f"{who.name} already plays {new}."
            else:
                before, after = who.overall, who.overall_at(new)
                old = who.position
                if old in order and who in order[old]:
                    order[old].remove(who)
                who.position = new
                who.events[league.year].append(f"Moved from {old} to {new}")
                import scout
                msg = (f"{who.name} moves from {old} ({scout.ovr_plain(before)}) to {new} ({scout.ovr_plain(after)}). "
                       f"He'll get better at it with reps and an offseason of work.")
                pos_i = POSITIONS.index(new)
        else:
            msg = "Try N, P, a position (TE), M 2 1, C 82 OL, R, S1 (a staff idea), or B."


def _home_field(league, team):
    """Toughest-places rank, the noise and the home record, in one line."""
    import stadium as sd
    rk = sd.rank_of(league, team)
    w, l, _, _, _ = sd.season_home(league, team)
    nr = sd.noise_rating(team)
    return (f"No. {rk} toughest place to play" if rk else "") + paint(
        f"  · {sd.noise_word(nr).lower()} ({nr}/10)" + (f" · {w}-{l} at home" if w + l else ""), C.GRAY)


def _crowd_note(league, team):
    import finance_screens
    n, avg, fill, sold = finance_screens.season_crowds(league, team)
    if not n:
        return ""
    return paint(f"  · avg {avg:,} ({fill * 100:.0f}%), {sold} sellout{'s' if sold != 1 else ''}", C.GRAY)


_TP = {}


def _wv_team(league, team):
    import webview
    if not webview.on():
        return
    try:
        import facilities as fa
        import team_momentum
        from models import Coach
        f = fa.ensure(team)
        coach = team.coach
        ratings = []
        for k in Team.RATING_KEYS:
            v = team.ratings[k]
            if k == "facilities":
                v = round((f["recruiting"] * 0.4 + f["training"] * 0.3 + f["stadium"] * 0.3) * 10)
            ratings.append({"label": Team.RATING_LABELS[k], "v": v})
        d = {"rank": league.rankings.rank_of(team), "full": team.full_name, "chant": team.chant,
             "color": webview._color(league, team), "mine": _is_mine(league, team),
             "info": [[l, v] for l, v in _TP.get("info", [])], "summary": [[l, webview.plain(v)] for l, v in _TP.get("summary", [])],
             "facilities": [{"k": fa.SHORT[k], "v": f[k], "grade": fa.grade(f[k])} for k in fa.KINDS],
             "ratings": ratings, "titles": ps.titles_for(league, team.school),
             "history": [{"yr": r[0], "rec": f"{r[1]}-{r[2]}", "conf": f"{r[3]}-{r[4]} {r[6] if len(r) > 6 else team.conference}",
                          "ach": list(r[5]) if len(r) > 5 and r[5] else []}
                         for r in [x for x in team.historical_records if x[0] >= 2026][-5:]][::-1],
             "form": webview.plain(team_momentum.line(team)) if team.wins + team.losses and not getattr(team, "fcs", False) else "",
             "injuries": [{"id": webview.pid(p), "pos": p.position, "name": p.name, "status": webview.plain(status_text(p))}
                          for p in team.injured()[:8]]}
        if coach is not None:
            from traits import blurbs as _blurbs
            d["coach"] = {"name": coach.name, "ratings": [{"label": Coach.RATING_LABELS[k], "v": coach.ratings[k]} for k in Coach.RATING_KEYS],
                          "traits": [n for n, _ in _blurbs(coach)] if labels(coach) else [],
                          "style": f"{coach.offense_scheme} offense · {coach.defense_scheme} defense"}
        webview.emit("team", d)
    except Exception:
        pass


def _print_team_page(league: League, team: Team):
    color = league.conference_color(team.conference)

    rank = league.rankings.rank_of(team)
    header = (f"#{rank}  " if rank else "") + team.full_name.upper()
    print(title_bar(header, color))
    print(pad(paint(f"“ {team.chant} ”", C.BYELLOW, C.BOLD, C.ITALIC), WIDTH, "center"))
    if rank:
        print(pad(paint(f"Ranked #{rank} in this week's Top 25", C.BYELLOW), WIDTH, "center"))
    print()

    hist = getattr(team, "conf_history", None)
    moved = ""
    if hist and len(hist) > 1:
        moved = paint(f"  since {hist[-1][0]} (was {hist[-2][1]})", C.GRAY)
    import realignment
    going = next((m for m in realignment.state(league)["pending"] if m["school"] == team.school), None)
    if going:
        moved += paint(f"  → {going['to']} in {going['effective']}", C.BMAGENTA)
    info = [
        ("Conference", paint(team.conference_label, color, C.BOLD) + moved),
        ("Stadium", team.stadium),
        ("Capacity", f"{team.capacity:,}" + _crowd_note(league, team)),
        ("Home field", _home_field(league, team)),
        ("Record", f"{team.record}  ({team.conf_record} {team.conference})"),
    ]
    games = league.team_games(team)
    last = next((g for g in reversed(games) if g.played), None)
    nxt = next((g for g in games if not g.played), None)

    def _vs(g):
        opp = g.opponent_of(team)
        r = (getattr(g, "ranks", None) or {}).get(opp) if g.played else league.rankings.rank_of(opp)
        return f"{'vs' if g.home is team or g.neutral else 'at'} {'#' + str(r) + ' ' if r else ''}{opp.school}"
    if last is not None:
        won = last.winner is team
        info.append(("Last game", paint("W" if won else "L", C.BGREEN if won else C.BRED, C.BOLD)
                     + f" {last.score_for(team)}-{last.score_for(last.opponent_of(team))} {_vs(last)}"))
    if nxt is not None:
        wk = league.week_name(nxt.week) if nxt.week <= REGULAR_SEASON_WEEKS else nxt.game_type
        info.append(("Next game", f"{_vs(nxt)}  {paint(wk, C.GRAY)}"))
    import sos
    srow = sos.of(league, team)
    if srow and srow.get("rank_full"):
        info.append(("Schedule", sos.tag(srow["rank_full"]) + paint(f" SoS · opp {sos.opp_record(srow)}", C.GRAY)))
    import personalities
    caps = [p for p in getattr(team, "captains", None) or [] if p in team.roster]
    chem = personalities.chemistry(team)
    info.append(("Locker room", f"{personalities.chem_word(chem)} ({chem:.0f})"
                 + (paint("  · captains " + ", ".join(p.last_name for p in caps), C.GRAY) if caps else "")))
    drafts = getattr(league, "drafts", {})
    picks = [x for yr in drafts.values() for x in yr if x["school"] == team.school]
    if picks:
        n = len(drafts)
        info.append(("Pro League Draft", f"{len(picks)} pick{'s' if len(picks) != 1 else ''} in the last {n} draft{'s' if n != 1 else ''} "
                                  f"({sum(x['round'] == 1 for x in picks)} in round 1)"))
    if getattr(team.coach, "seat", None) is not None:
        import coach_screens
        info.append(("Head Coach", f"{team.coach.name} ({team.coach.hired_year or '—'})  "
                                  f"seat {coach_screens.seat_tag(team.coach).strip()}"))
    for label, c in (("Off. Coord.", getattr(team, "oc", None)), ("Def. Coord.", getattr(team, "dc", None))):
        if c is not None:
            info.append((label, f"{c.name}  {rating(c.overall)}  {paint(c.offense_scheme if label.startswith('Off') else c.defense_scheme, C.GRAY)}"))
    import staff as _staff
    if team.coach is not None:
        bits = []
        for side, lab in (("off", "Off"), ("def", "Def")):
            cl = _staff.play_caller(team, side)
            who = "HC " + cl.name.split()[-1] if cl is team.coach else ("OC " if side == "off" else "DC ") + cl.name.split()[-1]
            bits.append(f"{lab}: {who} {paint('(' + (cl.offense_scheme if side == 'off' else cl.defense_scheme) + ')', C.GRAY)}")
        info.append(("Play calls", "  ".join(bits)))
    import finance as fi
    info.append(("Budget", f"{fi.money(fi.budget(team))}/yr  {paint('· NIL on roster ' + fi.money(fi.roster_nil(team)), C.GRAY)}"))
    summary = [
        ("Prestige", f"{rating(team.prestige)}  {stars(max(1, round(team.prestige / 20)))}"),
        ("Team", __import__("scout").team(team.team_ovr)),
        ("Offense", __import__("scout").team(team.offense_ovr)),
        ("Defense", __import__("scout").team(team.defense_ovr)),
    ]
    _TP["info"], _TP["summary"] = list(info), list(summary)
    from ui import clip
    for (l1, v1), (l2, v2) in zip_longest(info, summary, fillvalue=("", "")):
        left = f"   {paint(f'{l1:<12}', C.GRAY)}{v1}"
        if not l2:                                            # nothing beside it: the line gets the full width
            print(clip(left, WIDTH - 1))
            continue
        right = f"{paint(f'{l2:<13}', C.GRAY)}{v2}"
        print(pad(clip(left, 61), 62) + right)

    import facilities as fa
    f = fa.ensure(team)
    print("   " + paint("Facilities  ", C.GRAY) + "   ".join(
        f"{fa.SHORT[k]} {paint(str(f[k]), C.BWHITE, C.BOLD)}/10 {paint(fa.grade(f[k]), C.GRAY)}" for k in fa.KINDS)
        + paint("   [F] facilities", C.GRAY))
    print()
    print(section("PROGRAM RATINGS", color))
    print(paint("   The school's reputation, which builds prestige — not this year's roster (Team/Offense/Defense).",
                C.GRAY))
    keys = Team.RATING_KEYS
    half = len(keys) // 2
    for k1, k2 in zip(keys[:half], keys[half:]):
        cells = []
        for k in (k1, k2):
            v = team.ratings[k]
            if k == "facilities":                      # the same buildings as the tiers above, on one scale
                v = round((f["recruiting"] * 0.4 + f["training"] * 0.3 + f["stadium"] * 0.3) * 10)
            cells.append(f"{paint(f'{Team.RATING_LABELS[k]:<18}', C.WHITE)}{rating(v)}  {bar(v, 22)}")
        print("   " + pad(cells[0], 50) + cells[1])

    titles = ps.titles_for(league, team.school)
    if titles:
        print()
        print(pad(paint(f"🏆 National champions: {', '.join(str(y) for y in titles)}", C.BYELLOW, C.BOLD),
                  WIDTH, "center"))
    active_history = [rec for rec in team.historical_records if rec[0] >= 2026]
    if active_history or getattr(team, "achievements", []):
        print()
        print(section("PROGRAM HISTORY & ACHIEVEMENTS", color))
        for rec in active_history[-5:]:
            yr, w, l, cw, cl = rec[:5]
            ach = rec[5] if len(rec) > 5 else []
            then = rec[6] if len(rec) > 6 else team.conference
            ach_str = paint(f"  🏆 {', '.join(ach)}", C.BYELLOW) if ach else ""
            print(f"   {paint(str(yr), C.GRAY)}   {w}-{l}  ({cw}-{cl} {then}){ach_str}")
        if getattr(team, "achievements", []):
            ach_str = paint(f"  🏆 {', '.join(team.achievements)}", C.BYELLOW)
            print(f"   {paint('CUR ', C.GRAY)}  {team.wins}-{team.losses}  ({team.conf_wins}-{team.conf_losses} {team.conference}){ach_str}")

    print()
    coach = team.coach
    print(section(f"HEAD COACH  ·  {paint(coach.name.upper(), C.BWHITE, C.BOLD)}", color))
    keys = Coach.RATING_KEYS
    from traits import POSITION_SCOPE
    boost = {"trench_dev": "Trench Guru", "passing_dev": "QB Whisperer"}
    for k1, k2 in zip(keys[:3], keys[3:]):
        cells = []
        for k in (k1, k2):
            v = coach.ratings[k]
            tag = ""
            if k in boost and boost[k] in labels(coach):
                tag = paint(" +15%", C.BYELLOW)            # the trait lands on top of the rating
            cells.append(f"{paint(f'{Coach.RATING_LABELS[k]:<25}', C.WHITE)}{rating(v)}  {bar(v, 15)}{tag}")
        print("   " + pad(cells[0], 50) + cells[1])

    if labels(coach):
        from traits import blurbs as _blurbs
        print(paint(f"   {'Traits':<25}" + " · ".join(f"{n} ({b[0].lower() + b[1:]})" for n, b in _blurbs(coach)),
                    C.BYELLOW))
    off_sig, def_sig = signature_plays(coach)
    fourth = "conservative" if coach.aggression < 42 else "aggressive" if coach.aggression >= 68 else "balanced"
    bl = getattr(coach, "blitz", None)
    bl = coach.aggression if bl is None else bl
    blitz_w = "sits in coverage" if bl < 38 else "brings it" if bl >= 65 else "picks his spots"
    print(paint(f"   {'Style':<25}{coach.offense_scheme} offense · {coach.defense_scheme} defense · "
                f"4th down: {fourth} · blitz: {blitz_w}", C.GRAY))
    if _is_mine(league, team):
        import sim_strategy as _ss
        _sy = _ss.ensure(team)
        print(paint(f"   {'Sim strategy':<25}{_ss.LABELS[_sy['identity']]} · PA {_sy['play_action']} · shots {_sy['shots']} · 4th {_sy['fourth']}", C.GRAY))
    if off_sig or def_sig:
        print(paint(f"   {'Goes to':<25}" + ", ".join(off_sig + def_sig), C.GRAY))

    cycle = getattr(league, "recruiting", None)
    if cycle is not None:
        commits = cycle.commitments(team)
        avg = sum(r.stars for r in commits) / len(commits) if commits else 0
        print(paint(f"   {'Recruiting':<25}{len(commits)} commit{'s' if len(commits) != 1 else ''} for {league.year + 1}"
                    + (f" · {avg:.2f} stars · class rank #{cycle.class_rank(team)}" if commits else " · class unranked"),
                    C.GRAY))

    hurt = team.injured()
    if hurt:
        print()
        print(section(f"INJURY REPORT  ·  {len(hurt)} OUT", color))
        for p in hurt[:8]:
            print(f"   {paint(f'{p.position:<3}', C.BCYAN)}{pad(truncate(p.name, 22), 23)}"
                  f"{__import__('scout').ovr_short(p)}  {paint(status_text(p), C.BRED if p.inj_games >= 99 else C.YELLOW)}")
        if len(hurt) > 8:
            print(paint(f"   …and {len(hurt) - 8} more", C.GRAY))

    print()
    import playbook as _pb
    import staff as _st
    scheme = _st.play_caller(team, "off").offense_scheme if team.coach is not None else None
    pers = _pb.OFFENSE_SCHEMES.get(scheme, {}).get("personnel", {"11": 1})
    base = max(pers, key=pers.get)
    n_rb, n_te = int(base[0]), int(base[1])
    n_wr = 5 - n_rb - n_te
    print(section(f"STARTING LINEUP  ·  base offense {_pb.PERSONNEL_NAMES.get(base, base)}"
                  + (f" ({scheme})" if scheme else ""), color))
    starters = {pos: list(v) for pos, v in team.starters().items()}
    starters["RB"] = [p for p in team.players_at("RB") if p.inj_games <= 0][:n_rb] or starters["RB"]
    starters["TE"] = [p for p in team.players_at("TE") if p.inj_games <= 0][:n_te] or starters["TE"]
    starters["WR"] = [p for p in team.players_at("WR") if p.inj_games <= 0][:n_wr] or starters["WR"]
    offense = [(pos, p) for pos in ("QB", "RB", "WR", "TE", "OL") for p in starters[pos]]
    defense = [(pos, p) for pos in ("DL", "LB", "CB", "S") for p in starters[pos]]
    print(paint(f"   {'OFFENSE':<46}DEFENSE", C.GRAY, C.BOLD))
    for o, d in zip_longest(offense, defense):
        print("   " + pad(_lineup_cell(o), 46) + _lineup_cell(d))
    st = [(pos, p) for pos in ("K", "P") for p in starters[pos]]
    if st:
        print("   " + pad(_lineup_cell(st[0]), 46) + (_lineup_cell(st[1]) if len(st) > 1 else ""))
    import scout
    if scout.hidden(league):
        print(paint(f"   Staff read: {scout.LEGEND}", C.GRAY))


def _lineup_cell(entry):
    if not entry:
        return ""
    pos, p = entry
    tag = paint(" OUT", C.BRED, C.BOLD) if p.inj_games > 0 else ""
    return (f"{paint(f'{pos:<3}', C.BCYAN)}{paint(f'#{p.number:<3}', C.GRAY)}"
            f"{pad(truncate(p.short_name, 20), 21)}{paint(f'{p.class_label:<6}', C.GRAY)}{__import__('scout').ovr_short(p)}{tag}")


# ═══ Roster ═════════════════════════════════════════════════════════════════

def _transfer_from(p):
    """The school he transferred from, or None (older saves: read it off his timeline)."""
    t = getattr(p, "transfer_from", None) or getattr(p, "prev_school", None)
    if t:
        return t
    for evs in p.events.values():
        for e in evs:
            if e.startswith("Transferred to") and " from " in e:
                return e.rsplit(" from ", 1)[1]
    return None


def roster_view(league: League, team: Team):
    import finance as fi
    while True:
        clear()
        color = league.conference_color(team.conference)
        print(title_bar(f"{team.full_name.upper()} · ROSTER ({len(team.roster)})", color))
        paid = [p for p in team.roster if fi.player_nil(p)]
        print(paint(f"   NIL: {fi.money(fi.roster_nil(team))} a year to {len(paid)} players   ·   "
                    f"budget {fi.money(fi.budget(team))}   ·   [$] full payroll & budget", C.GRAY))
        fund_hdr = " ".join(f"{FUNDAMENTAL_ABBR[f]:>3}" for f in FUNDAMENTALS)
        header = (f"   {'#':>3}  {'NAME':<20}{'YR':<6}{'HT':<6}{'WT':>4}  {'OVR':>3} {'EXP':>3}  {'NIL/YR':>6}  {'HS':<5}  {'DEV':<3}  "
                  f"{fund_hdr}  {'PROF':>4}  ALT")
        import scout
        hide = scout.hidden(league)
        if hide:                                   # Coach Career: what your staff sees, not numbers
            from ui import visible_len as _vl
            lw = max([16] + [_vl(scout.ovr(p)) + 1 for p in team.roster])     # ranges read wider than words
            rest = 100 - (3 + 3 + 2 + 19 + 6 + lw + 8)
            show_hs = rest - 7 >= 30
            rest -= 7 if show_hs else 0
            bw = rest // 2
            ww = rest - bw - 1
            header = (f"   {'#':>3}  {'NAME':<19}{'YR':<6}{'LOOKS LIKE':<{lw}}{'NIL/YR':>6}  "
                      + (f"{'HS':<5}  " if show_hs else "") + f"{'BEST AT':<{bw + 1}}WORST AT")
        for pos in POSITIONS:
            players = team.players_at(pos)
            if not players:
                continue
            print()
            print(paint(f"   {POSITION_NAMES[pos].upper()}", color, C.BOLD))
            print(paint(header, C.GRAY))
            for p in players:
                if hide:
                    import subprof
                    subs = sorted(subprof.all_values(p), key=lambda x: -x[2])
                    def _sk(x, w):                           # the skill, in the color of how good he is at it
                        lab = x[1].lower()
                        if len(lab) > w:
                            lab = lab.replace("coverage", "cov.").replace("protection", "pro")
                        return paint(pad(truncate(lab, w), w), subprof.color(x[2]))
                    best = _sk(subs[0], bw) if subs else " " * bw
                    worst = _sk(subs[-1], ww) if subs else ""
                    tr = _transfer_from(p)
                    name = truncate(p.name, 17 if tr else 19) + (paint(" ⇄", C.BCYAN) if tr else "") \
                        + (paint(" ·", C.BRED) if p.inj_games > 0 else "")
                    amt = fi.player_nil(p)
                    nil_txt = paint(fi.money(amt), C.BGREEN) if amt else paint("—", C.GRAY)
                    name = truncate(p.name, 16 if tr else 18) + (paint(" ⇄", C.BCYAN) if tr else "") \
                        + (paint(" ·", C.BRED) if p.inj_games > 0 else "")
                    print(f"   {paint(f'{p.number:>3}', C.GRAY)}  {pad(name, 19)}"
                          f"{p.class_label:<6}{pad(scout.ovr(p), lw)}"
                          f"{pad(nil_txt, 6, 'right')}  " + (f"{stars(p.hs_stars)}  " if show_hs else "") + f"{best} {worst}"
                          f"{paint(' ' + status_text(p, short=True), C.BRED) if p.inj_games > 0 else ''}")
                    continue
                funds = " ".join(rating(p.fundamentals[f]) for f in FUNDAMENTALS)
                if pos in ("K", "P"):                      # a kicker is his leg and his aim
                    pwr = p.applied("strength")
                    acc = round((p.fundamentals["iq"] * 0.6 + p.fundamentals["playmaker"] * 0.4) * p.proficiency_at(pos))
                    funds = pad(f"{paint('PWR', C.GRAY)} {rating(pwr)}  {paint('Seaboard', C.GRAY)} {rating(acc)}", 23)
                prof = p.proficiency_at(p.position)
                alt_pos, alt_ovr = p.best_alternate()
                tr = _transfer_from(p)
                name = truncate(p.name, 17 if tr else 19) + (paint(" ⇄", C.BCYAN) if tr else "") \
                    + (paint(" ·", C.BRED) if p.inj_games > 0 else "")
                amt = fi.player_nil(p)
                nil_txt = paint(fi.money(amt), C.BGREEN) if amt else paint("—", C.GRAY)
                print(f"   {paint(f'{p.number:>3}', C.GRAY)}  {pad(name, 20)}"
                      f"{p.class_label:<6}{p.height_str:<6}{p.weight:>4}  {rating(p.overall)} {rating(p.experience_rating)}  {pad(nil_txt, 6, 'right')}  "
                      f"{stars(p.hs_stars)}  "
                      f"{_dev_grade(p)}  {funds}  {paint(f'{prof:>4.2f}', proficiency_color(prof))}  "
                      f"{paint(f'{alt_pos} {alt_ovr}', C.GRAY)}"
                      f"{paint('  ' + status_text(p, short=True), C.BRED) if p.inj_games > 0 else ''}")

        n_tr = sum(1 for p in team.roster if _transfer_from(p))
        print(paint(f"\n   ⇄ transfer ({n_tr} on the roster)   · injured   ·   rows are in depth-chart order", C.GRAY))
        if hide:
            print(paint("   LOOKS LIKE = your staff's read of him · BEST/WORST AT = his strongest and weakest skill at his\n"
                        "   position, colored by how good he is at it: ", C.GRAY)
                  + " ".join(paint(w, c) for w, c in (("elite", C.BMAGENTA), ("good", C.BGREEN), ("average", C.BWHITE),
                                                      ("below", C.BYELLOW), ("poor", C.BRED)))
                  + paint("\n   Height, weight and every skill: open his card (jersey #). Practice reports: tab 3 → [P].",
                          C.GRAY))
        else:
          print(paint("   EXP = game experience: live reps make performance steadier and pressure execution calmer · HS = high-school\n   stars · DEV = how fast he improves · STR SPD QCK IQ = strength, speed, quickness,\n"
                    "   football IQ · INJ = durability (higher is sturdier) · PLY = playmaker · PROF = how well his skills\n"
                    "   translate to his position (1.00 = fully) · ALT = his best other position and his overall there\n"
                    "   K/P: PWR = leg strength, Seaboard = accuracy.   The sim carries the working roster: the two-deep and\n"
                    "   the young players behind it, not a 105-man camp roster.", C.GRAY))
        mine = _is_mine(league, team)
        import webview
        webview.roster(league, team)
        choice = ask("Jersey # for player card, [$] payroll & budget, [S] schedule"
                     + (", [H] depth chart" if mine else "") + ", or Enter to go back:")
        if not choice or choice.lower() == "b":
            return
        if choice.strip().lower() == "s":
            schedule_view(league, team)
            continue
        if choice.strip().lower() == "h" and mine:
            depth_chart(league, team)
            continue
        if choice.strip() == "$":
            import finance_screens
            finance_screens.budget_screen(league, team)
            continue
        if choice.isdigit():
            p = _pick_by_number(team, int(choice))
            if p:
                player_card(league, p)


def _pick_by_number(team, number):
    """The player wearing a number — and if two do, ask which."""
    found = [p for p in team.roster if p.number == number]
    if len(found) <= 1:
        return found[0] if found else None
    for i, p in enumerate(found, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW)} #{number} {p.name}  {p.position}  {__import__('scout').ovr_plain(p)}")
    c = ask(f"Two players wear #{number} — which one?").strip()
    return found[int(c) - 1] if c.isdigit() and 1 <= int(c) <= len(found) else None


def _open_player(league: League, team: Team):
    choice = ask("Jersey #:")
    if choice.isdigit():
        p = _pick_by_number(team, int(choice))
        if p:
            player_card(league, p)
        else:
            print(paint(f"\n  Nobody wears #{choice}.", C.BRED))
            pause()


# ═══ Player card ════════════════════════════════════════════════════════════

def _player_header_legacy(league, p, team, color):
    """The player card's old text header (Settings -> Show faces off)."""
    print(f"   {paint(team.full_name, color, C.BOLD)}  ·  {POSITION_NAMES[p.position]}  ·  {p.class_label}  ·  "
          f"{p.height_str}, {p.weight} lbs")
    import scout
    hide = scout.hidden(league)
    art = "an" if scout.ovr_word(p.overall)[0] in "AEIOUaeiou" else "a"
    print(f"   {'Looks like ' + art if hide else 'Overall'} {scout.ovr(p)}   {paint('HS Recruit', C.GRAY)} {stars(p.hs_stars)}   "
          f"{paint('Development', C.GRAY)} {_dev_grade(p)}   {paint('Durability', C.GRAY)} "
          f"{p.durability.lower()}" + ("" if hide else f" ({p.fundamentals['injury']})"))
    print(paint(f"   Offseasons developed: {p.seasons_developed}   ·   "
                f"Ceiling at {p.position}: " + (f"{p.prof_ceiling:.2f}" if not hide else
                                                   "his ceiling looks " + __import__('subprof').word(p.prof_ceiling)),
                C.GRAY))
    if getattr(p, "generational", False):
        print(paint("   ✦ GENERATIONAL TALENT — the kind of prospect who comes along every few years", C.BMAGENTA, C.BOLD))
    tr = _transfer_from(p)
    if tr:
        print(paint(f"   ⇄ Transfer from {tr}", C.BCYAN))
    import finance as fi
    amt = fi.player_nil(p)
    print(f"   {paint('NIL deal', C.GRAY)} " + (paint(fi.money(amt) + ' a year', C.BGREEN, C.BOLD)
                                                + paint(f"  (paid by {team.school} every year he's on the roster)", C.GRAY)
                                                if amt else paint("none", C.GRAY)))
    import morale
    mv = morale.get(p)
    log = [f"{why} ({d:+d})" for _, d, why in p.__dict__.get("mood_log", [])[-3:] if d]
    print(f"   {paint('Morale', C.GRAY)} {paint(f'{mv:.0f}', morale.color(mv), C.BOLD)} "
          f"{paint(morale.word(mv), morale.color(mv))}"
          + (paint("   lately: " + "; ".join(reversed(log)), C.GRAY) if log else ""))
    print()


def _player_card_draw(league: League, p):
    clear()
    team = p.team
    color = league.team_color(team)
    print(title_bar(f"#{p.number} {p.name.upper()} · {p.position}", color))
    import faces
    import scout
    hide = scout.hidden(league)
    if faces.enabled():
        import faces_ui
        for ln in faces_ui.player_hero(league, p, color):
            print(ln)
        print()
    else:
        print(f"   {paint(team.full_name, color, C.BOLD)}  ·  {POSITION_NAMES[p.position]}  ·  {p.class_label}  ·  "
              f"{p.height_str}, {p.weight} lbs")
        art = "an" if scout.ovr_word(p.overall)[0] in "AEIOUaeiou" else "a"
        print(f"   {'Looks like ' + art if hide else 'Overall'} {scout.ovr(p)}   {paint('HS Recruit', C.GRAY)} {stars(p.hs_stars)}   "
              f"{paint('Development', C.GRAY)} {_dev_grade(p)}   {paint('Durability', C.GRAY)} "
              f"{p.durability.lower()}" + ("" if hide else f" ({p.fundamentals['injury']})"))
        print(paint(f"   Offseasons developed: {p.seasons_developed}   ·   "
                    f"Ceiling at {p.position}: " + (f"{p.prof_ceiling:.2f}" if not hide else
                                                       "his ceiling looks " + __import__('subprof').word(p.prof_ceiling)),
                    C.GRAY))
        if getattr(p, "generational", False):
            print(paint("   ✦ GENERATIONAL TALENT — the kind of prospect who comes along every few years", C.BMAGENTA, C.BOLD))
        tr = _transfer_from(p)
        if tr:
            print(paint(f"   ⇄ Transfer from {tr}", C.BCYAN))
        import finance as fi
        amt = fi.player_nil(p)
        print(f"   {paint('NIL deal', C.GRAY)} " + (paint(fi.money(amt) + ' a year', C.BGREEN, C.BOLD)
                                                    + paint(f"  (paid by {team.school} every year he's on the roster)", C.GRAY)
                                                    if amt else paint("none", C.GRAY)))
        import morale
        mv = morale.get(p)
        log = [f"{why} ({d:+d})" for _, d, why in p.__dict__.get("mood_log", [])[-3:] if d]
        print(f"   {paint('Morale', C.GRAY)} {paint(f'{mv:.0f}', morale.color(mv), C.BOLD)} "
              f"{paint(morale.word(mv), morale.color(mv))}"
              + (paint("   lately: " + "; ".join(reversed(log)), C.GRAY) if log else ""))
        print()
    import compliance
    gv = compliance.gpa(p)
    print(f"   {paint('Classroom', C.GRAY)} {paint(compliance.gpa_word(gv), compliance.gpa_color(gv), C.BOLD)}"
          + (paint(f" ({gv:.2f} GPA)", C.GRAY) if not hide else "")
          + (paint(f"   · {p.inj_desc}", C.BRED) if getattr(p, "suspended", False) and (p.inj_desc or "").startswith("academ") else ""))
    print()

    if blurbs(p):
        print(section("PERSONALITY", color))
        from traits import explain
        for name, why in explain(p):              # what he's like, and what that does on the field
            print(f"   {paint(pad(name, 16), C.BYELLOW, C.BOLD)}{paint(why, C.GRAY)}")
        print()

    _season_stat_block(p, color, league)

    print(section("CAREER TIMELINE", color))
    all_years = sorted(set(p.events.keys()) | set(p.yearly_stats.keys()) | {y for y, _ in p.history})
    # Track the pre-2026 rating as a baseline for the first displayed progression delta
    prev_ovr = next((o for y, o in reversed(p.history) if y < 2026), None)

    displayed_years = [yr for yr in all_years if yr >= 2026]
    if not displayed_years:
        print(paint("   No career history recorded yet.", C.GRAY))
        print()
    else:
        for yr in displayed_years:
            ovr = next((o for y, o in p.history if y == yr), prev_ovr)
            delta = ""
            if prev_ovr is not None and ovr is not None:
                d = ovr - prev_ovr
                what = " this offseason" if yr == displayed_years[0] else ""
                delta = paint(f" ({d:+d}{what})", C.BGREEN if d >= 0 else C.BRED)
            prev_ovr = ovr or prev_ovr

            ovr_str = (f"OVR {rating(ovr)}{delta}" if not hide else f"looked like: {scout.ovr(ovr)}") if ovr else ""
            print(f"   {paint(str(yr), C.BYELLOW, C.BOLD)}  {ovr_str}")

            for event in p.events.get(yr, []):
                print(f"      {paint('•', C.GRAY)} {event}")

            stats = p.yearly_stats.get(yr)
            if stats:
                bits = []
                if stats.get('pass_yds'):
                    bits.append(f"{stats['pass_yds']} pass yds, {stats['pass_td']} TD")
                if stats.get('rush_yds'):
                    bits.append(f"{stats['rush_yds']} rush yds, {stats['rush_td']} TD")
                if stats.get('rec_yds'):
                    bits.append(f"{stats['rec_yds']} rec yds, {stats['rec_td']} TD")
                if stats.get('tkl'):
                    bits.append(f"{stats['tkl']} tkl, {stats['sack']} sack, {stats['int']} INT")
                gp = getattr(p, "yearly_games", {}).get(yr)
                if bits:
                    print(f"      {paint('↳', C.GRAY)} {', '.join(bits)}"
                          + (paint(f"  ({gp} game{'s' if gp != 1 else ''})", C.GRAY) if gp else ""))
            print()

    import subprof
    print(section(f"{POSITION_NAMES[p.position].upper()} SKILLS" + ("" if hide else
                  paint("   (sub-proficiencies: how he plays each part of the position)", C.GRAY)), color))
    for key_, label_, v in subprof.all_values(p):
        print(f"   {pad(label_, 22)}{scout.sub(v, seed=p.name + key_, width=26 if hide else 6)}"
              + ("" if hide else f"  {bar(v, 24, PROFICIENCY_MAX, subprof.color(v))}"))
    if hide:
        import practice
        rep_ = practice.report(p, league.week)
        if rep_:
            import textwrap
            print()
            for ln in textwrap.wrap("Staff report: " + rep_, 92):
                print(paint("   " + ln, C.GRAY))
        if p.team is getattr(league, "user_team", None):
            text, form = practice.run(league, p.team).get(id(p), ("", 0))
            if text:
                print(paint(f"   This week in practice: {text}", C.BCYAN))
    print()
    if hide:
        print(section("ATHLETE", color))
        for f in FUNDAMENTALS:
            print(f"   {FUNDAMENTAL_NAMES[f]:<13}{scout.fund(p.fundamentals[f], width=24)}")
        print()
        print(section("OTHER POSITIONS", color))
        alts = sorted((x for x in POSITIONS if x != p.position), key=p.overall_at, reverse=True)[:3]
        for pos in alts:
            print(f"   {paint(f'{pos:<5}', C.BCYAN)}{scout.ovr(p.overall_at(pos))}")
        return
    print(section(f"FUNDAMENTALS   {paint('(raw → as ' + p.position + ', scaled by his ' + format(p.proficiency_at(p.position), '.2f') + ' ' + p.position + ' proficiency)', C.GRAY)}", color))
    for f in FUNDAMENTALS:
        raw = p.fundamentals[f]
        applied = p.applied(f)
        note = paint("  (not position-dependent)", C.GRAY) if f == "injury" else ""
        print(f"   {FUNDAMENTAL_NAMES[f]:<13}{rating(raw)}  {bar(raw, 30)}  {paint('→', C.GRAY)} {rating(applied)}{note}")
    print()

    print(section("POSITION PROFICIENCY", color))
    print(paint(f"   {'POS':<5}{'PROF':>5}  {'':<24}  OVR THERE", C.GRAY))
    for pos in sorted(POSITIONS, key=p.proficiency_at, reverse=True):
        prof = p.proficiency_at(pos)
        tag = paint("  ◄ primary", C.BYELLOW) if pos == p.position else ""
        if __import__('scout').hidden():
            print(f"   {paint(f'{pos:<5}', C.BCYAN)}{__import__('scout').prof(prof, p.name + pos, width=24)}"
                  f"{__import__('scout').ovr(p.overall_at(pos))}{tag}")
            continue
        print(f"   {paint(f'{pos:<5}', C.BCYAN)}{paint(f'{prof:>5.2f}', proficiency_color(prof))}  "
              f"{bar(prof, 24, PROFICIENCY_MAX, proficiency_color(prof))}  {rating(p.overall_at(pos))}{tag}")


def player_card(league: League, p):
    """A player's card. [N]/[P] walk his position room in depth-chart order."""
    while True:
        _player_card_draw(league, p)
        team = getattr(p, "team", None)
        room = list(team.players_at(p.position)) if team is not None and p in team.roster else []
        if len(room) < 2:
            import webview
            webview.player(league, p)
            pause()
            return
        i = room.index(p)
        import webview
        webview.player(league, p, {"i": i + 1, "n": len(room)})
        c = ask(f"[N] next {p.position} ({i + 1} of {len(room)})   [P] previous   [Enter] back").strip().lower()
        if c == "n":
            p = room[(i + 1) % len(room)]
        elif c == "p":
            p = room[(i - 1) % len(room)]
        else:
            return

def _stat_rows(line, games):
    """Rows of (label, value) for whatever this player actually did."""
    rows = []
    if line["pass_att"]:
        comp = f"{line['pass_cmp']}/{line['pass_att']}"
        pct = 100 * line["pass_cmp"] / line["pass_att"]
        rows.append(("PASSING", [("Comp/Att", comp), ("Pct", f"{pct:.1f}%"), ("Yards", line["pass_yds"]),
                                 ("TD", line["pass_td"]), ("INT", line["pass_int"]),
                                 ("Y/A", f"{line['pass_yds'] / line['pass_att']:.1f}"),
                                 ("Sacked", line["sacked"])]))
    if line["rush_att"]:
        rows.append(("RUSHING", [("Carries", line["rush_att"]), ("Yards", line["rush_yds"]),
                                 ("Avg", f"{line['rush_yds'] / line['rush_att']:.1f}"),
                                 ("TD", line["rush_td"]), ("Long", line["rush_long"]),
                                 ("Fumbles", line["fumbles"])]))
    if line["targets"] or line["rec"]:
        rows.append(("RECEIVING", [("Rec/Tgt", f"{line['rec']}/{line['targets']}"), ("Yards", line["rec_yds"]),
                                   ("Avg", f"{line['rec_yds'] / line['rec']:.1f}" if line["rec"] else "—"),
                                   ("TD", line["rec_td"]), ("Long", line["rec_long"])]))
    if any(line[k] for k in ("tkl", "tfl", "sack", "int", "pbu", "ff", "fr")):
        rows.append(("DEFENSE", [("Tackles", line["tkl"] + line["ast"]), ("TFL", line["tfl"]), ("Sacks", line["sack"]),
                                 ("INT", line["int"]), ("PBU", line["pbu"]), ("FF", line["ff"]),
                                 ("FR", line["fr"]), ("Missed", line["missed_tkl"])]))
        if line["tgt_d"]:
            pct = line["cmp_d"] / line["tgt_d"] * 100
            rows.append(("COVERAGE", [("Targeted", line["tgt_d"]), ("Allowed", line["cmp_d"]),
                                      ("Comp%", f"{pct:.0f}%"),
                                      ("Per game", f"{line['tgt_d'] / max(1, games):.1f}")]))
    if line["fg_att"] or line["xp_att"]:
        rows.append(("KICKING", [("FG", f"{line['fg_made']}/{line['fg_att']}"), ("Long", line["fg_long"]),
                                 ("XP", f"{line['xp_made']}/{line['xp_att']}")]))
    if line["punts"]:
        rows.append(("PUNTING", [("Punts", line["punts"]), ("Yards", line["punt_yds"]),
                                 ("Avg", f"{line['punt_yds'] / line['punts']:.1f}")]))
    if line["kr"] or line["pr"]:
        rows.append(("RETURNS", [("KR", line["kr"]), ("KR Yds", line["kr_yds"]), ("PR", line["pr"]),
                                 ("PR Yds", line["pr_yds"]), ("TD", line["kr_td"] + line["pr_td"])]))
    return rows


def _career_line(p):
    """Career totals, with every '_long' as the longest single play (older saves summed them)."""
    from collections import Counter
    c = Counter(p.career_stats)
    for k in list(c):
        if k.endswith("_long"):
            c[k] = max([y.get(k, 0) for y in getattr(p, "yearly_stats", {}).values()] or [0])
    return c


def _season_stat_block(p, color, league):
    line, games = p.season_stats, p.games_played
    label = f"{league.year} SEASON STATS"
    if not games:
        if p.career_games:
            line, games, label = _career_line(p), p.career_games, "CAREER STATS"
        else:
            return
    rows = _stat_rows(line, games)
    if not rows:
        print(section(f"{label}  ·  {games} game{'s' if games != 1 else ''} played", color))
        print(paint("   No statistics recorded.", C.GRAY))
        print()
        return
    print(section(f"{label}  ·  {games} game{'s' if games != 1 else ''} played", color))
    for group, cells in rows:
        text = "   ".join(f"{paint(k, C.GRAY)} {paint(f'{v:g}' if isinstance(v, float) else str(v), C.BWHITE, C.BOLD)}"
                           for k, v in cells)
        print(f"   {paint(f'{group:<10}', C.BCYAN)}{text}")
    if p.career_games and p.season_stats:
        c = p.career_stats + p.season_stats
        bits = []
        if c["pass_yds"]:
            bits.append(f"{c['pass_yds']:,} pass yds, {c['pass_td']} TD")
        if c["rush_yds"]:
            bits.append(f"{c['rush_yds']:,} rush yds, {c['rush_td']} TD")
        if c["rec_yds"]:
            bits.append(f"{c['rec']} rec, {c['rec_yds']:,} yds")
        if c["tkl"]:
            bits.append(f"{c['tkl']} tackles, {c['sack']} sacks")
        if bits:
            print(paint(f"   {'CAREER':<10}" + "   ".join(bits) +
                        f"   ({p.career_games + games} games)", C.GRAY))
    print()


def _dev_grade(p):
    g = p.potential_grade
    color = C.BMAGENTA if g.startswith("A") else C.BGREEN if g.startswith("B") else C.BYELLOW if g.startswith("C") else C.BRED
    return paint(f"{g:<3}", color, C.BOLD)


# ═══ Schedule ═══════════════════════════════════════════════════════════════

def portal_screen(league: League, report=None):
    """Who moved in the last transfer window."""
    report = report or getattr(league, "last_portal", None)
    team = getattr(league, "user_team", None)
    clear()
    if report is None or not report.entries:
        print(title_bar("TRANSFER PORTAL"))
        print(paint("\n   The portal opens after the season. Nobody has entered yet.", C.GRAY))
        pause()
        return
    print(title_bar(f"{report.year} TRANSFER PORTAL"))
    print(f"   {paint(str(len(report.entries)), C.BWHITE, C.BOLD)} players entered   ·   "
          f"{paint(str(len(report.moves)), C.BGREEN, C.BOLD)} found new homes   ·   "
          f"{paint(str(len(report.unsigned)), C.BRED, C.BOLD)} went unsigned")
    print()
    print(section("TOP TRANSFERS", C.BGREEN))
    best = sorted(report.moves, key=lambda m: -m[0].overall)[:12]
    for entry, dest in best:
        move = "↑" if dest.prestige > entry.origin.prestige + 5 else (
            "↓" if dest.prestige < entry.origin.prestige - 5 else "→")
        print(f"   {__import__('scout').ovr_short(entry.overall)}  {paint(pad(entry.position, 4), C.BCYAN)}"
              f"{pad(truncate(entry.player.name, 20), 21)}"
              f"{paint(pad(truncate(entry.origin.school, 15), 16), C.GRAY)}"
              f"{paint(move, C.BYELLOW)} {pad(truncate(dest.school, 15), 16)}"
              f"{paint(entry.reason, C.GRAY)}")
    if team is not None:
        ins, outs = report.by_team_in.get(team, []), report.by_team_out.get(team, [])
        print()
        print(section(f"{team.school.upper()}  ·  {len(ins)} IN, {len(outs)} OUT", C.BCYAN))
        for entry in ins:
            print(f"   {paint('IN ', C.BGREEN, C.BOLD)} {__import__('scout').ovr_short(entry.overall)} "
                  f"{paint(pad(entry.position, 4), C.BCYAN)}{pad(truncate(entry.player.name, 20), 21)}"
                  f"{paint('from ' + entry.origin.school, C.GRAY)}")
        for entry in outs:
            where = entry.destination.school if entry.destination else "nowhere — left the sport"
            print(f"   {paint('OUT', C.BRED, C.BOLD)} {__import__('scout').ovr_short(entry.overall)} "
                  f"{paint(pad(entry.position, 4), C.BCYAN)}{pad(truncate(entry.player.name, 20), 21)}"
                  f"{paint('to ' + where, C.GRAY)}")
    print()
    print(section("BIGGEST HAULS", C.BCYAN))
    hauls = sorted(report.by_team_in.items(), key=lambda kv: -sum(e.overall for e in kv[1]))[:6]
    for t, entries in hauls:
        names = ", ".join(f"{e.position} {e.player.last_name} ({__import__('scout').ovr_plain(e.overall)})" for e in entries[:4])
        print(f"   {pad(paint(truncate(t.school, 18), league.conference_color(t.conference), C.BOLD), 20)}"
              f"{len(entries)} added   {paint(truncate(names, 55), C.GRAY)}")
    pause()


def rankings_menu(league: League):
    while True:
        clear()
        label = "PRESEASON" if league.rankings.week == 0 else f"WEEK {league.rankings.week}"
        print(title_bar(f"{league.year} · {label} POLL & HEISMAN RACE"))
        print(f"   {paint('[1]', C.BYELLOW, C.BOLD)}  Top 25 (media poll)    "
              f"{paint('[2]', C.BYELLOW, C.BOLD)}  Golden Helmet race    "
              f"{paint('[3]', C.BYELLOW, C.BOLD)}  National Champions")
        print(f"   {paint('[4]', C.BGREEN, C.BOLD)}  NP Playoff Rankings    "
              f"{paint('[5]', C.BGREEN, C.BOLD)}  Selection Committee    "
              f"{paint('[6]', C.BYELLOW, C.BOLD)}  Toughest Places to Play    "
              f"{paint('[7]', C.BYELLOW, C.BOLD)}  Strength of Schedule")
        print(f"   {paint('[E]', C.BCYAN, C.BOLD)}  Edit the rankings (Top 25 or Playoff Rankings)    "
              f"{paint('[B]', C.GRAY)}  Back")
        import webview
        webview.emit("rmenu", {"label": f"{league.year} · {label.title()}", "items": [
            ["1", "Top 25", "the media poll"], ["2", "Golden Helmet race", "the best player in the country"],
            ["3", "National champions", "every title since 1998"], ["4", "NP Playoff Rankings", "the committee's top 25"],
            ["5", "Selection Committee", "who's in the room"], ["6", "Toughest places to play", "home fields, ranked"],
            ["7", "Strength of schedule", "every program's slate"], ["E", "Edit the rankings", "Top 25 or Playoff Rankings"]]})
        choice = ask("Select:").lower()
        if choice in ("4", "5"):
            import committee_screens
            (committee_screens.playoff_rankings if choice == "4" else committee_screens.members_screen)(league)
        elif choice == "1":
            top_25(league)
        elif choice == "2":
            heisman_race(league)
        elif choice == "3":
            champions_history(league)
        elif choice == "6":
            import stadium_screens
            stadium_screens.toughest_screen(league)
        elif choice == "7":
            import sos
            sos.screen(league)
        elif choice == "e":
            import ranking_editor
            ranking_editor.menu(league)
        else:
            return


def _movement(now, before):
    if before is None:
        return paint("  NEW", C.BGREEN, C.BOLD) if now <= TOP_N else paint("   —", C.GRAY)
    delta = before - now
    if delta > 0:
        return paint(f"  ▲{delta:<2}", C.BGREEN)
    if delta < 0:
        return paint(f"  ▼{-delta:<2}", C.BRED)
    return paint("   —", C.GRAY)


def _pts(r, team):
    p = getattr(r, "points", {}).get(team)
    f = getattr(r, "first_place", {}).get(team)
    txt = f"{p:>5}" if p is not None else "     "
    return txt + pad(paint(f"({f})", C.BYELLOW) if f else "", 4, "right")


def _top_25_draw(league: League):
    clear()
    r = league.rankings
    import rankings as _rk
    label = ("PRESEASON POLL" if r.week == 0 else "FINAL POLL" if r.week >= _rk.FINAL_WEEK
             else "FINAL REGULAR-SEASON POLL · NO VOTE DURING THE BOWLS" if r.week >= _rk.FROZEN_FROM - 1 and league.week >= _rk.FROZEN_FROM
             else f"POLL · AFTER WEEK {r.week}")
    print(title_bar(f"{league.year} TOP 25  ·  {label}"))
    print(paint(f"   {'RK':<4}{'TEAM':<26}{'CONF':<13}{'REC':<7}{'PTS':>6}  {'MOVE':<7}LAST RESULT", C.GRAY))
    for i, team in enumerate(r.top(), 1):
        color = league.conference_color(team.conference)
        before = r.previous_rank(team)
        played = [g for g in league.team_games(team) if g.played]
        if played:
            g = played[-1]
            opp = g.opponent_of(team)
            won = g.winner is team
            opp_rank = (getattr(g, "ranks", {}) or {}).get(opp)            # ranked at kickoff
            tag = f"#{opp_rank} " if opp_rank else ""
            res = (paint("W", C.BGREEN, C.BOLD) if won else paint("L", C.BRED, C.BOLD)) + \
                  f" {g.score_for(team)}-{g.score_for(opp)} {paint('vs' if g.home is team else 'at', C.GRAY)} " \
                  f"{tag}{truncate(opp.school, 16)}"
        else:
            res = paint("—", C.GRAY)
        from ui import clip
        print(clip(f"   {paint(f'{i:<4}', C.BYELLOW if i <= 5 else C.BWHITE)}"
                   f"{pad(paint(truncate(team.school + ' ' + team.nickname, 25), color, C.BOLD), 26)}"
                   f"{paint(pad(truncate(team.conference, 12), 13), C.GRAY)}{pad(team.record, 7)}"
                   f"{_pts(r, team)}  {pad(_movement(i, before), 7)}{res}", WIDTH))
    others = getattr(r, "others", None) or []
    if others:
        print(paint("\n   Also receiving votes: " + ", ".join(f"{t.school} {p}" for t, p in others[:14]), C.GRAY))
    print(paint(f"   {getattr(r, 'VOTERS', 62)} voters · 25 points for first, 1 for 25th · (n) first-place votes", C.GRAY))


def top_25(league: League):
    """The media poll. Open any ranked team's page or schedule from here."""
    while True:
        _top_25_draw(league)
        order = league.rankings.top()
        import ui as _u
        _u.footer(_u.key("#", "team page"), _u.key("S#", "that team's schedule"), _u.key("B", "back", C.GRAY))
        import webview
        if webview.on():
            try:
                r = league.rankings
                me = getattr(league, "user_team", None)
                rows = []
                for i, team in enumerate(order, 1):
                    before = r.previous_rank(team)
                    played = [g for g in league.team_games(team) if g.played]
                    last = ""
                    won = None
                    if played:
                        g = played[-1]
                        opp = g.opponent_of(team)
                        won = g.winner is team
                        orank = (getattr(g, "ranks", {}) or {}).get(opp)
                        last = f"{g.score_for(team)}-{g.score_for(opp)} {'vs' if g.home is team else 'at'} {'#' + str(orank) + ' ' if orank else ''}{opp.school}"
                    rows.append({"rank": i, "school": team.school, "nick": team.nickname, "conf": team.conference,
                                 "record": team.record, "pts": getattr(r, "points", {}).get(team),
                                 "first": getattr(r, "first_place", {}).get(team), "move": None if before is None else before - i,
                                 "new": before is None, "last": last, "won": won, "me": team is me,
                                 "color": webview._color(league, team)})
                webview.emit("top25", {"title": f"{league.year} Top 25", "label": webview.plain(r.week and f"after week {r.week}" or "preseason"),
                                       "rows": rows, "others": [f"{t.school} {p}" for t, p in (getattr(r, "others", None) or [])[:14]],
                                       "voters": getattr(r, "VOTERS", 62)})
            except Exception:
                pass
        choice = ask("Select:").strip().lower()
        if choice.startswith("s") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= len(order):
            schedule_view(league, order[int(choice[1:]) - 1])
        elif choice.isdigit() and 1 <= int(choice) <= len(order):
            team_view(league, order[int(choice) - 1])
        else:
            return


def heisman_race(league: League):
    clear()
    r = league.rankings
    label = "PRESEASON WATCH LIST" if r.week == 0 else f"AFTER WEEK {r.week}"
    print(title_bar(f"{league.year} HEISMAN RACE  ·  {label}"))
    if not r.heisman:
        print(paint("\n   Nobody has played a snap yet. Check back after week one.", C.GRAY))
        pause()
        return
    print(paint(f"   {'RK':<4}{'PLAYER':<21}{'POS':<4}{'TEAM':<21}{'MOVE':<6}SEASON", C.GRAY))
    for i, (p, score, blurb) in enumerate(r.heisman, 1):
        team = p.team
        color = league.conference_color(team.conference)
        before = r.heisman_movement(p)
        rank = r.rank_of(team)
        team_txt = (f"#{rank} " if rank else "") + truncate(team.school, 17)
        from ui import clip
        print(clip(f"   {paint(f'{i:>2}. ', C.BYELLOW if i == 1 else C.BWHITE)}"
                   f"{pad(truncate(p.name, 20), 21)}{paint(pad(p.position, 4), C.BCYAN)}"
                   f"{pad(paint(team_txt, color), 21)}{pad(_movement(i, before), 6)}{paint(blurb, C.GRAY)}", WIDTH))
    print(paint("\n   Voters weigh production, position, strength of schedule and how much his team wins.",
                C.GRAY))
    import webview
    if webview.on():
        try:
            webview.emit("heisman", {"title": f"{league.year} Golden Helmet race", "label": label.title(), "rows": [
                {"rank": i, "id": webview.pid(p), "name": p.name, "pos": p.position, "school": p.team.school,
                 "trank": r.rank_of(p.team), "move": (None if r.heisman_movement(p) is None else r.heisman_movement(p) - i),
                 "blurb": webview.plain(blurb), "color": webview._color(league, p.team)}
                for i, (p, score, blurb) in enumerate(r.heisman, 1)]})
        except Exception:
            pass
    pause()


def champions_history(league: League):
    clear()
    print(title_bar("NATIONAL CHAMPIONS  ·  BCS & PLAYOFF ERAS"))
    print(paint(f"   {'YEAR':<6}{'CHAMPION':<18}{'REC':<7}{'COACH':<18}{'TITLE GAME':<28}SITE / NOTE", C.GRAY, C.BOLD))
    history = sorted(league.champions, key=lambda c: -c.season)
    for c in history:
        mine = not c.real
        name_color = C.BYELLOW if mine else C.BWHITE
        game = f"def. {c.runner_up} {c.score}-{c.opp_score}" + (f" ({c.note})" if c.note in ("OT", "2OT") else "")
        note = c.note if c.note and c.note not in ("OT", "2OT") else ""
        print(f"   {paint(f'{c.season:<6}', C.BYELLOW if mine else C.GRAY)}"
              f"{pad(paint(truncate(c.champion, 17), name_color, C.BOLD), 18)}{c.record:<7}"
              f"{pad(truncate(c.coach, 17), 18)}{pad(truncate(game, 27), 28)}"
              + (paint(truncate(note, 20), C.BCYAN) if note else paint(truncate(c.site.split(' · ')[-1], 20), C.GRAY)))
    counts = {}
    for c in league.champions:
        counts[c.champion] = counts.get(c.champion, 0) + 1
    most = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if not history:
        print(paint(f"\n   No national champion yet in this world. The first one is crowned after the {league.year} title game.",
                    C.GRAY))
        pause()
        return
    print()
    print(section("TITLES SINCE 1998" if any(c.real for c in history) else f"TITLES SINCE {min(c.season for c in history)}",
                  C.BYELLOW))
    line = "   " + "   ".join(f"{paint(school, C.BWHITE)} {n}" for school, n in most)
    for chunk in _wrap_colored(line, WIDTH - 4):
        print(chunk)
    if any(c.real for c in history):
        print(paint("\n   Gold years were won in this world. 1998-2025 is the real record book you inherited.", C.GRAY))
    import webview
    webview.emit("champs", {"rows": [{"year": c.season, "school": c.champion, "record": c.record, "coach": c.coach,
                                      "game": f"def. {c.runner_up} {c.score}-{c.opp_score}" + (f" ({c.note})" if c.note in ("OT", "2OT") else ""),
                                      "mine": not c.real} for c in history],
                            "counts": [[s, n] for s, n in most]})
    pause()


def _wrap_colored(text, width):
    """Break a painted line on the three-space separators so it fits the screen."""
    parts, lines, cur = text.strip().split("   "), [], "  "
    for part in parts:
        if len(cur) > 2 and len(_strip(cur)) + len(_strip(part)) + 3 > width:
            lines.append(cur)
            cur = "  "
        cur += " " + part + "  "
    lines.append(cur)
    return lines


def _strip(text):
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def schedule_menu(league: League):
    """Weekly scoreboards for the whole country, one conference, or one team."""
    week = max(1, min(league.week or 1, 18))
    while True:
        clear()
        print(title_bar(f"{league.year} · SCHEDULES & SCORES"))
        print(f"   {paint('[1]', C.BYELLOW, C.BOLD)}  League-wide week   "
              f"{paint('[2]', C.BYELLOW, C.BOLD)}  Conference week   "
              f"{paint('[3]', C.BYELLOW, C.BOLD)}  Team schedule   "
              f"{paint('[4]', C.BYELLOW, C.BOLD)}  Past seasons")
        print(f"   {paint('[B]', C.GRAY)}  Back")
        print(paint("   Every finished game has a box score — pick it by number from any scoreboard or schedule.",
                    C.GRAY))
        print(rule())
        print(paint(f"   {league.status}", C.GRAY))
        choice = ask("Select:").lower()
        if choice in ("b", "", "q"):
            return
        if choice == "1":
            week = week_scoreboard(league, week)
        elif choice == "2":
            conf = pick_conference(league)
            if conf:
                week = week_scoreboard(league, week, conference=conf)
        elif choice == "3":
            team = pick_team(league)
            if team:
                schedule_view(league, team)
        elif choice == "4":
            past_seasons_menu(league)


def past_seasons_menu(league: League):
    import archive
    years = archive.seasons(league)
    clear()
    print(title_bar("PAST SEASONS"))
    if not years:
        print(paint("\n   No finished seasons yet. Every game and box score is kept once a season ends.", C.GRAY))
        pause()
        return
    for yr in years:
        champ = league.champion_of(yr)
        tag = f"  ·  national champion {champ.champion}" if champ and hasattr(champ, "champion") else ""
        print(f"   {paint(f'[{yr}]', C.BYELLOW, C.BOLD)}  {len(archive.games_for(league, yr))} games{paint(tag, C.GRAY)}")
    choice = ask("Which season? (Enter to go back)")
    if not choice.isdigit() or int(choice) not in years:
        return
    year = int(choice)
    week = 1
    while True:
        clear()
        print(title_bar(f"{year} SEASON"))
        print(f"   {paint('[1]', C.BYELLOW, C.BOLD)}  League-wide week   "
              f"{paint('[2]', C.BYELLOW, C.BOLD)}  Conference week   "
              f"{paint('[3]', C.BYELLOW, C.BOLD)}  Team schedule   {paint('[B]', C.GRAY)}  Back")
        c = ask("Select:").lower()
        if c in ("b", "", "q"):
            return
        if c == "1":
            week = week_scoreboard(league, week, year=year)
        elif c == "2":
            conf = pick_conference(league)
            if conf:
                week = week_scoreboard(league, week, conference=conf, year=year)
        elif c == "3":
            team = pick_team(league)
            if team:
                schedule_view(league, team, year=year)


class _KickoffRanks:
    """Poll ranks as they stood at kickoff of an archived game."""

    def __init__(self, g):
        self.ranks = getattr(g, "ranks", {})

    def rank_of(self, team):
        return self.ranks.get(team)


def pick_conference(league: League):
    clear()
    print(title_bar("PICK A CONFERENCE"))
    for i, (short, full, color) in enumerate(CONFERENCES, 1):
        n = len(league.conference_teams(short))
        print(f"   {paint(f'[{i:>2}]', C.BYELLOW)}  {pad(paint(full, color, C.BOLD), 34)}"
              f"{paint(f'{n} teams', C.GRAY)}")
    choice = ask("Conference # (Enter to go back):")
    if choice.isdigit() and 1 <= int(choice) <= len(CONFERENCES):
        return CONFERENCES[int(choice) - 1][0]
    return None


def week_scoreboard(league: League, week, conference=None, year=None):
    """One week of games; N/P to move through the season, a game's number for its
    box score. With `year`, a finished season from the archive."""
    import archive
    past = year is not None and year != league.year
    while True:
        clear()
        scope = conference or "ALL GAMES"
        print(title_bar(f"{year if past else league.year} · {league.week_name(week).upper()} · {scope.upper()}"))
        if past:
            games = archive.games_for(league, year, week=week)
            if conference:
                games = [g for g in games if conference in (g.home.conference, g.away.conference)]
            best = lambda g: min(g.ranks.get(g.home) or 99, g.ranks.get(g.away) or 99)
            games = sorted(games, key=lambda g: (0 if g.game_type == "National Championship" else 1, best(g)))
        else:
            games = league.schedule.get(week, [])
            if conference:
                members = set(league.conference_teams(conference))
                games = [g for g in games if g.home in members or g.away in members]
            if week > REGULAR_SEASON_WEEKS:
                from season import matchup_order
                games = sorted(matchup_order(games), key=lambda g: not g.played)
            else:
                games = sorted(games, key=lambda g: (not g.played, -(g.home.team_ovr + g.away.team_ovr)))
        numbered = {}
        if not games:
            print(paint("\n   No games scheduled.", C.GRAY))
        else:
            done = [g for g in games if g.played]
            todo = [g for g in games if not g.played]
            yours = next((g for g in games if _mine(league, g)), None)
            if yours is not None:
                print()
                num = done.index(yours) + 1 if yours in done else None
                print(paint("   YOUR GAME", C.BYELLOW, C.BOLD) + _schedule_row(yours, conference, league.rankings, num))
            for label, block in (("RESULTS", done), ("SCHEDULED", todo)):
                if not block:
                    continue
                print()
                print(paint(f"   {label}", C.BCYAN, C.BOLD))
                # Postseason rows carry bowl names, so they get the full width.
                half = len(block) if week > REGULAR_SEASON_WEEKS else (len(block) + 1) // 2
                for i, (a, b) in enumerate(zip_longest(block[:half], block[half:])):
                    na = i + 1 if label == "RESULTS" else None
                    nb = i + 1 + half if label == "RESULTS" and b else None
                    left = _schedule_row(a, conference, league.rankings, na)
                    right = _schedule_row(b, conference, league.rankings, nb) if b else ""
                    if _mine(league, a):
                        left = _schedule_row(a, conference, league.rankings, na, mine=True)
                    if b is not None and _mine(league, b):
                        right = _schedule_row(b, conference, league.rankings, nb, mine=True)
                    print(pad(left, 51) + right)
            numbered = {i: g for i, g in enumerate(done, 1)}   # left column counts down, then the right
        if conference and week <= REGULAR_SEASON_WEEKS and not past:
            byes = [t for t in league.conference_teams(conference)
                    if not any(t in (g.home, g.away) for g in league.schedule.get(week, []))]
            if byes:
                print(paint("\n   BYE: " + ", ".join(t.school for t in byes), C.GRAY))
        if week > REGULAR_SEASON_WEEKS and games:
            print(paint("\n   (n) NP seed", C.GRAY))
        print(paint("\n   #rank at kickoff  ·  c conference  ·  N neutral site  ·  F vs FCS  ·  ! upset", C.GRAY))
        print(paint(f"   {len(games)} games  ·  [#] box score   [N] next week   [P] previous week   "
                    f"[W#] jump to week (W7)   [B] back", C.GRAY))
        import webview
        if webview.on():
            try:
                kr = league.rankings

                def gr(g, n):
                    k = _kickoff(g, kr)
                    d = {"n": n, "mine": _mine(league, g), "played": bool(g.played), "neutral": bool(g.neutral),
                         "away": g.away.school, "home": g.home.school, "ar": _try_rank(k, g.away), "hr": _try_rank(k, g.home),
                         "box": bool(g.played and g.box is not None), "bowl": g.game_type if g.game_type != "Regular Season" else ""}
                    if g.played:
                        d.update(a=g.away_score, h=g.home_score, awayWon=g.winner is g.away)
                    return d
                done = [g for g in games if g.played]
                webview.emit("scores", {"title": f"{year if past else league.year} · {league.week_name(week)}",
                                        "scope": conference or "All games", "week": week,
                                        "done": [gr(g, i) for i, g in enumerate(done, 1)],
                                        "todo": [gr(g, None) for g in games if not g.played]})
            except Exception:
                pass
        choice = ask("Select:").lower()
        if choice == "n":
            week = min(18, week + 1)
        elif choice == "p":
            week = max(1, week - 1)
        elif choice.startswith("w") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= 18:
            week = int(choice[1:])
        elif choice.isdigit() and games and int(choice) in numbered:
            g = numbered[int(choice)]
            if g.box is not None:
                show_box_score(league, g)
        else:
            return week


def _schedule_row(g, conference=None, rankings=None, num=None, mine=False):
    if g is None:
        return ""
    lead = _num(num, mine) if num is not None else (paint("▶  ", C.BYELLOW, C.BOLD) if mine else "   ")
    if getattr(g, "archived", False) or (g.played and getattr(g, "ranks", None)):
        rankings = _KickoffRanks(g)
    tag = ""
    if getattr(g, "neutral", False) and getattr(g, "game_type", "Regular Season") == "Regular Season":
        tag = paint(" N", C.GRAY)
    elif g.conference_game and getattr(g, "game_type", "Regular Season") == "Regular Season":
        tag = paint(" c", C.GRAY)
    elif getattr(g.away, "fcs", False) or getattr(g.home, "fcs", False):
        tag = paint(" F", C.GRAY)

    tag += _post_tag(g)

    if g.played:
        win, lose = (g.home, g.away) if g.home_score > g.away_score else (g.away, g.home)
        ws, ls = max(g.home_score, g.away_score), min(g.home_score, g.away_score)
        at = "vs" if win is g.home else "at"
        if getattr(g, "archived", False):
            upset = paint(" !", C.BRED, C.BOLD) if g.ranks.get(lose) and not g.ranks.get(win) else ""
        else:
            upset = paint(" !", C.BRED, C.BOLD) if win.team_ovr + 6 < lose.team_ovr else ""
        return (f"{lead}{pad(_poll_tag(rankings, win) + truncate(win.school, 14), 17 if num is None else 16)}"
                f"{paint(f'{ws:>3}', C.BWHITE, C.BOLD)}  "
                f"{paint(at, C.GRAY)} {pad(_poll_tag(rankings, lose) + truncate(lose.school, 12), 15)}"
                f"{ls:>3}{tag}{upset}")
    return (f"{lead if mine else '   '}{pad(_poll_tag(rankings, g.away) + truncate(g.away.school, 14), 17)}{paint('  at', C.GRAY)}  "
            f"{pad(_poll_tag(rankings, g.home) + truncate(g.home.school, 14), 18)}{tag}")


def _post_tag(g, width=None):
    """' [Arroyo Bowl · NP QF]' for postseason games, '' otherwise."""
    gt = g.game_type
    if gt == "Regular Season":
        return ""
    short = {"NP First Round": "NP R1", "NP Quarterfinal": "NP QF", "NP Semifinal": "NP SF",
             "National Championship": "TITLE"}.get(gt)
    if gt == "Conference Championship":
        text = g.bowl_name.replace("Championship", "CCG")
    elif gt == "NP First Round":
        text = "NP 1st Round"
    elif gt == "National Championship":
        text = "NATIONAL TITLE"
    elif short:
        text = f"{g.bowl_name} · {short}"
    else:
        text = g.bowl_name
    return paint(f" [{text}]", C.BYELLOW)


def _seed(g, team):
    s = ps.seed_of(g, team) if g.game_type in ps.CFP_TYPES else None
    return f"({s})" if s else ""


def schedule_view(league: League, team: Team, year=None):
    """A team's season, week by week. Pick a played game by number for its box
    score; [Y] switches to another season this program played."""
    import archive
    import weather
    year = year or league.year
    while True:
        past = year != league.year
        clear()
        color = league.conference_color(team.conference)
        print(title_bar(f"{team.full_name.upper()} · {year} SCHEDULE", color))
        if past:
            games = archive.games_for(league, year, team.school)
            me = archive.team_stub(league, year, team.school)
            rec = next((r for r in getattr(team, "historical_records", []) if r[0] == year), None)
            if rec:
                print(f"   {paint('Record', C.GRAY)} {rec[1]}-{rec[2]}   {paint('Conference', C.GRAY)} {rec[3]}-{rec[4]}")
            else:
                print()
            by_week = {g.week: g for g in games}
            weeks = range(1, 19)
        else:
            me = team
            print(f"   {paint('Record', C.GRAY)} {team.record}   {paint('Conference', C.GRAY)} {team.conf_record}")
            by_week = {g.week: g for g in league.team_games(team)}
            weeks = sorted(league.schedule)
        import scout
        hide = scout.hidden(league)
        import sos
        sline = sos.line(league, team, year=year if past else None, hide=hide)
        if sline:
            print(sline + "\n")
        live = {t.school: t for t in league.teams}
        wrows = []
        print(paint(f"   {'#':>2} {'WEEK':<9} {'OPPONENT':<24}{'RESULT':<11}"
                    + ("" if past else f"{'THEM':<10}" + (f"{'THEY LOOK':<14}{'OUTLOOK':<12}" if hide else
                                                      f"{'OVR':>4}  {'WIN %':>6}   ")) + "NOTE", C.GRAY, C.BOLD))
        numbered = {}
        for week in weeks:
            g = by_week.get(week)
            if not g:
                if week <= REGULAR_SEASON_WEEKS and (not past or by_week):
                    print(paint(f"      {_wk(week)} BYE", C.GRAY))
                    wrows.append({"bye": True, "wk": _wk(week).strip()})
                continue
            opp = g.opponent_of(me)
            where = "vs" if g.home is me or g.neutral else "at"
            tags = []
            if g.conference_game and g.game_type == "Regular Season":
                tags.append(paint("conf", C.GRAY))
            elif getattr(opp, "fcs", False):
                tags.append(paint("FCS", C.GRAY))
            post = _post_tag(g).strip()
            if post:
                tags.append(post)
            if getattr(g, "showcase", None):
                tags.append(paint(f"{g.showcase} ({truncate(g.venue.split(',')[0], 18)})", C.BYELLOW))
            riv = rivalry_name(me, opp) if not past else None
            if riv:
                tags.append(paint(f"★ {riv}", C.BMAGENTA))
            seed = ps.seed_of(g, opp) if g.game_type in ps.CFP_TYPES else None
            # the rank he carried into the game once it's played; this week's poll for games still ahead
            rank = (getattr(g, "ranks", None) or {}).get(opp) if (past or g.played) else league.rankings.rank_of(opp)
            opp_txt = f"{where} {'(' + str(seed) + ') ' if seed else ''}{'#' + str(rank) + ' ' if rank else ''}{opp.school}"
            n = len(numbered) + 1
            numbered[n] = g
            num = paint(f"{n:>2}", C.GRAY)
            them, look = "", ""
            if not past:
                t = live.get(opp.school)
                if t is not None and (t.wins or t.losses):
                    now = league.rankings.rank_of(t)
                    them = paint(t.record, C.GRAY) + (paint(f" #{now}", C.BYELLOW) if now else "")
                elif t is not None and getattr(t, "last_season", None):
                    them = paint(f"'{str(league.year - 1)[2:]} {t.last_season[0]}-{t.last_season[1]}", C.GRAY)
                them = pad(them, 10)
                if not getattr(opp, "fcs", False):
                    look = pad(scout.team(opp.team_ovr, who=opp), 14) if hide else pad(rating(opp.team_ovr), 4, "right") + "  "
                else:
                    look = pad("", 14 if hide else 6)
            if g.played:
                won = g.winner is me
                res = paint("W" if won else "L", C.BGREEN if won else C.BRED, C.BOLD)
                score = f"{g.score_for(me)}-{g.score_for(opp)}"
                ot = " OT" if g.box is not None and g.box.ot_round else ""
                wxs = weather.short(g, league) if getattr(g, "wx", None) and weather.severity(g.wx) >= 2 else ""
                if wxs:
                    tags.append(paint(wxs, C.BCYAN))
                print(f"   {num} {_wk(week)} {pad(truncate(opp_txt, 23), 24)}{res} {pad(score + ot, 9)}{them}"
                      + (look + pad("", 12 if hide else 9) if not past else "") + " ".join(tags))
                wrows.append({"n": n, "wk": _wk(week).strip(), "opp": opp_txt, "won": won, "score": score + ot,
                              "them": them, "look": look, "tags": [t for t in tags], "played": True,
                              "box": g.box is not None})
            else:
                import carousel as cz
                try:
                    p = cz.win_prob(me, opp, 0 if g.neutral else (1 if g.home is me else -1))
                    p = min(0.99, max(0.01, p))
                    wp = paint(pad(scout.odds_short(p), 12) if hide else f"{p * 100:>6.0f}%  ",
                               C.BGREEN if p >= 0.6 else C.BYELLOW if p >= 0.4 else C.BRED)
                except Exception:
                    wp = pad("", 12 if hide else 9)
                wxs = weather.short(g, league).replace("fcst ", "")
                if wxs:
                    tags.append(paint(wxs, C.BCYAN))
                print(f"   {num} {_wk(week)} {pad(truncate(opp_txt, 23), 24)}{paint(pad('—', 11), C.GRAY)}{them}"
                      f"{look}{wp}{' '.join(tags)}")
                wrows.append({"n": n, "wk": _wk(week).strip(), "opp": opp_txt, "played": False, "them": them,
                              "look": look, "wp": wp, "wpv": locals().get("p"), "tags": [t for t in tags]})
        if past and not by_week:
            print(paint(f"   {team.school} has no games on file for {year}.", C.GRAY))
        years = [y for y in archive.seasons(league) if archive.games_for(league, y, team.school)]
        import ui as _u
        print()
        _u.footer(*([_u.key("#", "box score"), _u.key("T#", "opponent's team page"), _u.key("S#", "his schedule")]
                    if numbered else []),
                  _u.key("O", "another team's schedule"), _u.key("Y", "another season") if years else "",
                  _u.key("S", "strength of schedule"), _u.key("B", "back", C.GRAY))
        import webview
        if webview.on():
            for r in wrows:
                for k in ("them", "look", "wp"):
                    if k in r:
                        r[k] = webview.plain(r[k])
                r["tags"] = [webview.plain(t) for t in r.get("tags", [])]
                if not isinstance(r.get("wpv"), (int, float)):
                    r.pop("wpv", None)
            webview.schedule(league, team, year, wrows,
                             (f"{rec[1]}-{rec[2]}" if past and rec else team.record),
                             (f"{rec[3]}-{rec[4]}" if past and rec else ("" if past else team.conf_record)), sline)
        choice = ask("Select:").lower().replace(" ", "")
        pick = numbered.get(int(choice[1:])) if choice[:1] in ("t", "s") and choice[1:].isdigit() else None
        if pick is not None:
            other = live.get(pick.opponent_of(me).school)
            if other is None:
                print(paint("   That program isn't in this world anymore.", C.GRAY))
                pause()
            elif choice[0] == "t":
                team_view(league, other)
            else:
                schedule_view(league, other, year=year)
            continue
        if choice == "s":
            sos.screen(league, focus=team)
            continue
        if choice == "o":
            other = pick_team(league)
            if other:
                team, year = other, league.year
            continue
        if choice.isdigit() and int(choice) in numbered:
            g = numbered[int(choice)]
            if g.played and g.box is not None:
                show_box_score(league, g)
            elif not g.played:
                print(paint("   Not played yet. [T#] opens that team's page.", C.GRAY))
                pause()
        elif choice == "y" and years:
            options = [league.year] + years
            pick = ask(f"Which season? ({', '.join(map(str, options))})")
            if pick.isdigit() and int(pick) in options:
                year = int(pick)
        else:
            return


# ═══ Week results ═══════════════════════════════════════════════════════════

def _wk(week):
    label = f"Wk {week:>2}" if week <= REGULAR_SEASON_WEEKS else ps.WEEK_SHORT.get(week, "Post")
    return label.ljust(9)


def _kickoff(g, rankings):
    """A finished game shows the poll as it stood at kickoff — not this week's new poll,
    which already has the result baked in (a No. 5 that lost shows up as No. 15)."""
    if getattr(g, "played", False) and getattr(g, "ranks", None):
        return _KickoffRanks(g)
    return rankings


def _mine(league, g):
    import ad_mode
    you = getattr(league, "user_team", None) if getattr(league, "mode", None) == "career" else ad_mode.my_team(league)
    return g is not None and you is not None and you in (g.home, g.away)


def _num(n, mine):
    """Row number for a scoreboard; your game gets a marker so it can't blend in."""
    if mine:
        return paint(("▶" + f"{n:>2}" if n < 100 else "▶" + str(n)) + " ", C.BYELLOW, C.BOLD)
    return paint(f"{n:>3} ", C.GRAY)


def _result_line(g, rankings=None):
    rankings = _kickoff(g, rankings)
    w, l = g.winner, g.loser
    ws, ls = g.score_for(w), g.score_for(l)
    at = "vs" if (w is g.home or g.neutral) else "@"
    rk_w = rankings.rank_of(w) if rankings is not None else None
    rk_l = rankings.rank_of(l) if rankings is not None else None
    upset = ((l.team_ovr - w.team_ovr) >= 4
             or (rk_l and (not rk_w or rk_w - rk_l > 5))                  # ranked, and beaten by the unranked
             or (getattr(w, "fcs", False) and not getattr(l, "fcs", False)))   # FCS over FBS
    rounds = getattr(g.box, "ot_round", 0) if g.box is not None else 0
    ot_txt = "" if not rounds else "OT" if rounds == 1 else f"{rounds}OT"
    wr = _poll_tag(rankings, w)
    lr = _poll_tag(rankings, l)
    import classics
    classic = _LEAGUE[0] is not None and getattr(g, "box", None) is not None and classics.is_classic(_LEAGUE[0], g)
    # Fixed-width tail: OT column, then the flags, so the right-hand column never shifts.
    tail = " " + pad(paint(ot_txt, C.GRAY), 3)
    # The flags lead the line (right after its number), so in a two-column scoreboard they
    # can never be mistaken for the next column's game.
    flags = (paint("!", C.BRED, C.BOLD) if upset else " ") + (paint("★", C.BYELLOW, C.BOLD) if classic else " ")
    from ui import short_name
    return (f"{flags}{pad(paint(wr + short_name(w.school, 16 - len(wr)), C.BWHITE, C.BOLD), 16)}{ws:>3} "
            f"{pad(paint(at, C.GRAY), 2, 'right')} "
            f"{pad(lr + short_name(l.school, 16 - len(lr)), 16)}{ls:>3}{tail}")


def _final_line(g, rankings=None):
    """'BC 19, VT 14 · Final' — the last result, the way a crawl shows it."""
    from ui import abbr
    rankings = _kickoff(g, rankings)
    w, l = g.winner, g.loser
    rounds = getattr(g.box, "ot_round", 0) if g.box is not None else 0
    ot = "" if not rounds else " (OT)" if rounds == 1 else f" ({rounds}OT)"
    wr, lr = _poll_tag(rankings, w), _poll_tag(rankings, l)
    return (paint(f"{wr}{abbr(w.school)} {g.score_for(w)}", C.BWHITE, C.BOLD) + paint(", ", C.GRAY)
            + f"{lr}{abbr(l.school)} {g.score_for(l)}" + paint(f" · Final{ot}", C.GRAY))


def _poll_tag(rankings, team):
    """'#7 ' when a team is ranked — the way a scoreboard shows it."""
    if rankings is None:
        return ""
    r = rankings.rank_of(team)
    return f"#{r} " if r else ""


# ═══ Gameday ════════════════════════════════════════════════════════════════

def _matchup_card(league, g, idx, total, last):
    clear()
    post = ps.is_postseason(g)
    head = (f"{league.year} · {league.week_name(league.week).upper()}  ·  "
            + (f"GAME {idx} OF {total}" if total else "YOUR GAME"))
    print(title_bar(head))
    if last is not None:
        print(paint("   Last result: ", C.GRAY) + _final_line(last, league.rankings) + _post_tag(last))
    print()

    if post:
        _postseason_banner(g)
    else:
        import broadcast
        slot = broadcast.when(g)
        if slot:
            print(pad(paint(slot, C.BYELLOW if getattr(g, "window", None) else C.GRAY, C.BOLD), WIDTH, "center"))
            print()

    for label, t in (("AWAY", g.away), ("HOME", g.home)):
        c = t.coach
        color = league.team_color(t)
        rank = league.rankings.rank_of(t)
        seed = ps.seed_of(g, t) if g.game_type in ps.CFP_TYPES else None
        badge = (paint(f"({seed}) ", C.BGREEN, C.BOLD) if seed else "") + \
                (paint(f"#{rank} ", C.BYELLOW, C.BOLD) if rank else "")
        side = "    " if g.neutral else label
        print(f"   {paint(side, C.GRAY)}  {pad(badge + paint(t.full_name, C.BOLD, C.BWHITE), 38)}"
              f"{pad(paint(t.conference, color), 12)}{t.record:>5}   "
              + (f"{__import__('scout').team(t.team_ovr, who=t)}  {paint('O', C.GRAY)} "
                 f"{__import__('scout').team_short(t.offense_ovr, who=t)}  {paint('D', C.GRAY)} "
                 f"{__import__('scout').team_short(t.defense_ovr, who=t)}" if __import__('scout').hidden(league, t) else
                 f"OVR {rating(t.team_ovr)}   OFF {rating(t.offense_ovr)}  DEF {rating(t.defense_ovr)}"))
        blk = [paint(f"HC {c.name} · {c.offense_scheme} offense · {c.defense_scheme} defense · "
                     f"aggression {c.aggression}", C.GRAY)]
        if post:
            notes = ps.team_tags(league, g, t) + ps.path_lines(league, t, league.week)
            if notes:
                blk.append(paint(" · ".join(n[0].upper() + n[1:] for n in notes), C.BCYAN))
        hurt = [p for p in t.injured() if p in t.players_at(p.position)[:2]][:3]
        if hurt:
            blk.append(paint("OUT: " + ", ".join(f"{p.position} {p.last_name}" for p in hurt), C.BRED))
        import faces
        if faces.enabled():
            import faces_ui
            for ln in faces_ui.beside(faces.coach_portrait(c, mini=True), blk, indent=9, gap=2):
                print(ln)
        else:
            for ln in blk:
                print("         " + ln)

    if post:
        print()
        stakes = ps.stakes_lines(league, g)
        for i, line in enumerate(stakes):
            lead = paint("   STAKES  ", C.BYELLOW, C.BOLD) if i == 0 else "           "
            print(lead + paint(line, C.BWHITE if i == 0 else C.GRAY))
        riv = rivalry_name(g.home, g.away)
        if riv:
            print(paint(f"           A postseason edition of {riv}.", C.GRAY))
    else:
        kind = "Conference game" if g.conference_game else "Non-conference"
        where = f"{g.venue} (neutral site)" if g.neutral else f"{g.home.stadium} ({g.home.capacity:,})"
        riv = rivalry_name(g.home, g.away)
        print(paint(f"\n   {where}  ·  {kind}" + (f"  ·  {riv}" if riv else ""), C.GRAY))
        import rivalries
        s = rivalries.series(league, g.away, g.home)
        if s.n or s.trophy:
            bits = []
            if s.trophy:
                bits.append(f"{s.trophy[0].upper() + s.trophy[1:]}" + (f" (held by {s.holder})" if s.holder else " (up for grabs)"))
            if s.n:
                who, n = s.streak
                bits.append(f"series since {s.since}: {s.record_str()}" + (f", {who} has won {n} straight" if n >= 2 else ""))
                m = s.last
                bits.append(f"last meeting {m.year}: {m.winner} {m.wscore}-{m.lscore}")
            print(paint("   " + "  ·  ".join(bits), C.BCYAN))
        if not g.played and not g.neutral and not getattr(g.home, "fcs", False):
            import facilities
            att, cap, fill, why = facilities.forecast(league, g)
            crowd = "sellout expected" if fill >= 0.985 else f"expected crowd ~{att // 1000 * 1000:,} ({fill * 100:.0f}% full)"
            import stadium as sd
            rk = sd.rank_of(league, g.home)
            print(paint(f"   {crowd}" + (f"  ·  {why}" if why else "") + f"  ·  {sd.noise_word(sd.noise_rating(g.home)).lower()} "
                        f"building" + (f"  ·  No. {rk} toughest place to play" if rk and rk <= 25 else ""), C.GRAY))
    print()
    import hotseat
    mine = getattr(league, "user_team", None) in (g.home, g.away) and getattr(league, "mode", None) == "career" \
        and not hotseat.neutral()
    import webview
    webview.matchup(league, g, mine)
    if mine:
        return "mine"                                    # your game gets its own menu (_your_game)
    if getattr(league, "mode", None) == "spectator" and not g.played:
        import book_screens
        for ln in book_screens.card_lines(league, g):
            print(ln)
        if book_screens.card_lines(league, g):
            print()
    follow = _followed_ahead(league, g)
    print(f"   {paint('[C]', C.BYELLOW, C.BOLD)} Commentary     "
          f"{paint('[F]', C.BYELLOW, C.BOLD)} Fast Sim     "
          f"{paint('[W]', C.BYELLOW, C.BOLD)} Fast Sim to End of Week     {paint('(Enter = Fast Sim)', C.GRAY)}")
    if follow is not None:
        print(f"   {paint('[Y]', C.BYELLOW, C.BOLD)} Sim to the {follow.school} game "
              + paint("(fast-sims everything before it)", C.GRAY))
    if getattr(league, "mode", None) == "spectator" and not g.played and g.week > league.week - 1:
        print(f"   {paint('[B]', C.BGREEN, C.BOLD)} Bet this game " + paint("(The Window — lines close at kickoff)", C.GRAY))
    return ask("Select:").lower()


def _followed_ahead(league, g):
    """The team you follow, if its game is still to come this week (and this isn't it)."""
    import dashboard
    t = getattr(league, "follow_team", None)
    if getattr(league, "mode", None) == "career" or t is None or t in (g.home, g.away):
        return None
    for x in league.schedule.get(league.week, []):
        if t in (x.home, x.away) and not x.played:
            return t
    return None


YOUR_MODES = {"1": ("sim", "Sim it", "straight to the final score"),
              "2": ("moments", "Play the big moments", "the staff calls it; you take the headset when it matters"),
              "3": ("full", "Coach every snap", "every play is your call"),
              "4": ("watch", "Watch the broadcast", "full commentary, no play-calling")}


def _your_game_mode(league, g):
    """How you want to play your own game. Remembers your last choices, so Enter
    is usually all it takes."""
    import settings
    from commentary import SPEEDS
    st = settings.load()
    last = st.get("your_game_mode", "moments")
    last_key = next((k for k, v in YOUR_MODES.items() if v[0] == last), "2")
    print(paint("   ★ This is your game. How do you want to play it?", C.BMAGENTA, C.BOLD))
    from netplay import replay
    hvh = replay.online(league) and replay.both_human(league, g)
    if hvh:                                           # online, two players' programs: the staffs call it
        print(paint("   Two coaches from your world meet here: both staffs call it from your game plans.\n"
                    "   Watch the broadcast or sim it.", C.BYELLOW))
    played = bool(getattr(league, "__dict__", {}).get("_your_games_played"))
    for k, (mode, label, blurb) in YOUR_MODES.items():
        mark = paint("  ← last time" if played else "  ← suggested", C.BCYAN) if k == last_key else ""
        print(f"   {paint(f'[{k}]', C.BYELLOW if k == last_key else C.BYELLOW, C.BOLD)} {pad(label, 24)}"
              f"{paint(blurb, C.GRAY)}{mark}")
    print(paint("   During a game: at every quarter break you can skip a quarter, skip to the final, change the\n"
                "   speed, or switch between big moments and every snap. [S] mid-drive hands it to your staff.", C.GRAY))
    import webview
    webview.opts("How do you want to play it?", [(k, label + ("  ★" if k == last_key else ""), blurb)
                                                  for k, (mode_, label, blurb) in YOUR_MODES.items()],
                 "At every quarter break you can skip ahead, change the speed, or switch between big moments and every snap.")
    c = ask(f"Select (Enter = {YOUR_MODES[last_key][1]}):").strip()
    mode = YOUR_MODES.get(c or last_key, YOUR_MODES[last_key])[0]
    if hvh and mode in ("full", "moments"):
        mode = "watch"
    else:
        st["your_game_mode"] = mode
    league.__dict__["_your_games_played"] = True       # "last time" means last time in this career
    delay, call_d = None, True
    if mode != "sim":
        sp = st.get("game_speed", "3" if mode != "watch" else "2")
        print("   Speed:  " + "   ".join(f"{paint(f'[{k}]', C.BYELLOW, C.BOLD)} {name}" for k, (name, _) in SPEEDS.items()))
        webview.opts("Game speed", [(k, name + ("  ★" if k == sp else ""), "") for k, (name, _) in SPEEDS.items()])
        choice = ask(f"Select (Enter = {SPEEDS[sp][0]}):").strip() or sp
        choice = choice if choice in SPEEDS else sp
        st["game_speed"] = choice
        delay = SPEEDS[choice][1]
    if mode in ("full", "moments"):
        import staff
        t = league.user_team
        def who(side):
            c = staff.play_caller(t, side)
            return "you" if c is t.coach else f"{'OC' if side == 'off' else 'DC'} {c.name}"
        print(f"   Play-calling:  offense — {paint(who('off'), C.BWHITE, C.BOLD)}   "
              f"defense — {paint(who('def'), C.BWHITE, C.BOLD)}")
        mine_off, mine_def = who("off") == "you", who("def") == "you"
        opts = ["[Enter] keep"]
        if not (mine_off and mine_def):
            opts.append("[B] you call both")
        if not (mine_off and not mine_def):
            opts.append("[O] you call offense, DC defense")
        if not (mine_def and not mine_off):
            opts.append("[D] you call defense, OC offense")
        webview.opts(f"Play-calling: offense — {who('off')} · defense — {who('def')}",
                     [(o[1:o.index("]")], o[o.index("]") + 2:], "") for o in opts])
        d = ask("  ·  ".join(opts) + ":").strip().lower()
        if d in ("b", "o", "d"):
            staff.set_calls(t, off="HC" if d in ("b", "o") else "OC", df="HC" if d in ("b", "d") else "DC")
        cl = staff.calls(t)
        call_d = cl["def"] == "HC" or getattr(t, "dc", None) is None
        st["call_defense"] = call_d
    settings.save()
    return mode, delay, call_d


def _postseason_banner(g):
    """The block at the top of a postseason preview: what, where, when."""
    color = C.BYELLOW if g.game_type in ps.CFP_TYPES else C.BCYAN
    edge = "★" if g.game_type in ps.CFP_TYPES else "◆"
    print(pad(paint(f"{edge}  {ps.banner(g)}  {edge}", color, C.BOLD), WIDTH, "center"))
    if g.game_type == "NP First Round":
        sub = f"On campus at {g.home.stadium} ({g.home.capacity:,})  ·  {ps.date_words(g.date)}"
    else:
        sub = ps.site_line(g)
    print(pad(paint(sub, C.GRAY), WIDTH, "center"))
    print()


def gameday(league: League):
    from commentary import SPEEDS, Narrator, box_score_lines
    import broadcast
    import gameday_show
    import week
    import ad_mode
    if ad_mode.active(league) and not ad_mode.week_hub(league):   # the AD's desk before the week
        return
    import career_plus
    if career_plus.mine(league):
        career_plus.bowl_week(league, week.next_game(league, league.user_team))   # your bowl's week, once
    if not week.hub(league):                          # your week first: film, inbox, practice, the presser
        return
    snap = career_plus.before(league)                 # what the Weekly Wrap compares against
    games = league.start_week()                       # already in kickoff order
    if league.week <= REGULAR_SEASON_WEEKS:
        sat = broadcast.season_saturday(league.year, league.week)
        before = [g for g in games if g.date < sat]   # Thursday / Friday (and Lake Country Lights) nights
    else:
        before = []
    # In a career the week is about your game: everyone else plays around it (results after).
    state = {"last": None, "auto": getattr(league, "mode", None) == "career" and getattr(league, "user_team", None) is not None}
    order = list(enumerate(games, 1))
    show_done = False
    for i, g in order:
        if not show_done and g not in before:
            gameday_show.run_show(league, games)       # Saturday morning, live from the week's biggest campus
            show_done = True
        _play_one(league, g, i, len(games), state, SPEEDS, Narrator)
    league.finish_week(games)
    week_results(league, games)
    career_plus.wrap(league, snap, games)             # Coach Career: what your week changed
    if league.week == 14:
        career_plus.selection_show(league)            # Selection Day: the field and the bowls
    import recap
    recap.after_week(league, games)                   # Spectator: the week in one place, and [C] curate stories
    if getattr(league, "mode", None) == "spectator":
        import book_screens
        import sportsbook
        book = sportsbook.get(league, create=False)
        if book is not None and book.unseen:          # what the week did to your bankroll
            book_screens.report(league, book, title=f"{league.week_name(league.week).upper()} AT THE WINDOW")


def _play_one(league, g, i, total, state, SPEEDS, Narrator):
    import hotseat
    yours = getattr(league, "mode", None) == "career" and getattr(league, "user_team", None) in (g.home, g.away) \
        and not hotseat.neutral()
    if state["auto"] and not yours:
        league.play_game(g)
        state["last"] = g
        return
    if yours:
        _your_game(league, g, i, SPEEDS, Narrator)
        state["last"] = g
        return
    target = state.get("skip_to")
    if target is not None:
        if target not in (g.home, g.away):
            league.play_game(g)                        # on the way to the game you follow
            state["last"] = g
            return
        state["skip_to"] = None
    choice = None
    while choice not in ("c", "f", "w", "y"):
        choice = _matchup_card(league, g, i, total, state["last"]) or "f"       # Enter = fast sim
        if choice == "y" and _followed_ahead(league, g) is None:
            choice = None
        if choice == "b" and getattr(league, "mode", None) == "spectator":
            import book_screens
            import sportsbook
            book = sportsbook.get(league)
            if book is not None and sportsbook.line(book, league, g) is not None:
                if not book.welcomed:
                    book_screens.welcome(league, book)
                book_screens.game_screen(league, book, g)     # the lines are still open until kickoff
            choice = None
    if choice == "y":
        state["skip_to"] = league.follow_team
        print(paint(f"\n   Simulating ahead to {league.follow_team.school}...", C.GRAY))
        league.play_game(g)
    elif choice == "w":
        state["auto"] = True
        print(paint("\n   Simulating the rest of the week...", C.GRAY))
        league.play_game(g)
    elif choice == "f":
        league.play_game(g)
    elif choice == "p":
        import coach_mode
        g.controller = coach_mode.setup_for_game(league, g)
        print()
        print("   Broadcast speed:  " + "   ".join(
            f"{paint(f'[{k}]', C.BYELLOW, C.BOLD)} {name}" for k, (name, _) in SPEEDS.items()))
        speed = ask("Select (Enter = Fast):") or "3"
        delay = SPEEDS.get(speed, SPEEDS["2"])[1]
        clear()
        try:
            league.play_game(g, Narrator(booth_index=i - 1, delay=delay, rng=league.rng, league=league))
        finally:
            g.controller = None
        pause("Press Enter for the box score...")
        show_box_score(league, g)
    else:
        print()
        print("   Broadcast speed:  " + "   ".join(
            f"{paint(f'[{k}]', C.BYELLOW, C.BOLD)} {name}" for k, (name, _) in SPEEDS.items()))
        speed = ask("Select (Enter = Normal):") or "2"
        delay = SPEEDS.get(speed, SPEEDS["2"])[1]
        clear()
        league.play_game(g, Narrator(booth_index=i - 1, delay=delay, rng=league.rng, league=league))
        pause("Press Enter for the box score...")
        show_box_score(league, g)
    state["last"] = g


def _your_game(league, g, i, SPEEDS, Narrator):
    """Your game, your way: sim it, play the big moments, coach every snap, or watch."""
    import guide
    guide.tip(league, "your_game")               # before the matchup is drawn
    import coach_mode
    _matchup_card(league, g, i, 0, None)
    mode, delay, call_d = _your_game_mode(league, g)
    from netplay import replay
    if not (replay.online(league) and replay.both_human(league, g)):
        g.halftime_team = league.user_team            # you make the halftime call (halftime.py)
    net = _net_game(league, g, mode, call_d, i)       # online: what the host needs to play it the same
    if mode == "sim":
        print(paint("\n   Simulating...", C.GRAY))
        try:
            with net:
                league.play_game(g)
        finally:
            g.__dict__.pop("halftime_team", None)
        _quick_final(league, g)
        return
    narr = Narrator(booth_index=i - 1, delay=delay, rng=replay.narr_rng(league, g), league=league)
    if mode in ("full", "moments"):
        g.controller = coach_mode.setup_for_game(league, g, mode=mode, call_defense=call_d)
    clear()
    if mode == "moments":
        t = league.user_team
        o = g.away if g.home is t else g.home
        print(title_bar(f"{t.school.upper()} vs {o.school.upper()}  ·  BIG MOMENTS"))
        print(paint("\n   The staff has the headset. We'll bring you in when the game is on the line.", C.GRAY))
        narr.muted = True
    try:
        with net:
            league.play_game(g, narr)
    finally:
        ctl = getattr(g, "controller", None)
        g.controller = None
        g.__dict__.pop("halftime_team", None)
    if mode == "moments" and ctl is not None and not ctl.moments:
        print(paint("\n   No big moments this time — the game was decided without you needing the headset.", C.GRAY))
    pause("Press Enter for the box score...")
    show_box_score(league, g)
    import postgame
    postgame.run(league, g)


def _net_game(league, g, mode, call_d, i):
    """Online: record what you type during your game (the host replays it). Offline: nothing."""
    import contextlib
    if not league.__dict__.get("online_client"):
        return contextlib.nullcontext()
    import settings
    import staff
    from netplay import replay
    info = {"mode": mode, "call_d": bool(call_d), "booth": i - 1, "calls": dict(staff.calls(league.user_team)),
            "settings": {k: v for k, v in settings.load().items() if isinstance(v, (str, int, float, bool, dict, list))}}
    g.__dict__["_net"] = info
    return replay.recording(info)


def _quick_final(league, g):
    """A sim result: the final, the scoring summary, and the box score if you want it."""
    t = league.user_team
    o = g.away if g.home is t else g.home
    won = g.winner is t
    clear()
    print(title_bar(f"FINAL  ·  {g.away.school} {g.away_score}  {'vs' if g.neutral else 'at'}  {g.home.school} {g.home_score}"))
    print()
    print("   " + paint("WIN" if won else "LOSS", C.BGREEN if won else C.BRED, C.BOLD)
          + paint(f"  {t.school} {g.score_for(t)}, {o.school} {g.score_for(o)}", C.BWHITE, C.BOLD))
    sim = getattr(g, "sim", None) or getattr(g, "box", None)
    scoring = getattr(sim, "scoring", None) or []
    if scoring:
        print(paint("\n   Scoring:", C.GRAY))
        for sq, sc, team, what in scoring:
            qq = f"Q{sq}" if sq <= 4 else "OT"
            print(f"     {paint(f'{qq} {sc // 60}:{sc % 60:02d}', C.GRAY)}  {pad(team.school, 20)}{paint(str(what), C.GRAY)}")
    import webview
    if webview.on():
        webview.emit("final", {"won": won, "us": {"school": t.school, "score": g.score_for(t), "color": webview._color(league, t)},
                               "them": {"school": o.school, "score": g.score_for(o), "color": webview._color(league, o)},
                               "scoring": [{"q": f"Q{sq}" if sq <= 4 else "OT", "clock": f"{sc // 60}:{sc % 60:02d}",
                                            "team": team.school, "mine": team is t, "what": webview.plain(what)}
                                           for sq, sc, team, what in scoring], "box": g.box is not None})
    if ask("\n  [B] box score, Enter to continue:").strip().lower() == "b":
        show_box_score(league, g)
    import postgame
    postgame.run(league, g)


def bulk_sim(league: League):
    choice = ask("Simulate how many weeks? (or add 's' for whole seasons — e.g. 30s)").strip().lower()
    if choice.endswith("s") and choice[:-1].strip().isdigit():
        sim_seasons(league, int(choice[:-1]))
        return
    if not choice.isdigit():
        return

    weeks = int(choice)
    if weeks <= 0:
        return

    clear()
    print(title_bar(f"SIMULATING {weeks} WEEKS"))
    print()

    for _ in range(weeks):
        if league.season_complete:
            print(paint(f"   Stopped early: Reached the end of the {league.year} season.", C.BYELLOW))
            break
        import preseason
        if preseason.needed(league):
            preseason.mark_done(league)             # simming past fall camp keeps the schedule you have
        print(paint(f"   Simulating Week {league.week + 1}...", C.GRAY))
        import week
        week.auto_week(league)                      # your usual practice plan; people still reach out
        games = league.start_week()
        import gameday_show
        gameday_show.quiet_show(league, games)       # no show, but Campus Countdown still goes somewhere and picks
        for g in games:
            league.play_game(g)
        league.finish_week(games)

    print(paint("\n   Simulation complete.", C.BGREEN))
    pause()
    import recap
    recap.after_week(league)                          # Spectator: the last week's Recap


def _sim_week(league):
    import preseason
    if preseason.needed(league):
        preseason.mark_done(league)
    import week
    week.auto_week(league)
    games = league.start_week()
    import gameday_show
    gameday_show.quiet_show(league, games)
    for g in games:
        league.play_game(g)
    league.finish_week(games)


def _your_team(league):
    import ad_mode
    if getattr(league, "mode", None) == "career" and getattr(league, "user_coach", None) is not None:
        return league.user_coach.team
    if getattr(league, "mode", None) == "ad" and getattr(league, "ad_user", None):
        return league.ad_user["team"]
    return getattr(league, "follow_team", None)


def sim_seasons(league: League, n):
    """Run whole seasons back to back — every game, every offseason, no stops. Your
    staff, your agent and your AD's deputy make the calls you'd normally make."""
    if n <= 0:
        return
    n = min(n, 100)
    clear()
    print(title_bar(f"SIMULATING {n} SEASON{'S' if n != 1 else ''}"))
    print(paint("   Every game and every offseason, with nobody stopping to ask. In a coach career your agent\n"
                "   takes the best job if you're fired (or a much bigger one calls) and signs extensions; your\n"
                "   staff recruits and runs the portal. In AD mode, your deputy runs the program like any AD.\n"
                "   Ctrl+C stops after the current week (the world stays consistent).\n", C.GRAY))
    import time as _time
    import signal
    stop = {"now": False}
    def _ask_stop(*_):
        stop["now"] = True                             # finish the week we're in, then stop cleanly
    try:
        old_handler = signal.signal(signal.SIGINT, _ask_stop)
    except (ValueError, OSError):
        old_handler = None
    league.autosim = True
    rows = []
    try:
        for i in range(n):
            if stop["now"]:
                break
            t0 = _time.time()
            if league.season_complete:
                league.advance_offseason()
            yr = league.year
            while not league.season_complete and not stop["now"]:
                _sim_week(league)
                print(paint(f"\r   {yr}: {league.week_name(league.week):<28}", C.GRAY), end="", flush=True)
            if stop["now"] and not league.season_complete:
                print(paint(f"\n   Stopped after {league.week_name(league.week)} of {yr}.", C.BYELLOW))
                break
            you = _your_team(league)
            heis = league.rankings.heisman[0][0] if league.rankings.heisman else None
            line = f"   {yr}  season complete"
            title = next(iter(league.schedule.get(18, [])), None)
            if title is not None and title.played:
                line = f"   {yr}  🏆 {title.winner.school} ({title.winner.record}) def. {title.loser.school}"
            if heis is not None:
                line += paint(f"   · Golden Helmet: {heis.name} ({heis.position}, {heis.team.school})", C.GRAY)
            if you is not None:
                rk = league.rankings.rank_of(you)
                line += paint(f"   · {you.school} {you.record}" + (f" #{rk}" if rk else ""), C.BCYAN)
            print("\r" + line + " " * 4)
            rows.append(line)
            import classics
            cls = [c for c in classics.book(league) if c["year"] == yr]
            if cls:
                best = max(cls, key=lambda c: c["score"])
                print(paint(f"         ★ {len(cls)} instant classic{'s' if len(cls) != 1 else ''} — best: "
                            f"{truncate(best['headline'], 90)}", C.BYELLOW))
            import realignment
            for text in realignment.news_for(league, yr - 1):
                if text.startswith(("REALIGNMENT", "TV")) or "officially joins" in text:
                    print(paint(f"         {truncate(text, 110)}", C.BMAGENTA))
            if i < n - 1 and not stop["now"]:
                league.advance_offseason()             # the carousel, the portal, signing day — then next fall
            print(paint(f"      ({_time.time() - t0:.0f}s)", C.GRAY))
    finally:
        league.autosim = False
        if old_handler is not None:
            signal.signal(signal.SIGINT, old_handler)
    import career
    career.after_carousel(league)
    print(paint(f"\n   Done. It's {league.year}"
                + (" — the season is over; [A] advances to the offseason." if league.season_complete else "."), C.BGREEN))
    pause()


def show_box_score(league, g):
    from commentary import box_score_lines
    clear()
    away, home = g.away, g.home
    at = "vs" if g.neutral else "at"
    print(title_bar(f"BOX SCORE  ·  {away.school} {g.away_score}  {at}  {home.school} {g.home_score}"))
    if getattr(g, "archived", False):
        when = f"{g.year} · {league.week_name(g.week)}"
        if g.banner:
            print(pad(paint(g.banner, C.BYELLOW, C.BOLD), WIDTH, "center"))
        print(pad(paint(f"{when}  ·  {g.site}", C.GRAY), WIDTH, "center"))
    elif ps.is_postseason(g):
        print(pad(paint(ps.banner(g), C.BYELLOW, C.BOLD), WIDTH, "center"))
        print(pad(paint(ps.site_line(g), C.GRAY), WIDTH, "center"))
    print()
    lines = box_score_lines(g.box)
    for line in lines:
        print(line)
    import webview
    if webview.on():
        try:
            def side(t, sc):
                return {"school": t.school, "abbr": getattr(t, "abbr", t.school[:4]), "score": sc,
                        "color": webview._color(league, t) if hasattr(t, "conference") else None,
                        "won": g.winner is t if getattr(g, "winner", None) is not None else False}
            webview.emit("box", {"away": side(away, g.away_score), "home": side(home, g.home_score), "at": at,
                                 "banner": webview.plain(getattr(g, "banner", "") or (ps.banner(g) if ps.is_postseason(g) else "")),
                                 "lines": list(lines)})
        except Exception:
            pass
    pause()


def _try_rank(r, t):
    try:
        return r.rank_of(t)
    except Exception:
        return None


def week_results(league: League, games):
    if league.week > REGULAR_SEASON_WEEKS:
        from season import matchup_order
        games = matchup_order(games)
    else:
        games = sorted(games, key=lambda g: -(g.home.team_ovr + g.away.team_ovr))
    while True:
        clear()
        print(title_bar(f"{league.year} · {league.week_name(league.week).upper()} RESULTS"))
        print()
        mine = next(((n, g) for n, g in enumerate(games, 1) if _mine(league, g)), None)
        if mine:
            n, g = mine
            print(paint("   YOUR GAME  ", C.BYELLOW, C.BOLD) + _num(n, True) + _result_line(g, league.rankings)
                  + _post_tag(g))
            print()
        if league.week > REGULAR_SEASON_WEEKS:
            for n, g in enumerate(games, 1):
                print(_num(n, _mine(league, g)) + pad(_result_line(g, league.rankings), 48) + _post_tag(g))
            champ = next((g for g in games if g.game_type == "National Championship"), None)
            if champ:
                print()
                print(pad(paint(f"🏆  {champ.winner.full_name.upper()} ARE THE {league.year} NATIONAL CHAMPIONS  🏆",
                                C.BYELLOW, C.BOLD), WIDTH, "center"))
        else:
            half = (len(games) + 1) // 2
            for n, (a, b) in enumerate(zip_longest(games[:half], games[half:]), 1):
                left = _num(n, _mine(league, a)) + _result_line(a, league.rankings)
                right = (_num(n + half, _mine(league, b)) + _result_line(b, league.rankings)) if b else ""
                print(pad(left, 51) + right)
        import classics
        cl = sorted((c for c in classics.book(league) if c["year"] == league.year and c["week"] == league.week),
                    key=lambda c: -c["score"])
        if cl:
            print()
            print(paint("   ★ FOR THE BOOK — added to Instant Classics (Media Center)", C.BYELLOW, C.BOLD))
            for c in cl[:4]:
                print(paint(f"     {truncate(c['headline'], 110)}", C.BYELLOW))
        hurt = []
        for g in games:
            for q, clk, team, p, desc, sev, gms in (g.box.injuries if g.box else []):
                if gms and p in team.players_at(p.position)[:2]:
                    hurt.append((team, p, desc, gms))
        if hurt:
            print()
            print(paint("   INJURIES", C.BRED, C.BOLD))
            for team, p, desc, gms in hurt[:6]:
                out = "out for the season" if gms >= 99 else f"out {gms} game{'s' if gms != 1 else ''}"
                print(paint(f"   {team.abbr:<6}{p.position} {p.name} — {desc}, {out}", C.GRAY))
            if len(hurt) > 6:
                print(paint(f"   …and {len(hurt) - 6} more across the country", C.GRAY))
        print(paint("\n   Sorted by " + ("postseason importance" if league.week > REGULAR_SEASON_WEEKS
                                   else "matchup quality") + "  ·  ", C.GRAY) + paint("!", C.BRED, C.BOLD)
              + paint(" upset", C.GRAY) + paint("  ·  ", C.GRAY) + paint("★", C.BYELLOW, C.BOLD)
              + paint(" for the book (a classic or an upset for the ages)", C.GRAY)
              + (paint("  ·  ", C.GRAY) + paint("▶", C.BYELLOW, C.BOLD) + paint(" your game", C.GRAY) if mine else "")
              + paint("\n   Poll ranks are as of kickoff.", C.GRAY))
        import webview
        if webview.on():
            try:
                kr = league.rankings

                def wr(n, g):
                    k = _kickoff(g, kr)
                    return {"n": n, "mine": _mine(league, g), "box": g.box is not None, "neutral": bool(g.neutral),
                            "away": g.away.school, "home": g.home.school, "a": g.away_score, "h": g.home_score,
                            "ar": _try_rank(k, g.away), "hr": _try_rank(k, g.home), "awayWon": g.winner is g.away,
                            "tag": webview.plain(_post_tag(g))}
                webview.emit("results", {"title": f"{league.year} · {league.week_name(league.week)}",
                                         "rows": [wr(n, g) for n, g in enumerate(games, 1)],
                                         "classics": [webview.plain(c["headline"]) for c in cl[:4]],
                                         "injuries": [f"{t.abbr} {p.position} {p.name} — {d}, " +
                                                      ("out for the season" if n >= 99 else f"out {n} game{'s' if n != 1 else ''}")
                                                      for t, p, d, n in hurt[:6]]})
            except Exception:
                pass
        choice = ask("Game # for box score, Enter to continue:")
        if not choice:
            return
        if choice.isdigit() and 1 <= int(choice) <= len(games) and games[int(choice) - 1].box is not None:
            show_box_score(league, games[int(choice) - 1])


# ═══ End of season / offseason ══════════════════════════════════════════════

def season_wrap(league: League, advance=True):
    clear()
    print(title_bar(f"{league.year} SEASON FINAL"))
    champ = league.champion_of(league.year)
    title = next(iter(league.schedule.get(18, [])), None)
    if champ and title is not None:
        team = title.winner
        print()
        print(pad(paint(f"🏆  {league.year} NATIONAL CHAMPIONS  🏆", C.BYELLOW, C.BOLD), WIDTH, "center"))
        print(pad(paint(team.full_name.upper(), C.BWHITE, C.BOLD), WIDTH, "center"))
        print(pad(paint(f"{champ.record}  ·  def. {champ.runner_up} {champ.score}-{champ.opp_score}"
                        f"{' (' + champ.note + ')' if champ.note else ''}  ·  {champ.site}  ·  HC {champ.coach}",
                        C.GRAY), WIDTH, "center"))
        won = ps.titles_for(league, team.school)
        if len(won) > 1:
            print(pad(paint(f"Title #{len(won)} since 1998 — also {', '.join(str(y) for y in won[:-1])}", C.GRAY),
                      WIDTH, "center"))
        else:
            print(pad(paint("First national title for the program in the BCS/Playoff era", C.GRAY), WIDTH, "center"))
    print()
    print(section("COLLEGE FOOTBALL PLAYOFF", C.BYELLOW))
    for week in (15, 16, 17, 18):
        games = [g for g in league.schedule.get(week, []) if g.game_type in ps.CFP_TYPES and g.played]
        if not games:
            continue
        print(paint(f"   {ps.round_name(games[0]).upper()}", C.BCYAN, C.BOLD))
        for g in games:
            w, l = g.winner, g.loser
            where = "on campus" if g.game_type == "NP First Round" else g.display_name
            print(f"     {pad(paint(_seed(g, w) + ' ' + w.school, C.BWHITE, C.BOLD), 26)}{g.score_for(w):>3}"
                  f"   {pad(_seed(g, l) + ' ' + l.school, 24)}{g.score_for(l):>3}   {paint(where, C.GRAY)}")
    print()
    print(section("CONFERENCE CHAMPIONS", C.BYELLOW))
    for conf, team in league.conference_champions():
        color = league.conference_color(conf)
        ccg = next((g for g in league.schedule.get(14, []) if g.bowl_name == f"{conf} Championship"), None)
        how = (f"def. {ccg.loser.school} {ccg.score_for(team)}-{ccg.score_for(ccg.loser)}"
               if ccg and ccg.played and ccg.winner is team else "")
        print(f"   {pad(paint(conf, color, C.BOLD), 18)}{pad(team.full_name, 32)}"
              f"{team.record:>6}   {paint(how, C.GRAY)}")
    bowls = sorted((g for g in league.schedule.get(16, []) if g.game_type == "Bowl" and g.played),
                   key=lambda g: (g.tier or 9, g.date))
    if bowls:
        print()
        print(section(f"BOWL RESULTS  ·  {len(bowls)} GAMES", C.BYELLOW))
        half = (len(bowls) + 1) // 2
        for a, b in zip_longest(bowls[:half], bowls[half:]):
            cells = []
            for g in (a, b):
                if g is None:
                    continue
                w, l = g.winner, g.loser
                cells.append(f"{paint(pad(truncate(g.bowl_name, 22), 23), C.GRAY)}"
                             f"{pad(truncate(w.school, 14), 15)}{g.score_for(w):>2}-{g.score_for(l):<3}"
                             f"{truncate(l.school, 14)}")
            print("   " + pad(cells[0], 62) + (cells[1] if len(cells) > 1 else ""))
    print()
    print(section("BEST RECORDS", C.BYELLOW))
    best = sorted(league.teams, key=lambda t: (-t.win_pct, -t.wins, -t.team_ovr))[:10]
    for i, t in enumerate(best, 1):
        print(f"   {paint(f'{i:>2}.', C.GRAY)} {pad(t.full_name, 32)}{t.record:>6}  "
              f"{paint(t.conference, league.conference_color(t.conference))}")
    import career_plus
    if career_plus.mine(league):
        career_plus.season_end(league)                    # achievements, retired jerseys, a statue
        career_plus.report_card(league)                   # the AD's report card
    import people
    todo = [m for m in people.waiting(league) if m.get("kind") in ("pers_nil", "pers_draft")]
    if todo:
        print(paint(f"\n   {len(todo)} decision{'s' if len(todo) != 1 else ''} before the offseason: "
                    f"NIL raises and players weighing the Pro League.", C.BMAGENTA, C.BOLD))
        ask("Press Enter to go through them...")
        for m in todo:
            people.read_message(league, m)
    ask("Press Enter to begin the offseason...")
    import ad_mode
    ad_mode.season_review(league)                             # the AD's report card, and the call on the coach
    if not advance:
        return

    clear()
    print(paint("\n  The offseason calendar is opening — 17 weeks from season fallout to Media Days...", C.GRAY))
    import recap
    if getattr(league, "mode", None) == "spectator":
        report = recap.staged_offseason(league)               # a Recap (and Curate) at every stop
    else:
        report = league.advance_offseason()
    import offseason_cal
    if offseason_cal.active(league):
        offseason_cal.after(league, report)                   # February through July, on the calendar
        return
    import coach_screens
    coach_screens.carousel_report(league, report.year)       # the carousel spins first — its own screen
    import awards_screens
    awards_screens.awards_screen(league, report.year)
    awards_screens.draft_screen(league, report.year)
    offseason_report(league, report)
    import realignment
    realignment.offer_screen(league)                          # Athletic Director mode: an invitation is your call
    if getattr(report, "portal", None) is not None and getattr(report.portal, "user", None) is not None:
        import portal_screens
        portal_screens.window_results(league, report.portal)
    if getattr(report, "portal", None) is not None:
        portal_screen(league, report.portal)
    if getattr(report, "recruiting", None) is not None:
        if getattr(league, "mode", None) == "career":
            import recruit_ui
            recruit_ui.signing_day_live(league, report.recruiting, getattr(league, "user_team", None))
        recruiting_screens.final_rankings(league, getattr(league, "user_team", None),
                                          report=report.recruiting, year=report.year)
    if getattr(league, "mode", None) == "spectator":
        recap.screen(league)                                  # the Preseason Desk: the new season, and Curate


def offseason_report(league: League, report):
    clear()
    print(title_bar(f"{report.year}-{str(report.year + 1)[2:]} OFFSEASON REPORT"))
    print(f"   {paint(len(report.graduated), C.BWHITE, C.BOLD)} seniors graduated   ·   "
          f"{paint(len(report.developed), C.BWHITE, C.BOLD)} players developed   ·   "
          f"{paint(report.redshirted, C.BWHITE, C.BOLD)} freshmen redshirted   ·   "
          f"{paint(sum(len(c) for c in report.classes.values()), C.BWHITE, C.BOLD)} freshmen signed")
    print()

    print(section("BIGGEST RISERS", C.BGREEN))
    risers = sorted(report.developed, key=lambda r: -(r[3] - r[2]))[:12]
    for team, p, before, after in risers:
        print(f"   {pad(paint(team.school, league.conference_color(team.conference)), 20)}"
              f"{p.position:<3} {pad(truncate(p.name, 22), 23)}{paint(p.class_label, C.GRAY):<6}  "
              + (f"{rating(before)} → {rating(after)}  {paint(f'+{after - before}', C.BGREEN, C.BOLD)}   "
                 if not __import__('scout').hidden() else
                 f"{__import__('scout').ovr_short(before)} → {__import__('scout').ovr_short(after)}  "
                 f"{paint('big jump' if after - before >= 8 else 'stepped up', C.BGREEN, C.BOLD)}   ")
              + f"{paint(team.coach.name, C.GRAY)}")
    print()

    print(section("TOP RECRUITING CLASSES", C.BYELLOW))
    def class_score(recruits):
        return sum(r.hs_stars ** 2 for r in recruits)
    ranked = sorted(report.classes.items(), key=lambda kv: -class_score(kv[1]))[:10]
    for i, (team, recruits) in enumerate(ranked, 1):
        fives = sum(r.hs_stars == 5 for r in recruits)
        fours = sum(r.hs_stars == 4 for r in recruits)
        avg = sum(r.hs_stars for r in recruits) / max(1, len(recruits))
        print(f"   {paint(f'{i:>2}.', C.GRAY)} {pad(team.full_name, 30)}{len(recruits):>3} signees   "
              f"avg {avg:.2f}★   {paint(f'{fives}x 5★', C.BYELLOW)}  {fours}x 4★   "
              f"{paint(team.coach.name, C.GRAY)}")
    print()

    import personalities
    locker = [t for w, t in personalities.news(league, report.year) if w >= 14]
    if locker:
        print(section("NIL, THE DRAFT & THE LOCKER ROOM", C.BGREEN))
        for text in locker[:10]:
            print(f"   {truncate(text, 118)}")
        if len(locker) > 10:
            print(paint(f"   …and {len(locker) - 10} more.", C.GRAY))
        print()

    hall_report = getattr(report, "hall", None)
    if hall_report:
        import halloffame
        nat = hall_report.get("national") or {}
        inducted = nat.get("players", []) + nat.get("coaches", [])
        print(section(f"HALL OF FAME · CLASS OF {report.year}", C.BYELLOW))
        if inducted:
            for e in inducted:
                name = pad(paint(e["name"], C.BWHITE, C.BOLD), 24)
                where = pad(truncate(" / ".join(e["schools"]), 30), 31)
                print(f"   {name}{e['pos']:<4}{where}{e['pct']}% of the vote")
        elif nat.get("ballot"):
            top = nat["ballot"][0]
            print(paint(f"   Nobody reached {halloffame.THRESHOLD}%. Closest: {top['name']} ({top['pct']}%).", C.GRAY))
        progs = hall_report.get("programs") or {}
        if progs:
            n = sum(len(v) for v in progs.values())
            print(paint(f"   {n} inducted into {len(progs)} program halls.", C.GRAY))
        mine = halloffame.user_school(league)
        if mine and mine in halloffame.hall(league).pending:
            print(paint(f"   The {mine} Hall of Fame committee has nominees for you.", C.BMAGENTA, C.BOLD))
            if ask(paint("   [S] make your selections now, or Enter for later (Rankings tab -> [F]):", C.BMAGENTA)
                   ).strip().lower() == "s":
                halloffame.selection_screen(league, mine)
        print(paint("   Rankings tab -> [F] for the ceremony, the vote and every program's hall.", C.GRAY))
        print()

    import realignment
    news = realignment.news_for(league, report.year)
    if news:
        print(section("CONFERENCE REALIGNMENT & TV", C.BMAGENTA))
        for text in news[:8]:
            print(f"   {truncate(text, 118)}")
        print(paint("   Media Center → Conference Realignment for the whole map.", C.GRAY))
        print()

    moves = getattr(report, "carousel", None)
    if moves:
        import carousel as cz
        changes = len({m["school"] for m in cz.carousel_moves(league, report.year)})
        print(paint(f"   Coaching carousel: {changes} head coaching changes — see Coaches & Carousel → "
                    f"Coaching Carousel for the full report.", C.GRAY))
        print()

    print(section("NOTABLE DEPARTURES", C.BRED))
    for team, p in sorted(report.graduated, key=lambda r: -r[1].overall)[:6]:
        print(f"   {pad(team.school, 20)}{p.position:<3} {pad(p.name, 23)}{__import__('scout').ovr_short(p)}")
    print(paint(f"\n   Welcome to the {league.year} season.", C.BYELLOW, C.BOLD))
    pause()


# ═══ Whose ratings is this screen about? (spectator mode: your team through a scout's eye) ══
import scout as _scout
team_view = _scout.focused(team_view, lambda league, team, *a, **k: team)
depth_chart = _scout.focused(depth_chart, lambda league, team, *a, **k: team)
roster_view = _scout.focused(roster_view, lambda league, team, *a, **k: team)
schedule_view = _scout.focused(schedule_view, lambda league, team, *a, **k: team)
player_card = _scout.focused(player_card, lambda league, p, *a, **k: getattr(p, "team", None))


def _season_final_screen(league: League):
    """The year in review: champion, playoff, conference champions, bowls, best records."""
    clear()
    print(title_bar(f"{league.year} SEASON FINAL"))
    champ = league.champion_of(league.year)
    title = next(iter(league.schedule.get(18, [])), None)
    if champ and title is not None:
        team = title.winner
        print()
        print(pad(paint(f"🏆  {league.year} NATIONAL CHAMPIONS  🏆", C.BYELLOW, C.BOLD), WIDTH, "center"))
        print(pad(paint(team.full_name.upper(), C.BWHITE, C.BOLD), WIDTH, "center"))
        print(pad(paint(f"{champ.record}  ·  def. {champ.runner_up} {champ.score}-{champ.opp_score}"
                        f"{' (' + champ.note + ')' if champ.note else ''}  ·  {champ.site}  ·  HC {champ.coach}",
                        C.GRAY), WIDTH, "center"))
        won = ps.titles_for(league, team.school)
        if len(won) > 1:
            print(pad(paint(f"Title #{len(won)} since 1998 — also {', '.join(str(y) for y in won[:-1])}", C.GRAY),
                      WIDTH, "center"))
        else:
            print(pad(paint("First national title for the program in the BCS/Playoff era", C.GRAY), WIDTH, "center"))
    print()
    print(section("COLLEGE FOOTBALL PLAYOFF", C.BYELLOW))
    for week in (15, 16, 17, 18):
        games = [g for g in league.schedule.get(week, []) if g.game_type in ps.CFP_TYPES and g.played]
        if not games:
            continue
        print(paint(f"   {ps.round_name(games[0]).upper()}", C.BCYAN, C.BOLD))
        for g in games:
            w, l = g.winner, g.loser
            where = "on campus" if g.game_type == "CFP First Round" else g.display_name
            print(f"     {pad(paint(_seed(g, w) + ' ' + w.school, C.BWHITE, C.BOLD), 26)}{g.score_for(w):>3}"
                  f"   {pad(_seed(g, l) + ' ' + l.school, 24)}{g.score_for(l):>3}   {paint(where, C.GRAY)}")
    print()
    print(section("CONFERENCE CHAMPIONS", C.BYELLOW))
    for conf, team in league.conference_champions():
        color = league.conference_color(conf)
        ccg = next((g for g in league.schedule.get(14, []) if g.bowl_name == f"{conf} Championship"), None)
        how = (f"def. {ccg.loser.school} {ccg.score_for(team)}-{ccg.score_for(ccg.loser)}"
               if ccg and ccg.played and ccg.winner is team else "")
        print(f"   {pad(paint(conf, color, C.BOLD), 18)}{pad(team.full_name, 32)}"
              f"{team.record:>6}   {paint(how, C.GRAY)}")
    bowls = sorted((g for g in league.schedule.get(16, []) if g.game_type == "Bowl" and g.played),
                   key=lambda g: (g.tier or 9, g.date))
    if bowls:
        print()
        print(section(f"BOWL RESULTS  ·  {len(bowls)} GAMES", C.BYELLOW))
        half = (len(bowls) + 1) // 2
        for a, b in zip_longest(bowls[:half], bowls[half:]):
            cells = []
            for g in (a, b):
                if g is None:
                    continue
                w, l = g.winner, g.loser
                cells.append(f"{paint(pad(truncate(g.bowl_name, 22), 23), C.GRAY)}"
                             f"{pad(truncate(w.school, 14), 15)}{g.score_for(w):>2}-{g.score_for(l):<3}"
                             f"{truncate(l.school, 14)}")
            print("   " + pad(cells[0], 62) + (cells[1] if len(cells) > 1 else ""))
    print()
    print(section("BEST RECORDS", C.BYELLOW))
    best = sorted(league.teams, key=lambda t: (-t.win_pct, -t.wins, -t.team_ovr))[:10]
    for i, t in enumerate(best, 1):
        print(f"   {paint(f'{i:>2}.', C.GRAY)} {pad(t.full_name, 32)}{t.record:>6}  "
              f"{paint(t.conference, league.conference_color(t.conference))}")

def _pre_offseason(league: League):
    """Before the offseason: NIL raises, players weighing the NFL, and the AD's report card (your own mail)."""
    import people
    todo = [m for m in people.waiting(league) if m.get("kind") in ("pers_nil", "pers_draft")]
    if todo:
        print(paint(f"\n   {len(todo)} decision{'s' if len(todo) != 1 else ''} before the offseason: "
                    f"NIL raises and players weighing the NFL.", C.BMAGENTA, C.BOLD))
        ask("Press Enter to go through them...")
        for m in todo:
            people.read_message(league, m)
    ask("Press Enter to begin the offseason...")
    import ad_mode
    ad_mode.season_review(league)                             # the AD's report card, and the call on the coach
