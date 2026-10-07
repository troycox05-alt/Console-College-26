"""
offseason_cal.py — Year-round offseason hub.

Phase 1 turns the offseason into a 17-week calendar that mirrors the regular
season rhythm.  The underlying recruiting/portal/carousel mechanics remain the
same for now; they are scheduled into weekly slots and exposed through one hub,
one agenda, real deadlines, national boards and a persistent save state.

The important architectural rule is that the hub owns TIME, while each system
owns its own action.  Phase 2 can make recruiting, the portal and the carousel
advance every week without redesigning this screen again.
"""
import random
import textwrap

from ui import (C, ask, clear, columns, key, pad, paint, panel, pause, rule,
                section, title_bar, truncate)

FOCUS_BLUR = 0.4
MAX_FOCUS = 3

# Same nominal length as the regular-season calendar.  Several weeks currently
# host an existing one-shot system; the "quiet" weeks are real information /
# deadline weeks already, ready for Phase 2's weekly simulation.
WEEKS = [
    dict(n=1,  mon="JAN", key="carousel", label="Season Fallout",
         blurb="Firings, retirements and the first head-coach searches hit the wire.", deadline="Coaching carousel opens"),
    dict(n=2,  mon="JAN", key="staff", label="Your Staff",
         blurb="Decide who stays, who goes and which chairs need filling.", deadline="Staff decisions"),
    dict(n=3,  mon="JAN", key="staffcar", label="Staff Carousel",
         blurb="Assistant interviews, poaching and coaching dominoes across the country.", deadline="Assistant market"),
    dict(n=4,  mon="JAN", key="portal", label="Portal Window I Opens",
         blurb="The winter portal board is live. Retention and immediate roster help matter now.", deadline="Portal Window I opens"),
    dict(n=5,  mon="JAN", key="portal_market", label="Portal Market",
         blurb="The first wave settles and the national transfer board starts taking shape.", deadline="Portal recruiting continues"),
    dict(n=6,  mon="JAN", key="portal_deadline", label="Portal Deadline",
         blurb="Last calls on the winter window. Roster holes are becoming real.", deadline="Portal Window I deadline"),
    dict(n=7,  mon="FEB", key="recruit_finish", label="Signing Push",
         blurb="Unsigned high-school targets and shaky classes dominate the final push.", deadline="National Signing Day next week"),
    dict(n=8,  mon="FEB", key="signing", label="National Signing Day",
         blurb="The class signs, flips land and the incoming roster becomes official.", deadline="National Signing Day"),
    dict(n=9,  mon="FEB", key="awards", label="Program Reset",
         blurb="Review the year, awards, development and what the roster now needs.", deadline="Roster / staff reset"),
    dict(n=10, mon="MAR", key="winter", label="Winter Development",
         blurb="Strength work, development and roster planning set the spring baseline.", deadline="Spring practice next week"),
    dict(n=11, mon="MAR", key="spring", label="Spring Ball I",
         blurb="Choose an emphasis, identify position battles and test position moves.", deadline="Spring practice block I"),
    dict(n=12, mon="APR", key="spring2", label="Spring Ball II",
         blurb="Staff evaluations settle as the spring game approaches.", deadline="Spring-game depth review"),
    dict(n=13, mon="APR", key="aday", label="A-Day",
         blurb="Blue vs. White: spring film, standouts and the last big evaluation day.", deadline="Spring game"),
    dict(n=14, mon="MAY", key="postspring", label="Portal Window II Opens",
         blurb="Spring depth charts trigger a second, smaller wave of player movement.", deadline="Post-spring portal opens"),
    dict(n=15, mon="MAY", key="draft", label="Portal II Deadline & Draft",
         blurb="The second portal window closes while the pro draft reshapes the national picture.", deadline="Portal Window II deadline"),
    dict(n=16, mon="JUN", key="summer", label="Summer Workouts",
         blurb="Freshmen move in, conditioning begins and the staff readies camp.", deadline="Summer roster lock"),
    dict(n=17, mon="JUL", key="media", label="Media Days",
         blurb="Preseason polls, expectations and the handoff into fall camp.", deadline="Fall camp opens next"),
]
BY_KEY = {w["key"]: w for w in WEEKS}
BY_NUM = {w["n"]: w for w in WEEKS}
DECISION_KEYS = {"staff", "staffcar", "portal", "signing", "spring", "aday"}

_replay = {}                     # transient replay callbacks; never required to load a save
_CONTEXT = {}                    # transient current reports; never persisted into the save


def active(league):
    return getattr(league, "mode", None) == "career" and not getattr(league, "autosim", False) \
        and getattr(league, "user_team", None) is not None


def _state(league):
    st = league.__dict__.setdefault("offseason_state", {})
    # Migration from the old v39/v40 calendar state.
    old = league.__dict__.get("off_cal") or {}
    if not st:
        st.update({"version": 3, "season": old.get("season"), "week": 0, "completed_weeks": [],
                   "completed_tasks": [], "snapshots": {}, "portal_summary": {}, "portal2_summary": {}, "class_summary": {},
                   "agenda_seen": [], "news": []})
    st["version"] = max(3, int(st.get("version", 1)))
    st.setdefault("week", 0)
    st.setdefault("completed_weeks", [])
    st.setdefault("completed_tasks", [])
    st.setdefault("snapshots", {})
    st.setdefault("portal_summary", {})
    st.setdefault("portal2_summary", {})
    st.setdefault("class_summary", {})
    st.setdefault("agenda_seen", [])
    st.setdefault("news", [])
    st.setdefault("spring", {})
    st.setdefault("preseason", {})
    return st


def _save(league):
    try:
        import saves
        saves.autosave(league)
    except Exception:
        pass


def _last_season_snapshot(league, team):
    """Primitive data only, so the snapshot is safe in old/new saves."""
    snap = {"record": getattr(team, "record", ""), "year": league.year,
            "school": team.school, "conference": team.conference}
    if not (team.wins or team.losses):                      # the records were already reset: use the book
        last = getattr(team, "last_season", None)
        if last:
            snap["record"] = f"{last[0]}-{last[1]}"
        try:
            snap["final_rank"] = league.rankings.rank_of(team)
        except Exception:                                   # noqa: BLE001 — a snapshot never blocks the offseason
            snap["final_rank"] = None
        return snap
    try:
        import team_stats
        vals = team_stats.values(league, team)
        allv = team_stats._eligible(league)
        for key_, good in (("ppg", True), ("opp_ppg", False), ("total_off", True), ("total_def", False),
                           ("explosive", True), ("explosive_allowed", False), ("to_margin", True)):
            snap[key_] = vals.get(key_, 0)
            snap[key_ + "_rank"] = team_stats._rank(allv, team, key_, good)
    except Exception:
        pass
    try:
        snap["final_rank"] = league.rankings.rank_of(team)
    except Exception:
        snap["final_rank"] = None
    return snap


