"""
career.py — You, as a head coach. Or nobody at all.

  choose_mode()     Coach Career or Spectator, right after the world is built
  create_coach()    name, age, background, schemes, fourth-down philosophy
  first_job()       real offers from the bottom rungs (or a sandbox dream job)
  offers()          every offseason: openings that want you, and teams that'd
                    fire their own coach to get you
  earn_traits()     reputations you earn from what your teams actually do
  career_screen()   your profile, your seat, your goals, your story

The carousel treats you like every other coach: your AD judges your seasons,
your seat heats up, and you can be fired. The only difference is that job
offers come to you as choices instead of being decided for you.
"""
import random

from ui import C, WIDTH, ask, clear, pad, paint, pause, rating, rule, section, stepper, title_bar, truncate

BACKGROUNDS = {
    "1": ("Offensive Coordinator", "Called plays at a big program. Quarterbacks love you.",
          {"passing_dev": 8, "offense_dev": 5, "recruiting": 2}, "schemer", "Spread RPO", "4-2-5 Quarters"),
    "2": ("Defensive Coordinator", "Built defenses that travel. Nobody out-physicals your teams.",
          {"db_dev": 8, "trench_dev": 5}, "disciplinarian", "Pro Style", "Pressure 3-4"),
    "3": ("Recruiting Coordinator", "You can walk into any living room in the country and win it.",
          {"recruiting": 12}, "salesman", "Spread RPO", "4-2-5 Quarters"),
    "4": ("Offensive Line Coach", "Your lines move people. Your teams run the ball when everybody knows it's coming.",
          {"trench_dev": 10, "offense_dev": 3}, "trench_guru", "Smashmouth", "4-3 Zone"),
    "5": ("High School Legend", "A shelf of state titles and a program everybody in the state knows. Players run through walls for you.",
          {"offense_dev": 4, "db_dev": 4, "recruiting": 4}, "motivator", "Power Spread", "3-3-5 Stack"),
    "6": ("Former Pro League Quarterback", "Everybody knows your name. You still have to prove you can coach.",
          {"passing_dev": 10, "recruiting": 6, "trench_dev": -4}, "qb_whisperer", "West Coast", "Multiple Man"),
}
PHILOSOPHY = {"1": ("Conservative", 30), "2": ("Balanced", 55), "3": ("Aggressive", 78)}
PHILOSOPHY_NOTES = {
    "1": "Punt it away and trust your defense. Fewer disasters, fewer comebacks. Best with a strong defense.",
    "2": "Go for it when the numbers say so — short yardage, plus territory. The sensible default.",
    "3": "Fourth-and-4 is a green light. Wins games you shouldn't — and loses some too.",
}

# A few words on each scheme for people who don't live on football message boards.
# (idea, what it needs, who it's like)
OFFENSE_NOTES = {
    "Air Raid": ("Spread the field with four receivers and throw it — quick, short passes that add up, "
                 "with deep shots when the defense creeps up.",
                 "An accurate QB and lots of receivers. Linemen pass-block more than they maul.",
                 "The pass-happy programs out on the High Plains."),
    "Spread RPO": ("Spread out, then let the QB read one defender and hand off, keep it, or throw — "
                   "run-pass options put a linebacker in a bind on every snap.",
                   "A quick-thinking QB who can run a little, and a running back who hits the hole.",
                   "The modern college default — most of the top programs live here."),
    "Pro Style": ("The pro look: tight ends, sometimes a fullback, a real run game that sets up play-action.",
                  "A pocket QB, a tight end who can block and catch, and big linemen.",
                  "Old-school powers that win at the line of scrimmage."),
    "West Coast": ("Short, timed throws used almost like runs — get the ball to playmakers in space "
                   "and move the chains.",
                   "A smart, accurate QB and receivers and backs who are good after the catch.",
                   "Lots of pro-influenced college staffs."),
    "Smashmouth": ("Line up with extra blockers and run it down their throat. Play-action when they "
                   "load the box. Shortens the game.",
                   "Big offensive linemen, tight ends, and a bruising running back. Receivers matter less.",
                   "Classic cold-weather Midwest football."),
    "Triple Option": ("The QB reads two defenders on every run — hand off, keep, or pitch. Very hard to "
                      "prepare for; rarely throws.",
                      "A tough QB who runs, disciplined linemen, and backs who hold onto the ball. "
                      "Receivers barely matter (and won't want to come).",
                      "The service academies and a few stubborn programs."),
    "Power Spread": ("Spread formations with gap-scheme power runs and a running QB — "
                     "physical, but with space to work.",
                     "A big dual-threat QB, strong linemen, and a tight end who blocks.",
                     "The dual-threat powers of the 2000s and 2010s."),
    "Veer & Shoot": ("Go fast and go vertical — receivers read the coverage and adjust routes on the fly. "
                     "The fastest tempo in the game.",
                     "A QB with a big arm and fast receivers who read defenses. Gets you more possessions.",
                     "The run-and-shoot family tree, still alive in Texas."),
}
DEFENSE_COMPS = {
    "4-3 Zone": "The classic sound defense — a generation of Midwest and Southern teams.",
    "4-2-5 Quarters": "The defense built in Texas to stop the spread.",
    "Pressure 3-4": "The zone-blitz 3-4 of the pros; blitz-happy college staffs everywhere.",
    "3-3-5 Stack": "The odd stack — undersized, fast, and always moving.",
    "Multiple Man": "The modern powerhouse look — press corners and match-up coverage.",
    "Tite Front": "The Plains' answer to spread-to-run offenses.",
}
# Why a background points at a defense.
DEFENSE_REASON = {
    "4-3 Zone": "it pairs with a run-first offense: stay sound, tackle, and don't give up anything cheap",
    "4-2-5 Quarters": "it's built to stop the spread offenses you'll see every week",
    "Pressure 3-4": "it's how defensive minds make their name: pressure, sacks, and turnovers",
    "3-3-5 Stack": "it wins with speed and effort — the kind of players who run through walls for you",
    "Multiple Man": "it takes away the easy throws you spent your career making",
}
PRESSURE_CALLS = {"Fire Zone", "Cover 0 Blitz", "Run Blitz", "Nickel Blitz", "Sim Pressure"}
MAN_CALLS = {"Cover 1 Man", "Cover 2 Man", "Cover 0 Blitz", "Cover 1 Robber", "Bracket"}
BLITZ = {"1": ("Sit in coverage", 25), "2": ("Pick your spots", 50), "3": ("Bring it", 75)}
BLITZ_NOTES = {
    "1": "Rush four, keep everyone else in coverage. Few sacks, few big plays allowed.",
    "2": "Pressure on obvious passing downs and when it's working. The sensible default.",
    "3": "Send five and six all game. More sacks and turnovers — and more busted coverages.",
}


def _defense_stats(calls):
    """A defense's call sheet in two numbers: how often it sends pressure, and how often it plays man."""
    total = sum(calls.values()) or 1
    press = sum(v for k, v in calls.items() if k in PRESSURE_CALLS) / total
    man = sum(v for k, v in calls.items() if k in MAN_CALLS) / total
    return f"pressure {press * 100:.0f}% of snaps · {'man' if man >= 0.5 else 'zone'}-first ({man * 100:.0f}% man)"


