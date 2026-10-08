"""
skills.py — Your coaching tree (Career mode — your coach only).

Money buys your ratings (coach_dev.py). Reputation traits are handed to you by
the world (traits.py). The tree is the part you choose: perks that change how
the game's systems work for you. You earn skill points with results and spend
them on six branches.

EARNING POINTS  (the December review, plus a few career milestones)
  Finishing a season (any record)               +1
  Beating your expected win total by 2+ / 4+    +1 / +2
  A bowl game / winning it                      +1 / +1
  A conference title                            +2
  A playoff trip / the national title           +2 / +3
  Beating your rival                            +1
  Each of your AD's goals met                   +1
  A top-25 recruiting class (top 10)            +1 (+2)
  A player you coached goes in round 1          +1 each (after the draft)
  Career milestones: first win, 50 wins, 100 wins, 150 wins   +1 each

  A rebuilding year is about 2 points, a good year 4-5, a title run 8+. A long
  career earns roughly 50-70; the whole tree costs about 110 — you specialize.

HOW A BRANCH WORKS
  Four tiers. Tier 1 is open; each tier after that opens once you've spent
  enough in that branch (4, then 7, then 13). Tier 2 is a FORK: two perks,
  you pick one, and the other is locked for good. Tier 4 is the capstone.
  Costs: tier 1 = 2 points (Position Guru has 3 ranks), fork = 3, tier 3 = 3,
  capstone = 5.

RESPEC
  Free once whenever you take a new job (a new school can mean a new identity).
  Otherwise it costs a quarter of what you've spent; the rest comes back.

The tree is on the COACH tab (tab 6 → [T]) and on your career page ([T]).
"""
from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate
from netplay import capture

GATES = (0, 4, 7, 13)                   # points spent in the branch to open tiers 1-4
COST = {1: 2, 2: 3, 3: 3, 4: 5}
GROUPS = {"QB/WR": ("QB", "WR"), "RB/TE": ("RB", "TE"), "OL/DL": ("OL", "DL"), "LB/CB/S": ("LB", "CB", "S")}