def _start(league, season):
    st = _state(league)
    if st.get("season") != season:
        st.clear()
        st.update({"version": 3, "season": season, "week": 0, "completed_weeks": [], "completed_tasks": [],
                   "snapshots": {}, "portal_summary": {}, "portal2_summary": {}, "class_summary": {}, "agenda_seen": [], "news": [],
                   "spring": {}, "preseason": {}})
        _replay.clear()
        team = getattr(league, "user_team", None)
        if team is not None:
            st["snapshots"]["last_season"] = _last_season_snapshot(league, team)
        _save(league)
    elif not st.get("completed_weeks") and not st.get("week"):
        # Opened before the season was played (a new world reads the calendar in August): the
        # snapshot was taken at 0-0. Until the offseason's first week, keep it current.
        team = getattr(league, "user_team", None)
        if team is not None and (team.wins or team.losses):
            st.setdefault("snapshots", {})["last_season"] = _last_season_snapshot(league, team)
    return st


def _team(league):
    return getattr(league, "user_team", None)


def _portal_score(entries):
    return sum(max(0, getattr(e, "overall", 0) - 45) ** 1.18 for e in entries)


def _portal_rank(league, report, team):
    if report is None or team is None:
        return None
    scores = []
    for t in league.teams:
        xs = list(getattr(report, "by_team_in", {}).get(t, []))
        if xs:
            scores.append((t, _portal_score(xs)))
    scores.sort(key=lambda x: -x[1])
    return next((i for i, (t, _) in enumerate(scores, 1) if t is team), None)


def _recruit_rank(league, team, report=None):
    if team is None:
        return None
    if report is not None:
        ranks = getattr(report, "ranks", {}) or {}
        if team in ranks:
            return ranks[team]
    try:
        return league.recruiting.class_rank(team)
    except Exception:
        return None


def _overall_class_rank(league, team, portal_report=None, class_report=None):
    """A lightweight combined incoming-class board for the hub.
    Phase 2 will replace this with the living commitment/signing model.
    """
    if team is None:
        return None
    try:
        import recruiting
        scored = []
        for t in league.teams:
            if class_report is not None:
                recruits = list(getattr(class_report, "classes", {}).get(t, []))
            else:
                recruits = list(league.recruiting.commitments(t))
            rp = recruiting.class_points(recruits)
            pp = _portal_score(list(getattr(portal_report, "by_team_in", {}).get(t, []))) if portal_report else 0
            score = rp + pp * 1.75
            if score > 0:
                scored.append((t, score))
        scored.sort(key=lambda x: -x[1])
        return next((i for i, (t, _) in enumerate(scored, 1) if t is team), None)
    except Exception:
        return None


def _money(league, team):
    try:
        import finance
        return finance.money(max(0, finance.available(league, team)))
    except Exception:
        return "—"


def _staff_count(team):
    try:
        import poscoach
        rooms = poscoach.staff_of(team)
        have = sum(c is not None for c in rooms.values())
        total = len(rooms)
        return f"{have}/{total} rooms"
    except Exception:
        return "staff set"


def _program_lines(league, st, team):
    portal = _CONTEXT.get("portal")
    klass = _CONTEXT.get("class_report")
    # Reports themselves are deliberately not stored in the persisted dict by callers; summaries survive saves.
    pr = st.get("portal_summary", {}).get("rank")
    p2r = st.get("portal2_summary", {}).get("rank")
    rr = st.get("class_summary", {}).get("rank") or st.get("portal_summary", {}).get("recruit_rank") or _recruit_rank(league, team, klass)
    ov = st.get("class_summary", {}).get("overall_rank") or st.get("portal2_summary", {}).get("overall_rank") or st.get("portal_summary", {}).get("overall_rank")
    if ov is None:
        ov = _overall_class_rank(league, team, portal, klass)
    portal_text = (f"I {('#' + str(pr)) if pr else '—'} / II {('#' + str(p2r)) if p2r else '—'}"
                   if int(st.get("week") or 0) >= 14 else (('#' + str(pr)) if pr else '—'))
    ranks = (f"Class ranks: recruiting {('#' + str(rr)) if rr else '—'}  portal {portal_text}"
             f"  overall {('#' + str(ov)) if ov else '—'}")
    lines = [paint(ranks, C.BWHITE, C.BOLD),
             f"Roster {len(team.roster)}/85   ·   Available budget {_money(league, team)}",
             f"Staff {_staff_count(team)}"]
    try:
        import people
        unread = people.unread(league)
        lines.append(f"Inbox {unread} unread" if unread else "Inbox clear")
    except Exception:
        pass
    return lines


def _last_year_lines(st):
    s = st.get("snapshots", {}).get("last_season", {})
    if not s:
        return ["Last-season snapshot unavailable."]
    out = [f"{s.get('school', '')} · {s.get('year', '')} finish: {s.get('record', '—')}" +
           (f"   ·   final #{s['final_rank']}" if s.get("final_rank") else "")]
    pairs = [("Scoring offense", "ppg", "ppg_rank", True), ("Scoring defense", "opp_ppg", "opp_ppg_rank", False),
             ("Total offense", "total_off", "total_off_rank", True), ("Total defense", "total_def", "total_def_rank", False),
             ("Explosive plays", "explosive", "explosive_rank", True), ("Turnover margin", "to_margin", "to_margin_rank", True)]
    for label, k, rk, _ in pairs[:5]:
        if k in s:
            val = s[k]
            txt = f"{val:.1f}" if isinstance(val, (int, float)) else str(val)
            out.append(f"{pad(label, 17)} {pad(txt, 7, 'right')}   {('#' + str(s.get(rk))) if s.get(rk) else '—'}")
    return out[:5]


def _carousel_lines(league, season):
    rows = list(getattr(league, "carousel", {}).get(season, []) or [])
    out = []
    for item in rows[-8:][::-1]:
        text = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item)
        out.append(truncate(text, 46))
    return out[:5] or ["The coaching market is quiet right now."]


