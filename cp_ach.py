"""
cp_ach.py — Achievements, the legacy score and the Hall of Fame track (Coach Career).

Ninety-odd achievements in nine groups, each a tier (bronze 10 points, silver 25, gold 50,
platinum 100). Counting ones show their progress (47 of 100 wins); hidden ones stay "???"
until you earn them. Everything is worked out from your record — every game you've coached,
archived seasons included — so an old save earns what it already did.

  evaluate(league, final=False)   unlock what's been earned (weekly; final=True at season end)
  legacy_score(league)            points + a résumé score → the Hall of Fame track
  screen(league)                  the Achievements screen
"""
from ui import (
    WIDTH,
    C,
    ask,
    clear,
    clip,
    footer,
    key,
    pad,
    paint,
    tabs,
    title_bar,
    truncate,
)

TIER = {"B": ("Bronze", 10, "\033[38;5;173m"), "S": ("Silver", 25, "\033[38;5;250m"),
        "G": ("Gold", 50, C.BYELLOW), "P": ("Platinum", 100, C.BCYAN)}
CATS = ["Winning", "Big Games", "Postseason", "Rivals", "Program", "Recruiting", "Players", "Career", "Oddities"]

# (key, name, what it takes, group, tier, hidden, progress: (counter, target) or None)
ALL = [
    # Winning
    ("first_win", "First Win", "Win your first game as a head coach", "Winning", "B", False, ("wins", 1)),
    ("wins_25", "Twenty-Five", "Win 25 games", "Winning", "B", False, ("wins", 25)),
    ("wins_50", "Fifty", "Win 50 games", "Winning", "S", False, ("wins", 50)),
    ("wins_100", "100 Wins", "Win 100 games", "Winning", "G", False, ("wins", 100)),
    ("wins_150", "150 Wins", "Win 150 games", "Winning", "G", False, ("wins", 150)),
    ("wins_200", "200 Wins", "Win 200 games", "Winning", "P", False, ("wins", 200)),
    ("wins_250", "250 Wins", "Win 250 games", "Winning", "P", False, ("wins", 250)),
    ("ten_wins", "Double Digits", "Win 10 games in a season", "Winning", "S", False, ("ten_seasons", 1)),
    ("ten_x3", "Habit", "Three 10-win seasons", "Winning", "G", False, ("ten_seasons", 3)),
    ("ten_x10", "Ten of Them", "Ten 10-win seasons", "Winning", "P", False, ("ten_seasons", 10)),
    ("twelve", "Twelve", "Win 12 games in a season", "Winning", "S", False, None),
    ("thirteen", "Lucky Thirteen", "Win 13 or more games in a season", "Winning", "G", False, None),
    ("undefeated", "Perfect Regular Season", "Go 12-0 in the regular season", "Winning", "G", False, None),
    ("perfect", "Perfection", "Undefeated, national champions", "Winning", "P", False, None),
    ("fortress", "Fortress", "Unbeaten at home (5+ home games)", "Winning", "S", False, None),
    ("road_warriors", "Road Warriors", "Unbeaten on the road (4+ road games)", "Winning", "G", False, None),
    ("turnaround", "Turnaround", "Win 5 more games than the year before, same school", "Winning", "S", False, None),
    ("day_one", "Day One", "Win 10 games in your first season at a school", "Winning", "G", False, None),
    # Big games
    ("beat_top10", "Top-10 Takedown", "Beat a top-10 team", "Big Games", "B", False, None),
    ("beat_no1", "Giant Killer", "Beat the No. 1 team in the country", "Big Games", "G", False, None),
    ("road_top5", "Hostile Territory", "Beat a top-5 team on the road", "Big Games", "G", False, None),
    ("road_no1", "Silence the Crowd", "Beat No. 1 in their stadium", "Big Games", "P", True, None),
    ("nobody_saw", "Nobody Saw It Coming", "Beat a top-5 team while unranked", "Big Games", "G", False, None),
    ("ranked_10", "Ranked Wins", "Beat 10 ranked teams", "Big Games", "S", False, ("ranked_wins", 10)),
    ("ranked_25", "Big-Game Coach", "Beat 25 ranked teams", "Big Games", "G", False, ("ranked_wins", 25)),
    ("ranked_50", "Giant Slayer", "Beat 50 ranked teams", "Big Games", "P", False, ("ranked_wins", 50)),
    ("comeback", "Comeback Kids", "Win a game you trailed by 17 or more", "Big Games", "S", False, None),
    ("comeback_21", "Never Out of It", "Win a game you trailed by 21 or more", "Big Games", "G", True, None),
    ("ot_win", "Bonus Football", "Win in overtime", "Big Games", "B", False, None),
    ("marathon", "Marathon", "Win in triple overtime or longer", "Big Games", "S", True, None),
    ("underdogs", "Underdogs", "Beat three ranked teams in one season while unranked", "Big Games", "G", True, None),
    # Postseason
    ("bowl_win", "Bowl Winner", "Win a bowl game", "Postseason", "B", False, ("bowl_wins", 1)),
    ("bowl_5", "Bowl Regulars", "Win 5 bowl games", "Postseason", "S", False, ("bowl_wins", 5)),
    ("bowl_10", "December Specialists", "Win 10 bowl games", "Postseason", "G", False, ("bowl_wins", 10)),
    ("bowl_streak", "Three Straight", "Win bowl games in three straight seasons", "Postseason", "S", False, None),
    ("survive", "Survive and Advance", "Go 6-6 and get to a bowl", "Postseason", "B", True, None),
    ("playoff_trip", "Dancing", "Make the playoff", "Postseason", "S", False, ("playoff_apps", 1)),
    ("playoff_5", "Fixture", "Make the playoff five times", "Postseason", "G", False, ("playoff_apps", 5)),
    ("playoff_win", "Playoff Win", "Win a playoff game", "Postseason", "S", False, ("playoff_wins", 1)),
    ("final_four", "Final Four", "Reach the semifinals", "Postseason", "S", False, None),
    ("title_game", "Playing for It All", "Reach the national title game", "Postseason", "G", False, None),
    ("natl_title", "National Champions", "Win the national title", "Postseason", "P", False, ("titles", 1)),
    ("repeat", "Back to Back", "Win two national titles in a row", "Postseason", "P", False, None),
    ("dynasty", "Dynasty", "Win three national titles", "Postseason", "P", False, ("titles", 3)),
    ("anywhere", "Anywhere, Anytime", "Win national titles at two schools", "Postseason", "P", True, None),
    # Rivals
    ("rival_win", "Bragging Rights", "Beat your rival", "Rivals", "B", False, None),
    ("rival3", "Own the Rivalry", "Beat your rival three years running", "Rivals", "S", False, None),
    ("rival5", "Their Worst Nightmare", "Beat your rival five years running", "Rivals", "G", False, None),
    ("rival_10", "Series Domination", "Beat one rival 10 times", "Rivals", "P", False, ("rival_best", 10)),
    ("old_friends", "Old Friends", "Beat a school you used to coach", "Rivals", "S", True, None),
    ("teacher", "The Teacher", "Beat a former assistant", "Rivals", "S", False, None),
    ("student", "The Student Becomes the Master", "Lose to a former assistant", "Rivals", "B", True, None),
    ("slay_legend", "Slay the Legend", "Beat a head coach with 150 or more wins", "Rivals", "S", False, None),
    # Program
    ("conf_title", "League Champions", "Win a conference title", "Program", "S", False, ("conf_titles", 1)),
    ("conf_3", "League Dynasty", "Win three conference titles", "Program", "G", False, ("conf_titles", 3)),
    ("conf_5", "Run the League", "Win five conference titles", "Program", "P", False, ("conf_titles", 5)),
    ("ran_table", "Ran the Table", "Go unbeaten in conference play", "Program", "S", False, None),
    ("worst_first", "Worst to First", "A losing season, then a conference title", "Program", "G", True, None),
    ("no1_week", "Number One", "Be ranked No. 1", "Program", "S", False, None),
    ("top_poll", "Top of the Poll", "Finish No. 1 in the final poll", "Program", "G", False, None),
    ("top10_finish", "Top-10 Finish", "Finish in the final top 10", "Program", "B", False, None),
    ("never_left", "Never Left", "Ranked every week of a season", "Program", "G", False, None),
    ("sellout", "Sold Out", "Fill the stadium for every home game (5+)", "Program", "S", False, None),
    ("points_days", "Points for Days", "Lead the country in scoring", "Program", "G", False, None),
    ("brick_wall", "Brick Wall", "Allow the fewest points per game in the country", "Program", "G", False, None),
    ("statue", "Cast in Bronze", "Earn a statue outside the stadium", "Program", "P", False, None),
    ("decade", "Ten Years In", "Coach ten seasons at one school", "Program", "G", False, ("tenure", 10)),
    # Recruiting
    ("top10_class", "Top-10 Class", "Sign a top-10 recruiting class", "Recruiting", "S", False, None),
    ("top5_class", "Recruiting Machine", "Sign a top-5 recruiting class", "Recruiting", "G", False, None),
    ("no1_class", "Best Class in America", "Sign the No. 1 recruiting class", "Recruiting", "P", False, None),
    ("five_haul", "Five-Star Haul", "Three five-stars in one class", "Recruiting", "G", False, None),
    ("full_house", "Full House", "25 commitments in one class", "Recruiting", "S", False, None),
    ("borders", "Lock the Borders", "Ten in-state commitments in one class", "Recruiting", "S", False, None),
    ("top10_x5", "Recruiting Power", "Five top-10 classes", "Recruiting", "P", False, ("top10_classes", 5)),
    # Players
    ("heisman", "Golden Helmet", "Coach the Golden Helmet winner", "Players", "G", False, ("helmets", 1)),
    ("helmets_2", "Helmet Factory", "Coach two Golden Helmet winners", "Players", "P", False, ("helmets", 2)),
    ("aa_1", "All-American Coach", "Coach a first-team All-American", "Players", "B", False, ("aas", 1)),
    ("aa_10", "All-American Program", "Coach 10 first-team All-Americans", "Players", "S", False, ("aas", 10)),
    ("aa_40", "Talent Factory", "Coach 40 first-team All-Americans", "Players", "G", False, ("aas", 40)),
    ("first_rounder", "Pro Factory", "Send a player to the first round of the draft", "Players", "S", False, ("firsts", 1)),
    ("firsts_10", "Draft-Day Regular", "Ten first-round picks", "Players", "G", False, ("firsts", 10)),
    ("pick_one", "First Overall", "Coach the No. 1 overall pick", "Players", "G", True, None),
    ("pipeline", "Pipeline", "Ten players drafted in one year", "Players", "G", False, None),
    ("triple", "Triple Threat", "A 3,000-yard passer, 1,000-yard rusher and 1,000-yard receiver in one season",
     "Players", "G", False, None),
    ("jersey", "Hang It Up", "Retire a player's number", "Players", "S", False, None),
    ("from_nowhere", "From Nowhere", "A walk-on becomes a starter", "Players", "B", True, None),
    # Career
    ("journeyman", "Have Whistle, Will Travel", "Be head coach at three schools", "Career", "S", False, ("schools", 3)),
    ("three_schools", "Journeyman Winner", "Have a winning season at three schools", "Career", "G", False, None),
    ("blue_blood", "Blue Blood", "Get hired by one of the sport's elite programs", "Career", "S", False, None),
    ("climb", "The Climb", "Go from a Group of Five job to a Power job", "Career", "S", False, None),
    ("seasons_20", "Twenty Seasons", "Coach 20 seasons", "Career", "G", False, ("seasons", 20)),
    ("seasons_30", "Lifer", "Coach 30 seasons", "Career", "P", False, ("seasons", 30)),
    ("coy", "Coach of the Year", "Win Coach of the Year", "Career", "G", False, None),
    ("tree_1", "Branching Out", "A former assistant becomes a head coach", "Career", "S", False, ("tree_hc", 1)),
    ("tree_5", "Coaching Tree", "Five former assistants become head coaches", "Career", "P", False, ("tree_hc", 5)),
    ("straight_a", "Straight A's", "An A from your AD", "Career", "S", False, None),
    ("valedictorian", "Valedictorian", "A 4.0 from your AD", "Career", "G", True, None),
    ("storyteller", "Storyteller", "Finish every chapter of a story start", "Career", "G", False, None),
    ("favorite", "The AD's Favorite", "AD trust of 90 or more", "Career", "S", False, None),
    ("survivor", "Survivor", "Survive a red-hot seat with a winning season", "Career", "G", True, None),
    # Oddities
    ("goose_egg", "Goose Egg", "Win by shutout", "Oddities", "B", False, None),
    ("zeroed", "Zeroed Out", "Shut out a ranked team", "Oddities", "G", False, None),
    ("half_hundred", "Half a Hundred", "Score 50 in a game", "Oddities", "B", False, None),
    ("video_game", "Video-Game Numbers", "Score 70 in a game", "Oddities", "G", True, None),
    ("no_mercy", "No Mercy", "Win by 50 or more", "Oddities", "S", True, None),
    ("rock_fight", "Rock Fight", "Win while scoring 10 or fewer", "Oddities", "S", True, None),
    ("shootout", "Shootout", "Win a game where both teams score 45+", "Oddities", "S", True, None),
    ("humbled", "Humbled", "Lose to an FCS team", "Oddities", "B", True, None),
    ("see_me", "See Me After Class", "An F from your AD", "Oddities", "B", True, None),
]
BY = {a[0]: a for a in ALL}
ACH = [(a[0], a[1], a[2]) for a in ALL]               # career_plus's (key, name, what) view
ACH_BY = {a[0]: (a[1], a[2]) for a in ALL}

