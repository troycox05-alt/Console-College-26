"""
preseason.py — The preseason week (fall camp), before Week 1. Coach Career.

The dashboard's [A] opens it once a year, before your first game:

  YOUR SCHEDULE    all twelve games. Non-conference games can be changed.
  RECRUITING       build your board — add and drop targets, look at film.
                   A limited contact period is open: evaluate, contact and offer. Visits begin in Week 1.
  INBOX            your AD sets the tone for the year; your captains check in.
  Enter            kick off the season (straight into Week 1's week hub).

CUSTOM NON-CONFERENCE SCHEDULE
  Pick any of your non-conference games and choose a new opponent for that
  week. The rest of college football keeps its twelve games: the team you
  take is swapped out of its own game that week, and your old opponent gets
  that game instead (or a guarantee game against an FCS school).

  What you can't touch: conference games, protected and traditional rivalries
  (Florida–Florida State, the Cy-Hawk, Rivalry Week), and anything already
  played. Who'll say yes:
    - anyone for a game on their field
    - a Power program won't play at a Group of Five stadium (it's a road game
      for you, or nothing)
    - FCS schools always come — they're getting paid
  The schedule you build is the one the seat, the committee and the polls
  judge you on: every opponent's strength counts.
"""
import scout
import season
from ui import C, ask, clear, columns, key, pad, paint, panel, pause, rating, rule, title_bar, truncate


def needed(league):
    me = getattr(league, "user_coach", None)
    return (getattr(league, "mode", None) == "career" and me is not None and me.team is not None
            and league.week == 0 and league.year not in league.__dict__.get("_preseason_done", set()))


def mark_done(league):
    done = league.__dict__.setdefault("_preseason_done", set())
    if league.year in done:
        return
    # User has had the same Week 0 contact period through the recruiting screen.
    # Let every CPU staff use its restricted Week 0 budget once before Week 1.
    league.recruiting.weekly_tick(0, user_team=getattr(league, "user_team", None))
    done.add(league.year)


# ═══ The schedule ═══════════════════════════════════════════════════════════

def _pair(a, b):
    return frozenset((a.school, b.school))


LOCKED = ({frozenset(p) for p in season.RIVALRY_WEEK} | set(season.FIXED_WEEKS) | set(season.EARLY_RIVALRIES))


def locked_reason(g, team):
    if g.played:
        return "already played"
    if g.conference_game:
        return "conference game"
    from carousel import PROTECTED, PRIMARY_RIVAL
    opp = g.opponent_of(team)
    if _pair(team, opp) in LOCKED or _pair(team, opp) in {frozenset(p) for p in PROTECTED}:
        return "rivalry — not yours to move"
    if PRIMARY_RIVAL.get(team.school) == opp.school or PRIMARY_RIVAL.get(opp.school) == team.school:
        return "rivalry — not yours to move"
    return None


def _game_of(league, team, week):
    return next((g for g in league.schedule.get(week, []) if team in (g.home, g.away)), None)


def _opponents(league, team):
    return {g.opponent_of(team) for g in league.team_games(team)}


def candidates(league, team, g):
    """Who could take this date: [(opponent, note, can_host_you)]."""
    w = g.week
    old = g.opponent_of(team)
    already = _opponents(league, team)
    out = []
    busy_fcs = {t for x in league.schedule.get(w, []) for t in (x.home, x.away) if getattr(t, "fcs", False)}
    free_fcs = [f for f in league.fcs_teams if f not in busy_fcs]
    # FCS schools that are free that week (if your old opponent is FBS, another one has to be free for him).
    if getattr(old, "fcs", False) or len(free_fcs) >= 2:
        for f in free_fcs:
            if f not in already and f is not old:
                out.append((f, "FCS guarantee game", True))
    # FBS teams playing a movable non-conference game that week.
    for y in league.teams:
        if y is team or y in already or y is old:
            continue
        gy = _game_of(league, y, w)
        if gy is None or gy.conference_game or locked_reason(gy, y):
            continue
        z = gy.opponent_of(y)
        if z is team or z is old:
            continue
        # The leftover game — your old opponent against y's old opponent — has to be a legal one.
        if getattr(old, "fcs", False) and getattr(z, "fcs", False):
            continue
        if not getattr(old, "fcs", False) and not getattr(z, "fcs", False):
            if old.conference == z.conference and old.conference != "Independent":
                continue
        if z in _opponents(league, old):
            continue
        if y.conference == team.conference and y.conference != "Independent":
            continue
        power_y = season.schedule_tier(y) == "power"
        power_me = season.schedule_tier(team) == "power"
        can_host = not (power_y and not power_me)
        note = f"plays {z.school} that week" if not getattr(z, "fcs", False) else f"was hosting FCS {z.school}"
        out.append((y, note, can_host))
    return out