def _national_lines(league, st, week):
    if week <= 3:
        rows = list(getattr(league, "carousel", {}).get(st.get("season"), []) or [])
        # Reveal the carousel as a multi-week news cycle instead of dumping every headline at once.
        if rows:
            cut1 = max(1, len(rows) // 3)
            cut2 = max(cut1 + 1, (len(rows) * 2) // 3)
            seg = rows[:cut1] if week == 1 else rows[cut1:cut2] if week == 2 else rows[cut2:]
            out = []
            for item in seg[-8:][::-1]:
                text = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else str(item)
                out.append(truncate(text, 46))
            if out:
                return out[:5]
        return _carousel_lines(league, st.get("season"))
    if 4 <= week <= 7:
        pr = st.get("portal_summary", {})
        lines = []
        if pr:
            lines.append(f"Portal: {pr.get('entries', 0)} entries · {pr.get('moves', 0)} commitments")
            if pr.get("rank"):
                lines.append(f"Your transfer class: #{pr['rank']}")
        try:
            cycle = league.recruiting
            leaders = sorted((t for t in league.teams if cycle.commitments(t)), key=lambda t: cycle.class_rank(t) or 999)[:3]
            if leaders:
                lines.append("Recruiting leaders: " + ", ".join(f"#{cycle.class_rank(t)} {t.school}" for t in leaders))
        except Exception:
            pass
        return lines or ["Portal and recruiting boards are still forming."]
    if 8 <= week <= 15:
        lines = []
        cs = st.get("class_summary", {})
        if 11 <= week <= 13:
            try:
                import spring_cycle
                lines.extend(spring_cycle.spring_summary_lines(league, _team(league), 3))
            except Exception:
                pass
        if week >= 14:
            p2 = st.get("portal2_summary", {})
            if p2:
                line = f"Portal II: {p2.get('entries', 0)} entries · {p2.get('moves', 0)} moves"
                if p2.get("rank"):
                    line += f" · your class #{p2['rank']}"
                lines.append(line)
        if cs.get("rank"):
            lines.append(f"Recruiting class: #{cs['rank']}")
        if cs.get("overall_rank"):
            lines.append(f"Overall incoming class: #{cs['overall_rank']}")
        if week < 11:
            lines.extend(_carousel_lines(league, st.get("season"))[:2])
        return lines[:5] or ["Spring football is setting the next depth chart."]
    # Summer / preseason board.
    try:
        import preseason_board
        return preseason_board.summary_lines(league, _team(league))
    except Exception:
        try:
            top = league.rankings.top(5)
            names = []
            for i, x in enumerate(top, 1):
                t = x[0] if isinstance(x, tuple) else x
                names.append(f"#{i} {t.school}")
            return names or ["Preseason poll not available yet."]
        except Exception:
            return ["Preseason poll not available yet."]


def todo(league, team, week=None):
    out = []
    try:
        import people
        n = people.unread(league)
        if n:
            out.append(f"{n} unread message{'s' if n != 1 else ''} in your inbox")
    except Exception:
        pass
    try:
        import poscoach
        open_rooms = [g for g, c in poscoach.staff_of(team).items() if c is None]
        if getattr(team, "oc", None) is None or getattr(team, "dc", None) is None:
            out.append("A coordinator chair is open")
        if open_rooms:
            out.append(f"{len(open_rooms)} position-coach room{'s' if len(open_rooms) != 1 else ''} open")
    except Exception:
        pass
    try:
        import finance
        if finance.available(league, team) < 0:
            out.append(f"Over budget by {finance.money(-finance.available(league, team))}")
    except Exception:
        pass
    if len(team.roster) > 85:
        out.append(f"Roster at {len(team.roster)} — over the 85 limit")
    if week in (4, 5, 6):
        out.append("Winter portal window is active")
    if week == 7:
        out.append("National Signing Day is next week")
    if week in (11, 12):
        out.append("Spring practice block is active")
    if week == 13:
        out.append("Spring game this week — its film can change the post-spring depth chart")
    if week in (14, 15):
        out.append("Post-spring portal window is active")
    return out


def _schedule_lines(current):
    out = []
    lo = max(1, current - 1)
    hi = min(17, lo + 5)
    lo = max(1, hi - 5)
    for n in range(lo, hi + 1):
        w = BY_NUM[n]
        mark = "▶" if n == current else "✓" if n < current else "·"
        col = C.BYELLOW if n == current else C.BGREEN if n < current else C.GRAY
        out.append(f"{paint(mark, col, C.BOLD)} W{n:02d} {w['mon']}  {truncate(w['label'], 25)}")
    return out


def _draw(league, st, week, msg=""):
    clear()
    w = BY_NUM[week]
    team = _team(league)
    season = st.get("season", league.year)
    print(title_bar(f"OFFSEASON · WEEK {week}/17 · {w['label'].upper()}",
                    sub=f"{team.school} · {season}-{str(season + 1)[2:]}"))
    print(paint(f"   {w['mon']}  ·  {w['blurb']}", C.GRAY))
    print(paint(f"   Next deadline: {w['deadline']}", C.BCYAN, C.BOLD))
    if msg:
        print(paint(f"   {msg}", C.BGREEN, C.BOLD))
    print()
    left = panel("OFFSEASON SCHEDULE", _schedule_lines(week), 42, color=C.BCYAN, title_color=C.BCYAN, height=7)
    right = panel("PROGRAM STATUS", _program_lines(league, st, team), 57,
                  color=league.team_color(team) if hasattr(league, "team_color") else C.BYELLOW,
                  title_color=C.BWHITE, height=7)
    print("\n".join(columns(left, right, gap=1)))
    print()
    nat = panel("NATIONAL BOARD", _national_lines(league, st, week), 50, color=C.BMAGENTA, title_color=C.BMAGENTA, height=6)
    last = panel("LAST SEASON", _last_year_lines(st), 49, color=C.GRAY, title_color=C.BWHITE, height=6)
    print("\n".join(columns(nat, last, gap=1)))
    desk = todo(league, team, week)
    if desk:
        print(section("ON YOUR DESK", C.BYELLOW))
        for x in desk[:5]:
            print(paint(f"   • {x}", C.BYELLOW))
    print(rule())
    print("   " + "   ".join([key("A", "week agenda", C.BGREEN), key("I", "inbox"), key("R", "roster"),
                                  key("C", "recruiting class"), key("T", "transfer class"), key("$", "budget"), key("S", "staff"), key("V", "save")]))


def _agenda(league, st, week, action_label=None, action=None, required=False):
    team = _team(league)
    w = BY_NUM[week]
    while True:
        clear()
        print(title_bar(f"WEEK {week} AGENDA · {w['label'].upper()}", sub=team.school))
        done = w["key"] in st["completed_tasks"]
        print(section("MUST / SHOULD HANDLE", C.BYELLOW))
        if action is not None:
            tag = paint("DONE", C.BGREEN, C.BOLD) if done else paint("REQUIRED", C.BRED, C.BOLD) if required else paint("AVAILABLE", C.BCYAN, C.BOLD)
            print(f"   {paint('[1]', C.BYELLOW, C.BOLD)} {action_label or w['label']}   {tag}")
        else:
            print(paint("   No required action this week. Use the hub to review the program and national board.", C.GRAY))
        extras = todo(league, team, week)
        if extras:
            print(section("WATCH BEFORE YOU ADVANCE", C.BCYAN))
            for x in extras[:6]:
                print(f"   • {x}")
        print()
        print("   " + "   ".join([key("1", "re-enter primary task" if done else "handle primary task", dim=action is None),
                                      key("A", "advance week", C.BGREEN), key("Enter", "back to hub")]))
        c = ask("Agenda:").strip().lower()
        if c == "1" and action is not None:
            action()
            if w["key"] not in st["completed_tasks"]:
                st["completed_tasks"].append(w["key"])
            _replay[w["key"]] = action
            done = True
            _save(league)
            continue
        if c == "a":
            if required and action is not None and not done:
                print(paint("\n   This week's primary decision is still unresolved. Handle it before advancing.", C.BRED, C.BOLD))
                pause()
                continue
            return "advance"
        return "back"




def _recruiting_class_view(league, team):
    """Keep the current/signed high-school class visible for the entire offseason."""
    cycle = league.recruiting
    commits = list(cycle.commitments(team))
    report = _CONTEXT.get("class_report")
    signed = list(getattr(report, "classes", {}).get(team, [])) if report is not None else []
    if commits or not signed:
        import recruiting_screens
        recruiting_screens.class_view(league, team)
        return
    clear()
    print(title_bar(f"{team.school.upper()} · {league.year} SIGNED RECRUITING CLASS"))
    avg = sum(getattr(r, "stars", 0) for r in signed) / len(signed) if signed else 0
    rank = _recruit_rank(league, team, report)
    print(f"   {paint('Signees', C.GRAY)} {len(signed)}    {paint('Average', C.GRAY)} {avg:.2f}★    "
          f"{paint('National class rank', C.GRAY)} {('#' + str(rank)) if rank else 'Unranked'}")
    print()
    for r in sorted(signed, key=lambda x: (x.position, -getattr(x, 'stars', 0), x.name)):
        print(f"   {paint(pad(r.position, 4), C.BCYAN)} {pad(truncate(r.name, 24), 25)}"
              f"{paint(str(getattr(r, 'stars', 0)) + '★', C.BYELLOW)}  {paint(getattr(r, 'home_state', '—'), C.GRAY)}")
    pause()

def _transfer_class_view(league, team):
    """Always-available view of this offseason's incoming transfers."""
    reports = []
    for rep in (_CONTEXT.get("portal"), getattr(league, "last_portal", None), getattr(league, "last_portal2", None)):
        if rep is not None and all(rep is not x for x in reports):
            reports.append(rep)
    entries = []
    for rep in reports:
        entries.extend(e for e in getattr(rep, "by_team_in", {}).get(team, []) if e not in entries)
    clear()
    print(title_bar(f"{team.school.upper()} · TRANSFER CLASS", sub=f"{league.year} OFFSEASON"))
    if not entries:
        print(paint("\n   No incoming transfers recorded yet this offseason.", C.GRAY))
        pause()
        return
    entries.sort(key=lambda e: (-getattr(e, "overall", 0), e.position, e.player.name))
    print(paint(f"   {len(entries)} incoming transfer{'s' if len(entries) != 1 else ''}", C.GRAY))
    print()
    for e in entries:
        deal = 0
        for rep in reports:
            deal = max(deal, getattr(rep, "deals", {}).get(e, 0) or 0)
        nil = f" · NIL {__import__('finance').money(deal)}/yr" if deal else ""
        print(f"   {paint(pad(e.position, 4), C.BCYAN)} {pad(truncate(e.player.name, 22), 23)}"
              f"{__import__('scout').ovr_short(e.overall)}  {pad(e.player.class_label, 7)} "
              f"{paint('from ' + truncate(e.origin.school, 24), C.GRAY)}{paint(nil, C.BGREEN) if nil else ''}")
    pause()

def _open_aux(league, choice):
    team = _team(league)
    if choice == "i":
        import people
        people.inbox_screen(league)
    elif choice == "r":
        import screens
        screens.roster_view(league, team)
    elif choice == "$":
        import finance_screens
        finance_screens.budget_screen(league, team)
    elif choice == "s":
        import staff_room
        staff_room.manage(league, team)
    elif choice == "c":
        _recruiting_class_view(league, team)
    elif choice == "t":
        _transfer_class_view(league, team)
    elif choice == "v":
        import saves
        saves.save_screen(league)


def week_hub(league, week, action_label=None, action=None, required=False, msg=""):
    """One offseason week.  A opens the agenda; advancing records exactly one week."""
    st = _state(league)
    st["week"] = week
    # Keep winter/spring alive: contextual mail arrives once when each offseason week opens.
    try:
        import offseason_mail
        offseason_mail.ensure_week(league, week)
    except Exception as e:                       # never block the offseason, but never hide a bug either
        league.__dict__.setdefault("error_log", []).append((league.year, f"offseason mail week {week}: {e!r}"))
        print(paint(f"   (Offseason mail for week {week} failed: {e}. The week continues.)", C.BRED))
        pause()
    if week not in st["agenda_seen"]:
        st["agenda_seen"].append(week)
    _save(league)
    while True:
        _draw(league, st, week, msg)
        c = ask("Offseason hub:").strip().lower()
        if c == "a":
            if _agenda(league, st, week, action_label, action, required) == "advance":
                if week not in st["completed_weeks"]:
                    st["completed_weeks"].append(week)
                st["week"] = min(17, week + 1)
                _save(league)
                return
        elif c in ("i", "r", "c", "t", "$", "s", "v"):
            _open_aux(league, c)
        elif c.startswith("v") and c[1:].isdigit():
            k = BY_NUM.get(int(c[1:]), {}).get("key")
            if k in _replay:
                _replay[k]()


def _walk_to(league, target):
    st = _state(league)
    current = max(1, int(st.get("week") or 1))
    # If the state was just initialized, Week 1 is still pending.
    while current < target:
        if current not in st["completed_weeks"]:
            week_hub(league, current)
        current += 1
        st["week"] = current


def _phase(league, key_, fn, required=None, label=None):
    w = BY_KEY[key_]
    _walk_to(league, w["n"])
    st = _state(league)
    if w["n"] in st["completed_weeks"]:
        return None
    if required is None:
        required = key_ in DECISION_KEYS
    return week_hub(league, w["n"], label or w["label"], fn, required=required)


# ═══ Existing systems scheduled onto the new weekly clock ═══════════════════

def january(league, team):
    if not active(league):
        import staff_screens
        staff_screens.review(league, team)
        return
    _start(league, league.year)
    import coach_screens
    import hc_search

    def carousel_view():
        coach_screens.carousel_report(league, league.year)
        hc_search.tracker(league, league.year)
        try:
            import offseason_cycle
            offseason_cycle.job_market_preview(league)
        except Exception:
            pass
    _phase(league, "carousel", carousel_view, required=False, label="Review coaching fallout and interview calls")

    import staff_room
    def staff_and_job_decision():
        try:
            import offseason_cycle
            offseason_cycle.resolve_job_market(league)
        except Exception:
            raise
        # If you changed jobs, manage the staff at the school you actually coach now.
        current = getattr(league, "user_team", None) or team
        staff_room.manage(league, current)
    _phase(league, "staff", staff_and_job_decision, required=True,
           label="Decide job offers and review your staff")


def staff_carousel(league, rng):
    import staff_carousel as sc
    if not active(league) or staff_user(league) is None:
        sc.run(league, rng, show=False)
        return
    year = league.year
    fn = lambda: sc.run(league, rng, show=True)
    _replay["staffcar"] = lambda: sc.replay(league, year)
    _phase(league, "staffcar", fn, required=True, label="Run the assistant-coach carousel")


def staff_user(league):
    import staff
    return staff.user_team(league)


def wrap_portal(league, window):
    if window is None or not active(league):
        return window

    def run(*a, **kw):
        # report exists here: entries are known, destinations are not yet resolved.
        report = a[1] if len(a) > 1 else None
        st = _state(league)
        if report is not None:
            st["portal_summary"].update(entries=len(getattr(report, "entries", [])))
        return _phase(league, "portal", lambda: window(*a, **kw), required=True,
                      label="Work Portal Window I")
    return run


def portal_complete(league, report):
    """Record the winter portal. Weekly Phase-2 reports have already lived through Weeks 4-6."""
    if not active(league):
        return
    st = _state(league)
    team = _team(league)
    st["portal_summary"] = {
        "entries": len(getattr(report, "entries", []) or []),
        "moves": len(getattr(report, "moves", []) or []),
        "rank": _portal_rank(league, report, team),
        "recruit_rank": _recruit_rank(league, team),
        "overall_rank": _overall_class_rank(league, team, report, None),
        "in": len(getattr(report, "by_team_in", {}).get(team, []) or []),
        "out": len(getattr(report, "by_team_out", {}).get(team, []) or []),
    }
    # transient only; used to compute the combined board during this running offseason
    _CONTEXT["portal"] = report
    if not getattr(report, "weekly", False):
        for k in ("portal_market", "portal_deadline", "recruit_finish"):
            _phase(league, k, lambda: None, required=False)
    _save(league)


def _after_prepare(league, report):
    _start(league, report.year)
    st = _state(league)
    team = league.user_team
    _CONTEXT["portal"] = getattr(report, "portal", None)
    _CONTEXT["class_report"] = getattr(report, "recruiting", None)
    if getattr(report, "recruiting", None) is not None:
        rr = _recruit_rank(league, team, report.recruiting)
        ov = _overall_class_rank(league, team, getattr(report, "portal", None), report.recruiting)
        st["class_summary"] = {"rank": rr, "overall_rank": ov,
                               "signed": len(getattr(report.recruiting, "classes", {}).get(team, []) or [])}
    return st, team


def after_part1(league, report):
    """Signing review through A-Day. Online replays this as one deterministic per-team moment."""
    st, team = _after_prepare(league, report)
    import screens
    import awards_screens

    def signing():
        if getattr(report, "portal", None) is not None and getattr(report.portal, "user", None) is not None:
            import portal_screens
            portal_screens.window_results(league, report.portal)
        if getattr(report, "portal", None) is not None:
            screens.portal_screen(league, report.portal)
        if getattr(report, "recruiting", None) is not None:
            import recruiting_screens
            recruiting_screens.final_rankings(league, team, report=report.recruiting, year=report.year)
    if BY_KEY["signing"]["n"] in st.get("completed_weeks", []):
        signing()
        _replay["signing"] = signing
    else:
        _phase(league, "signing", signing, required=True, label="National Signing Day")

    def reset_week():
        awards_screens.awards_screen(league, report.year)
        screens.offseason_report(league, report)
    _phase(league, "awards", reset_week, required=False, label="Review awards and roster report")
    _phase(league, "winter", lambda: _winter_review(league, team, report), required=False,
           label="Review winter development")
    import spring_cycle
    _phase(league, "spring", lambda: spring_cycle.run_block(league, team, 1), required=True,
           label="Set spring plan and run Practice Block I")
    _phase(league, "spring2", lambda: spring_cycle.run_block(league, team, 2), required=True,
           label="Run Practice Block II and review battles")
    _phase(league, "aday", lambda: a_day(league, team), required=True, label="Play / simulate A-Day")


def after_part2(league, report):
    """Post-spring review through Media Days. Online replays this per team after Portal II."""
    st, team = _after_prepare(league, report)
    import awards_screens
    if getattr(report, "portal2", None) is not None and getattr(report.portal2, "user", None) is not None:
        try:
            import portal_screens
            portal_screens.window_results(league, report.portal2)
        except Exception:
            pass
    _post_spring_review(league, team)
    awards_screens.draft_screen(league, report.year)
    import realignment
    realignment.offer_screen(league)
    _phase(league, "summer", lambda: summer(league, team), required=False, label="Summer workouts")
    _phase(league, "media", lambda: media_days(league, team), required=False, label="Media Days / preseason poll")
    _CONTEXT.pop("portal", None)
    _CONTEXT.pop("class_report", None)
    st["finished"] = True
    _save(league)


def after(league, report):
    """Signing Day through Media Days, each on the weekly hub."""
    after_part1(league, report)
    import offseason_cycle
    pwindow = getattr(league, "portal_hook", None)
    report.portal2 = offseason_cycle.run_spring_portal(league, league.rng, league.year, window=pwindow)
    after_part2(league, report)

def _winter_review(league, team, report):
    clear()
    print(title_bar(f"WINTER DEVELOPMENT · {team.school.upper()}"))
    changed = [(p, before, after) for t, p, before, after in getattr(report, "developed", []) if t is team and after != before]
    changed.sort(key=lambda x: x[2] - x[1], reverse=True)
    print(paint("   The roster's offseason development work is in. Spring will tell you how much of it your staff can see.", C.GRAY))
    print(section("BIGGEST MOVERS", C.BCYAN))
    for p, before, after in changed[:10]:
        print(f"   {pad(p.position, 4)}{pad(truncate(p.name, 24), 25)} {before:>3} → {after:<3}  {paint(f'{after-before:+d}', C.BGREEN)}")
    if not changed:
        print(paint("   No rating movement to call out.", C.GRAY))
    pause()


def _spring_two_review(league, team):
    clear()
    print(title_bar(f"SPRING BALL II · {team.school.upper()}"))
    bs = battles(league, team)
    if not bs:
        print(paint("   Your staff sees no close position battle heading into A-Day.", C.BGREEN))
    else:
        print(paint("   These rooms remain the tightest heading into the spring game:", C.GRAY))
        for gap, pos, a, b in bs[:8]:
            print(f"   {pad(pos,4)} {pad(truncate(a.name,22),23)} vs {pad(truncate(b.name,22),23)}  {paint(f'gap {gap:.1f}', C.GRAY)}")
    pause()


def _post_spring_review(league, team):
    clear()
    print(title_bar(f"POST-SPRING ROSTER · {team.school.upper()}"))
    print(paint("   A-Day is in the book. Review the rooms before the live post-spring portal window opens.", C.GRAY))
    try:
        import depth_ui
        from models import POSITIONS
        counts = []
        for pos in POSITIONS:
            room = team.players_at(pos)
            if room:
                counts.append((len(room), pos, room[0].name))
        for n, pos, starter in sorted(counts)[:10]:
            print(f"   {pad(pos,4)} {n:>2} players   ·   current top: {starter}")
    except Exception:
        pass
    pause()


# ═══ Spring practice ════════════════════════════════════════════════════════

def read_mult(league, team, p, pos=None):
    """Blur multiplier on the staff's read of a player: his position coach's eye, and spring focus."""
    import poscoach
    pos = pos or p.position
    m = poscoach.eye_mult(team, pos)
    f = team.__dict__.get("spring_focus")
    if f and f.get("year") == league.year and pos in f.get("pos", ()):
        m *= FOCUS_BLUR
    if f and f.get("year") == league.year and f.get("emphasis") == "competition":
        m *= 0.85
    return m


def _yr(p):
    return ("FR", "SO", "JR", "SR")[max(0, min(3, p.year))] + ("*" if getattr(p, "redshirt", False) else "")


def battles(league, team):
    """Where the last starter and the first man behind him are close, as your staff sees it."""
    import practice
    counts = practice.starter_counts(team)
    out = []
    for pos, n in counts.items():
        if pos in ("K", "P"):
            continue
        room = sorted(team.players_at(pos), key=lambda p: -practice.perceived(league, team, p))
        if len(room) <= n:
            continue
        a, b = room[n - 1], room[n]
        gap = practice.perceived(league, team, a) - practice.perceived(league, team, b)
        if gap <= 4 or (pos == "QB" and gap <= 7):
            out.append((abs(gap), pos, a, b))
    return sorted(out, key=lambda x: x[0])[:8]


EMPHASES = {
    "1": ("fundamentals", "Fundamentals", "Teach. Your freshmen and sophomores get extra growth."),
    "2": ("competition", "Competition", "Live periods, ones vs. ones. Your staff reads everyone a bit sharper "
                                        "all season."),
    "3": ("chemistry", "Chemistry", "Team-building, leadership council. The locker room's mood lifts."),
}


def spring_practice(league, team):
    """Spring ball: an emphasis for the fifteen practices, the position battles, and position trials."""
    clear()
    print(title_bar(f"SPRING PRACTICE  ·  {team.school.upper()}  ·  {league.year}"))
    print(paint("   Fifteen practices in March and April. First: what's the emphasis?\n", C.GRAY))
    for k, (_, name, blurb) in EMPHASES.items():
        print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)} {paint(name, C.BWHITE, C.BOLD)} — {blurb}")
    ch = ask("Emphasis (Enter = Fundamentals):").strip()
    key, name, _ = EMPHASES.get(ch, EMPHASES["1"])
    team.spring_focus = {"year": league.year, "pos": set(), "emphasis": key}
    rng = random.Random(f"spring:{team.school}:{league.year}")
    if key == "fundamentals":
        import development
        import facilities
        tr = facilities.training_rating(team)
        young = [p for p in team.roster if p.year <= 1]
        before = sum(p.overall for p in young)
        for p in young:
            development.develop_player(p, team.coach, tr, rng, team=team, scale=0.12, in_season=True)
        gain = sum(p.overall for p in young) - before
        print(paint(f"\n   Fundamentals: your {len(young)} freshmen and sophomores put on "
                    f"{max(0, gain)} rating points between them.", C.BGREEN))
    elif key == "chemistry":
        import morale
        for p in team.roster:
            morale.nudge(p, 5, "spring team-building", league)
        print(paint("\n   Chemistry: the leadership council meets every week. The locker room feels it.", C.BGREEN))
    else:
        print(paint("\n   Competition: ones against ones every day. Your staff sees more than usual.", C.BGREEN))
    pause()
    _battles(league, team)
    position_trials(league, team, rng)


