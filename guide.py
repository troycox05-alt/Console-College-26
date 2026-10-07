"""
guide.py — The guided first week (Settings -> [G]; on by default).

The first time you open each screen in your first week — fall camp through your
first game's postgame report — somebody on your staff pulls you aside and tells
you what it's for and what to press. One card per screen, once. After the first
game (or the second week, in AD and spectator modes) the guide goes quiet.

    league.guide = {"start": year, "seen": [keys], "done": False}

guide.tip(league, key) is called at the top of a screen; it shows the card if the
guide is on and that card hasn't been seen. [G] on any card turns the guide off
(for good, in Settings); [Enter] carries on.
"""
from ui import C, ask, clear, paint, panel, title_bar

# key: (who, title, lines).  who: "oc", "dc", "ad", "ops" (director of operations), "sid"
TIPS = {
    "welcome": ("ops", "Welcome to the building", [
        "For your first week I'll pop in the first time you open something new, tell you what",
        "it's for, and get out of the way.",
        "",
        "This is the dashboard. Eight tabs across the top (press 1-8): HOME, SCHEDULE, TEAM,",
        "RECRUITING, RANKINGS, COACH, MEDIA, SYSTEM. Every key in [brackets] on a screen does",
        "something. [A] always moves the calendar forward: fall camp first, then Week 1.",
        "",
        "Three things to know on day one: your AD grades you against the goals on tab 6,",
        "recruiting never stops (tab 4), and [V] saves. Press [?] any time for the manual.",
    ]),
    "welcome_ad": ("ops", "Welcome to the director's chair", [
        "You run the department: the budget, the facilities, the coach's seat. The coach runs the team.",
        "[C] from any tab opens your office. [A] moves the calendar forward. [V] saves.",
        "I'll pop in the first time you open something new this week.",
    ]),
    "welcome_spectator": ("sid", "Welcome to the press box", [
        "You're watching the whole country. The dashboard follows one team (tab 3 or 6 -> [F] to switch).",
        "[A] plays the next week, [M] sims weeks or whole seasons, [B] opens the sportsbook.",
        "Tab 5 has the polls, the Golden Helmet race, the record book [R] and the Hall of Fame [F].",
    ]),
    "tab2": ("ops", "Schedule", [
        "Your season and everyone else's. [S] your full schedule and results, [W] every scoreboard",
        "in the country, [T] conference standings, [F] the weather: forecasts are real, and rain,",
        "wind, cold and altitude change games. Plan for them in practice.",
    ]),
    "tab3": ("oc", "Your team", [
        "[R] the roster (open any player for his card), [H] the depth chart, [P] the practice report:",
        "who's rising, who's hurt, position battles. [$] is the budget and NIL.",
        "You see players the way your staff sees them: words and grades, not exact numbers.",
    ]),
    "tab4": ("dc", "Recruiting", [
        "Next year's roster is being decided right now. [R] opens the hub. You get recruiting hours",
        "every week: spend them on the kids on your board, or set standing orders and let the staff work.",
        "Needs are listed on the left. A quarterback class matters more than a kicker class.",
    ]),
    "tab5": ("sid", "Rankings", [
        "The media poll [T], the playoff rankings [P] once the committee meets, the Golden Helmet race [H].",
        "[R] is the record book: every record since 2026, national and school by school.",
        "[F] is the Hall of Fame. Your program has its own, and you pick its classes.",
        "[O] ranks every schedule: who's played the hardest, and who has the hardest road left.",
    ]),
    "tab6": ("ad", "You, and what I expect", [
        "This is where you stand with me. The goals on the right are what I'll judge you on,",
        "and the hot seat moves every Saturday. [C] is your career, [T] your coaching tree",
        "(skill points from wins and milestones), [S] your staff, [I] your inbox.",
    ]),
    "tab7": ("sid", "Media", [
        "Headlines, the recruiting wire, the coaching carousel, and the compliance wire.",
        "What people say about you here feeds recruiting and your seat.",
    ]),
    "tab8": ("ops", "System", [
        "[V] save, [L] load, [S] settings (the guide lives there: [G] turns it on or off), [E] export",
        "everything to a spreadsheet, [H] the manual. The game autosaves every week.",
    ]),
    "fall_camp": ("oc", "Fall camp", [
        "Camp is your last chance to set things before it counts.",
        "[D] depth chart: the staff set one; move anybody you want. [C] the camp report: position battles",
        "and who's looked good. [S] your schedule: games marked • can still be changed.",
        "[I] your inbox has the first messages of the year. Answer them: replies have effects.",
        "When you're ready, Enter kicks off Week 1.",
    ]),
    "week_hub": ("oc", "The week", [
        "Every week before a game looks like this, Monday to Friday on one screen:",
        "  MONDAY film on the opponent  ·  TUESDAY [I] inbox  ·  WEDNESDAY [P] practice focus",
        "  THURSDAY [M] press conference (optional)  ·  FRIDAY [G] the game plan",
        "Each practice focus is a trade-off (more lift, more injury risk). [1]-[5] load a whole routine.",
        "Enter goes to Saturday with what's set, so a quick week is one keystroke.",
    ]),
    "practice": ("oc", "The practice report", [
        "Who's trending up and down, position battles, injuries and how long they'll be out.",
        "A backup who's passed a starter shows up here first. Act on it in the depth chart.",
    ]),
    "depth": ("oc", "The depth chart", [
        "Top of each position starts. Pick a player to move him; the staff flags moves they'd make.",
        "Playing time moves morale: a senior buried on the chart may look at the portal in December.",
    ]),
    "game_plan": ("dc", "Friday: the game plan", [
        "Pick one key on offense [O#] and one on defense [D#]. The film suggests what works against",
        "this opponent. [S] scripts your opening plays. [R] takes the staff's plan.",
        "After the game you'll see whether each key worked.",
    ]),
    "presser": ("sid", "The press conference", [
        "Two questions from the real week. Every answer has a tone: confident, measured, fiery or humble.",
        "Each has an upside and a cost (recruits, your players' mood, bulletin-board material).",
        "The line under each answer shows what it does (Settings can hide it).",
    ]),
    "inbox": ("ops", "Your inbox", [
        "Your AD, your players, recruits, staff. Most messages want an answer, and answers carry weight:",
        "form on Saturday, morale, recruiting interest, your standing with the AD.",
        "Unanswered messages get a default answer after a while. It's rarely the best one.",
    ]),
    "recruiting": ("dc", "The recruiting hub", [
        "[F] finds prospects, [G] suggests ones who fit you. [1] is your board: put kids on it, then spend",
        "hours on them (calls, visits, pitches that match what they want). [Q] standing orders let the",
        "staff spend hours for you every week. [V] official visits are the big closers.",
    ]),
    "board": ("dc", "Your board", [
        "Everyone you're recruiting, and where you stand with each. Spend hours on the ones you can",
        "actually get: a kid who's 90% to a rival isn't worth your whole week.",
    ]),
    "your_game": ("oc", "Saturday: your game", [
        "Pick how to play it. Sim it and watch the score; play the big moments (the staff calls it until",
        "a big spot, then it's you); coach every snap; or just watch the broadcast.",
        "Big moments is a good first game. At every quarter break you can change your mind.",
    ]),
    "report": ("ad", "The week's work", [
        "This is what your week was worth: the practice focus, the presser, your inbox answers,",
        "the game plan's keys, all in points on the scoreboard. It's how you learn what works.",
        "",
        "That's a week. From here I'll leave you to it. The guide can be turned back on",
        "for a new career in Settings -> [G]. Good luck, coach.",
    ]),
    "ad_office": ("ops", "Your office", [
        "The budget, facilities and the stadium, the coach's contract and seat, your boosters.",
        "Every week the desk brings decisions. The fans and the board react to results and to you.",
    ]),
    "career": ("ad", "Your career", [
        "Your record, your contract, your seat and my goals for you, season by season.",
        "Win, and other schools call in December. Lose, and I might.",
    ]),
}