def _cp():
    import career_plus
    return career_plus


def _sch(t):
    return getattr(t, "school", t)


# ═══ Your record, game by game ══════════════════════════════════════════════

_CACHE = {}


def my_games(league):
    """[(year, game, my team)] — every game you've coached, oldest first."""
    me = getattr(getattr(league, "user_coach", None), "name", None)
    arc = getattr(league, "archive", {}) or {}
    tag = (id(league), league.year, league.week, len(arc), sum(len(v) for v in league.schedule.values()))
    if _CACHE.get("tag") == tag:
        return _CACHE["rows"]
    out = []
    for y in sorted(arc):
        for g in arc[y]:
            for t, n in (getattr(g, "hc", None) or {}).items():
                if n == me:
                    out.append((y, g, t))
                    break
    if league.year not in arc:
        for w in sorted(league.schedule):
            for g in league.schedule[w]:
                if not g.played:
                    continue
                for t, n in (getattr(g, "hc", None) or {}).items():
                    if n == me:
                        out.append((league.year, g, t))
                        break
    _CACHE.update(tag=tag, rows=out)
    return out


def seasons(league, final=False):
    """Your seasons as season_line dicts: the finished ones, plus this one when final."""
    import carousel as cz
    coach = league.user_coach
    hist = [h for h in coach.history if isinstance(h, dict)]
    t = coach.team
    if final and t is not None and t.coach is coach and not any(h.get("year") == league.year and h.get("school") == t.school
                                                               for h in hist) and (t.wins or t.losses):
        hist = hist + [cz.season_line(league, t)]
    return hist