def position_trials(league, team, rng):
    """Try up to two players somewhere new. Spring reps teach him the spot; your staff grades it;
    you decide whether he moves."""
    import depth
    from development import RELATED
    ideas = depth.move_ideas(league, team)
    tried = 0
    while tried < 2:
        clear()
        print(title_bar("SPRING PRACTICE  ·  POSITION TRIALS"))
        print(paint("   Try a player at a new position for the spring (up to two). He gets the reps there;\n"
                    "   your staff grades him at both spots, and you decide whether the move sticks.\n", C.GRAY))
        if ideas:
            print(paint("   Your staff's ideas:", C.BCYAN))
            for i, (p, old, new, why) in enumerate(ideas[:5], 1):
                print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(p.name, 22)}{old} → {new}   "
                      + paint(why, C.GRAY))
        print(paint("   Or type a player's name to pick your own.  [Enter] done", C.GRAY))
        ch = ask("Trial:").strip()
        if not ch:
            return
        if ch.isdigit() and 1 <= int(ch) <= min(5, len(ideas)):
            p, old, new, _ = ideas[int(ch) - 1]
        else:
            hits = [p for p in team.roster if ch.lower() in p.name.lower()]
            if not hits:
                continue
            p = hits[0]
            old = p.position
            opts = [x for x in RELATED.get(old, []) if x not in ("K", "P")]
            if not opts:
                continue
            for i, x in enumerate(opts, 1):
                print(f"   [{i}] {x}")
            sel = ask(f"Try {p.name} at:").strip()
            if not (sel.isdigit() and 1 <= int(sel) <= len(opts)):
                continue
            new = opts[int(sel) - 1]
        tried += 1
        p.proficiency[new] = min(1.0, p.proficiency.get(new, 0.5) + 0.06)      # fifteen practices of reps
        here, there = depth.grade(league, team, p, old), depth.grade(league, team, p, new)
        rank_new = sorted([depth.grade(league, team, q, new) for q in team.players_at(new)] + [there],
                          reverse=True).index(there) + 1
        print(paint(f"\n   Staff grades {p.name}: {old} {round(here)}  ·  {new} {round(there)} "
                    f"(would be No. {rank_new} at {new})", C.BWHITE, C.BOLD))
        if ask(f"Move {p.name} to {new} for good? (y/n)").strip().lower() in ("y", "yes"):
            depth.apply_move(league, team, p, new)
            print(paint(f"   {p.name} is a {new} now.", C.BGREEN))
            ideas = [x for x in ideas if x[0] is not p]
        else:
            print(paint(f"   {p.name} stays at {old} — the reps there still help his versatility.", C.GRAY))
        pause()