# key: (branch, tier, name, what it does, fork group or None, max ranks)
PERKS = {
    # ── RECRUITER ──
    "silver_tongue": ("recruiter", 1, "Silver Tongue", "+8% interest from every recruiting pitch", None, 1),
    "film_junkie":   ("recruiter", 1, "Film Junkie", "evaluating film costs 1 hour instead of 2, and "
                                                     "often reveals two things at once", None, 1),
    "hometown":      ("recruiter", 2, "Hometown Hero", "+15% interest from recruits in your state", "r2", 1),
    "national":      ("recruiter", 2, "National Brand", "distance hurts your pitch half as much", "r2", 1),
    "promise_keeper": ("recruiter", 3, "Promise Keeper", "recruiting promises pull 25% harder; the first "
                                                         "one you break each year is forgiven", None, 1),
    "flip_artist":   ("recruiter", 3, "Flip Artist", "pushing another school's commit loses nothing, "
                                                     "and flip efforts pull 50% harder", None, 1),
    "machine":       ("recruiter", 4, "Machine", "+15% recruiting hours every week", None, 1),
    # ── DEVELOPER ──
    "position_guru": ("developer", 1, "Position Guru", "+10% development for one position group per rank "
                                                       "(you pick the group; stacks with your background trait)",
                      None, 3),
    "strength":      ("developer", 1, "Strength Program", "in-season injuries 8% less likely", None, 1),
    "redshirt_factory": ("developer", 2, "Redshirt Factory", "freshmen who sit (4 games or fewer) develop "
                                                             "20% faster", "d2", 1),
    "plug_and_play": ("developer", 2, "Plug and Play", "your freshmen arrive about 3 overall better", "d2", 1),
    "walk_on_magic": ("developer", 3, "Walk-on Magic", "walk-ons develop 25% faster — like scholarship kids",
                      None, 1),
    "nfl_pipeline":  ("developer", 3, "Pro League Pipeline", "every draft pick you coached lifts next year's recruits "
                                                      "at his position", None, 1),
    "everybody_better": ("developer", 4, "Everybody Gets Better", "+6% development for the whole roster",
                         None, 1),
    "scouts_eye":    ("developer", 4, "Scout's Eye", "estimates next to every scouting word: 'quality starter "
                                                     "(76-81)', 'good (1.03-1.09)' — yours and everyone else's",
                      None, 1),
    # ── MOTIVATOR ──
    "open_door":     ("motivator", 1, "Open Door", "sitting down with players costs no recruiting hours; "
                                                   "morale boosts land 25% harder", None, 1),
    "captains_council": ("motivator", 1, "Captain's Council", "captains pull the locker room's mood 50% harder",
                         None, 1),
    "players_coach": ("motivator", 2, "Players' Coach", "portal odds 20% lower — but discipline calls do half "
                                                        "as much for the room", "m2", 1),
    "hard_nosed":    ("motivator", 2, "Hard Nosed", "discipline calls do 50% more for the room — but morale "
                                                    "settles a few points lower", "m2", 1),
    "halftime_speech": ("motivator", 3, "Halftime Speech", "'light into them' at halftime is 15% likelier "
                                                           "to land", None, 1),
    "thick_skin":    ("motivator", 3, "Thick Skin", "unhappy wild cards drag their position groups half as much",
                      None, 1),
    "run_through_wall": ("motivator", 4, "Run Through a Wall", "chemistry is worth up to 1.5 points on "
                                                               "Saturday (instead of 0.9)", None, 1),
    # ── TACTICIAN ──
    "film_room":     ("tactician", 1, "Film Room", "the practice-focus lift is 25% stronger", None, 1),
    "clock_manager": ("tactician", 1, "Clock Manager", "+poise in every one-score fourth quarter", None, 1),
    "riverboat":     ("tactician", 2, "Riverboat", "+20 fourth-down aggression, and trick plays come 50% more",
                      "t2", 1),
    "field_position": ("tactician", 2, "Field Position", "+0.4 in the fourth quarter whenever you lead",
                       "t2", 1),
    "halftime_genius": ("tactician", 3, "Halftime Genius", "your halftime adjustments work 50% harder", None, 1),
    "big_game":      ("tactician", 3, "Big-Game Coach", "+0.5 against ranked teams and your rival", None, 1),
    "schemer":       ("tactician", 4, "Schemer", "the other staff's in-game adjustments work half as well "
                                                 "after halftime", None, 1),
    # ── POLITICIAN ──
    "media_savvy":   ("politician", 1, "Media Savvy", "measured answers stop costing recruits; humble answers "
                                                      "stop annoying win-now ADs", None, 1),
    "booster_circuit": ("politician", 1, "Booster Circuit", "when you ask your AD for money, he finds 25% more",
                        None, 1),
    "teflon":        ("politician", 2, "Teflon", "losses heat your seat 20% less", "p2", 1),
    "lightning_rod": ("politician", 2, "Lightning Rod", "your seat moves 25% more both ways — but recruits "
                                                        "like you 10% more", "p2", 1),
    "trusted_voice": ("politician", 3, "Trusted Voice", "AD trust gains +30%, losses −30%", None, 1),
    "fundraiser":    ("politician", 3, "Fundraiser", "budget growth 50% faster, and a higher ceiling on a single year's raise", None, 1),
    "face":          ("politician", 4, "Face of the Program", "bigger jobs call (you're a top candidate at more "
                                                              "places), and AD trust never falls below 40", None, 1),
    # ── PROGRAM BUILDER ──
    "groundbreaker": ("builder", 1, "Groundbreaker", "facility upgrades cost 15% less", None, 1),
    "collective":    ("builder", 1, "Collective Ties", "+5% to your NIL pool every year", None, 1),
    "coaching_tree": ("builder", 2, "Coaching Tree", "coordinators are more willing to come work for you, "
                                                     "and slower to leave", "b2", 1),
    "scheme_identity": ("builder", 2, "Scheme Identity", "recruits who fit your schemes feel it: +15 to your "
                                                         "scheme-fit pitch", "b2", 1),
    "stadium_exp":   ("builder", 3, "Stadium Experience", "+0.3 at home, and 25% more stadium revenue", None, 1),
    "staff_developer": ("builder", 3, "Staff Developer", "your coordinators count 50% more in player "
                                                         "development", None, 1),
    "blueprint":     ("builder", 4, "Blueprint", "your facilities never slip, and your budget never shrinks",
                      None, 1),
}
BRANCHES = [("recruiter", "RECRUITER"), ("developer", "DEVELOPER"), ("motivator", "MOTIVATOR"),
            ("tactician", "TACTICIAN"), ("politician", "POLITICIAN"), ("builder", "PROGRAM BUILDER")]