def _hc_wins(league, name):
    for t in league.teams:
        if t.coach is not None and t.coach.name == name:
            hist = [h for h in getattr(t.coach, "history", []) if isinstance(h, dict)]
            return sum(h.get("w", 0) for h in hist) + t.wins
    return 0


def context(league, final=False):
    """Every count the achievements read."""
    me = league.user_coach
    st = _cp().state(league)
    games = my_games(league)
    ss = seasons(league, final)
    c = {"wins": sum(1 for _y, g, t in games if _sch(g.winner) == _sch(t)),
         "seasons": len(ss), "ten_seasons": sum(1 for s in ss if s["w"] >= 10),
         "bowl_wins": sum(1 for s in ss if s.get("bowl_win")),
         "playoff_apps": sum(1 for s in ss if s.get("cfp")),
         "titles": sum(1 for s in ss if s.get("title")),
         "conf_titles": sum(1 for s in ss if s.get("conf_champ")),
         "schools": len({s["school"] for s in ss} | ({me.team.school} if me.team is not None else set())),
         "ranked_wins": 0, "playoff_wins": 0, "rival_best": 0, "top10_classes": 0,
         "helmets": 0, "aas": 0, "firsts": 0, "tree_hc": 0, "tenure": 0}
    if me.team is not None:
        c["tenure"] = league.year - (me.hired_year or league.year) + 1
    rival_w = {}
    import rivalries
    for _y, g, t in games:
        opp = g.opponent_of(t)
        won = _sch(g.winner) == _sch(t)
        rk = {_sch(k): v for k, v in (getattr(g, "ranks", None) or {}).items()}
        if won and rk.get(_sch(opp)):
            c["ranked_wins"] += 1
        if won and g.game_type in ("NP First Round", "NP Quarterfinal", "NP Semifinal", "National Championship"):
            c["playoff_wins"] += 1
        if won and rivalries.is_rivalry(_sch(t), _sch(opp)):
            k = (_sch(t), _sch(opp))
            rival_w[k] = rival_w.get(k, 0) + 1
    c["rival_best"] = max(rival_w.values(), default=0)
    years_at = {(s["year"], s["school"]) for s in ss}
    if me.team is not None:
        years_at.add((league.year, me.team.school))
    for y, a in (getattr(league, "awards", {}) or {}).items():
        if a.get("heisman") and (y, _sch(a["heisman"][1])) in years_at:
            c["helmets"] += 1
        c["aas"] += sum(1 for _g, _p, tt in a.get("first", []) or [] if (y, _sch(tt)) in years_at)
    for y, picks in (getattr(league, "drafts", {}) or {}).items():
        c["firsts"] += sum(1 for x in picks if x.get("round") == 1 and ((y, x.get("school")) in years_at
                                                                         or (y - 1, x.get("school")) in years_at))
    c["top10_classes"] = sum(1 for v in st.get("classes", {}).values() if v.get("rank") and v["rank"] <= 10)
    try:
        c["tree_hc"] = sum(1 for r in _cp().tree(league) if r[3].startswith("head coach"))
    except Exception:                                   # noqa: BLE001, S110
        pass
    return c, games, ss