def _battles(league, team):
    bs = battles(league, team)
    clear()
    print(title_bar(f"SPRING PRACTICE  ·  {team.school.upper()}  ·  {league.year}"))
    print(paint("   Fifteen practices. Pick up to three position battles for your staff to zero in on —\n"
                "   extra reps, extra film, one-on-ones every day. All season, you'll know who's really better there.\n",
                C.GRAY))
    if not bs:
        print(paint("   No real battles this spring — your staff likes the starters everywhere.", C.BGREEN))
        pause()
        return
    for i, (gap, pos, a, b) in enumerate(bs, 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)}  {pad(pos, 4)}{pad(truncate(a.name, 22), 23)}{pad(_yr(a), 5)}"
              f"{paint('vs', C.GRAY)}  {pad(truncate(b.name, 22), 23)}{_yr(b)}")
    raw = ask(f"\nBattles to focus on (e.g. 1,3,4 — up to {MAX_FOCUS}; Enter = let the staff spread it out):")
    picks = []
    for tok in raw.replace(" ", ",").split(","):
        if tok.isdigit() and 1 <= int(tok) <= len(bs) and int(tok) - 1 not in picks:
            picks.append(int(tok) - 1)
    picks = picks[:MAX_FOCUS]
    team.spring_focus["pos"] = {bs[i][1] for i in picks}
    import practice
    clear()
    print(title_bar("SPRING PRACTICE  ·  WHAT YOUR STAFF SAW"))
    for i, (gap, pos, a, b) in enumerate(bs):
        va, vb = practice.perceived(league, team, a), practice.perceived(league, team, b)
        lead, trail = (a, b) if va >= vb else (b, a)
        d = abs(va - vb)
        if i in picks:
            verdict = ("clear winner" if d >= 3 else "has the edge" if d >= 1.2 else "by a hair")
            print(f"   {paint('★', C.BYELLOW, C.BOLD)} {pad(pos, 4)}{paint(lead.name, C.BWHITE, C.BOLD)} "
                  f"{paint(verdict, C.BGREEN)} over {trail.name}")
        else:
            print(f"     {pad(pos, 4)}{paint('Still open — ', C.GRAY)}{lead.name} and {trail.name}, staff split")
    print(paint("\n   Focused rooms read sharper all season: the practice report, the staff's depth chart.", C.GRAY))
    import depth
    depth.staff_sort_yours(league, team)            # the chart they'll take into the summer
    pause()