def _free_fcs(league, week, exclude=()):
    """The FCS school that's free that week and has sold the fewest games."""
    busy = {t for x in league.schedule.get(week, []) for t in (x.home, x.away) if getattr(t, "fcs", False)}
    options = [f for f in league.fcs_teams if f not in busy and f not in exclude]
    if not options:
        return None
    count = {}
    for x in league.schedule.values():
        for gg in x:
            for t in (gg.home, gg.away):
                if getattr(t, "fcs", False):
                    count[t] = count.get(t, 0) + 1
    return min(options, key=lambda f: count.get(f, 0))


def swap(league, team, g, new, you_host):
    """Replace your opponent on g's date with `new`. Everyone keeps twelve games."""
    w = g.week
    old = g.opponent_of(team)
    games = league.schedule[w]
    games.remove(g)
    home, away = (team, new) if you_host else (new, team)
    games.append(season.Game(w, home, away, False))
    if getattr(new, "fcs", False):
        if not getattr(old, "fcs", False):                         # your old opponent needs a game
            f = _free_fcs(league, w, exclude={new})
            if f is not None:
                games.append(season.Game(w, old, f, False))
        return f"{new.school} is on your schedule in Week {w}."
    gy = _game_of(league, new, w)
    z = gy.opponent_of(new)
    games.remove(gy)
    if getattr(z, "fcs", False):
        games.append(season.Game(w, old, z, False))
    elif getattr(old, "fcs", False):
        games.append(season.Game(w, z, old, False))
    else:
        # A money game is played at the bigger program; otherwise z keeps its home date.
        tz, to = season.schedule_tier(z), season.schedule_tier(old)
        if tz != to:
            h, a = (z, old) if tz == "power" else (old, z)
        else:
            h, a = (z, old) if gy.home is z else (old, z)
        games.append(season.Game(w, h, a, False))
    return f"{new.school} is on your schedule in Week {w}. {old.school} plays {z.school} instead."


def schedule_screen(league):
    team = league.user_coach.team
    import carousel as cz
    while True:
        clear()
        print(title_bar(f"{league.year} SCHEDULE  ·  {team.school.upper()}  ·  NON-CONFERENCE"))
        print(paint("   Pick a non-conference game to change the opponent. Conference games and rivalries stay put.",
                    C.GRAY))
        print()
        rows = []
        for g in league.team_games(team):
            if g.game_type != "Regular Season":
                continue
            opp = g.opponent_of(team)
            site = "vs" if g.home is team or g.neutral else "at"
            why = locked_reason(g, team)
            p = cz.win_prob(team, opp, 0 if g.neutral else (1 if g.home is team else -1), league)
            tag = paint("conference", C.GRAY) if g.conference_game else \
                paint("locked: " + why, C.BYELLOW) if why else paint("change it", C.BGREEN)
            rows.append((g, why is None))
            num = paint(f"[{len(rows)}]", C.BYELLOW, C.BOLD) if why is None else "   "
            level = "FCS" if getattr(opp, "fcs", False) else opp.conference
            print(f"   {num} {paint(pad(f'Wk {g.week}', 7), C.GRAY)}{site} {pad(truncate(opp.school, 22), 23)}"
                  f"{paint(pad(truncate(level, 14), 15), C.GRAY)}{scout.team_short(getattr(opp, 'team_ovr', 50))}   "
                  f"{pad(scout.odds_short(p) + ('' if scout.hidden() else ' to win'), 12)} {tag}")
        exp = sum(cz.win_prob(team, g.opponent_of(team), 0 if g.neutral else (1 if g.home is team else -1), league)
                  for g, _ in rows)
        print(rule())
        print(paint(f"   Projected: about {exp:.1f} wins against this schedule." if not scout.hidden() else
                    f"   Staff's gut: somewhere around {max(0, round(exp) - 1)}-{round(exp) + 1} wins against this schedule.",
                    C.BCYAN))
        c = ask("Game # to change (Enter = done):").strip()
        if not c:
            return
        if c.isdigit() and 1 <= int(c) <= len(rows) and rows[int(c) - 1][1]:
            _pick_opponent(league, team, rows[int(c) - 1][0])