# ═══ State ══════════════════════════════════════════════════════════════════

def _st(coach):
    st = coach.__dict__.get("tree")
    if st is None:
        st = coach.tree = {"have": {}, "points": 0, "spent": 0, "log": [], "group": None,
                           "free_respec": False, "forgiven": {}, "milestones": set()}
    return st


def user_coach_of(team):
    c = getattr(team, "coach", None)
    return c if c is not None and getattr(c, "is_user", False) else None


def rank(coach, key):
    if coach is None or not getattr(coach, "is_user", False) or "tree" not in coach.__dict__:
        return 0
    return coach.tree["have"].get(key, 0)


def has(coach, key):
    return rank(coach, key) > 0


def team_has(team, key):
    return has(user_coach_of(team), key)


def guru_mult(team, position):
    c = user_coach_of(team)
    r = rank(c, "position_guru")
    if not r:
        return 1.0
    grp = _st(c).get("group")
    return 1 + 0.10 * r if grp and position in GROUPS.get(grp, ()) else 1.0


# ═══ Earning ════════════════════════════════════════════════════════════════

def award(league, n, why, quiet=False):
    coach = getattr(league, "user_coach", None)
    if coach is None or n <= 0:
        return
    st = _st(coach)
    st["points"] += n
    st["log"].append((league.year, n, why))
    del st["log"][:-30]


def season_review(league):
    """December: what the season earned. Posts one summary to the inbox."""
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if coach is None or team is None:
        return
    st = _st(coach)
    if st.get("reviewed") == league.year:
        return
    st["reviewed"] = league.year
    got = [(1, "finished the season")]
    try:
        import carousel as cz
        xw, _ = cz.expectation(league, team, coach)
        over = team.wins - xw
        if over >= 4:
            got.append((2, f"beat the expected win total by {over:.0f}"))
        elif over >= 2:
            got.append((1, f"beat the expected win total by {over:.0f}"))
    except Exception:
        pass
    games = [g for g in league.team_games(team) if g.played]
    bowls = [g for g in games if g.game_type == "Bowl"]
    if bowls:
        got.append((1, "made a bowl"))
        if bowls[-1].winner is team:
            got.append((1, f"won the {bowls[-1].bowl_name}"))
    ach = getattr(team, "achievements", [])
    if any(a.endswith("Champion") and "National" not in a for a in ach):
        got.append((2, "won the conference"))
    if "NP Appearance" in ach:
        got.append((2, "made the playoff"))
    if any(g.game_type == "National Championship" and g.winner is team for g in games):
        got.append((3, "won the national title"))
    import carousel as cz
    rival = cz.PRIMARY_RIVAL.get(team.school)
    if rival and any(g.opponent_of(team).school == rival and g.winner is team for g in games):
        got.append((1, f"beat {rival}"))
    for gl in getattr(team, "goals", []):
        try:
            s, _ = cz.goal_status(team, coach, gl, league.year)
            if s == "met":
                got.append((1, f"goal met: {gl.short.lower()}"))
        except Exception:
            pass
    try:
        cr = league.recruiting.class_rank(team)
        if cr and cr <= 10:
            got.append((2, f"a top-10 recruiting class (No. {cr})"))
        elif cr and cr <= 25:
            got.append((1, f"a top-25 recruiting class (No. {cr})"))
    except Exception:
        pass
    total = sum(n for n, _ in got)
    for n, why in got:
        award(league, n, why)
    import people
    lines = "; ".join(f"+{n} {why}" for n, why in got)
    people._post(league, "Your coaching tree", "Career", f"{total} skill point{'s' if total != 1 else ''} earned",
                 f"The {league.year} season earned you {total}: {lines}. You have {st['points']} to spend — "
                 "tab 6 COACH → [T].", kind="result", color=C.BMAGENTA)