# ═══ A-Day ══════════════════════════════════════════════════════════════════

def _split(team):
    """Blue and White: alternate down every room, then even out so each side can line up.
    A lone kicker or punter kicks for both (that's how spring games do it)."""
    import copy
    from models import POSITIONS
    from game_sim import DEPTH_NEED
    blue, white = copy.copy(team), copy.copy(team)
    br, wr = [], []
    for pos in POSITIONS:
        room = team.players_at(pos)
        b, w = room[0::2], room[1::2]
        need = DEPTH_NEED.get(pos, 1)
        while len(w) < need and len(b) > need:
            w.append(b.pop())
        while len(b) < need and len(w) > need:
            b.append(w.pop())
        if pos in ("K", "P") and room and not w:
            w = room[:1]
        br += b
        wr += w
    blue.roster, white.roster = br, wr
    for t, name in ((blue, "Blue"), (white, "White")):
        t.school = name
        t.__dict__["depth_order"] = {pos: [p for p in order if p in t.roster]
                                     for pos, order in team.__dict__.get("depth_order", {}).items()}
    return blue, white


def a_day(league, team):
    from season import Game
    from game_sim import GameSim
    blue, white = _split(team)
    g = Game(0, blue, white, False, game_type="Spring Game", bowl_name=f"{team.school} A-Day",
             venue=team.stadium, neutral=False)
    rng = random.Random(f"aday:{team.school}:{league.year}")
    clear()
    print(title_bar(f"A-DAY  ·  {team.school.upper()} SPRING GAME  ·  {team.stadium.upper()}"))
    try:
        sim = GameSim(g, rng, None, persist_injuries=False)
        sim.play()
    except Exception as e:                          # never let an exhibition break the offseason
        print(paint(f"\n   Storms rolled through and the spring game was called off. ({type(e).__name__})", C.GRAY))
        pause()
        return
    g.box = sim
    try:
        import spring_cycle
        spring_cycle.apply_aday_film(league, team, sim)
        sp = spring_cycle._state(league)
        sp.setdefault("aday", {})["score"] = f"Blue {g.home_score}, White {g.away_score}"
    except Exception:
        pass
    print(pad(paint(f"BLUE {g.home_score}  ·  WHITE {g.away_score}", C.BWHITE, C.BOLD), 100, "center"))
    print(paint("   First team on Blue, second team on White, alternating down every room.\n", C.GRAY))
    # Keep the default A-Day screen quick. The full exhibition box is optional below.
    try:
        print(section("SPRING GAME SNAPSHOT", C.BCYAN))
        for side, label in ((blue, "BLUE"), (white, "WHITE")):
            ts = sim.team_stats[side]
            print(f"   {pad(label,7)} {ts.get('total_yds', 0):>3} yds   "
                  f"{ts.get('first_downs', 0):>2} 1st downs   "
                  f"{ts.get('explosive_plays', 0):>2} explosive   "
                  f"{ts.get('turnovers', 0):>1} TO")
    except Exception:
        pass
    focus = team.__dict__.get("spring_focus", {}).get("pos", set())
    standouts = []
    for p, line in sim.stats.items():
        yds = line.get("pass_yds", 0) + line.get("rush_yds", 0) + line.get("rec_yds", 0)
        defn = line.get("tackles", 0) * 8 + line.get("sacks", 0) * 25 + line.get("ints", 0) * 30
        standouts.append((yds + defn, p))
    standouts.sort(key=lambda x: -x[0])
    print(section("A-DAY STANDOUTS"))
    for _, p in standouts[:5]:
        tag = paint("  ★ spring battle", C.BYELLOW) if p.position in focus else ""
        print(f"   {pad(p.position, 4)}{p.name}{tag}")
    league.__dict__.setdefault("a_days", {})[league.year] = (g.home_score, g.away_score,
                                                             [p.name for _, p in standouts[:5]])
    _a_day_recruits(league, team)
    show = ask("View the full A-Day box score? (y/n):").strip().lower()
    if show in ("y", "yes"):
        try:
            from commentary import box_score_lines
            print()
            for line in box_score_lines(sim):
                print(line)
            pause()
        except Exception:
            pass