def _pick_opponent(league, team, g):
    import carousel as cz
    opts = candidates(league, team, g)
    tier = None
    page = 0
    while True:
        view = [o for o in opts if tier is None or
                (tier == "fcs" and getattr(o[0], "fcs", False)) or
                (tier != "fcs" and not getattr(o[0], "fcs", False) and season.schedule_tier(o[0]) == tier)]
        view.sort(key=lambda o: -getattr(o[0], "team_ovr", 0))
        per = 18
        pages = max(1, (len(view) + per - 1) // per)
        page = min(page, pages - 1)
        clear()
        old = g.opponent_of(team)
        print(title_bar(f"WEEK {g.week}  ·  REPLACING {old.school.upper()}"))
        label = {None: "everyone", "power": "Power programs", "group": "Group of Five", "fcs": "FCS"}[tier]
        print(paint(f"   Available that week: {len(view)} ({label}).   ✗ = won't come to your place — road game only.",
                    C.GRAY))
        print()
        for i, (o, note, host) in enumerate(view[page * per:(page + 1) * per], page * per + 1):
            p = cz.win_prob(team, o, 1 if host else -1, league)
            rk = league.rankings.rank_of(o)
            name = (f"#{rk} " if rk else "") + o.school
            level = "FCS" if getattr(o, "fcs", False) else o.conference
            print(f"   {paint(f'{i:>3}', C.BYELLOW)}  {pad(truncate(name, 24), 25)}{paint(pad(truncate(level, 14), 15), C.GRAY)}"
                  f"{scout.team_short(getattr(o, 'team_ovr', 50))}  {pad(scout.odds_short(p), 10, 'right')}  "
                  f"{paint('' if host else '✗ ', C.BRED)}{paint(truncate(note, 30), C.GRAY)}")
        print(rule())
        print(paint(f"   [#] schedule them   [P] Power  [G] Group of Five  [F] FCS  [A] all   "
                    f"[N/V] page {page + 1}/{pages}   Enter = back", C.GRAY))
        c = ask("Select:").strip().lower()
        if not c:
            return
        if c in ("p", "g", "f", "a"):
            tier = {"p": "power", "g": "group", "f": "fcs", "a": None}[c]
            page = 0
        elif c == "n":
            page = (page + 1) % pages
        elif c == "v":
            page = (page - 1) % pages
        elif c.isdigit() and 1 <= int(c) <= len(view):
            o, note, host = view[int(c) - 1]
            you_host = False
            if host:
                where = ask(f"Where? [H] home (default)  [A] at {o.school}:").strip().lower()
                you_host = where != "a"
            else:
                if ask(f"{o.school} won't come to you. Play it at their place? (y/n)").strip().lower() not in ("y", "yes"):
                    continue
            msg = swap(league, team, g, o, you_host)
            league.__dict__.setdefault("career_log", []).append((league.year, f"Scheduled {o.school} for Week {g.week}."))
            print(paint("   " + msg, C.BGREEN, C.BOLD))
            pause()
            return




def redshirt_screen(league, team):
    """Preseason redshirt protection. Planned players stay out of normal lineups; four-game rule still governs eligibility."""
    while True:
        clear()
        print(title_bar(f"{league.year} REDSHIRT PLAN · {team.school.upper()}"))
        print(paint("   Protect a player from normal game usage. He can still appear in up to four games and keep the year.", C.GRAY))
        print(paint("   A formation-sub assignment or emergency can use him; more than four games burns the plan.", C.GRAY))
        print()
        eligible = [p for p in team.roster if not getattr(p, "redshirt", False) and p.year < 3]
        eligible.sort(key=lambda p: (p.position, p.year, p.name))
        for i, p in enumerate(eligible, 1):
            planned = p.__dict__.get("redshirt_plan") == league.year
            tag = paint("PROTECT", C.BGREEN, C.BOLD) if planned else paint("available", C.GRAY)
            print(f"   {i:>2}. {p.position:<3} #{p.number:<3} {pad(truncate(p.name, 25), 26)} {p.class_label:<5} {tag}")
        if not eligible:
            print(paint("   No eligible players on this roster.", C.GRAY))
        print(rule())
        c = ask("Player # to toggle · [C] clear all · Enter = back:").strip().lower()
        if not c:
            return
        if c == "c":
            for p in eligible:
                p.__dict__.pop("redshirt_plan", None)
            continue
        if c.isdigit() and 1 <= int(c) <= len(eligible):
            q = eligible[int(c) - 1]
            if q.__dict__.get("redshirt_plan") == league.year:
                q.__dict__.pop("redshirt_plan", None)
            else:
                q.redshirt_plan = league.year

# ═══ The preseason hub ══════════════════════════════════════════════════════

def depth_line(league, team):
    """Fall camp: who set the depth chart, and what the staff would change."""
    import depth
    if getattr(team, "depth_set", None) != league.year:
        return paint("   DEPTH CHART  yours as you left it — [D] to look it over", C.GRAY)
    counts = depth.starters(team)
    order = getattr(team, "depth_order", {})
    last = {id(p) for p in getattr(team, "_last_starters", [])}
    new = [p for pos, lst in order.items() for p in [x for x in lst if x in team.roster][:counts.get(pos, 1)]
           if last and id(p) not in last]
    ideas = [x for x in getattr(team, "depth_ideas", []) if x[4] == league.year and x[0].position == x[1]]
    bits = [paint("   DEPTH CHART  ", C.BCYAN, C.BOLD) + "set by your staff for camp"]
    if new:
        bits.append(f"{len(new)} new starter{'s' if len(new) != 1 else ''}")
    if ideas:
        bits.append(paint(f"{len(ideas)} position move{'s' if len(ideas) != 1 else ''} suggested", C.BYELLOW))
    return " · ".join(bits) + paint("  — [D] to adjust", C.GRAY)


def hub(league):
    """Fall camp. Returns True to kick off Week 1, False to go back to the dashboard."""
    import people
    import carousel as cz
    team = league.user_coach.team
    import guide
    guide.tip(league, "fall_camp")
    people.weekly(league)
    while True:
        clear()
        print(title_bar(f"{league.year} PRESEASON  ·  FALL CAMP  ·  {team.school.upper()}",
                        league.conference_color(team.conference)))
        rk = league.rankings.rank_of(team)
        games = [g for g in league.team_games(team) if g.game_type == "Regular Season"]
        exp = sum(cz.win_prob(team, g.opponent_of(team), 0 if g.neutral else (1 if g.home is team else -1), league)
                  for g in games)
        sched = []
        for g in games:
            opp = g.opponent_of(team)
            site = "vs" if g.home is team or g.neutral else "at"
            mark = paint("•", C.BGREEN) if locked_reason(g, team) is None else " "
            sched.append(f"{mark} {paint(pad(f'Wk {g.week}', 6), C.GRAY)}{site} {truncate(opp.school, 30)}")
        left = panel("YOUR SCHEDULE  (• = you can change it)", sched, 50, height=12)
        cyc = league.recruiting
        board = getattr(team, "recruiting_targets", [])
        rec = [f"Board {paint(str(len(board)), C.BWHITE, C.BOLD)}/40 · {paint('18h contact period', C.BYELLOW)}"]
        n_un = people.unread(league)
        inb = [f"{paint(str(n_un), C.BYELLOW, C.BOLD)} unread"] + \
              [paint("· ", C.GRAY) + truncate(f"{people.sender_label(m, short=True)}: {m['subject']}", 42)
               for m in list(reversed(people.inbox(league)))[:2]]
        import textwrap
        goal_lines = ["Goals:"] + [ln for x in team.goals
                                   for ln in textwrap.wrap("• " + x.short, 45, subsequent_indent="  ")]
        outlook = [f"Preseason poll: {paint('#' + str(rk), C.BYELLOW, C.BOLD) if rk else 'unranked'}",
                   (f"Projected: about {paint(f'{exp:.1f}', C.BWHITE, C.BOLD)} wins " if not scout.hidden() else
                    f"Staff's gut: {paint(f'{max(0, round(exp) - 1)}-{round(exp) + 1}', C.BWHITE, C.BOLD)} wins ")
                   + paint("(bowl-eligible: 6)", C.GRAY)] + [paint(x, C.GRAY) for x in goal_lines[:6]]
        right = panel("OUTLOOK", outlook, 49, height=len(outlook)) + \
            panel("RECRUITING", rec, 49, height=1) + panel("INBOX", inb, 49, height=3)
        for ln in columns(left, right):
            print(ln)
        print(depth_line(league, team))
        print(rule())
        print("   " + "   ".join([key("Enter", "kick off Week 1", C.BGREEN), key("D", "Decide your Depth"), key("F", "formation subs"),
                                  key("X", "redshirt plan"), key("C", "camp report"), key("S", "schedule"),
                                  key("R", "recruits"), key("I", "inbox"), key("B", "back", C.GRAY)]))
        c = ask("Fall camp:").strip().lower()
        if c == "":
            from models import POSITIONS
            import depth_staff
            done = team.__dict__.setdefault("depth_decided", {}).setdefault(league.year, set())
            missing = [p for p in POSITIONS if p not in done]
            if missing:
                yn = ask(f"{len(missing)} position rooms are undecided. [Y] let staff decide the rest  [N] go back:").strip().lower()
                if yn != "y":
                    continue
                for pos in missing:
                    depth_staff.apply_order(team, pos, depth_staff.order(league, team, pos, "blend"))
                    done.add(pos)
                team.depth_set = league.year
            mark_done(league)
            return True
        if c == "b":
            return False
        if c == "c":
            import practice
            practice.screen(league, team)
        elif c == "f":
            import formation_subs
            formation_subs.screen(league, team)
        elif c == "x":
            redshirt_screen(league, team)
        elif c == "d":
            import depth_ui
            depth_ui.decide_camp(league, team)
        elif c == "s":
            schedule_screen(league)
        elif c == "r":
            import recruiting_screens
            league._recruit_readonly = False
            recruiting_screens.recruiting_menu(league)
        elif c == "i":
            people.inbox_screen(league)