def milestones(league):
    """First win, 50, 100, 150 — checked every week."""
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if coach is None or team is None:
        return
    st = _st(coach)
    wins = sum(h.get("w", 0) for h in coach.history) + team.wins
    for m in (1, 50, 100, 150, 200):
        if wins >= m and m not in st["milestones"]:
            st["milestones"].add(m)
            if m == 1 and coach.history and sum(h.get("w", 0) for h in coach.history) >= 1:
                continue                                     # an old save: that first win was long ago
            award(league, 1, "your first win as a head coach" if m == 1 else f"career win No. {m}")
            import people
            people._post(league, "Your coaching tree", "Career", "Milestone: +1 skill point",
                         ("Your first win as a head coach." if m == 1 else f"Career win No. {m}.")
                         + f" You have {st['points']} to spend.", kind="result", color=C.BMAGENTA)


def draft_points(league, picks):
    """After the draft: first-rounders you coached."""
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if coach is None or team is None:
        return []
    firsts = [x for x in picks if x["round"] == 1 and x["school"] == team.school]
    for x in firsts:
        award(league, 1, f"{x['name']} went in round 1")
    return firsts


# ═══ Buying ═════════════════════════════════════════════════════════════════

def spent_in(coach, branch):
    st = _st(coach)
    total = 0
    for key, r in st["have"].items():
        b, tier, *_ = PERKS[key]
        if b == branch:
            total += COST[tier] * r
    return total


def status(coach, key):
    """'have', 'max', 'buy', 'locked' (fork taken), 'gated' (needs points in branch), 'poor'."""
    st = _st(coach)
    branch, tier, name, what, fork, ranks = PERKS[key]
    r = st["have"].get(key, 0)
    if r >= ranks:
        return "have"
    if fork and any(k != key and PERKS[k][4] == fork and st["have"].get(k) for k in PERKS):
        return "locked"
    if spent_in(coach, branch) < GATES[tier - 1]:
        return "gated"
    if st["points"] < COST[tier]:
        return "poor"
    return "buy"


@capture.hook("coach", "tree", capture.b_tree)
def buy(league, coach, key, group=None):
    st = _st(coach)
    s = status(coach, key)
    if s != "buy":
        return False, {"have": "You already have it.", "locked": "You took the other side of that fork.",
                       "gated": f"Spend {GATES[PERKS[key][1] - 1]} in this branch first.",
                       "poor": "Not enough skill points."}.get(s, "Can't buy that.")
    if key == "position_guru" and not st.get("group"):
        if group not in GROUPS:
            return False, "Pick a position group first."
        st["group"] = group
    tier = PERKS[key][1]
    st["points"] -= COST[tier]
    st["spent"] += COST[tier]
    st["have"][key] = st["have"].get(key, 0) + 1
    st["log"].append((league.year, -COST[tier], f"learned {PERKS[key][2]}"))
    return True, f"Learned: {PERKS[key][2]}" + (f" (rank {st['have'][key]})" if PERKS[key][5] > 1 else "") + "."


def respec(league, coach):
    st = _st(coach)
    spent = st["spent"]
    if not spent:
        return False, "Nothing to reset."
    back = spent if st.get("free_respec") else int(spent * 0.75)
    st["points"] += back
    st["spent"] = 0
    st["have"] = {}
    st["group"] = None
    st["free_respec"] = False
    st["log"].append((league.year, back, "reset the tree"))
    return True, f"Tree reset. {back} of {spent} points back."


def new_job(coach):
    """Called when your coach takes a new job: one free respec."""
    if getattr(coach, "is_user", False):
        _st(coach)["free_respec"] = True


# ═══ The screen ═════════════════════════════════════════════════════════════

MARK = {"have": ("●", C.BGREEN), "buy": ("○", C.BYELLOW), "poor": ("○", C.GRAY), "locked": ("✕", C.BRED),
        "gated": ("·", C.GRAY), "max": ("●", C.BGREEN)}


