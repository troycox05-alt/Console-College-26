"""
cp_cards.py — The AD's report cards, deeper (Coach Career).

  report_card(league)   end of season: up to 13 graded areas, weighted by what your AD cares about,
                        a letter in his voice, three other voices (the money, the press, the students),
                        trends against last year, and what the grade costs or earns you
  midterm(league)       Week 7: a mid-season progress report (shown once, after the wrap)
  cards_screen(league)  every card you've had, the GPA over time, and any one card in full
"""
import random
import textwrap

from ui import (
    WIDTH,
    C,
    ask,
    bar,
    clear,
    clip,
    footer,
    key,
    pad,
    paint,
    pause,
    section,
    title_bar,
)

PTS = {"A+": 4.3, "A": 4, "A-": 3.7, "B+": 3.3, "B": 3, "B-": 2.7, "C+": 2.3, "C": 2, "C-": 1.7, "D": 1, "F": 0}
GRADE_COLOR = {"A": C.BGREEN, "B": C.GREEN, "C": C.BYELLOW, "D": C.BRED, "F": C.BRED}

# what each AD leans on (missing = 1.0)
WEIGHTS = {
    "win_now": {"Winning": 2.0, "Postseason": 1.6, "Development": 0.6},
    "big_game": {"Big games": 2.0, "Rivalry": 1.6},
    "conference": {"Conference": 2.2},
    "analytics": {"Development": 2.0, "Recruiting": 1.5, "Winning": 0.8},
    "booster": {"Rivalry": 1.6, "The stands": 1.6, "Money": 1.4, "Big games": 1.3},
    "turnaround": {"Winning": 1.4, "Development": 1.6, "Program buzz": 1.4},
    "recruiting": {"Recruiting": 2.2},
    "traditionalist": {"Rivalry": 2.0, "Home field": 1.6, "Discipline": 1.6},
    "patient": {"Development": 1.6, "Culture": 1.6, "Winning": 0.8},
}
ASKS = {"Winning": "Win more than you should. {w} wins would turn heads.",
        "Big games": "Beat somebody ranked. The fan base remembers Saturdays like that.",
        "Conference": "Finish in the top half of the league, at least.",
        "Rivalry": "Beat {rival}. I don't care what else happens that day.",
        "Home field": "Defend your own stadium. Nobody should leave here happy.",
        "Recruiting": "Sign a top-{want} class. It's what this program should be doing.",
        "Development": "Your players need to get better. The roster should be stronger by next fall.",
        "Culture": "Fix the locker room. I hear things, and I don't like what I hear.",
        "Discipline": "Keep them out of the papers. One more suspension and it's my problem too.",
        "The stands": "Fill the stadium. Win at home and the people come back.",
        "Money": "Live inside the budget. The NIL pool isn't a credit card.",
        "Postseason": "Get to the postseason, and win when you're there.",
        "Program buzz": "Get us ranked and keep us there. Recruits watch the poll."}


def _cp():
    import career_plus
    return career_plus


def grade(score):
    cuts = ((0.55, "A+"), (0.35, "A"), (0.2, "A-"), (0.1, "B+"), (0.0, "B"), (-0.1, "B-"), (-0.2, "C+"),
            (-0.3, "C"), (-0.42, "C-"), (-0.55, "D"), (-9, "F"))
    return next(g for c, g in cuts if score >= c)


def letter(gpa):
    return "A" if gpa >= 3.7 else "B" if gpa >= 2.85 else "C" if gpa >= 2.0 else "D" if gpa >= 1.2 else "F"


def _suspensions(team, year):
    n = 0
    for p in team.roster:
        n += sum(1 for e in p.events.get(year, []) if str(e).startswith("Suspended"))
    return n