# ═══ Unlocking ══════════════════════════════════════════════════════════════

def _g_note(y, g, t):
    opp = g.opponent_of(t)
    return f"{g.score_for(t)}-{g.score_for(opp)} vs {_sch(opp)}, {y}"


def _deficit(g, t):
    box = getattr(g, "box", None)
    if box is None:
        return 0
    lines = {_sch(k): v for k, v in box.line.items()}
    a, b = lines.get(_sch(t), []), lines.get(_sch(g.opponent_of(t)), [])
    worst = ra = rb = 0
    for q in range(min(len(a), len(b))):
        ra += a[q]
        rb += b[q]
        worst = max(worst, rb - ra)
    return worst


def evaluate(league, final=False):
    """Unlock everything you've earned. Returns the names of what's new."""
    cp = _cp()
    if not cp.mine(league):
        return []
    st = cp.state(league)
    got = st["ach"]
    new = []

    def un(k, note=""):
        if k not in got and cp.unlock(league, k, note):
            new.append(BY[k][1])
    c, games, ss = context(league, final)
    # the counters
    for k, _n, _d, _cat, _tier, _hid, prog in ALL:
        if prog and k not in got and c.get(prog[0], 0) >= prog[1] and prog[0] not in ("tenure",):
            un(k, f"{c[prog[0]]}" if prog[1] > 1 else "")
    if c.get("tenure", 0) >= 10:
        un("decade", f"{c['tenure']} seasons at {league.user_team.school}")
    # game by game
    tree_names = set()
    try:
        tree_names = {r[1] for r in cp.tree(league)}
    except Exception:                                   # noqa: BLE001, S110
        pass
    old_schools = {s["school"] for s in ss} - ({league.user_team.school} if league.user_team else set())
    for y, g, t in games:
        opp = g.opponent_of(t)
        won = _sch(g.winner) == _sch(t)
        me, them = g.score_for(t), g.score_for(opp)
        rk = {_sch(k): v for k, v in (getattr(g, "ranks", None) or {}).items()}
        ro, rm = rk.get(_sch(opp)), rk.get(_sch(t))
        road = g.away is t and not getattr(g, "neutral", False)
        hc = {_sch(k): v for k, v in (getattr(g, "hc", None) or {}).items()}
        their = hc.get(_sch(opp))
        note = _g_note(y, g, t)
        if not won:
            if getattr(opp, "fcs", False):
                un("humbled", note)
            if their and their in tree_names:
                un("student", f"{their}, {note}")
            continue
        if ro and ro <= 10:
            un("beat_top10", note)
        if ro == 1:
            un("beat_no1", note)
            if road:
                un("road_no1", note)
        if ro and ro <= 5 and road:
            un("road_top5", note)
        if ro and ro <= 5 and not rm:
            un("nobody_saw", note)
        d = _deficit(g, t)
        if d >= 17:
            un("comeback", f"down {d}, {note}")
        if d >= 21:
            un("comeback_21", f"down {d}, {note}")
        ot = getattr(getattr(g, "box", None), "ot_round", 0) or 0
        if ot:
            un("ot_win", note)
        if ot >= 3:
            un("marathon", note)
        if them == 0:
            un("goose_egg", note)
            if ro:
                un("zeroed", note)
        if me >= 50:
            un("half_hundred", note)
        if me >= 70:
            un("video_game", note)
        if me - them >= 50:
            un("no_mercy", note)
        if me <= 10:
            un("rock_fight", note)
        if me >= 45 and them >= 45:
            un("shootout", note)
        try:
            import rivalries
            if rivalries.is_rivalry(_sch(t), _sch(opp)):
                un("rival_win", note)
        except Exception:                               # noqa: BLE001, S110
            pass
        if _sch(opp) in old_schools:
            un("old_friends", note)
        if their and their in tree_names:
            un("teacher", f"{their}, {note}")
        if their and _hc_wins(league, their) >= 150:
            un("slay_legend", f"{their}, {note}")
    # rivalry streaks (per rival, in order)
    streak = {}
    for y, g, t in games:
        try:
            import rivalries
            if not rivalries.is_rivalry(_sch(t), _sch(g.opponent_of(t))):
                continue
        except Exception:                               # noqa: BLE001, S112
            continue
        k = (_sch(t), _sch(g.opponent_of(t)))
        streak[k] = streak.get(k, 0) + 1 if _sch(g.winner) == _sch(t) else 0
        if streak[k] >= 3:
            un("rival3", f"{streak[k]} straight over {k[1]}")
        if streak[k] >= 5:
            un("rival5", f"{streak[k]} straight over {k[1]}")
    _season_checks(league, ss, un, final)
    # players, people
    for y, picks in (getattr(league, "drafts", {}) or {}).items():
        mine_ = [x for x in picks if any(x.get("school") == s["school"] and s["year"] in (y, y - 1) for s in ss)
                 or (league.user_team and x.get("school") == league.user_team.school and y >= (league.user_coach.hired_year or 0))]
        if any(x.get("overall_pick") == 1 for x in mine_):
            un("pick_one", next(x["name"] for x in mine_ if x.get("overall_pick") == 1))
        if len(mine_) >= 10:
            un("pipeline", f"{len(mine_)} picks, {y}")
    coy = [y for y, a in (getattr(league, "awards", {}) or {}).items() if a.get("coach") and a["coach"][0] == league.user_coach.name]
    if coy:
        un("coy", str(coy[0]))
    if st["jerseys"]:
        j = st["jerseys"][0]
        un("jersey", f"No. {j['number']}, {j['name']}")
    if any(s["kind"] == "walk-on" for s in st["stories"]):
        un("from_nowhere")
    try:
        import ad_trust
        if ad_trust.get(league.user_coach, league.user_team) >= 90:
            un("favorite")
    except Exception:                                   # noqa: BLE001, S110
        pass
    for y, cd in st.get("cards", {}).items():
        if cd["overall"] == "A":
            un("straight_a", f"{y}, GPA {cd['gpa']}")
        if cd["gpa"] >= 4.0:
            un("valedictorian", f"{y}, GPA {cd['gpa']}")
        if cd["overall"] == "F":
            un("see_me", str(y))
    if st.get("start", {}).get("done"):
        un("storyteller", st["start"].get("title", ""))
    return new