DEFENSE_NOTES = {
    "4-3 Zone": ("Four linemen, three linebackers, and zone coverage — the balanced, textbook defense. "
                 "Rarely beats itself.",
                 "Good linemen and linebackers who tackle. Corners don't have to be superstars."),
    "4-2-5 Quarters": ("A fifth defensive back instead of a linebacker, with safeties who both cover and "
                       "come up to stop the run. Built for spread offenses.",
                       "Smart, physical safeties and corners who can cover. Undersized is fine."),
    "Pressure 3-4": ("Three linemen, four linebackers, and blitzes from everywhere. Creates sacks and "
                     "turnovers — and gives up big plays when it misses.",
                     "Big linemen who eat blockers and athletic linebackers who rush the passer."),
    "3-3-5 Stack": ("Three down linemen and eight players moving around behind them. Disguise and "
                    "confusion; hard to block.",
                    "Fast linebackers and safeties. Doesn't need a lot of 300-pounders."),
    "Multiple Man": ("Lock the corners on receivers man-to-man and bring pressure. Takes away easy "
                     "throws — if your corners can hold up.",
                     "Great cornerbacks, first and foremost. Without them, it's a big-play machine."),
    "Tite Front": ("Three linemen squeezed inside to clog the run, with coverage behind that changes "
                   "after the snap. The modern answer to spread-to-run teams.",
                   "Stout interior linemen and rangy safeties."),
}


def _tempo_word(sec):
    return "up-tempo" if sec <= 22 else "moderate tempo" if sec <= 29 else "methodical, clock-eating"


def _fit_line(table):
    """Which positions a scheme makes easier (and harder) to recruit."""
    up = [p for p, v in sorted(table.items(), key=lambda x: -x[1]) if v >= 6]
    down = [p for p, v in sorted(table.items(), key=lambda x: x[1]) if v <= -4]
    bits = []
    if up:
        bits.append("recruits want to play " + "/".join(up) + " here")
    if down:
        bits.append("harder sell to " + "/".join(down))
    return "; ".join(bits)


# ═══ Mode ═══════════════════════════════════════════════════════════════════

MODES = (
    ("1", "career", "COACH CAREER", C.BGREEN,
     "Build your own head coach, take a job at the bottom of the sport, recruit, call plays — and try "
     "not to get fired.",
     ["The headset on Saturdays", "Recruiting and the portal", "Your AD and your hot seat"]),
    ("2", "spectator", "SPECTATOR", C.BCYAN,
     "Control nothing. Watch the whole sport run itself for as long as you like — and bet on it at "
     "The Window.",
     ["Every game, every carousel", "The Window: a sportsbook", "Sim a hundred years"]),
    ("3", "ad", "ATHLETIC DIRECTOR", C.BMAGENTA,
     "Run a program from the top: hire and fire the coach, write his contract, build, price the "
     "tickets. The board grades you.",
     ["Coaching searches", "Facilities, the stadium", "Fans, boosters, budget"]),
)


def pick_mode():
    """New Game: how do you want to play? Returns 'career' | 'ad' | 'spectator' | 'commissioner',
    or None (back)."""
    import textwrap
    from ui import panel, columns, footer, key, back_key
    while True:
        clear()
        print(title_bar("NEW GAME · HOW DO YOU WANT TO PLAY?", sub="NEW GAME"))
        print()
        cards = []
        for k, _, name, col, blurb, bullets in MODES:
            lines = [paint(x, C.BWHITE) for x in textwrap.wrap(blurb, 28)]
            lines += [""] * (5 - len(lines))
            lines += [""] + [paint("› ", col) + paint(b, C.GRAY) for b in bullets]
            lines += ["", paint(f"[{k}]", col, C.BOLD) + paint(" choose", C.BWHITE)]
            cards.append(panel(name, lines, 32, color=col, title_color=col, height=11))
        for ln in columns(*cards, gap=2):
            print(ln)
        print()
        print(paint("   [4] COMMISSIONER", C.BYELLOW, C.BOLD)
              + paint("   Run a Discord league: members coach programs, you import their orders.", C.BWHITE))
        print(paint("       No coach of your own. You run the world from the Commissioner Desk.", C.GRAY))
        print()
        print(paint("   You can switch later: a coach can retire into Spectator, and every mode shares one world.",
                    "\033[38;5;244m"))
        footer(key("1-4", "choose", C.BGREEN), back_key("Main menu"))
        c = ask("Select:").strip().lower()
        if c in ("b", "back", "q"):
            return None
        if c in ("4", "5", "commissioner", "commish"):
            return "commissioner"
        for k, mode, *_ in MODES:
            if c == k:
                return mode



def customize_universe():
    """New-game per-save simulation rules. Returns a complete rules dict, or None to go back."""
    import world_rules
    from ui import footer, key, back_key
    rules = world_rules.normalize()
    preset = "balanced"
    while True:
        clear()
        print(title_bar("NEW GAME · CUSTOMIZE YOUR UNIVERSE", sub="WORLD RULES"))
        print(paint("\n   These choices belong to this save only. Toggle any system, or start from a preset.\n", C.GRAY))
        for i, k in enumerate(world_rules.DEFAULTS, 1):
            name, desc = world_rules.LABELS[k]
            state = paint("ON ", C.BGREEN, C.BOLD) if rules[k] else paint("OFF", C.BRED, C.BOLD)
            hotkey = "0" if i == 10 else str(i)
            print(f"   {paint(f'[{hotkey}]', C.BYELLOW, C.BOLD)} {name:<28} {state}   {paint(desc, C.GRAY)}")
        print()
        print(paint("   [A] Balanced", C.BGREEN, C.BOLD) + paint("   [C] Chaos / everything on   [S] Stable world   [Enter] continue", C.BWHITE))
        print(paint("   Stable keeps the football systems but removes most off-field churn.", C.GRAY))
        footer(key("1-0", "toggle"), key("Enter", "continue", C.BGREEN), back_key("mode select"))
        c = ask("Select:").strip().lower()
        if c in ("back", "q"):
            return None
        if c == "":
            return world_rules.normalize(rules)
        if c in ("a", "c", "s"):
            preset = {"a":"balanced", "c":"chaos", "s":"stable"}[c]
            rules = dict(world_rules.PRESETS[preset]); continue
        if c.isdigit():
            n=int(c); keys=list(world_rules.DEFAULTS)
            # 0 is the tenth toggle for compact keyboard navigation.
            idx = 9 if n == 0 else n-1
            if 0 <= idx < len(keys):
                k=keys[idx]; rules[k]=not rules[k]

def start_mode(league, mode):
    """After the world is built: set up the mode you picked."""
    if mode == "ad":
        import ad_mode
        ad_mode.start(league)
        return
    if mode == "career":
        coach = create_coach(league)
        if coach is not None:
            first_job(league, coach)
            return
    if mode == "commissioner":
        import commissioner
        commissioner.start(league)
        return
    league.mode = "spectator"
    league.user_team = None
    league.user_coach = None
    choose_follow(league)


def choose_mode(league):
    """Pick a mode for a world that's already built (older entry point)."""
    start_mode(league, pick_mode() or "spectator")


def choose_follow(league):
    """Spectator mode: whose season fills the dashboard. Changeable any time (tab 3 or 6 → [F])."""
    top = league.rankings.order[0] if league.rankings.order else league.teams[0]
    clear()
    print(title_bar("WHO DO YOU FOLLOW?"))
    print(paint("\n   The dashboard, the game previews and the week's headlines center on one team.", C.GRAY))
    print(paint(f"   Type a school or nickname, or press Enter for the preseason No. 1 ({top.school}).", C.GRAY))
    print(paint("   You can switch any time from tab 3 TEAM or tab 6 COACH → [F].", C.GRAY))
    from screens import pick_team
    t = pick_team(league)
    league.follow_team = t or top


# ═══ Building your coach ════════════════════════════════════════════════════