def areas(league, mid=False):
    """[(area, grade, why)] for your season so far."""
    import carousel as cz
    team, coach = league.user_team, league.user_coach
    st = _cp().state(league)
    s = cz.season_line(league, team)
    rows = []
    if mid:
        xw, _n = cz.expected_wins(league, team)
        rows.append(("Winning", grade((s["w"] - xw) / 2.0), f"{s['w']}-{s['l']}, against {xw:.1f} expected so far"))
    else:
        xw, _n = cz.expectation(league, team, coach)
        rows.append(("Winning", grade((s["w"] - xw) / 3.0), f"{s['w']}-{s['l']} against an expected {xw:.1f} wins"))
    t25 = s["t25w"] + s["t25l"]
    if t25:
        rows.append(("Big games", grade((s["t25w"] - s["t25l"]) / max(2, t25) * 0.7),
                     f"{s['t25w']}-{s['t25l']} against ranked teams" + (f", {s['t25_road_w']} on the road" if s["t25_road_w"] else "")))
    cg = s["cw"] + s["cl"]
    if cg:
        rows.append(("Conference", grade((s["cw"] / cg - 0.5) * 1.2 + (0.3 if s["conf_champ"] else 0)),
                     f"{s['cw']}-{s['cl']}" + (f" · {team.conference} champions" if s["conf_champ"] else "")))
    rival = cz._rival_of(team, league)
    rival = rival[0] if rival else None
    if rival and rival in s["opps"]:
        w, l_ = s["beat"].count(rival), s["lost_to"].count(rival)
        rows.append(("Rivalry", "A" if w and not l_ else "F" if l_ and not w else "C",
                     f"{'beat' if w else 'lost to'} {rival}" + (" twice" if max(w, l_) > 1 else "")))
    hg = s["hw"] + s["hl"]
    if hg >= 3:
        rows.append(("Home field", grade((s["hw"] / hg - 0.6) * 1.5), f"{s['hw']}-{s['hl']} at home"))
    rk = league.recruiting.class_rank(team)
    want = cz._class_expectation(team, league)
    if rk:
        rows.append(("Recruiting", grade((want - rk) / max(8, want)), f"No. {rk} class (a program like this signs around No. {want})"))
    elif not mid:
        rows.append(("Recruiting", "D", "No ranked class yet"))
    start = st["ovr_start"].get(league.year)
    if start is not None and not mid:
        d = team.team_ovr - start
        rows.append(("Development", grade(d / 5), f"team rating {start:.0f} → {team.team_ovr:.0f}"
                     if isinstance(start, (int, float)) else "the roster changed"))
    try:
        import morale
        import personalities
        ch = personalities.chemistry(team)
        mo = morale.avg(team.roster)
        rows.append(("Culture", grade((ch - 50) / 40 + (mo - 55) / 80), f"chemistry {ch:.0f}, morale {mo:.0f}"))
    except Exception:                                   # noqa: BLE001, S110 — a grade is never worth a crash
        pass
    sus = _suspensions(team, league.year)
    rows.append(("Discipline", "A" if sus == 0 else "B" if sus == 1 else "C" if sus <= 3 else "D" if sus <= 5 else "F",
                 "nobody suspended" if sus == 0 else f"{sus} suspension{'s' if sus != 1 else ''}"))
    homes = [g for g in league.team_games(team) if g.home is team and not g.neutral and g.played and getattr(g, "attendance", None)]
    if homes and team.capacity:
        pct = sum(g.attendance for g in homes) / len(homes) / team.capacity
        rows.append(("The stands", grade((pct - 0.85) * 2.5), f"{pct * 100:.0f}% full on average"))
    if not mid:
        try:
            import finance
            pool = finance.nil_pool(league, team)
            avail = finance.available(league, team)
            if pool > 0:
                rows.append(("Money", grade(avail / pool * 2 - 0.05) if avail >= 0 else "D" if avail > -pool * 0.1 else "F",
                             f"{finance.money(avail)} of next year's NIL pool still free" if avail >= 0
                             else f"{finance.money(-avail)} over next year's NIL pool"))
        except Exception:                               # noqa: BLE001, S110
            pass
    if s["post"] and not mid:
        rows.append(("Postseason", "A" if s["title"] or s["cfp_win"] else "B+" if s["cfp"] or s["bowl_win"] else "C",
                     s["post"]))
    pre = st.get("years", {}).get(str(league.year), {}).get("pre_rank", "x")
    now = league.rankings.rank_of(team)
    if pre != "x":
        if pre and now:
            sc = (pre - now) / 12 + (0.15 if now <= 10 else 0)
        elif now:
            sc = 0.35
        elif pre:
            sc = -0.4
        else:
            sc = -0.15
        was = f"No. {pre}" if pre else "unranked"
        is_ = f"No. {now}" if now else "unranked"
        rows.append(("Program buzz", grade(sc), f"{was} in the preseason → {is_}"))
    return rows


def weighted(rows, style):
    w = WEIGHTS.get(style, {})
    tot = sum(w.get(a, 1.0) for a, _, _ in rows) or 1
    return sum(PTS[g] * w.get(a, 1.0) for a, g, _ in rows) / tot