def _season_checks(league, ss, un, final):
    st = _cp().state(league)
    prev_by_school = {}
    bowl_run = 0
    for s in sorted(ss, key=lambda s: s["year"]):
        y, sch = s["year"], s["school"]
        tag = f"{s['w']}-{s['l']}, {sch} {y}"
        if s["w"] >= 10:
            un("ten_wins", tag)
        if s["w"] >= 12:
            un("twelve", tag)
        if s["w"] >= 13:
            un("thirteen", tag)
        if s.get("title") and s["l"] == 0:
            un("perfect", tag)
        if s.get("hw", 0) >= 5 and s.get("hl", 1) == 0:
            un("fortress", tag)
        if s.get("rw", 0) >= 4 and s.get("rl", 1) == 0:
            un("road_warriors", tag)
        if s.get("cw", 0) >= 6 and s.get("cl", 1) == 0:
            un("ran_table", tag)
        prev = prev_by_school.get(sch)
        if prev is not None and s["w"] - prev["w"] >= 5:
            un("turnaround", f"{prev['w']} → {s['w']} wins, {sch} {y}")
        if prev is not None and prev["w"] < prev["l"] and s.get("conf_champ"):
            un("worst_first", f"{sch} {y}")
        if prev is None and s["w"] >= 10:
            un("day_one", tag)
        prev_by_school[sch] = s
        if s.get("bowl_win"):
            bowl_run += 1
            if bowl_run >= 3:
                un("bowl_streak", f"through {y}")
        elif s.get("bowl") or s.get("cfp"):
            bowl_run = 0
        if s.get("bowl") and s["w"] - (1 if s.get("bowl_win") else 0) == 6 and s["l"] - (0 if s.get("bowl_win") else 1) == 6:
            un("survive", tag)
        post = s.get("post", "")
        if "Semifinal" in post or "Championship" in post or s.get("title") or "National" in post:
            un("final_four", f"{sch} {y}")
        if s.get("title") or "Lost National Championship" in post:
            un("title_game", f"{sch} {y}")
        fr = s.get("final_rank")
        if fr == 1:
            un("top_poll", f"{sch} {y}")
        if fr and fr <= 10:
            un("top10_finish", f"No. {fr}, {sch} {y}")
    titles = [(s["year"], s["school"]) for s in ss if s.get("title")]
    if len({sch for _y, sch in titles}) >= 2:
        un("anywhere", ", ".join(f"{sch} {y}" for y, sch in titles[:3]))
    yrs = sorted(y for y, _ in titles)
    if any(b - a == 1 for a, b in zip(yrs, yrs[1:])):     # noqa: RUF007 — Python 3.8 has no pairwise
        un("repeat", ", ".join(map(str, yrs[:3])))
    winning = {s["school"] for s in ss if s["w"] > s["l"]}
    if len(winning) >= 3:
        un("three_schools", ", ".join(sorted(winning)))
    # the season record st keeps for the things season_line doesn't
    for y, row in st.get("years", {}).items():
        sch = row.get("school", "")
        if row.get("no1"):
            un("no1_week", f"{sch} {y}")
        if row.get("weeks") and row.get("ranked_weeks") == row.get("weeks") and row["weeks"] >= 14:
            un("never_left", f"{sch} {y}")
        if row.get("sellout"):
            un("sellout", f"{sch} {y}")
        if row.get("off_rank") == 1:
            un("points_days", f"{sch} {y}")
        if row.get("def_rank") == 1:
            un("brick_wall", f"{sch} {y}")
        if row.get("triple"):
            un("triple", f"{sch} {y}")
        if row.get("underdog_wins", 0) >= 3:
            un("underdogs", f"{sch} {y}")
        if row.get("survived"):
            un("survivor", f"{sch} {y}")
    for y, cl in st.get("classes", {}).items():
        rk = cl.get("rank")
        if rk and rk <= 10:
            un("top10_class", f"No. {rk}, {y}")
        if rk and rk <= 5:
            un("top5_class", f"No. {rk}, {y}")
        if rk == 1:
            un("no1_class", str(y))
        if cl.get("fives", 0) >= 3:
            un("five_haul", f"{cl['fives']} five-stars, {y}")
        if cl.get("n", 0) >= 25:
            un("full_house", f"{cl['n']} commits, {y}")
        if cl.get("instate", 0) >= 10:
            un("borders", f"{cl['instate']} in-state, {y}")
    # where you've been hired
    for e in st.get("hires", []):
        if e.get("prestige", 0) >= 85:
            un("blue_blood", f"{e['school']}, {e['year']}")
        if e.get("from_g5") and e.get("power"):
            un("climb", f"{e.get('from')} → {e['school']}")