def _cell(coach, key, width):
    st = _st(coach)
    s = status(coach, key)
    mark, col = MARK[s]
    name = PERKS[key][2]
    ranks = PERKS[key][5]
    if ranks > 1:
        r = st["have"].get(key, 0)
        mark = "●" * r + "○" * (ranks - r)
        col = C.BGREEN if r else col
    return paint(pad(f"{mark} {truncate(name, width - len(mark) - 2)}", width), col)


def tree_screen(league):
    coach = league.user_coach
    msg = ""
    while True:
        clear()
        st = _st(coach)
        print(title_bar(f"COACHING TREE  ·  COACH {coach.name.upper()}  ·  {st['points']} TO SPEND "
                        f"({st['spent']} SPENT)"))
        print(paint("   Earn points with results (the December review, milestones, first-round picks). "
                    "Each branch opens tier by tier; tier 2 is a fork.", C.GRAY))
        if st.get("free_respec"):
            print(paint("   New job: your next reset is free.", C.BCYAN))
        from traits import COACH_TRAITS
        born = [COACH_TRAITS[t][0] for t in getattr(coach, "traits", []) if t in COACH_TRAITS]
        if born:
            print(paint(f"   Starting trait (from your background, always on): {', '.join(born)}", C.GRAY))
        print()
        w = 30                                         # three branches across: names fit whole
        for half in (BRANCHES[:3], BRANCHES[3:]):
            start = BRANCHES.index(half[0]) + 1
            print("   " + "".join(paint(pad(f"{i}. {lab}  ({spent_in(coach, b)} spent)", w + 1), C.BWHITE, C.BOLD)
                                 for i, (b, lab) in enumerate(half, start)))
            for tier in (1, 2, 3, 4):
                if tier > 1:
                    print("   " + "".join(paint(pad(f"── needs {GATES[tier - 1]} pts in branch ──", w + 1), C.GRAY)
                                          for _ in half))
                keys_by_b = [[k for k, v in PERKS.items() if v[0] == b and v[1] == tier] for b, _ in half]
                for row in range(max(len(x) for x in keys_by_b)):
                    line = "   "
                    for ks in keys_by_b:
                        line += (_cell(coach, ks[row], w) + " ") if row < len(ks) else " " * (w + 1)
                    print(line)
            print()
        print(paint("   ● have   ○ can buy (gray = not enough points)   ✕ locked out by your fork   · needs more "
                    "points in the branch", C.GRAY))
        if st.get("group"):
            print(paint(f"   Position Guru group: {st['group']}", C.GRAY))
        recent = [f"{'+' if n > 0 else ''}{n} {why}" for _, n, why in st["log"][-4:]]
        if recent:
            print(paint("   Lately: " + "; ".join(reversed(recent)), C.GRAY))
        print(rule())
        if msg:
            print(paint("   " + msg, C.BCYAN))
            msg = ""
        import webview
        if webview.on():
            try:
                br = []
                for i, (b, lab) in enumerate(BRANCHES, 1):
                    perks = []
                    for k, v in PERKS.items():
                        if v[0] != b:
                            continue
                        perks.append({"name": v[2], "tier": v[1], "status": status(coach, k), "ranks": v[5],
                                      "have": st["have"].get(k, 0)})
                    br.append({"key": str(i), "label": lab, "spent": spent_in(coach, b), "perks": perks})
                webview.emit("tree", {"name": coach.name, "points": st["points"], "spent": st["spent"],
                                      "free": bool(st.get("free_respec")), "born": born, "group": st.get("group") or "",
                                      "recent": recent, "branches": br, "gates": list(GATES), "msg": webview.plain(msg)})
            except Exception:
                pass
        c = ask("Branch # to open, [R] reset the tree, Enter = back:").strip().lower()
        if c == "":
            return
        if c == "r":
            cost = "free" if st.get("free_respec") else f"you lose {st['spent'] - int(st['spent'] * 0.75)} points"
            if ask(f"Reset every perk ({cost})? Type YES:").strip().upper() == "YES":
                ok, msg = respec(league, coach)
            continue
        if c.isdigit() and 1 <= int(c) <= len(BRANCHES):
            msg = _branch(league, coach, BRANCHES[int(c) - 1])