def create_coach(league):
    from league import make_coach
    from models import Team
    from traits import COACH_TRAITS
    import carousel as cz
    clear()
    print(title_bar("NEW CAREER · YOUR COACH", sub=stepper(1, 8, "NEW CAREER")))
    print(paint("\n   Who's taking the job? Enter takes the suggestion at every step of this.\n", C.GRAY))
    first = ask("First name:").strip().title() or "Chris"
    last = ask("Last name:").strip().title() or "Walker"
    age = ask("Age (30-60, Enter for 38):").strip()
    age = int(age) if age.isdigit() and 30 <= int(age) <= 60 else 38
    clear()
    print(title_bar(f"COACH {last.upper()} · BACKGROUND", sub=stepper(2, 8, "NEW CAREER")))
    for k, (label, blurb, tilt, trait, off, dfn) in BACKGROUNDS.items():
        print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)}  {paint(label, C.BWHITE, C.BOLD)}  "
              f"{paint('— starts with ' + COACH_TRAITS[trait][0], C.BCYAN)}")
        print(paint(f"        {blurb}", C.GRAY))
    bg = ask("Background:").strip()
    bg = bg if bg in BACKGROUNDS else "1"
    label, blurb, tilt, trait, off_default, def_default = BACKGROUNDS[bg]
    note = _age_note(bg, age)
    if note:
        print(paint(f"\n   {note}", C.BCYAN))
        pause()

    import playbook as pb
    clear()
    print(title_bar("YOUR SCHEMES · OFFENSE", sub=stepper(3, 8, "NEW CAREER")))
    offs = list(pb.OFFENSE_SCHEMES)
    defs = list(pb.DEFENSE_SCHEMES)
    from recruiting import OFF_SCHEME_FIT, DEF_SCHEME_FIT
    import textwrap

    def block(text, color=C.GRAY):
        for ln in textwrap.wrap(text, 86):
            print(paint("        " + ln, color))

    print(paint("   Your offense decides the plays you call, how fast you play, and which recruits want you.", C.GRAY))
    print(paint(f"   Your background suggests {off_default}. Nothing locks you in — any scheme can win.", C.GRAY))
    print()
    print(paint(f"   {'':4}{'SCHEME':<15}{'RUN RATE':<10}{'TEMPO':<26}{'RECRUITS WANT':<15}HARDER SELL", C.GRAY, C.BOLD))
    for i, name in enumerate(offs, 1):
        spec = pb.OFFENSE_SCHEMES[name]
        want = [p for p, v in sorted(OFF_SCHEME_FIT.get(name, {}).items(), key=lambda x: -x[1]) if v >= 6]
        hard = [p for p, v in sorted(OFF_SCHEME_FIT.get(name, {}).items(), key=lambda x: x[1]) if v <= -4]
        rr = f"{spec['run'] * 100:.0f}%"
        print(f"   {paint(f'{i:>2}', C.BYELLOW, C.BOLD)}  {pad(name, 15)}{pad(rr, 10)}"
              f"{pad(_tempo_word(spec['tempo']), 26)}{pad(paint('/'.join(want) or '—', C.BCYAN), 15)}"
              f"{paint('/'.join(hard) or '—', C.BYELLOW)}")
    print()
    for i, name in enumerate(offs, 1):
        idea, needs, like = OFFENSE_NOTES.get(name, ("", "", ""))
        spec = pb.OFFENSE_SCHEMES[name]
        stats = f"run rate {spec['run'] * 100:.0f}% · {_tempo_word(spec['tempo'])}"
        mark = paint("  ← suggested", C.BCYAN) if name == off_default else ""
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(name, C.BWHITE, C.BOLD)}   {paint(stats, C.BCYAN)}{mark}")
        block(idea, C.BWHITE)
        block("Needs: " + needs)
        fit = _fit_line(OFF_SCHEME_FIT.get(name, {}))
        block((like + (" " if like else "")) + (fit[0].upper() + fit[1:] + "." if fit else ""))
    o = ask(f"Offense (Enter for {off_default}):").strip()
    off_s = offs[int(o) - 1] if o.isdigit() and 1 <= int(o) <= len(offs) else off_default
    clear()
    print(title_bar("YOUR SCHEMES · DEFENSE", sub=stepper(4, 8, "NEW CAREER")))
    print(paint(f"   Offense: {off_s}. Now the defense — it decides your coverages and which defensive recruits", C.GRAY))
    reason = DEFENSE_REASON.get(def_default)
    for ln in textwrap.wrap(f"you win. Your background suggests {def_default}" + (f" — {reason}." if reason else "."), 92):
        print(paint("   " + ln, C.GRAY))
    print()
    print(paint(f"   {'':4}{'SCHEME':<16}{'PRESSURE':<10}{'COVERAGE':<20}{'RECRUITS WANT':<15}HARDER SELL", C.GRAY, C.BOLD))
    for i, name in enumerate(defs, 1):
        calls = pb.DEFENSE_SCHEMES[name]
        total = sum(calls.values()) or 1
        press = sum(v for k, v in calls.items() if k in PRESSURE_CALLS) / total
        man = sum(v for k, v in calls.items() if k in MAN_CALLS) / total
        table = DEF_SCHEME_FIT.get(name, {})
        want = [p for p, v in sorted(table.items(), key=lambda x: -x[1]) if v >= 6]
        hard = [p for p, v in sorted(table.items(), key=lambda x: x[1]) if v <= -2]
        cov = f"{'man' if man >= 0.5 else 'zone'}-first ({man * 100:.0f}% man)"
        print(f"   {paint(f'{i:>2}', C.BYELLOW, C.BOLD)}  {pad(name, 16)}{pad(f'{press * 100:.0f}%', 10)}{pad(cov, 20)}"
              f"{pad(paint('/'.join(want) or '—', C.BCYAN), 15)}{paint('/'.join(hard) or '—', C.BYELLOW)}")
    print()
    for i, name in enumerate(defs, 1):
        idea, needs = DEFENSE_NOTES.get(name, ("", ""))
        mark = paint("  ← suggested", C.BCYAN) if name == def_default else ""
        stats = _defense_stats(pb.DEFENSE_SCHEMES[name])
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {paint(name, C.BWHITE, C.BOLD)}   {paint(stats, C.BCYAN)}{mark}")
        block(idea, C.BWHITE)
        table = DEF_SCHEME_FIT.get(name, {})
        fit = _fit_line(table)
        flat = [p for p in ("DL", "LB", "CB", "S") if table.get(p, 0) == 0]
        hard = [p for p in ("DL", "LB", "CB", "S") if table.get(p, 0) < 0]
        tail = (" " + fit[0].upper() + fit[1:] + "." if fit else "") + \
            (f" Harder sell to {'/'.join(hard)}." if hard else "") + \
            (f" Neutral at {'/'.join(flat)} (no edge, no penalty)." if flat else "")
        block("Needs: " + needs + tail)
        comp = DEFENSE_COMPS.get(name)
        if comp:
            block(comp)
    d = ask(f"Defense (Enter for {def_default}):").strip()
    def_s = defs[int(d) - 1] if d.isdigit() and 1 <= int(d) <= len(defs) else def_default
    clear()
    print(title_bar("YOUR SCHEMES · FOURTH DOWN & BLITZ", sub=stepper(5, 8, "NEW CAREER")))
    print(paint(f"   {off_s} offense, {def_s} defense. Two last calls: fourth down, and how often you blitz.", C.GRAY))
    print()
    for k, (name, _) in PHILOSOPHY.items():
        print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)} {paint(name, C.BWHITE, C.BOLD)}")
        block(PHILOSOPHY_NOTES[k])
    print(paint("\n   In the game you can overrule any fourth-down call yourself — this is what your staff does\n"
                "   when they have the headset.", C.GRAY))
    ph = ask("Fourth down (Enter for Balanced):").strip()
    aggr = PHILOSOPHY.get(ph, PHILOSOPHY["2"])[1]
    print()
    print(section("BLITZ"))
    print(paint(f"   How often your {def_s} sends extra rushers, on top of what the scheme already calls.", C.GRAY))
    dcalls = pb.DEFENSE_SCHEMES[def_s]
    base_press = sum(v for kk, v in dcalls.items() if kk in PRESSURE_CALLS) / (sum(dcalls.values()) or 1)
    for k, (name, lvl) in BLITZ.items():
        est = min(0.95, base_press * (0.5 + lvl / 100))
        print(f"   {paint(f'[{k}]', C.BYELLOW, C.BOLD)} {paint(name, C.BWHITE, C.BOLD)}   "
              f"{paint(f'pressure on about {est * 100:.0f}% of snaps', C.BCYAN)}")
        block(BLITZ_NOTES[k])
    bz = ask("Blitz (Enter for Pick your spots):").strip()
    blitz_level = BLITZ.get(bz, BLITZ["2"])[1]

    shell = Team("—", "—", "—", 0, "—", None, "", {k: 60 for k in Team.RATING_KEYS})
    shell.ratings["coach"] = 60
    coach = make_coach(f"{first} {last}", shell)
    for k in coach.ratings:                 # a level start, so your background is what sets you apart
        coach.ratings[k] = 55
    for k, v in tilt.items():
        coach.ratings[k] = int(max(35, min(90, coach.ratings[k] + v)))
    coach.overall = 60
    coach.offense_scheme, coach.defense_scheme, coach.aggression = off_s, def_s, aggr
    coach.blitz = blitz_level
    coach.team = None
    coach.traits = [trait]
    cz.init_coach(coach, league.year, origin=f"{label} (you)")
    coach.age = age
    coach.ceiling = 96                      # you can become anything — if you win
    coach.personality = "builder"
    coach.retire_age = 99                   # you decide when you're done
    coach.is_user = True
    coach.background = label
    import difficulty
    coach.difficulty = difficulty.choose(sub=stepper(6, 8, "NEW CAREER"))
    import coach_prestige
    coach.prestige_start = coach_prestige.choose(sub=stepper(7, 8, "NEW CAREER"))
    league.mode = "career"
    league.user_coach = coach
    league.user_offer_hook = offer_prompt
    import portal_screens
    league.portal_hook = portal_screens.portal_window
    league.career_log = [(league.year, f"Began a head coaching career. Background: {label}. "
                                       f"Reputation: {coach_prestige.level(coach)['name']}.")]
    return coach