# ═══ The season record (what season_line doesn't keep) ══════════════════════

def weekly(league):
    """career_plus.weekly: ranked weeks, No. 1, underdog wins."""
    cp = _cp()
    team = league.user_team
    st = cp.state(league)
    row = st.setdefault("years", {}).setdefault(str(league.year), {"school": team.school})
    if league.week >= 1:
        rk = league.rankings.rank_of(team)
        if "pre_rank" not in row and league.week == 1:
            row["pre_rank"] = league.rankings.previous_rank(team)
        wk = row.setdefault("wk_seen", [])
        if league.week not in wk:
            wk.append(league.week)
            row["weeks"] = len(wk)
            row["ranked_weeks"] = row.get("ranked_weeks", 0) + (1 if rk else 0)
        if rk == 1:
            row["no1"] = True
        row["seat_peak"] = max(row.get("seat_peak", 0), getattr(league.user_coach, "seat", 0))
    for g in league.team_games(team):
        if g.played and g.week == league.week and g.winner is team:
            r = getattr(g, "ranks", None) or {}
            if r.get(g.opponent_of(team)) and not r.get(team):
                row["underdog_wins"] = row.get("underdog_wins", 0) + 1


def season_record(league):
    """Season end: the class, the stadium, the national stat ranks, the triple threat, the seat."""
    cp = _cp()
    team, coach = league.user_team, league.user_coach
    st = cp.state(league)
    row = st.setdefault("years", {}).setdefault(str(league.year), {"school": team.school})
    homes = [g for g in league.team_games(team) if g.home is team and not g.neutral and g.played]
    if len(homes) >= 5 and team.capacity and all((getattr(g, "attendance", 0) or 0) >= team.capacity for g in homes):
        row["sellout"] = True
    fbs = [t for t in league.teams if not getattr(t, "fcs", False) and t.wins + t.losses]

    def per(t, k):
        n = max(1, t.wins + t.losses)
        return (t.points_for if k == "pf" else t.points_against) / n
    row["off_rank"] = sorted(fbs, key=lambda t: -per(t, "pf")).index(team) + 1 if team in fbs else None
    row["def_rank"] = sorted(fbs, key=lambda t: per(t, "pa")).index(team) + 1 if team in fbs else None
    best = {"pass_yds": 0, "rush_yds": 0, "rec_yds": 0}
    for p in team.roster:
        for k in list(best):
            best[k] = max(best[k], p.season_stats.get(k, 0))
    row["triple"] = best["pass_yds"] >= 3000 and best["rush_yds"] >= 1000 and best["rec_yds"] >= 1000
    seat_peak = max(getattr(coach, "seat", 0), row.get("seat_peak", 0))
    prev = st["years"].get(str(league.year - 1), {})
    if prev.get("seat_end", 0) >= 75 and team.wins > team.losses:
        row["survived"] = True
    row["seat_end"] = seat_peak
    cyc = league.recruiting
    commits = cyc.commitments(team)
    st.setdefault("classes", {})[str(league.year)] = {
        "rank": cyc.class_rank(team), "n": len(commits), "fives": sum(1 for r in commits if r.stars >= 5),
        "fours": sum(1 for r in commits if r.stars == 4),
        "instate": sum(1 for r in commits if getattr(r, "home_state", None) == team.home_state)}