def _a_day_recruits(league, team):
    """A-Day is a recruiting event: in-state juniors in the stands, and the kids on your board."""
    from recruiting_data import TEAM_STATES
    cycle = getattr(league, "recruiting", None)
    if cycle is None:
        return
    st = TEAM_STATES.get(team.school)
    st = st[0] if isinstance(st, (list, tuple)) else st
    board = set(map(id, getattr(team, "recruiting_targets", []) or []))
    guests = sorted((r for r in cycle.pool if not r.signed and (r.home_state == st or id(r) in board)),
                    key=lambda r: r.national_rank)[:10]
    if not guests:
        return
    lift = 2 + team.prestige / 40
    for r in guests:
        r.interest[team] = min(100, r.interest.get(team, 0) + lift)
    names = ", ".join(f"{r.stars}★ {r.position} {r.player.name}" for r in guests[:4])
    note = f"In the stands: {len(guests)} recruits, including {names}. They liked what they saw."
    print()
    for line in textwrap.wrap(note, 92):
        print(paint("   " + line, C.BGREEN))


# ═══ Summer and Media Days ══════════════════════════════════════════════════

def summer(league, team):
    import depth
    clear()
    print(title_bar(f"SUMMER WORKOUTS  ·  {team.school.upper()}"))
    print(paint("   Freshmen are on campus. Strength work, seven-on-seven and final roster planning bridge spring to camp.\n", C.GRAY))
    try:
        import preseason_board
        board = preseason_board.build(league, team)
        print(section("PROGRAM OUTLOOK", C.BCYAN))
        print(f"   Roster talent: {paint('#' + str(board['talent_rank']), C.BWHITE, C.BOLD) if board.get('talent_rank') else '—'} nationally")
        if board.get("strengths"):
            print("   Strongest rooms: " + ", ".join(f"{pos} ({score:.0f})" for score, pos in board["strengths"][:3]))
        if board.get("weaknesses"):
            print("   Rooms to watch: " + ", ".join(f"{pos} ({score:.0f})" for score, pos in board["weaknesses"][:3]))
    except Exception:
        pass
    ideas = getattr(team, "depth_ideas", [])
    print(paint("\n   Your staff carries the spring evaluations into fall camp; camp still makes the final depth call.", C.BGREEN))
    if ideas:
        print(paint(f"   They also suggest {len(ideas)} position move{'s' if len(ideas) != 1 else ''} — see Decide Your Depth in camp.", C.BYELLOW))
    pause()