def _age_note(bg, age):
    """A line of story when your age and your background say something together."""
    young, old = age <= 36, age >= 50
    notes = {
        "1": ("The youngest play-caller in the conference last year. Now the whole headset is yours.",
              "Twenty-some years of calling plays for other men. Finally, your name on the door."),
        "2": ("A defensive wunderkind. Every AD asks if you're ready. You are.",
              "Your defenses have been beating head coaches for decades. Time to be one."),
        "3": ("You've been in more living rooms than most coaches twice your age.",
              "You know every high school coach in three states — and their fathers."),
        "4": ("A line coach this young getting a head job? Your linemen would run through a wall to prove it right.",
              "A lifetime in the trenches. Somebody finally noticed who built those lines."),
        "5": ("A young high school legend: you won fast, and you won everywhere.",
              "Decades of Friday nights. Plenty of people said you'd never get a college job."),
        "6": ("A couple of years removed from your last snap. The players still have your jersey.",
              "Twenty years out of the league. The kids know your name from their fathers."),
    }
    pair = notes.get(bg)
    if not pair:
        return ""
    return pair[0] if young else pair[1] if old else ""


# ═══ Getting a job ══════════════════════════════════════════════════════════

def first_job(league, coach):
    rng = random.Random(f"firstjob:{coach.name}:{league.seed}")
    import coach_prestige as cp
    pool = cp.offer_pool(league, coach)                  # who calls depends on how big a name you are
    offers = rng.sample(pool, 4)
    import carousel as _cz
    for t in offers:
        _cz.refresh_roster_goals(t)
    import finance as fi
    deals = {t.school: fi.hc_offer(league, t, coach, rng) for t in offers}
    def detail(i):
        t = offers[i]
        import carousel as cz
        clear()
        print(title_bar(f"OFFER {i + 1} OF 4 · {t.full_name.upper()}", sub=stepper(8, 8, "NEW CAREER")))
        print()
        print(f"   {paint(t.full_name, C.BWHITE, C.BOLD)}   {paint(t.conference, league.conference_color(t.conference))}   "
              f"prestige {rating(round(t.prestige))}   roster {__import__('scout').team(t.team_ovr)}   "
              f"{paint('AD: ' + cz.AD_STYLES[t.ad['style']][0], C.GRAY)}")
        print()
        _goal_lines(t)
        print()
        offer_line(league, t, deals[t.school])
        from ui import footer, key, back_key
        footer(key(str(i + 1), "take this job", C.BGREEN), key(f"N{i + 1}", "negotiate (risky)"), back_key("All offers"))

    while True:
        clear()
        print(title_bar("YOUR FIRST HEAD COACHING JOB", sub=stepper(8, 8, "NEW CAREER")))
        print(paint("\n   " + FIRST_JOB_INTRO[cp.key_of(coach)] + " Every dollar\n"
                    "   you take is a dollar that doesn't go to your players' NIL — and what you earn pays for your own\n"
                    "   development as a coach.", C.GRAY))
        print()
        import carousel as cz
        print(paint(f"   {'':5}{'PROGRAM':<26}{'CONFERENCE':<16}{'PRESTIGE':<9}{'ROSTER':<14}{'CONTRACT':<17}NIL/YR",
                    "\033[38;5;244m", C.BOLD))
        from ui import rule as _rule
        print("   " + _rule(width=96))
        for i, t in enumerate(offers, 1):
            d = deals[t.school]
            if d.get("pulled"):
                terms, nil = paint("offer pulled", C.BRED), ""
            else:
                terms = paint(f"{d['years']} yr{'s' if d['years'] != 1 else ''} · {fi.money(d['salary'])}", C.BGREEN, C.BOLD)
                nil = paint(fi.money(fi.nil_left_with(league, t, d["salary"])), C.BWHITE)
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)}  {pad(paint(truncate(t.full_name, 25), C.BWHITE, C.BOLD), 26)}"
                  f"{pad(paint(truncate(t.conference, 15), league.conference_color(t.conference)), 16)}"
                  f"{pad(rating(round(t.prestige)), 9)}{pad(__import__('scout').team(t.team_ovr), 14)}"
                  f"{pad(terms, 17)}{nil}")
            print(paint(truncate(f"        {cz.AD_STYLES[t.ad['style']][0]} AD · goals: " +
                                 " · ".join(g.short for g in t.goals), 99), "\033[38;5;244m"))
        from ui import footer, key
        footer(key("V#", "the full offer (goals, every clause)"), key("#", "take the job", C.BGREEN),
               key("N#", "negotiate (risky)"), key("D", "dream job — any program (sandbox)"),
               key("S", "a story start: The Rebuild, The Hot Seat, Replace a Legend", C.BCYAN))
        choice = ask("Take which job?").strip().lower()
        if choice.startswith("v") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= 4:
            detail(int(choice[1:]) - 1)
            nxt = ask("Select:").strip().lower()
            if nxt == choice[1:] or nxt.startswith("n"):
                choice = nxt
            else:
                continue
        if choice.isdigit() and 1 <= int(choice) <= 4:
            team = offers[int(choice) - 1]
            offer = deals[team.school]
            if offer.get("pulled"):
                print(paint(f"   {team.school} pulled that offer.", C.BRED))
                pause()
                continue
            if ask(f"Sign with {team.school}: {fi.terms(offer)}? (y/n)").lower() in ("y", "yes"):
                break
        elif choice.startswith("n") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= 4:
            t = offers[int(choice[1:]) - 1]
            signed = False
            while True:
                deals[t.school] = negotiate(league, t, deals[t.school], coach)
                if deals[t.school].get("pulled"):
                    break
                nxt = ask(f"{t.school}: [A] accept {fi.terms(deals[t.school], total=False)}   [N] ask again   "
                          f"(Enter = back to the jobs)").strip().lower()
                if nxt == "a":
                    team, offer, signed = t, deals[t.school], True
                    break
                if nxt != "n":
                    break
            if signed:
                break
            if all(d.get("pulled") for d in deals.values()):
                print(paint("   Every AD walked away. There's still the dream job — or a new world.", C.BRED))
                pause()
        elif choice == "s":
            import career_plus
            t, kind = career_plus.story_start(league, coach, rng)
            if t is not None:
                offer = fi.hc_offer(league, t, coach, rng)
                take_job(league, coach, t, first=True, offer=offer)
                career_plus.apply_start(league, coach, t, kind)
                return
        elif choice == "d":
            from screens import pick_team
            team = pick_team(league)
            if team:
                offer = fi.hc_offer(league, team, coach, rng)
                clear()
                print(title_bar(f"DREAM JOB  ·  {team.school.upper()}"))
                print()
                offer_line(league, team, offer, indent="   ")
                print()
                if ask("Sign it? (y/n)").lower() in ("y", "yes"):
                    break
    take_job(league, coach, team, first=True, offer=offer)