def note_hire(league, coach, team, from_team=None):
    """career.take_job: where you've been hired (blue bloods, the climb)."""
    from season import schedule_tier
    st = _cp().state(league)
    frm = from_team
    st.setdefault("hires", []).append({
        "school": team.school, "year": league.year, "prestige": round(team.prestige),
        "power": schedule_tier(team) == "power", "from": frm.school if frm else None,
        "from_g5": bool(frm is not None and schedule_tier(frm) != "power")})


# ═══ The legacy score ═══════════════════════════════════════════════════════

TRACK = [(0, "Just getting started", C.GRAY), (150, "Respected", C.BWHITE), (400, "Program Builder", C.BCYAN),
         (800, "Hall of Fame track", C.BGREEN), (1300, "Hall of Famer", C.BYELLOW), (2200, "All-Time Great", C.BMAGENTA),
         (3500, "Mount Rushmore", C.BRED)]


def legacy_score(league):
    """(total, achievement points, résumé points, label, color, next threshold)."""
    st = _cp().state(league)
    pts = sum(TIER[BY[k][4]][1] for k in st["ach"] if k in BY)
    c, _g, _ss = context(league, False)
    res = (c["wins"] + 15 * c["conf_titles"] + 60 * c["titles"] + 10 * c["playoff_wins"] + 4 * c["bowl_wins"]
           + 6 * c["ten_seasons"] + 3 * c["aas"] + 20 * c["helmets"] + 4 * c["firsts"] + 12 * c["tree_hc"])
    total = pts + res
    label, col, nxt = TRACK[0][1], TRACK[0][2], None
    for i, (cut, lab, cc) in enumerate(TRACK):
        if total >= cut:
            label, col = lab, cc
            nxt = TRACK[i + 1][0] if i + 1 < len(TRACK) else None
    return total, pts, res, label, col, nxt