def media_days(league, team):
    import preseason_board
    board = preseason_board.build(league, team)
    st = _state(league)
    st["preseason"] = {k: v for k, v in board.items() if k not in ("watch", "strengths", "weaknesses")}
    clear()
    print(title_bar(f"MEDIA DAYS  ·  {league.year} PRESEASON"))
    try:
        top = league.rankings.top(25)
    except Exception:
        top = None
    if top:
        print(section("PRESEASON TOP 15", C.BYELLOW))
        for i, t in enumerate(top[:15], 1):
            t = t[0] if isinstance(t, tuple) else t
            mark = paint("  ◀ you", C.BGREEN, C.BOLD) if t is team else ""
            print(f"   {i:>2}. {pad(t.full_name, 34)}{mark}")
    print(section("YOUR FORECAST", C.BCYAN))
    rk = board.get("poll_rank")
    print(f"   AP-style preseason poll: {paint('#' + str(rk), C.BYELLOW, C.BOLD) if rk else 'unranked'}")
    print(f"   {team.conference} media projection: {paint('#' + str(board.get('conference_rank')), C.BWHITE, C.BOLD)} of {board.get('conference_size')}")
    pw = f"{board.get('projected_wins', 0):.1f}"
    print(f"   Projected regular-season wins: {paint(pw, C.BWHITE, C.BOLD)}")
    print(f"   Roster talent: {paint('#' + str(board.get('talent_rank')), C.BWHITE, C.BOLD)} nationally")
    if board.get("strengths"):
        print("   Best rooms: " + ", ".join(pos for _, pos in board["strengths"][:3]))
    if board.get("weaknesses"):
        print("   Biggest questions: " + ", ".join(pos for _, pos in board["weaknesses"][:3]))
    watch = board.get("watch", {})
    mine = []
    for award, entries in watch.items():
        for p, t in entries:
            if t is team:
                mine.append(f"{award}: {p.position} {p.name}")
    if mine:
        print(section("PRESEASON WATCH LISTS", C.BMAGENTA))
        for x in mine[:6]:
            print("   " + x)
    try:
        conf_picks, aa_picks = preseason_board.preseason_honors(league, team)
        if conf_picks or aa_picks:
            print(section("PRESEASON HONORS", C.BCYAN))
            if aa_picks:
                text = "All-America projection: " + ", ".join(f"{p.position} {p.name}" for p in aa_picks[:6])
                for line in textwrap.wrap(text, 92):
                    print("   " + line)
            if conf_picks:
                text = "All-conference projection: " + ", ".join(f"{p.position} {p.name}" for p in conf_picks[:8])
                for line in textwrap.wrap(text, 92):
                    print("   " + line)
    except Exception:
        pass
    print(paint("\n   Media week is over. Fall camp is next; the offseason hub will hand you directly to preseason camp.", C.GRAY))
    pause()