FIRST_JOB_INTRO = {
    "unknown": "Four athletic directors called. Nobody hands a first-time head coach a blue blood.",
    "rising": "Four athletic directors called. Your name's been going around, and they want in early.",
    "established": "Four athletic directors called. Power 4 schools, and every one of them has done its homework.",
    "elite": "Four athletic directors called. Blue bloods. They want the headline, and they'll want the rings.",
}


def _goal_lines(t):
    """Offer cards: every goal with how often it's asked for, and how the AD watches — wrapped, never cut."""
    import textwrap
    import carousel as cz
    for i, ln in enumerate(textwrap.wrap("Goals: " + "  ·  ".join(g.compact for g in t.goals), 90)):
        print(paint("        " + ("" if i == 0 else "       ") + ln, C.GRAY))
    print(paint("        " + cz.ad_judging(t, short=True), C.GRAY))


def offer_line(league, team, offer, indent="        ", mine=None):
    """One contract offer: the terms, every clause, and what it leaves for NIL."""
    import finance as fi
    style = team.ad.get("style", "conference")
    if offer.get("pulled"):
        print(f"{indent}{paint('OFFER PULLED — the AD walked away from the table.', C.BRED, C.BOLD)}")
        return
    tag = ""
    if offer.get("counters"):
        tag = paint(f"  ({offer['counters']} ask{'s' if offer['counters'] != 1 else ''} so far"
                    + (f", seat starts +{offer['pressure']}" if offer.get("pressure", 0) > 0 else "") + ")", C.BCYAN)
    print(f"{indent}{paint('Contract', C.GRAY)}  {paint(fi.terms(offer), C.BGREEN, C.BOLD)}{tag}")
    for line in fi.clause_lines(offer):
        print(paint(f"{indent}          {line}", C.GRAY))
    fee = fi.release_fee(mine, league) if mine is not None and fi.contract(mine) else 0
    extra = f" (after paying your {fi.money(fee)} release)" if fee else ""
    print(paint(f"{indent}          budget {fi.money(fi.budget(team))}/yr · after operations, staff and you: "
                f"{fi.money(fi.nil_left_with(league, team, offer['salary']) - fee)}/yr for player NIL{extra}", C.GRAY))
    print(paint(f"{indent}          this AD: {fi.AD_CONTRACT[style]['blurb']} · {fi.patience_word(team)} patience", C.GRAY))


NEG_KEYS = {"1": "money10", "2": "money20", "3": "years", "4": "guarantee", "5": "release", "6": "offset",
            "7": "incentives"}


def _ask_detail(want, offer):
    """What an ask would change, before → after, so you know what you're asking for."""
    import finance as fi
    sal, yrs = offer["salary"], offer["years"]
    if want == "money10":
        return f"{fi.money(sal, exact=True)} → {fi.money(sal * 1.10, exact=True)}"
    if want == "money20":
        return f"{fi.money(sal, exact=True)} → {fi.money(sal * 1.20, exact=True)}"
    if want == "years":
        return f"{yrs} → {min(8, yrs + 1)}-{min(8, yrs + 2)} yrs (his call)" if yrs < 8 else "already at 8"
    if want == "guarantee":
        b = offer.get("buyout", 0.6)
        return f"{b * 100:.0f}% → {min(0.95, b + 0.15) * 100:.0f}%"
    if want == "release":
        r = offer.get("release", 0.4)
        return f"{r * 100:.0f}% → {r * 50:.0f}% a year"
    if want == "offset":
        return "offset → none" if offer.get("offset") else "there isn't one"
    if want == "incentives":
        return f"base -15%, bonuses ~2x"
    return ""


REFUSALS = {
    "money10": "That number is what the budget has, Coach.",
    "money20": "That number is what the budget has, Coach.",
    "years": "{years} years is what the board approved. That's the offer.",
    "guarantee": "I'm not guaranteeing more than I have to for a first-time head coach.",
    "release": "If you leave early, somebody's going to pay for it.",
    "offset": "If somebody else hires you, they can pay you.",
    "incentives": "Let's keep it simple.",
}


def negotiate(league, team, offer, coach, n_offers=1, extension=False):
    """Counter as many times as you dare. Returns the offer now on the table
    (marked "pulled" if the AD walked away)."""
    import finance as fi
    if offer.get("pulled"):
        print(paint(f"   {team.school}'s AD isn't taking your calls.", C.BRED))
        pause()
        return offer
    print(paint(f"   AD {team.ad['name']} has {fi.patience_word(team)} patience. Every ask risks him walking away —"
                f" more so the harder you push and the longer it goes.", C.GRAY))
    print(paint("   Whatever he gives you, he remembers: your seat starts warmer by what you squeezed out of him.",
                C.GRAY))
    asked = offer.get("counters", 0)
    if asked:
        print(paint(f"   You've asked {asked} time{'s' if asked != 1 else ''} already — every ask from here is riskier."
                    + (f" Seat so far: +{offer['pressure']}." if offer.get("pressure") else ""), C.BYELLOW))
    for key, want in NEG_KEYS.items():
        label, aggr, pressure = fi.ASKS[want]
        risk = "low" if aggr <= 0.05 else "medium" if aggr <= 0.1 else "high"
        seat = f"seat {pressure:+d}" if pressure else ""
        detail = _ask_detail(want, offer)
        print(f"   {paint(f'[{key}]', C.BYELLOW)} {pad(label, 28)}{pad(paint(detail, C.BWHITE), 30)}"
              f"{paint(f'risk {risk:<7}{seat}', C.GRAY)}")
    want = NEG_KEYS.get(ask("Ask for (Enter = never mind):").strip().lower())
    if want is None:
        return offer
    rng = random.Random(f"counter:{team.school}:{coach.name}:{league.year}:{want}:{offer.get('counters', 0)}")
    new, outcome, said = fi.counter(league, team, offer, want, rng, fi.leverage(league, coach, n_offers),
                                    extension=extension)
    col = {"granted": C.BGREEN, "half": C.BYELLOW, "refused": C.BYELLOW, "pulled": C.BRED}[outcome]
    print(paint(f"   AD {team.ad['name']} {said}.", col, C.BOLD))
    if outcome == "refused":
        print(paint('   "' + REFUSALS.get(want, "That's the offer.").format(years=offer["years"]) + '"', C.BWHITE))
        print(paint("   Your seat doesn't move — nothing was given — but he's a little warier the next time you ask.",
                    C.GRAY))
    elif outcome in ("granted", "half"):
        print(paint(f"   Seat starts +{new.get('pressure', 0)} from what you've squeezed out of him so far.", C.GRAY))
    if not new.get("pulled"):
        print(paint(f"   On the table now: {fi.terms(new)}", C.GRAY))
    pause()
    return new


def _signature_room(team, coach):
    """Your background is the thing you do best in the building. An inherited
    coordinator can be good at it, but not better than the head coach who built
    his career on it (the O-line coach is the best line coach on his own staff)."""
    tilt = next((b[2] for b in BACKGROUNDS.values() if b[0] == getattr(coach, "background", None)), None)
    if not tilt:
        return
    sig = [k for k, v in tilt.items() if v >= 8 and k != "recruiting"]
    for c in (getattr(team, "oc", None), getattr(team, "dc", None)):
        if c is None:
            continue
        for k in sig:
            cap = coach.ratings.get(k, 55) - 2
            if c.ratings.get(k, 0) > cap:
                c.ratings[k] = cap