def _letter(league, rows, overall, gpa, style):
    team = league.user_team
    w = WEIGHTS.get(style, {})
    rng = random.Random(f"card:{league.year}:{team.school}")
    best = max(rows, key=lambda r: (PTS[r[1]] * w.get(r[0], 1.0), w.get(r[0], 1.0)))
    worst = min(rows, key=lambda r: (PTS[r[1]] - 0.2 * w.get(r[0], 1.0)))
    open_ = {
        "A": ["Coach, I'll keep this short, because there's not much to say except thank you.",
              "This was the season we hired you for. Maybe a little better."],
        "B": ["A good year. Not a perfect one, but a good one, and I don't take that for granted.",
              "Solid work, Coach. We moved forward, and everybody in this building felt it."],
        "C": ["I'll be honest with you, because that's how this works: this was an ordinary year.",
              "We didn't go backward. I can't say we went forward, either."],
        "D": ["This isn't the letter I wanted to write.",
              "I've had a lot of calls this fall, Coach, and not many of them were friendly."],
        "F": ["There's no easy way to say it: this season was not acceptable.",
              "I defended you in rooms you weren't in this year. I can't do that again."],
    }[overall]
    lean = {"win_now": "You know how I judge this job: the scoreboard, this year.",
            "big_game": "You know what I watch: the big Saturdays, the ranked teams, the rival.",
            "conference": "You know where my eyes are: the league standings.",
            "analytics": "You know I look past the record, at the roster and the process underneath it.",
            "booster": "You know who I answer to. The people who write the checks were watching.",
            "turnaround": "All I've ever asked is that the arrow point up.",
            "recruiting": "Talent wins, and I grade the classes before anything else.",
            "traditionalist": "Beat the rival, win at home, stay out of the papers. That's the job here.",
            "patient": "I've told you I'd give you time. I meant it."}.get(style, "")
    praise = f"The {best[0].lower()} stood out: {best[2]}. That matters to me."
    concern = (f"What I need to see change is the {worst[0].lower()} ({worst[2]})."
               if PTS[worst[1]] < 3.0 else "If I'm reaching for a concern, it's keeping this going. Programs get comfortable.")
    close = {"A": "Enjoy the holidays. You've earned them.", "B": "Let's build on it.",
             "C": "Next year has to be better, and I think it can be.",
             "D": "I need to see a real plan before spring practice.", "F": "We'll talk after the bowls."}[overall]
    return [rng.choice(open_), lean, praise, concern, close, f"— {team.ad['name']}, Director of Athletics"]


def _voices(league, rows):
    g = {a: PTS[gr] for a, gr, _ in rows}
    out = []
    money = (g.get("Rivalry", 3) + g.get("The stands", 3) + g.get("Big games", 3) + g.get("Winning", 3)) / 4
    out.append(("Booster president", letter(money),
                "The checks keep coming. Keep winning the ones people talk about." if money >= 3 else
                "A few of our donors are asking questions. I'm answering them, for now." if money >= 2 else
                "Our people are holding their wallets. That's never good."))
    press = (g.get("Winning", 3) + g.get("Program buzz", 3) + g.get("Postseason", 2.5)) / 3
    out.append(("The beat writer", letter(press),
                "The best season the program's had in a while, and the coach is the reason." if press >= 3.4 else
                "An honest year's work. The ceiling question is still open." if press >= 2.4 else
                "The honeymoon's over, if there ever was one."))
    kids = (g.get("Home field", 3) + g.get("The stands", 3) + g.get("Culture", 3)) / 3
    out.append(("The student section", letter(kids),
                "Rushed the field once and would do it again." if kids >= 3.4 else
                "Showed up, stayed till the fourth quarter, mostly." if kids >= 2.4 else
                "Left at halftime more than we'd like to admit."))
    return out


FX = {"A": (4, -4), "B": (2, -2), "C": (0, 0), "D": (-3, 3), "F": (-6, 6)}


def report_card(league):
    cp = _cp()
    if not cp.mine(league):
        return
    import ad_trust
    import effects
    team = league.user_team
    st = cp.state(league)
    style = team.ad.get("style", "patient")
    rows = areas(league)
    gpa = weighted(rows, style)
    overall = letter(gpa)
    let = _letter(league, rows, overall, gpa, style)
    voices = _voices(league, rows)
    prev = st.get("cards", {}).get(league.year - 1)
    prev_g = {a: g for a, g, _ in prev["rows"]} if prev and prev.get("school", team.school) == team.school else {}
    trust_d, seat_d = FX[overall]
    if trust_d:
        ad_trust.change(league, trust_d, f"the {league.year} report card ({overall})")
    if seat_d:
        effects.apply(league, {"seat": seat_d}, f"the {league.year} report card")
    card = {"overall": overall, "gpa": round(gpa, 2), "rows": [(a, g, w) for a, g, w in rows], "letter": let,
            "voices": voices, "school": team.school, "style": style, "fx": [trust_d, seat_d]}
    st.setdefault("cards", {})[league.year] = card
    cp._log(league, (league.year, f"Report card from the AD: {overall} (GPA {gpa:.2f})."))
    cp._story(league, "report card", f"Report card: {overall} from AD {team.ad['name']} (GPA {gpa:.2f}).")
    show(league, league.year, card, prev_g, live=True)


