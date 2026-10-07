"""
cp_starts.py — Story starts with chapters (Coach Career).

Fifteen first chapters. Each picks the kind of program you take over, sets the stage (the AD you
answer to, how warm your seat starts, the mood in the building, sometimes money), and writes three
chapters with deadlines: "Go bowling by your third season." Finish a chapter and the AD, the seat
and the locker room feel it; miss one and the story moves on without you. Finish all three and the
epilogue is yours (and so is the Storyteller achievement).

  pick(league, coach, rng)      the menu → (team, kind) or (None, None)
  apply(league, coach, team, k) after take_job: set the stage, write the chapters
  season_end(league)            check the chapters (career_plus.season_end)
  status_line(league)           one line for the legacy screen / This Week
  screen(league)                your story: chapters, deadlines, what's done
"""
import textwrap

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
    pause,
    section,
    title_bar,
    truncate,
)

# chapter: (title, goal text, objective, deadline season (1 = your first))
STARTS = {
    "rebuild": ("The Rebuild", "One of the ten weakest rosters in the sport. A patient AD, a long leash.",
                [("Signs of Life", "Win four games in a season", ("wins", 4), 2),
                 ("Bowl Bound", "Get to a bowl game", ("bowl",), 3),
                 ("Arrival", "Win nine games in a season", ("wins", 9), 5)]),
    "hotseat": ("The Hot Seat", "A program that expects to win and hasn't. You inherit the heat.",
                [("Stop the Bleeding", "A winning season, right away", ("winning",), 1),
                 ("Win the One That Matters", "Beat the rival", ("rival_win",), 2),
                 ("Cool It Down", "Win nine games in a season", ("wins", 9), 3)]),
    "legend": ("Replace a Legend", "A blue blood whose coach retired with the rings. Every loss gets compared.",
               [("Nine Is a Disappointment", "Win nine games in your first season", ("wins", 9), 1),
                ("Your Own Banner", "Win the conference", ("conf_title",), 3),
                ("Out of His Shadow", "Make the playoff", ("playoff",), 4)]),
    "homecoming": ("Homecoming", "Your alma mater calls. The fans love you already. That won't last if you lose.",
                   [("Home Again", "Beat the rival", ("rival_win",), 2),
                    ("Prove It Wasn't Nostalgia", "Win eight games in a season", ("wins", 8), 3),
                    ("Hang a Banner", "Win the conference", ("conf_title",), 6)]),
    "cleanup": ("Clean Up the Mess", "Scandal, a fired staff and a locker room that doesn't trust anyone. Fix the culture.",
                [("Trust", "Get team chemistry to 55 or better by season's end", ("chem", 55), 1),
                 ("Respectable", "A winning season", ("winning",), 2),
                 ("Redemption", "Win a bowl game", ("bowl_win",), 4)]),
    "climb": ("The Climb", "The bottom of a Group of Five league. Win here, and the big jobs will call.",
              [("Make Some Noise", "A winning season", ("winning",), 2),
               ("League Champs", "Win the conference", ("conf_title",), 4),
               ("The Call", "Get hired by a Power program", ("power_job",), 6)]),
    "boosters": ("The Boosters' Pick", "The money picked you. Extra NIL for two years, and the people who paid want it back.",
                 [("Spend It Well", "Sign a top-15 recruiting class", ("class", 15), 2),
                  ("Return on Investment", "Win ten games in a season", ("wins", 10), 3),
                  ("Top Ten", "Finish in the top 10", ("rank", 10), 4)]),
    "promoted": ("Promoted From Within", "You were the coordinator. The players asked for you. Keep them believing.",
                 [("Same Team, New Boss", "Win eight games in your first season", ("wins", 8), 1),
                  ("December Win", "Win a bowl game", ("bowl_win",), 2),
                  ("Your Program Now", "Finish in the top 15", ("rank", 15), 3)]),
    "no_qb": ("No Quarterback", "A good roster with nobody to throw it. Find one, or build around it.",
              [("Manage the Game", "A winning season, right away", ("winning",), 1),
               ("Find Your Guy", "Get to a bowl game", ("bowl",), 2),
               ("Ten With Your QB", "Win ten games in a season", ("wins", 10), 3)]),
    "fallen": ("Fallen Giant", "The banners are old and the roster is ordinary. The name still means something.",
               [("Respect", "Get to a bowl game", ("bowl",), 1),
                ("Back in the Poll", "Finish in the Top 25", ("rank", 25), 2),
                ("Giant Again", "Finish in the top 10", ("rank", 10), 4)]),
    "little_brother": ("Little Brother", "The rival has owned this series for years. Everybody here knows the number.",
                       [("Just One", "Beat the rival", ("rival_win",), 3),
                        ("Not a Fluke", "Beat the rival twice", ("rival_wins", 2), 5),
                        ("Big Brother Now", "Win the conference", ("conf_title",), 6)]),
    "dark_horse": ("Dark Horse", "The best roster outside the Power leagues. Crash the party.",
                   [("Take the League", "Win the conference", ("conf_title",), 2),
                    ("Get Noticed", "Finish in the Top 25", ("rank", 25), 2),
                    ("Crash the Party", "Make the playoff", ("playoff",), 3)]),
    "win_now": ("Win Now or Else", "A top-five roster and an AD who fired the last guy at ten wins. Win now.",
                [("Get In", "Make the playoff in your first season", ("playoff",), 1),
                 ("Win in January", "Win a playoff game", ("playoff_win",), 2),
                 ("The Only Thing", "Win the national title", ("title",), 3)]),
    "long_game": ("The Long Game", "The weakest Power program there is. Seven years, a patient AD, no shortcuts.",
                  [("Bowl Bound", "Get to a bowl game", ("bowl",), 3),
                   ("Nine Wins", "Win nine games in a season", ("wins", 9), 5),
                   ("The Summit", "Win the conference", ("conf_title",), 7)]),
    "surprise": ("Surprise Me", "A random program and a random story. No peeking.", []),
}
SETUP = {   # AD style, starting seat, chemistry nudge, NIL income per year for two years
    "rebuild": ("patient", 5, 0, 0), "hotseat": ("win_now", 55, -4, 0), "legend": ("big_game", 32, 0, 0),
    "homecoming": ("traditionalist", 15, 8, 0), "cleanup": ("patient", 10, -20, 0), "climb": ("turnaround", 12, 0, 0),
    "boosters": ("booster", 35, 0, 2_500_000), "promoted": ("conference", 20, 12, 0), "no_qb": ("analytics", 25, 0, 0),
    "fallen": ("turnaround", 28, 0, 0), "little_brother": ("traditionalist", 22, 0, 0), "dark_horse": ("big_game", 18, 4, 0),
    "win_now": ("win_now", 45, 0, 0), "long_game": ("patient", 0, 0, 0),
}
INTRO = {
    "rebuild": "{school} hasn't been good in a long time, and everybody knows it. Your AD hired you to build, not to patch. He'll give you time. Use it.",
    "hotseat": "{pred} lasted three years and didn't win enough. The fan base is restless, the boosters are louder, and your AD wants results this season. You start warm.",
    "legend": "{pred} retired with the rings, the statue and the whole state behind him. You get his roster, his expectations and every comparison.",
    "homecoming": "You played here. Your name is still in the media guide. The people in the stands remember you, and they expect you to remember them.",
    "cleanup": "The last staff left in a hurry. Half the roster stopped trusting the building. Before you win anything, you have to fix that.",
    "climb": "Nobody's watching {school}. That's the point. Win here and the phone rings.",
    "boosters": "The collective made one call, and it was about you. The money's real: two years of extra NIL. So is the expectation.",
    "promoted": "You called the plays here last year. When the job opened, the players went to the AD and asked for you.",
    "no_qb": "Everything's here but the quarterback. The starter left, and the room behind him is young, raw or both.",
    "fallen": "{school} used to be on television every Saturday. The banners are faded, and the recruits don't remember them.",
    "little_brother": "{rival} has owned this series for years. The fans can recite the score of every loss. Change that.",
    "dark_horse": "{school} has a roster most Power programs would trade for, and a schedule nobody respects. Make them respect it.",
    "win_now": "Ten wins got the last coach fired. This roster is built to win the whole thing, and your AD reminds you daily.",
    "long_game": "The bottom of the Power leagues. Your AD said seven years and meant it. Build it right.",
}