def take_job(league, coach, team, first=False, how="hired", offer=None):
    import carousel as cz
    import finance as fi
    old = team.coach
    if old is not None and old is not coach:
        if first:
            old.contract = None               # the job was open when you arrived; nobody owes him anything
        cz.vacate(league, team, "fired")
        old.kind = "fired"
    prev_team = coach.team if coach.team is not team else None
    if coach.team is not None and coach.team is not team:
        cz.vacate(league, coach.team, "left")
    if coach in league.coach_pool:
        league.coach_pool.remove(coach)
    team.set_coach(coach)
    import scout
    scout.bind(league)                                # Coach Career words from the first screen on
    import skills
    skills.new_job(coach)                             # a new school: one free reset of your coaching tree
    fi.sign(league, team, coach, offer or fi.hc_offer(league, team, coach), start=league.year if first else league.year + 1)
    coach.__dict__.setdefault("career_earnings", 0)
    import coach_dev
    coach.__dict__.setdefault("bank", coach_dev.START_BANK)
    coach.status = "employed"
    coach.hired_year = league.year if first else league.year + 1
    coach.seat = 18 + int((offer or {}).get("pressure", 0))     # what you squeezed out of the AD, he remembers
    coach.seat_last = coach.seat
    coach.hot_years = 0
    team.ratings["coach"] = coach.overall
    team.coach_changed = True
    team.coach_log.append((coach.hired_year, coach.name))
    league.user_team = team
    try:
        import cp_ach
        cp_ach.note_hire(league, coach, team, prev_team or getattr(coach, "_last_team", None))
    except Exception:                                 # noqa: BLE001, S110 — a note never blocks a hire
        pass
    team.recruiting_targets = []                    # your board starts empty — you build it
    _signature_room(team, coach)
    import staff as _staff
    _staff.spread_regions(team)
    league.__dict__.setdefault("career_log", []).append((league.year, f"Hired as head coach at {team.school} — {fi.terms(coach.contract)}."))
    if first or league.week == 0:
        import depth
        depth.staff_sort_yours(league, team)         # your staff sets the chart; it's yours from here
    if first:
        clear()
        print(title_bar(f"WELCOME TO {team.school.upper()}"))
        print()
        print(f"   {paint(team.full_name, C.BWHITE, C.BOLD)} — {team.conference}")
        import textwrap
        from dashboard import nav
        print(f"   {paint('Your AD:', C.GRAY)} {team.ad['name']}")
        for ln in textwrap.wrap(cz.ad_judging(team), 90):
            print(paint("     " + ln, C.GRAY))
        print(f"   {paint('Your goals:', C.GRAY)}")
        for g in team.goals:
            print(f"     • {g.label}")
        print(f"   {paint('Your deal:', C.GRAY)} {fi.terms(coach.contract)} (through {coach.contract['end']})")
        print(f"   {paint('Football budget:', C.GRAY)} {fi.money(fi.budget(team))} a year. It grows when the program "
              f"wins and shrinks")
        print(paint("     after years of losing. What your staff doesn't cost goes to NIL.", C.GRAY))
        print()
        print(paint("   Where things are on the dashboard:", C.BWHITE, C.BOLD))
        for label, what in (("Your budget", "budget"), ("Recruiting (yours now)", "recruiting"),
                            ("Develop your coach (bank: " + fi.money(coach.bank) + ")", "develop"),
                            ("Your inbox", "inbox"), ("Play the next week", "play")):
            print(f"     {pad(label, 40)}{paint(nav(what), C.BCYAN)}")
        print(paint("   Before every game you pick how to play it: sim it, play the big moments, coach every snap,\n"
                    "   or watch the broadcast.", C.GRAY))
        pause()


# ═══ Offseason offers ═══════════════════════════════════════════════════════

def offers(league, rng):
    """Jobs that want you: openings where you'd be a top candidate, plus a big
    program willing to push its own coach out if you've been winning."""
    import carousel as cz
    coach = getattr(league, "user_coach", None)
    if coach is None or coach.status == "retired":
        return []
    mine = coach.team
    floor = (mine.prestige + 4) if mine else 0
    out = []
    pool = [c for c in league.coach_pool if c.status == "unemployed" and not getattr(c, "is_user", False)]
    for team in sorted((t for t in league.teams if t.coach is None), key=lambda t: -t.prestige):
        if team.prestige < floor:
            continue
        # the same list the AD would look at: available coaches and sitting head coaches below this job
        sitting = [t.coach for t in league.teams if t.coach is not None and not getattr(t.coach, "is_user", False)
                   and t.prestige < team.prestige - 3 and t.coach.history]
        me = cz.candidate_score(team, coach, league, rng, sitting=mine is not None)
        better = sum(1 for c in pool + sitting if cz.candidate_score(team, c, league, rng, sitting=c.team is not None) > me)
        import skills
        if better <= (4 if skills.has(coach, "face") else 2):     # Face of the Program: more places want you
            out.append((team, "opening"))
    if mine is not None and cz.track_record(coach, league) >= 0.12 and len(coach.history) >= 2:
        for team in sorted(league.teams, key=lambda t: -t.prestige):
            import skills
            if team.coach and not getattr(team.coach, "is_user", False) \
                    and team.coach.seat >= (45 if skills.has(coach, "face") else 55) \
                    and team.prestige >= mine.prestige + 10 and cz.AD_STYLES[team.ad["style"]][2]["hire"] == "splash":
                out.append((team, "poach"))
                break
    out = out[:4]
    import finance as fi
    terms = {}
    import job_market
    league.__dict__.pop("_user_offer_terms", None)
    pursued = [x for x in job_market.career_offers(league, coach, rng) if all(x[0] is not t for t, _ in out)]
    terms.update(league.__dict__.pop("_user_offer_terms", {}) or {})
    out += pursued
    for team, kind in out:
        if team.school in terms:
            continue
        offer = fi.hc_offer(league, team, coach, rng)
        if kind == "poach":
            offer["salary"] = int(offer["salary"] * 1.1)       # they're paying extra to get you
        terms[team.school] = offer
    league._user_offer_terms = terms
    return out