# ═══ The screen ═════════════════════════════════════════════════════════════

def progress_of(league, c, a):
    prog = a[6]
    if not prog:
        return None
    return min(c.get(prog[0], 0), prog[1]), prog[1]


def screen(league):
    cp = _cp()
    tab = 1
    while True:
        st = cp.state(league)
        got = st["ach"]
        c, _g, _s = context(league)
        total, pts, _res, label, col, nxt = legacy_score(league)
        clear()
        print(title_bar(f"ACHIEVEMENTS · {len(got)} OF {len(ALL)}"))
        allpts = sum(TIER[a[4]][1] for a in ALL)
        print(f"\n   {paint(f'{pts}', C.BYELLOW, C.BOLD)}{paint(f' of {allpts} achievement points', C.GRAY)}   "
              f"{paint('Legacy score', C.GRAY)} {paint(str(total), C.BWHITE, C.BOLD)}  {paint(label, col, C.BOLD)}"
              + (paint(f"   next: {nxt}", C.GRAY) if nxt else ""))
        tiers = "   ".join(paint(f"{TIER[t][0]} {sum(1 for a in ALL if a[4] == t and a[0] in got)}/{sum(1 for a in ALL if a[4] == t)}",
                                 TIER[t][2]) for t in "BSGP")
        print(f"   {tiers}\n")
        print(tabs([f"{n} {sum(1 for a in ALL if a[3] == n and a[0] in got)}" for n in CATS[:5]], tab if tab <= 5 else 0))
        if tab > 5:
            print(tabs([f"{n} {sum(1 for a in ALL if a[3] == n and a[0] in got)}" for n in CATS[5:]], tab - 5))
        cat = CATS[tab - 1]
        print(paint(f"   {cat}", C.BWHITE, C.BOLD))
        for a in [a for a in ALL if a[3] == cat]:
            k, name, desc, _cat, tier, hidden, _p = a
            tn, _tp, tc = TIER[tier]
            chip = paint(pad(tn, 9), tc, C.BOLD)
            if k in got:
                note = got[k].get("note") or ""
                print(clip(f"   {paint('★', C.BYELLOW, C.BOLD)} {paint(pad(name, 30), C.BWHITE, C.BOLD)}{chip}"
                           f"{paint(str(got[k]['year']), C.GRAY)}  {paint(truncate(note, 36), C.GRAY)}", WIDTH))
            elif hidden:
                print(clip(f"   {paint('☆', C.GRAY)} {paint(pad('???', 30), C.GRAY)}{chip}{paint('Hidden. Keep coaching.', C.GRAY)}", WIDTH))
            else:
                pr = progress_of(league, c, a)
                tail = ""
                if pr:
                    from ui import bar
                    tail = f"  {bar(pr[0], 12, pr[1], C.BCYAN)} {paint(f'{pr[0]}/{pr[1]}', C.GRAY)}"
                print(clip(f"   {paint('☆', C.GRAY)} {paint(pad(name, 30), C.GRAY)}{chip}{paint(pad(truncate(desc, 38), 39) if pr else truncate(desc, 58), C.GRAY)}{tail}", WIDTH))
        footer(key("1-9", "group"), key("B", "back", C.GRAY))
        x = ask("Select:").strip().lower()
        if x.isdigit() and 1 <= int(x) <= len(CATS):
            tab = int(x)
        else:
            return