def _cp():
    import career_plus
    return career_plus


def _fbs(league):
    return [t for t in league.teams if not getattr(t, "fcs", False)]


def _rival(league, team):
    import carousel as cz
    r = cz._rival_of(team, league)
    return r[0] if r else None


def pool_for(league, kind, rng):
    from season import schedule_tier
    teams = _fbs(league)
    power = [t for t in teams if schedule_tier(t) == "power"]
    g5 = [t for t in teams if schedule_tier(t) != "power"]
    med = sorted(t.team_ovr for t in teams)[len(teams) // 2]
    if kind == "rebuild":
        return sorted(teams, key=lambda t: t.team_ovr)[:10]
    if kind == "hotseat":
        return [t for t in sorted(teams, key=lambda t: -t.prestige)[10:45] if t.team_ovr < med + 8][:10] \
            or sorted(teams, key=lambda t: -t.prestige)[10:20]
    if kind == "legend":
        return sorted(teams, key=lambda t: -t.prestige)[:8]
    if kind == "homecoming":
        return sorted(teams, key=lambda t: -t.prestige)[15:75:5]
    if kind == "cleanup":
        return sorted(power, key=lambda t: -t.prestige)[12:40:3]
    if kind == "climb":
        return sorted(g5, key=lambda t: t.prestige)[:10]
    if kind == "boosters":
        import finance
        return sorted([t for t in power if 55 <= t.prestige <= 82], key=lambda t: -finance.budget(t))[:10]
    if kind == "promoted":
        return sorted([t for t in power if t.team_ovr >= med], key=lambda t: -t.prestige)[5:35:3]
    if kind == "no_qb":
        def qb(t):
            room = list(t.players_at("QB"))
            return room[0].overall if room else 0
        return sorted([t for t in teams if t.team_ovr >= med], key=qb)[:10]
    if kind == "fallen":
        return sorted([t for t in sorted(teams, key=lambda t: -t.prestige)[:35] if t.team_ovr < med + 4],
                      key=lambda t: t.team_ovr)[:10] or sorted(teams, key=lambda t: -t.prestige)[20:30]
    if kind == "little_brother":
        import rivalries
        rows = []
        for t in teams:
            r = _rival(league, t)
            if not r:
                continue
            s = rivalries.series(league, t.school, r)
            w, l_ = s.wins.get(t.school, 0), s.wins.get(r, 0)
            if l_ > w:
                rows.append((l_ - w, t))
        rows.sort(key=lambda x: -x[0])
        return [t for _, t in rows[:10]] or sorted(power, key=lambda t: t.prestige)[:10]
    if kind == "dark_horse":
        return sorted(g5, key=lambda t: -t.team_ovr)[:10]
    if kind == "win_now":
        return sorted(teams, key=lambda t: -t.team_ovr)[:6]
    if kind == "long_game":
        return sorted(power, key=lambda t: t.team_ovr)[:8]
    return []


def pick(league, coach, rng):
    """Pick a story start. Returns (team, kind) or (None, None)."""
    keys = list(STARTS)
    while True:
        clear()
        print(title_bar("A STORY START · PICK YOUR FIRST CHAPTER"))
        print(paint("\n   Same game, a different first chapter. Each one picks the kind of program you take over, the AD\n"
                    "   you answer to and three chapters with deadlines. Finish them for the epilogue.\n", C.GRAY))
        for i, k in enumerate(keys, 1):
            name, blurb, chs = STARTS[k]
            dl = paint(f"  {len(chs)} chapters · {max(c[3] for c in chs)} yrs", C.GRAY) if chs else ""
            print(clip(f"   {paint(f'[{i:>2}]', C.BYELLOW, C.BOLD)} {paint(pad(name, 22), C.BWHITE, C.BOLD)}"
                       f"{paint(truncate(blurb, 52), C.GRAY)}{dl}", WIDTH))
        c = ask("Which story? (# for details, Enter = back):").strip()
        if not c.isdigit() or not 1 <= int(c) <= len(keys):
            return None, None
        kind = keys[int(c) - 1]
        if kind == "surprise":
            kind = rng.choice([k for k in keys if k != "surprise"])
            pool = pool_for(league, kind, rng)
            if not pool:
                continue
            return rng.choice(pool), kind
        team = _pick_program(league, kind, rng)
        if team is not None:
            return team, kind


def _pick_program(league, kind, rng):
    name, blurb, chs = STARTS[kind]
    pool = pool_for(league, kind, rng)
    import scout
    while True:
        clear()
        print(title_bar(f"{name.upper()} · PICK YOUR PROGRAM"))
        print(paint(f"\n   {blurb}", C.GRAY))
        print(section("THE CHAPTERS", C.BMAGENTA))
        for i, (t_, goal, _o, by) in enumerate(chs, 1):
            print(f"   {paint(f'{i}.', C.BMAGENTA, C.BOLD)} {paint(pad(t_, 26), C.BWHITE, C.BOLD)}{pad(goal, 46)}"
                  f"{paint(f'by season {by}', C.GRAY)}")
        style, seat, _chem, money = SETUP[kind]
        import carousel as cz
        print(paint(f"\n   Your AD: {cz.AD_STYLES[style][0]} ({cz.AD_STYLES[style][1].lower()}). Your seat starts at {seat}/100."
                    + (f" Extra NIL: {money // 1_000_000:.1f}M a year for two years." if money else ""), C.GRAY))
        print(section("THE PROGRAMS", C.BCYAN))
        for i, t in enumerate(pool, 1):
            r = _rival(league, t)
            extra = ""
            if kind == "little_brother" and r:
                import rivalries
                s = rivalries.series(league, t.school, r)
                extra = f"   vs {r}: {s.record_str(t.school)}"
            elif kind == "no_qb":
                room = list(t.players_at("QB"))
                extra = f"   QB room: {scout.team(room[0].overall) if room else 'empty'}"
            print(clip(f"   {paint(f'[{i:>2}]', C.BYELLOW, C.BOLD)}  {pad(t.full_name, 30)}{paint(pad(t.conference, 14), C.GRAY)}"
                       f"prestige {round(t.prestige):>3}   roster {scout.team(t.team_ovr)}{paint(extra, C.GRAY)}", WIDTH))
        if kind == "homecoming":
            print(paint("\n   Or type any school's name: your alma mater can be anywhere.", C.GRAY))
        c = ask("Which program? (Enter = back):").strip()
        if not c:
            return None
        if c.isdigit() and 1 <= int(c) <= len(pool):
            return pool[int(c) - 1]
        if kind == "homecoming":
            m = league.search(c)
            if m:
                return m[0]


def apply(league, coach, team, kind):
    """After take_job: set the stage for the story."""
    cp = _cp()
    st = cp.state(league)
    name, _blurb, chs = STARTS[kind]
    old = [n for y, n in getattr(team, "coach_log", []) if n != coach.name]
    pred = old[-1] if old else "the last coach"
    style, seat, chem, money = SETUP[kind]
    team.ad["style"] = style
    coach.seat = coach.seat_last = seat
    if chem:
        import personalities
        personalities._nudge(team, chem)
    if money:
        for y in (league.year, league.year + 1):
            team.__dict__.setdefault("income", []).append({"what": "the collective (story start)", "amount": money, "year": y + 1})
    if kind == "legend":
        team.__dict__["legend"] = pred
    if kind == "no_qb":
        import morale
        for p in list(team.players_at("QB"))[:1]:
            morale.nudge(p, -10, "the new staff says the job is open", league)
    rival = _rival(league, team)
    st["start"] = {"kind": kind, "title": name, "school": team.school, "year": league.year, "rival": rival,
                   "chapters": [{"title": t_, "goal": g_, "obj": list(o_), "by": league.year + by - 1, "status": "open",
                                 "when": None} for t_, g_, o_, by in chs]}
    text = INTRO.get(kind, "").format(school=team.school, pred=pred, rival=rival or "The rival")
    cp._log(league, (league.year, f"Story start: {name} at {team.school}."))
    cp._story(league, "story start", f"{name}: {text}")
    clear()
    print(title_bar(f"{name.upper()} · {team.school.upper()}", league.team_color(team)))
    print()
    for ln in textwrap.wrap(text, 90):
        print("   " + ln)
    import carousel as cz
    print(paint(f"\n   Your AD: {team.ad['name']} ({cz.AD_STYLES[team.ad['style']][0]}). Hot seat to start: {coach.seat}/100.", C.GRAY))
    print(section("YOUR CHAPTERS", C.BMAGENTA))
    for i, ch in enumerate(st["start"]["chapters"], 1):
        print(f"   {paint(f'{i}.', C.BMAGENTA, C.BOLD)} {paint(pad(ch['title'], 26), C.BWHITE, C.BOLD)}{pad(ch['goal'], 46)}"
              f"{paint('by ' + str(ch['by']), C.GRAY)}")
    print(paint("\n   Legacy (tab 6 → L) → [S] shows your story any time.", C.GRAY))
    pause()


# ═══ The chapters ═══════════════════════════════════════════════════════════

def _met(league, story, obj, rows, final_year):
    k = obj[0]
    if k == "power_job":
        return any(h.get("power") and h["year"] > story["year"] for h in _cp().state(league).get("hires", []))
    if k == "class":
        return any(c.get("rank") and c["rank"] <= obj[1] and story["year"] <= int(y) <= final_year
                   for y, c in _cp().state(league).get("classes", {}).items())
    if k == "chem":
        import personalities
        t = league.user_team
        return t is not None and t.school == story["school"] and personalities.chemistry(t) >= obj[1]
    rival = story.get("rival")
    for s in rows:
        if k == "wins" and s["w"] >= obj[1]:
            return True
        if k == "winning" and s["w"] > s["l"]:
            return True
        if k == "bowl" and (s.get("bowl") or s.get("cfp")):
            return True
        if k == "bowl_win" and (s.get("bowl_win") or s.get("cfp_win")):
            return True
        if k == "conf_title" and s.get("conf_champ"):
            return True
        if k == "playoff" and s.get("cfp"):
            return True
        if k == "playoff_win" and s.get("cfp_win"):
            return True
        if k == "title" and s.get("title"):
            return True
        if k == "rank" and s.get("final_rank") and s["final_rank"] <= obj[1]:
            return True
        if k == "rival_win" and rival and rival in s.get("beat", []):
            return True
    if k == "rival_wins" and rival:
        return sum(s.get("beat", []).count(rival) for s in rows) >= obj[1]
    return False


def season_end(league):
    cp = _cp()
    st = cp.state(league)
    story = st.get("start")
    if not story or not story.get("chapters") or story.get("closed"):
        return
    import cp_ach
    rows = [s for s in cp_ach.seasons(league, final=True) if s["school"] == story["school"] and s["year"] >= story["year"]]
    here = league.user_team is not None and league.user_team.school == story["school"]
    import ad_trust
    import effects
    for i, ch in enumerate(story["chapters"], 1):
        if ch["status"] != "open":
            continue
        obj = tuple(ch["obj"])
        if _met(league, story, obj, rows, league.year):
            ch["status"], ch["when"] = "done", league.year
            if here:
                effects.apply(league, {"seat": -6, "chem": 3}, f"story chapter: {ch['title']}")
                ad_trust.change(league, 5, f"chapter {i} of the story: {ch['title']}")
            cp._story(league, "chapter", f"Chapter {i} complete — {ch['title']}: {ch['goal'].lower()}.")
            cp._log(league, (league.year, f"Story chapter complete: {ch['title']}."))
        elif league.year >= ch["by"] or (not here and obj[0] != "power_job"):
            ch["status"], ch["when"] = "missed", league.year
            if here:
                ad_trust.change(league, -3, f"missed a chapter of the story: {ch['title']}")
            cp._story(league, "chapter", f"Chapter {i} missed — {ch['title']}"
                                         + ("" if here else f" (you left {story['school']})") + ".")
    if all(ch["status"] != "open" for ch in story["chapters"]):
        story["closed"] = league.year
        done = sum(ch["status"] == "done" for ch in story["chapters"])
        story["done"] = done == len(story["chapters"])
        ep = epilogue(story, done)
        story["epilogue"] = ep
        cp._story(league, "chapter", f"Epilogue — {story['title']}: {ep}")
        cp._log(league, (league.year, f"The story ends: {story['title']} ({done} of {len(story['chapters'])} chapters)."))


def epilogue(story, done):
    n = len(story["chapters"])
    sch = story["school"]
    if done == n:
        return f"Every chapter written. At {sch}, they'll tell this one for years."
    if done == n - 1:
        return f"Nearly all of it. {sch} got most of what it was promised."
    if done:
        return f"Some of it. The rest of {sch}'s story belongs to somebody else."
    return f"None of it went the way it was drawn up. {sch} moved on, and so did you."


def status_line(league):
    st = _cp().state(league)
    story = st.get("start")
    if not story:
        return ""
    chs = story.get("chapters") or []
    if not chs:
        return f"Story: {STARTS.get(story.get('kind'), ('Your story',))[0]} at {story.get('school')}."
    done = sum(ch["status"] == "done" for ch in chs)
    nxt = next((ch for ch in chs if ch["status"] == "open"), None)
    if nxt is None:
        return f"Story: {story['title']} — finished, {done} of {len(chs)} chapters."
    return f"Story: {story['title']} — {done}/{len(chs)} done · next: {nxt['goal'].lower()} by {nxt['by']}"


def screen(league):
    st = _cp().state(league)
    story = st.get("start")
    clear()
    if not story:
        print(title_bar("YOUR STORY"))
        print(paint("\n   You didn't start with a story. They're on the first-job screen ([S]) when you start a career.", C.GRAY))
        pause()
        return
    title = story.get("title") or STARTS.get(story.get("kind"), ("Your story",))[0]
    print(title_bar(f"{title.upper()} · {story['school'].upper()} · SINCE {story['year']}"))
    blurb = STARTS.get(story.get("kind"), ("", ""))[1]
    print(paint(f"\n   {blurb}", C.GRAY))
    chs = story.get("chapters") or []
    if chs:
        print(section("THE CHAPTERS", C.BMAGENTA))
        for i, ch in enumerate(chs, 1):
            mark = {"done": paint("✓ DONE", C.BGREEN, C.BOLD), "missed": paint("✕ MISSED", C.BRED, C.BOLD),
                    "open": paint("… OPEN", C.BYELLOW, C.BOLD)}[ch["status"]]
            left = ch["by"] - league.year
            when = (f"in {ch['when']}" if ch["when"] else
                    "this season" if left == 0 else f"{left + 1} seasons left" if left > 0 else "")
            print(clip(f"   {paint(f'{i}.', C.BMAGENTA, C.BOLD)} {paint(pad(ch['title'], 26), C.BWHITE, C.BOLD)}"
                       f"{pad(ch['goal'], 44)}{pad(mark, 10)}  {paint(when, C.GRAY)}", WIDTH))
    if story.get("epilogue"):
        print(section("EPILOGUE", C.BYELLOW))
        for ln in textwrap.wrap(story["epilogue"], 92):
            print("   " + ln)
    footer(key("Enter", "back", C.GRAY))
    ask("")