def offer_prompt(league, offers_list, fired):
    """Called by the carousel during the offseason. Returns the team you take, or None."""
    import carousel as cz
    coach = league.user_coach
    clear()
    if fired:
        print(title_bar("YOU'VE BEEN FIRED"))
        last = coach.history[-1] if coach.history else None
        print()
        print(paint(f"   {coach.history[-1]['school'] if last else 'Your school'}'s athletic director has made a change.",
                    C.BRED, C.BOLD))
        reasons = next((e[2] for e in reversed(coach.seat_log) if len(e) == 3), [])
        if reasons:
            print(paint("   " + "; ".join(reasons).capitalize() + ".", C.GRAY))
    else:
        print(title_bar("THE PHONE IS RINGING"))
    print()
    for note in league.__dict__.get("_pursuit_notes", []) or []:
        print(paint(f"   Your agent: {note}.", C.GRAY))
    if not offers_list:
        print(paint("   Nobody's calling this year." + (" You'll sit out a season — the offers may come next winter."
                                                        if fired else ""), C.GRAY))
        pause()
        return None
    import finance as fi
    terms = league.__dict__.setdefault("_user_offer_terms", {})
    mine = fi.contract(coach) if coach.team is not None and not fired else None
    first_pass = True
    while True:
        if not first_pass:
            clear()
            print(title_bar("YOU'VE BEEN FIRED" if fired else "THE PHONE IS RINGING"))
            print()
        first_pass = False
        if mine:
            print(paint(f"   Your deal at {coach.team.school}: {fi.terms(mine, total=False)} through {mine['end']}.", C.GRAY))
            print()
        for i, (t, kind) in enumerate(offers_list, 1):
            style = cz.AD_STYLES[t.ad["style"]][0]
            note = paint("  (they'd move on from their coach to hire you)", C.BYELLOW) if kind == "poach" else \
                paint("  (you went after this one)", C.BGREEN) if kind == "pursued" else ""
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)}  {pad(paint(t.full_name, C.BWHITE, C.BOLD), 36)}"
                  f"{pad(paint(t.conference, league.conference_color(t.conference)), 14)}"
                  f"prestige {rating(round(t.prestige))}   roster {__import__('scout').team(t.team_ovr)}   {paint('AD: ' + style, C.GRAY)}{note}")
            _goal_lines(t)
            if t.school not in terms:
                terms[t.school] = fi.hc_offer(league, t, coach)
            offer_line(league, t, terms[t.school], mine=coach if mine else None)
        print()
        stay = "Stay where you are" if coach.team is not None and not fired else "Sit out a year"
        print(f"   {paint('[#]', C.BGREEN, C.BOLD)}  take the job   {paint('[I#]', C.BYELLOW, C.BOLD)}  interview with the AD   "
              f"{paint('[N#]', C.BYELLOW, C.BOLD)}  negotiate (risky)   {paint('[T]', C.BYELLOW)}  search tracker   "
              f"{paint('[S]', C.BGREEN, C.BOLD)}  {stay}")
        choice = ask("Your decision:").strip().lower()
        if choice == "t":
            import hc_search
            hc_search.tracker(league)
            continue
        if choice.startswith("i") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= len(offers_list):
            import hc_search
            t, _ = offers_list[int(choice[1:]) - 1]
            terms[t.school] = hc_search.interview(league, t, coach, terms[t.school])
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(offers_list):
            team, kind = offers_list[int(choice) - 1]
            if terms[team.school].get("pulled"):
                print(paint(f"   {team.school} pulled that offer.", C.BRED))
                pause()
                continue
            if ask(f"Sign with {team.school}: {fi.terms(terms[team.school])}? (y/n)").lower() not in ("y", "yes"):
                continue
            if kind == "poach" and team.coach is not None:
                cz._news(league, "fired", f"{team.school} moves on from {team.coach.name} to hire {coach.name}")
                cz.vacate(league, team, "fired")
            return team
        if choice.startswith("n") and choice[1:].isdigit() and 1 <= int(choice[1:]) <= len(offers_list):
            t, _ = offers_list[int(choice[1:]) - 1]
            terms[t.school] = negotiate(league, t, terms[t.school], coach, n_offers=len(offers_list))
            continue
        return None                                  # [S] (or Enter): stay put


def extension_prompt(league, team, offer, expiring, reason=None):
    """Your AD wants to talk contract. Returns the deal you sign, or None."""
    if getattr(league, "autosim", False):
        return offer                                    # simming seasons: sign what the AD puts in front of you
    import finance as fi
    import carousel as cz
    coach = league.user_coach
    cur = fi.contract(coach)
    while True:
        clear()
        print(title_bar("CONTRACT TALKS  ·  " + team.school.upper()))
        print()
        if expiring:
            print(paint(f"   Your contract at {team.school} is up after this season.", C.BYELLOW, C.BOLD))
        else:
            why = {"after winning the national title": "after the national title",
                   "after a big season": "after the season you just had",
                   "to keep bigger programs away": "before bigger programs come calling",
                   "before the deal gets short": "before your deal gets short"}.get(reason, "before your deal gets short")
            print(paint(f"   AD {team.ad['name']} wants to lock you up {why}.", C.BGREEN, C.BOLD))
        if cur:
            print(paint(f"   Current deal: {fi.terms(cur, total=False)} through {cur['end']}.", C.GRAY))
        print(paint(f"   AD style: {cz.AD_STYLES[team.ad['style']][0]} — {fi.AD_CONTRACT[team.ad['style']]['blurb']}.   "
                    f"Your seat: {coach.seat}/100.", C.GRAY))
        print()
        print(f"   {paint('THE OFFER', C.BWHITE, C.BOLD)}")
        offer_line(league, team, offer, indent="   ")
        print()
        leave = ("walk — you leave " + team.school + " and see who calls") if expiring else "keep your current deal"
        print(f"   {paint('[A]', C.BGREEN, C.BOLD)} sign it   {paint('[N]', C.BYELLOW, C.BOLD)} negotiate (risky)   "
              f"{paint('[D]', C.BRED, C.BOLD)} decline — {leave}")
        choice = ask("Sign, counter or decline:").strip().lower()
        if choice == "a":
            return offer
        if choice == "n":
            offer = negotiate(league, team, offer, coach, extension=True)
            if offer.get("pulled"):
                if expiring:
                    print(paint(f"   Talks are over. Your contract at {team.school} runs out.", C.BRED, C.BOLD))
                else:
                    print(paint("   Talks are over for now. You'll play out your current deal.", C.BYELLOW, C.BOLD))
                pause()
                return "pulled"
        elif choice == "d":
            if not expiring or ask(f"Walk away from {team.school}? (y/n)").lower() in ("y", "yes"):
                return None


def after_carousel(league):
    """Keep your recruiting board pointed at your job, whatever just happened."""
    coach = getattr(league, "user_coach", None)
    if coach is not None:
        league.user_team = coach.team


# ═══ Reputations you earn ═══════════════════════════════════════════════════

def earn_traits(league, coach, s):
    """Traits come from what your teams do — not from a menu."""
    from traits import COACH_TRAITS
    t = coach.team
    if t is None:
        return
    have = set(coach.traits)
    earned = []

    def give(key, why):
        if key not in have and len(coach.traits) < 5:
            coach.traits.append(key)
            have.add(key)
            earned.append((key, why))

    games = s["w"] + s["l"]
    if s.get("title") or s.get("conf_champ") or s.get("close_w", 0) >= 4:
        give("closer", "your teams win the close ones, and they win in December")
    qbs = t.players_at("QB")
    if qbs:
        q = qbs[0].season_stats
        if q["pass_att"] >= 200 and (8.4 * q["pass_yds"] + 330 * q["pass_td"] + 100 * q["pass_cmp"]
                                      - 200 * q["pass_int"]) / q["pass_att"] >= 158:
            give("qb_whisperer", f"{qbs[0].name} had one of the best passing seasons in the country")
    rush = sum(p.season_stats["rush_yds"] for p in t.roster)
    att = sum(p.season_stats["rush_att"] for p in t.roster)
    if att >= 350 and rush / att >= 5.4:
        give("trench_guru", "your lines moved people all season")
    mine = [h for h in coach.history if h["school"] == t.school]
    if len(mine) >= 2 and mine[-1]["roster"] - mine[-2]["roster"] >= 3:
        give("developer", "your roster got a lot better in one year")
    if games and s["w"] / games - s.get("exp", 0.5) >= 0.22:
        give("motivator", "your team played way over its head")
    if coach.aggression >= 70 and s["w"] > s["l"]:
        give("riverboat", "fourth and four is a green light — and it's working")
    if len(mine) >= 3 and all(h["w"] > h["l"] for h in mine[-3:]):
        give("culture", "three straight winning seasons — nobody wants to leave")
    for key, why in earned:
        league.__dict__.setdefault("career_log", []).append((league.year, f"Earned a reputation: {COACH_TRAITS[key][0]} — {why}."))
        import carousel as cz
        cz._news(league, "hired", f"{coach.name} is earning a reputation at {t.school}: {COACH_TRAITS[key][0]}")


def earn_class_traits(league, coach, class_rank):
    from traits import COACH_TRAITS
    t = coach.team
    if t is None or not class_rank:
        return
    if class_rank <= 15 and t.prestige < 78 and "salesman" not in coach.traits and len(coach.traits) < 5:
        coach.traits.append("salesman")
        league.__dict__.setdefault("career_log", []).append((league.year, f"Earned a reputation: {COACH_TRAITS['salesman'][0]} — "
                                               f"a top-15 class at a program that doesn't sign top-15 classes."))