SPEAKER_ROLE = {"oc": "offensive coordinator", "dc": "defensive coordinator", "ad": "athletic director",
                "ops": "director of operations", "sid": "sports information director"}


def enabled():
    import settings
    return settings.load().get("guided_week", True)


def start(league):
    """A new career (or AD run, or spectator world): the guide starts with it."""
    league.guide = {"start": league.year, "seen": [], "done": not enabled()}


def active(league):
    g = league.__dict__.get("guide")
    if not g or g.get("done") or not enabled():
        return False
    if league.year != g["start"] or league.week >= 2:
        g["done"] = True
        return False
    return True


def _speaker(league, who):
    team = getattr(league, "user_team", None)
    if team is None and getattr(league, "user_coach", None) is not None:
        team = league.user_coach.team
    name = None
    if team is not None:
        if who in ("oc", "dc") and getattr(team, who, None) is not None:
            name = getattr(team, who).name
        elif who == "ad" and getattr(team, "ad", None):
            name = team.ad.get("name")
    if name is None:
        import random
        from names import full_name
        name = full_name(random.Random(f"guide:{who}:{getattr(league, 'seed', 0)}"))
    return name, SPEAKER_ROLE[who]


def tip(league, key):
    """Show the card for this screen, once. Returns True if one was shown."""
    if league is None or not active(league):
        return False
    g = league.guide
    if key in g["seen"] or key not in TIPS:
        return False
    g["seen"].append(key)
    who, title, lines = TIPS[key]
    name, role = _speaker(league, who)
    clear()
    print(title_bar("YOUR FIRST WEEK", sub="GUIDE"))
    print()
    body = [paint(f"{name}, your {role}:", C.BCYAN, C.BOLD), ""] + [paint(ln, C.BWHITE) if ln else "" for ln in lines]
    for ln in panel(title.upper(), body, 104, color=C.BCYAN, title_color=C.BYELLOW):
        print(ln)
    c = ask("[Enter] got it   [G] turn the guide off:").strip().lower()
    if c == "g":
        g["done"] = True
        import settings
        settings.load()["guided_week"] = False
        settings.save()
        print(paint("\n   Guide off. Settings -> [G] turns it back on for your next career.", C.GRAY))
    if key == "report":
        g["done"] = True
    return True


def welcome_key(league):
    mode = getattr(league, "mode", None)
    return "welcome_ad" if mode == "ad" else "welcome_spectator" if mode == "spectator" else "welcome"


def migrate(league):
    """Older saves: no guide (you're past your first week)."""
    if "guide" not in league.__dict__:
        league.guide = {"start": league.year, "seen": [], "done": True}