def _branch(league, coach, branch):
    b, label = branch
    keys = [k for k, v in PERKS.items() if v[0] == b]
    clear()
    st = _st(coach)
    print(title_bar(f"{label}  ·  {spent_in(coach, b)} SPENT HERE  ·  {st['points']} TO SPEND"))
    print()
    for i, k in enumerate(keys, 1):
        _, tier, name, what, fork, ranks = PERKS[k]
        s = status(coach, k)
        mark, col = MARK[s]
        tag = {"have": "learned", "buy": f"{COST[tier]} pts", "poor": f"{COST[tier]} pts (need more)",
               "locked": "locked — you took the other fork", "gated": f"opens at {GATES[tier - 1]} spent here"}[s]
        if ranks > 1:
            tag = f"rank {st['have'].get(k, 0)}/{ranks} · " + ("maxed" if s == "have" else
                                                                f"{COST[tier]} pts (need more)" if s == "poor"
                                                                else f"{COST[tier]} pts")
        fork_tag = paint("  FORK", C.BMAGENTA) if fork else ""
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint('T' + str(tier), C.GRAY)} "
              f"{paint(pad(name, 24), col, C.BOLD)}{paint(pad(tag, 30), C.GRAY)}{fork_tag}")
        print(paint(f"        {what}", C.GRAY))
    import webview
    if webview.on():
        try:
            rows = []
            for i, k in enumerate(keys, 1):
                _, tier, name, what, fork, ranks = PERKS[k]
                rows.append({"key": str(i), "tier": tier, "name": name, "what": what, "fork": bool(fork),
                             "status": status(coach, k), "cost": COST[tier], "ranks": ranks, "have": st["have"].get(k, 0),
                             "gate": GATES[tier - 1]})
            webview.emit("branch", {"label": label, "spent": spent_in(coach, b), "points": st["points"], "rows": rows})
        except Exception:
            pass
    c = ask("Learn which? (Enter = back):").strip()
    if not (c.isdigit() and 1 <= int(c) <= len(keys)):
        return ""
    k = keys[int(c) - 1]
    group = None
    if k == "position_guru" and not st.get("group") and status(coach, k) == "buy":
        gl = list(GROUPS)
        print("   " + "   ".join(f"{paint(f'[{i}]', C.BYELLOW)} {g}" for i, g in enumerate(gl, 1)))
        g = ask("Which position group? (locked in until you reset the tree)").strip()
        if not (g.isdigit() and 1 <= int(g) <= len(gl)):
            return ""
        group = gl[int(g) - 1]
    if PERKS[k][4] and status(coach, k) == "buy":
        other = next(PERKS[x][2] for x in PERKS if x != k and PERKS[x][4] == PERKS[k][4])
        if ask(f"This is a fork: taking {PERKS[k][2]} locks out {other}. Type YES:").strip().upper() != "YES":
            return ""
    ok, text = buy(league, coach, k, group)
    return text


def after_offseason(league, report):
    """After the draft and signing day: points for first-rounders, and Pro League Pipeline's pull on the new class."""
    coach = getattr(league, "user_coach", None)
    team = getattr(coach, "team", None)
    if coach is None or team is None or getattr(league, "mode", None) != "career":
        return
    picks = (getattr(report, "draft", None) or {}).get("picks", []) if isinstance(getattr(report, "draft", None), dict) \
        else []
    mine = [x for x in picks if x["school"] == team.school]
    firsts = draft_points(league, picks)
    if firsts:
        import people
        people._post(league, "Your coaching tree", "Career", f"Round 1: +{len(firsts)} skill point"
                     + ("s" if len(firsts) != 1 else ""),
                     "First-round picks you coached: " + ", ".join(x["name"] for x in firsts) + ".",
                     kind="result", color=C.BMAGENTA)
    if mine and has(coach, "nfl_pipeline"):
        by_pos = {}
        for x in mine:
            by_pos[x["pos"]] = by_pos.get(x["pos"], 0) + (6 if x["round"] == 1 else 4 if x["round"] <= 3 else 2)
        for r in league.recruiting.pool:
            v = by_pos.get(r.position)
            if v:
                r.interest[team] = min(100, r.interest.get(team, 0) + v)