# ═══ Your career screen ═════════════════════════════════════════════════════

def career_screen(league):
    import guide
    guide.tip(league, "career")
    import carousel as cz
    import coach_screens as cs
    coach = league.user_coach
    while True:
        clear()
        team = coach.team
        where = team.full_name if team else ("Retired" if coach.status == "retired" else "Out of coaching")
        print(title_bar(f"MY CAREER  ·  COACH {coach.name.upper()}"))
        import difficulty
        bg_ = getattr(coach, "background", None) or getattr(coach, "origin", "") or ""
        print(f"   {paint(where, C.BWHITE, C.BOLD)}   {paint(bg_, C.GRAY)}   age {coach.age}   "
              f"OVR {rating(coach.overall)}   {paint('difficulty: ' + difficulty.name(coach), C.GRAY)}")
        if team is not None:
            heat = coach.seat
            print(f"   Seat: {cs.seat_tag(coach)} {heat}/100   {paint('AD ' + team.ad['name'] + ' (' + cz.AD_STYLES[team.ad['style']][0] + ')', C.GRAY)}")
            import ad_trust
            tv = ad_trust.get(coach, team)
            recent = ad_trust.lines(coach, team, 3)
            print(f"   AD trust: {paint(f'{tv:.0f}/100 · {ad_trust.word(tv)}', ad_trust.color(tv), C.BOLD)}   "
                  + paint(("lately: " + "; ".join(f"{why} ({d:+.0f})" for d, why in reversed(recent))) if recent
                          else "a clean slate", C.GRAY))
            print(paint("   Trust decides how hard results hit your seat, and how much he finds when you ask for money.",
                        C.GRAY))
            import finance as fi
            k = fi.contract(coach)
            if k:
                print(f"   Contract: {paint(fi.deal_line(k, league), C.BGREEN)}   "
                      f"{paint('owed if fired: ' + fi.money(fi.owed(coach, league), exact=True), C.GRAY)}")
        if getattr(coach, "career_earnings", 0) or fi_contract(coach):
            import finance as fi
            print(paint(f"   Career earnings: {fi.money(getattr(coach, 'career_earnings', 0))} "
                        f"(paid at the end of every season, plus any buyout)", C.GRAY))
            print()
            print(section(f"{team.school.upper()} GOALS", C.BYELLOW))
            cs._print_goals(league, team, coach)
        car = cz.splits(coach.history)
        live = (team is not None and team.coach is coach and (team.wins or team.losses)
                and not (coach.history and coach.history[-1].get("year") == league.year))
        if live:                                               # this season isn't in the book until it ends
            car["w"], car["l"] = car["w"] + team.wins, car["l"] + team.losses
        print()
        print(section("CAREER", C.BGREEN))
        print(f"   {car['w']}-{car['l']} overall{paint(' (this season included)', C.GRAY) if live else ''} · {car['t25w']}-{car['t25l']} vs Top 25 · "
              f"{car['titles']} national titles · {car['cfp']} NP trips · {car['confs']} conference titles · "
              f"{car['bowls']} bowls")
        from traits import COACH_TRAITS
        print(f"   Reputation: {', '.join(COACH_TRAITS[t][0] for t in coach.traits if t in COACH_TRAITS) or '—'}")
        print()
        print(section("YOUR STORY", C.BCYAN))
        story = getattr(league, "career_log", [])[-12:]
        for yr, text in story:
            print(f"   {paint(str(yr), C.GRAY)}  {text}")
        if not story:
            print(paint("   Nothing written yet. Each season's big moments (titles, hires, firings, milestones) land here.", C.GRAY))
        print(rule())
        import coach_dev
        coach_dev.ensure(coach)
        dev_note = f"{fi_money(coach.bank)} in the bank" + ("" if coach.team is not None else " — needs a job")
        import skills
        tp = skills._st(coach)["points"]
        print(f"   {paint('[T]', C.BYELLOW, C.BOLD)} coaching tree ({tp} skill point{'s' if tp != 1 else ''} to spend, "
              f"{skills._st(coach)['spent']} spent)")
        print(f"   {paint('[D]', C.BGREEN, C.BOLD)} develop your coach ({dev_note})   "
              f"{paint('[P]', C.BYELLOW)} full coach profile   {paint('[S]', C.BYELLOW)} my staff")
        print(f"   {paint('[M]', C.BYELLOW)} budget & NIL   {paint('[F]', C.BYELLOW)} facilities   "
              f"{paint('[K]', C.BYELLOW)} change my schemes   "
              f"{paint('[L]', C.BYELLOW)} difficulty   {paint('[R]', C.BRED)} retire   {paint('[B]', C.GRAY)} back")
        import webview
        if webview.on():
            try:
                import finance as fi
                from traits import COACH_TRAITS
                d = {"name": coach.name, "where": where, "bg": bg_, "age": coach.age, "ovr": coach.overall,
                     "difficulty": difficulty.name(coach), "rec": car, "live": bool(live),
                     "rep": [COACH_TRAITS[t][0] for t in coach.traits if t in COACH_TRAITS],
                     "story": [[yr, webview.plain(text)] for yr, text in reversed(story)],
                     "bank": webview.plain(fi_money(coach.bank)), "points": tp, "spent": skills._st(coach)["spent"],
                     "color": webview._color(league, team) if team is not None else None, "hasTeam": team is not None,
                     "schemes": f"{coach.offense_scheme} · {coach.defense_scheme}",
                     "installs": __import__("scheme_change").status_lines(team) if team is not None else []}
                if team is not None:
                    import ad_trust
                    tv = ad_trust.get(coach, team)
                    d.update(seat=coach.seat, seatWord=webview.plain(cs.seat_tag(coach)),
                             ad=f"{team.ad['name']} ({cz.AD_STYLES[team.ad['style']][0]})", trust=round(tv),
                             trustWord=ad_trust.word(tv),
                             trustLog=[f"{why} ({dd:+.0f})" for dd, why in reversed(ad_trust.lines(coach, team, 3))])
                    k = fi.contract(coach)
                    if k:
                        d.update(contract=webview.plain(fi.deal_line(k, league)), owed=fi.money(fi.owed(coach, league), exact=True))
                    try:
                        d["goals"] = [{"text": webview.plain(g.get("text", "")), "status": g.get("status", ""), "note": webview.plain(g.get("note", ""))}
                                      for g in (__import__("gui_data").coach_card(league, team) or {}).get("goals", [])]
                    except Exception:
                        pass
                webview.emit("career", d)
            except Exception:
                pass
        choice = ask("Select:").lower()
        if choice == "t":
            skills.tree_screen(league)
        elif choice == "d":
            coach_dev.develop_screen(league)
        elif choice == "m" and team is not None:
            import finance_screens
            finance_screens.budget_screen(league, team)
        elif choice == "f" and team is not None:
            import finance_screens
            finance_screens.facilities_screen(league, team)
        elif choice == "k" and team is not None:
            import scheme_change
            scheme_change.screen(league, coach, team)
        elif choice == "p":
            cs.coach_view(league, coach)
        elif choice == "l":
            import difficulty
            difficulty.menu(league)
        elif choice == "s":
            import staff_screens
            import staff_room
            staff_room.manage(league)
        elif choice == "r":
            if ask("Retire and watch the world as a spectator? Type YES:").strip().upper() == "YES":
                if team is not None:
                    cz._news(league, "retired", f"{coach.name} retires from coaching ({cz._record(coach)})")
                    cz.vacate(league, team, "retired")
                    if not league.season_complete:
                        cz.name_interim(league, team)
                coach.status = "retired"
                league.retired_coaches.append(coach)
                league.__dict__.setdefault("career_log", []).append((league.year, "Retired from coaching."))
                league.mode = "spectator"
                league.user_team = None
                return
        else:
            return


def fi_contract(coach):
    import finance as fi
    return fi.contract(coach)


def fi_money(x):
    import finance as fi
    return fi.money(x)