def show(league, year, card, prev_g=None, live=False):
    import carousel as cz
    team = league.user_team
    w = WEIGHTS.get(card.get("style"), {})
    page = 1
    while True:
        clear()
        print(title_bar(f"{year} REPORT CARD · {card.get('school', team.school).upper()}", league.team_color(team) if live else C.BYELLOW))
        st_name = cz.AD_STYLES.get(card.get("style"), ("", ""))
        if page == 1:
            print(paint(f"\n   {st_name[0]} AD — {st_name[1].lower()}. ★ = what he weighs heaviest.", C.GRAY))
            print(paint(f"\n   {'AREA':<16}{'GRADE':<7}{'VS LAST':<9}WHY", C.GRAY, C.BOLD))
            for area, g, why in card["rows"]:
                star = paint("★", C.BYELLOW) if w.get(area, 1.0) >= 1.5 else " "
                tr = ""
                if prev_g and area in prev_g:
                    d = PTS[g] - PTS[prev_g[area]]
                    tr = paint(f"▲ {prev_g[area]}", C.BGREEN) if d > 0 else paint(f"▼ {prev_g[area]}", C.BRED) if d < 0 \
                        else paint("=", C.GRAY)
                print(clip(f"  {star}{pad(area, 16)}{paint(pad(g, 7), GRADE_COLOR.get(g[0], C.BWHITE), C.BOLD)}"
                           f"{pad(tr, 9)}{paint(why, C.GRAY)}", WIDTH))
            ov = card["overall"]
            gp = f"GPA {card['gpa']:.2f} (weighted)"
            print(f"\n   {pad('OVERALL', 16)}{paint(pad(ov, 7), GRADE_COLOR[ov], C.BOLD)}{pad('', 9)}"
                  f"{paint(gp, C.GRAY)}  {bar(card['gpa'], 20, 4.3, GRADE_COLOR[ov])}")
            td, sd = card.get("fx", [0, 0])
            if td or sd:
                print(paint(f"\n   What it means: AD trust {td:+d}, hot seat {sd:+d}.", C.BGREEN if td > 0 else C.BRED, C.BOLD))
            else:
                print(paint("\n   What it means: nothing moves. An ordinary year buys an ordinary amount of patience.", C.GRAY))
        elif page == 2:
            print(section("HIS LETTER", C.BCYAN))
            for para in card.get("letter", []):
                for ln in textwrap.wrap(para, 90):
                    print("   " + ln)
                print()
            print(section("OTHER VOICES", C.BMAGENTA))
            for who, g, said in card.get("voices", []):
                print(clip(f"   {pad(who, 20)}{paint(pad(g, 3), GRADE_COLOR.get(g[0], C.BWHITE), C.BOLD)}{paint(said, C.GRAY)}", WIDTH))
        else:
            print(section("WHAT HE WANTS NEXT YEAR", C.BCYAN))
            import carousel as cz2
            want = cz2._class_expectation(team, league)
            rival = cz2._rival_of(team, league)
            worst = sorted(card["rows"], key=lambda r: PTS[r[1]] - 0.3 * w.get(r[0], 1.0))[:3]
            told = 0
            for area, g, _ in worst:
                if PTS[g] < 3.3:
                    print("   • " + ASKS.get(area, "Keep it going.").format(w=max(team.wins + 1, 8), want=max(5, want),
                                                                          rival=rival[0] if rival else "the rival"))
                    told += 1
            if not told:
                print("   • More of the same. Don't let the program get comfortable.")
            if live:
                print(section("THE GOALS", C.BYELLOW))
                import coach_screens
                coach_screens._print_goals(league, team, league.user_coach)
                import ad_trust
                tv = ad_trust.get(league.user_coach, team)
                print(paint(f"\n   Hot seat {league.user_coach.seat}/100 ({cz2.seat_label(league.user_coach.seat).lower()}) · "
                            f"AD trust {tv:.0f}/100 ({ad_trust.word(tv)}). His verdict comes with the carousel.", C.GRAY))
        footer(key("1", "grades"), key("2", "his letter"), key("3", "next year"), key("Enter", "done", C.BGREEN))
        c = ask("Select:").strip()
        if c in ("1", "2", "3"):
            page = int(c)
        else:
            return


def midterm(league):
    """After the Week 7 wrap: how the AD sees the first half."""
    cp = _cp()
    if not cp.mine(league) or league.week != 7:
        return
    st = cp.state(league)
    if f"mid:{league.year}" in st["seen"]:
        return
    st["seen"].append(f"mid:{league.year}")
    team = league.user_team
    style = team.ad.get("style", "patient")
    rows = areas(league, mid=True)
    gpa = weighted(rows, style)
    ov = letter(gpa)
    st.setdefault("midterms", {})[league.year] = {"overall": ov, "gpa": round(gpa, 2), "rows": rows}
    clear()
    print(title_bar(f"MID-SEASON PROGRESS REPORT · {league.year}", league.team_color(team)))
    print(paint(f"\n   Halfway. A note from AD {team.ad['name']} — not a verdict, a check-in.\n", C.GRAY))
    w = WEIGHTS.get(style, {})
    for area, g, why in rows:
        star = paint("★", C.BYELLOW) if w.get(area, 1.0) >= 1.5 else " "
        print(clip(f"  {star}{pad(area, 16)}{paint(pad(g, 6), GRADE_COLOR.get(g[0], C.BWHITE), C.BOLD)}{paint(why, C.GRAY)}", WIDTH))
    print(f"\n   {pad('SO FAR', 17)}{paint(pad(ov, 6), GRADE_COLOR[ov], C.BOLD)}{paint(f'GPA {gpa:.2f}', C.GRAY)}")
    worst = min(rows, key=lambda r: PTS[r[1]] - 0.3 * w.get(r[0], 1.0))
    note = ({"A": "Keep doing exactly this.", "B": "On track. Finish it.", "C": "The second half decides what kind of year this is.",
             "D": "I'm worried, Coach. The second half has to be different.", "F": "This can't continue."}[ov])
    print(paint(f"\n   \"{note}" + (f" Watch the {worst[0].lower()}." if PTS[worst[1]] < 3 else "") + "\"", C.BCYAN, C.ITALIC))
    pause()


def cards_screen(league):
    cp = _cp()
    while True:
        st = cp.state(league)
        cards = st.get("cards", {})
        mids = st.get("midterms", {})
        clear()
        print(title_bar("REPORT CARDS FROM YOUR AD"))
        if not cards and not mids:
            print(paint("\n   The first one comes at the end of this season (a mid-season progress report after Week 7).", C.GRAY))
            pause()
            return
        print(paint(f"\n   {'':6}{'SEASON':<8}{'SCHOOL':<18}{'OVERALL':<9}{'GPA':<6}", C.GRAY, C.BOLD))
        ys = sorted(cards)
        for i, y in enumerate(ys, 1):
            cd = cards[y]
            ov = cd["overall"]
            m = mids.get(y)
            mid = paint(f"   mid-season {m['overall']}", C.GRAY) if m else ""
            print(clip(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)}  {pad(str(y), 8)}{pad(cd.get('school', ''), 18)}"
                       f"{paint(pad(ov, 9), GRADE_COLOR[ov], C.BOLD)}{pad(str(cd['gpa']), 6)}{bar(cd['gpa'], 20, 4.3, GRADE_COLOR[ov])}{mid}", WIDTH))
        live_mid = [y for y in mids if y not in cards]
        for y in live_mid:
            m = mids[y]
            print(clip(f"        {pad(str(y), 8)}{pad(league.user_team.school if league.user_team else '', 18)}"
                       f"{paint(pad(m['overall'], 9), GRADE_COLOR[m['overall']])}{pad(str(m['gpa']), 6)}"
                       f"{paint('mid-season progress report', C.GRAY)}", WIDTH))
        if len(ys) >= 2:
            avg = sum(cards[y]["gpa"] for y in ys) / len(ys)
            best = max(ys, key=lambda y: cards[y]["gpa"])
            print(paint(f"\n   Career GPA {avg:.2f} · best {best} ({cards[best]['gpa']})", C.GRAY))
        footer(key("#", "open a card"), key("B", "back", C.GRAY))
        c = ask("Select:").strip()
        if c.isdigit() and 1 <= int(c) <= len(ys):
            y = ys[int(c) - 1]
            cd = cards[y]
            if "letter" not in cd:
                cd = dict(cd, letter=["(This card came before the AD started writing letters.)"], voices=[])
            prev = cards.get(y - 1)
            show(league, y, cd, {a: g for a, g, _ in prev["rows"]} if prev else None)
        else:
            return
