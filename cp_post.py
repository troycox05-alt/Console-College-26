"""
cp_post.py — Selection Day and bowl week, deeper (Coach Career).

  selection_show(league)   the chair's statement, the reveal with every team's case, then the pages:
                           [B] the bracket, [D] the debate (last four in, first four out), [C] bids by
                           conference, [W] every bowl by tier, [Y] your path and your title odds
  trip_week(league, g)     the week before your bowl or playoff game: the matchup, the history, who's
                           sitting out, and five days of decisions (practice, media day, curfew...)
"""
import math
import random
import textwrap
import time

from ui import (
    WIDTH,
    C,
    ask,
    clear,
    clip,
    columns,
    footer,
    key,
    pad,
    paint,
    panel,
    pause,
    section,
    title_bar,
    truncate,
)

CFP = ("NP First Round", "NP Quarterfinal", "NP Semifinal", "National Championship")
QUARTER = {1: 1, 8: 1, 9: 1, 2: 2, 7: 2, 10: 2, 3: 3, 6: 3, 11: 3, 4: 4, 5: 4, 12: 4}
PAIRS = {1: (8, 9), 2: (7, 10), 3: (6, 11), 4: (5, 12)}
HALF = {1: 4, 4: 1, 2: 3, 3: 2}


def _cp():
    import career_plus
    return career_plus


def _case(league, t, champs):
    import carousel as cz
    s = cz.season_line(league, t)
    bits = [f"{s['t25w']} ranked win{'s' if s['t25w'] != 1 else ''}"]
    if t in champs:
        bits.insert(0, f"{t.conference} champion")
    bad = sum(1 for g in league.team_games(t) if g.played and g.winner is not t
              and not (getattr(g, "ranks", None) or {}).get(g.opponent_of(t)))
    if bad:
        bits.append(f"{bad} loss{'es' if bad != 1 else ''} to unranked teams")
    return ", ".join(bits)


def _sos(league, t):
    try:
        import sos
        row = sos.of(league, t)
        return row.get("rank_played") if row else None
    except Exception:                                   # noqa: BLE001
        return None


def selection_show(league):
    cp = _cp()
    if not cp.mine(league) or not getattr(league, "playoff_seeds", None):
        return
    st = cp.state(league)
    if f"sel:{league.year}" in st["seen"]:
        return
    st["seen"].append(f"sel:{league.year}")
    team = league.user_team
    seeds = list(league.playoff_seeds)
    champs = set(getattr(league, "conf_champs", {}).values())
    import committee
    order = [t for t in committee.order_for_selection(league) if t not in seeds and not getattr(t, "fcs", False)]
    clear()
    print(title_bar(f"{league.year} SELECTION DAY · THE PLAYOFF FIELD"))
    top = seeds[0]
    chair = random.Random(f"chair:{league.year}").choice(["Dana Whitfield", "Marcus Ollery", "Joan Petrakis", "Ray Castellanos"])
    why = _case(league, top, champs)
    why = why[:1].upper() + why[1:]
    print(paint(f"\n   Committee chair {chair}: \"{top.school} was our clear No. 1. {why}. "
                "The hardest\n   conversation was the last spot in the field, and it went late into the night.\"\n", C.BCYAN, C.ITALIC))
    print(paint("   The five highest-ranked conference champions are in, then seven at-large. Seeds 1-4 get a bye.\n", C.GRAY))
    slow = 0.0 if getattr(league, "_fast_reveal", False) else 0.35
    for i in range(len(seeds), 0, -1):
        t = seeds[i - 1]
        me = t is team
        line = (f"   {paint(f'({i:>2})', C.BYELLOW if i <= 4 else C.BWHITE, C.BOLD)}  "
                f"{paint(pad(truncate(t.full_name, 28), 29), C.BGREEN if me else C.BWHITE, C.BOLD)}{pad(t.record, 6)}"
                f"{paint(truncate(_case(league, t, champs), 50), C.GRAY)}" + (paint("  ◀ YOU", C.BGREEN, C.BOLD) if me else ""))
        print(clip(line, WIDTH), flush=True)
        if slow:
            time.sleep(slow)
    print(paint("\n   First four out: " + ", ".join(f"{t.school} ({t.record})" for t in order[:4]), C.GRAY))
    print()
    _your_line(league, team, seeds)
    page = None
    while True:
        footer(key("B", "bracket"), key("D", "the debate"), key("C", "conferences"), key("W", "the bowls"),
               *([key("Y", "your path")] if team in seeds else []), key("Enter", "continue", C.BGREEN))
        c = ask("Select:").strip().lower()
        if c in ("b", "d", "c", "w") or (c == "y" and team in seeds):
            page = c
            clear()
            {"b": lambda: _bracket(league, seeds, team), "d": lambda: _debate(league, seeds, order, champs, team),
             "c": lambda: _confs(league, seeds), "w": lambda: _bowls(league, team), "y": lambda: _path(league, seeds, team)}[page]()
        else:
            return


def _your_line(league, team, seeds):
    cp = _cp()
    if team in seeds:
        s = seeds.index(team) + 1
        if s <= 4:
            print(paint(f"   You're the No. {s} seed: a bye, and a quarterfinal in a bowl on New Year's.", C.BGREEN, C.BOLD))
        else:
            g = next((x for x in league.schedule.get(15, []) if team in (x.home, x.away)), None)
            if g:
                o = g.opponent_of(team)
                print(paint(f"   You're the No. {s} seed: {'home vs' if g.home is team else 'at'} No. {seeds.index(o) + 1} "
                            f"{o.school} in the first round.", C.BGREEN, C.BOLD))
        cp._log(league, (league.year, f"In the playoff as the No. {s} seed."))
        cp._story(league, "landmark", f"Selection Day: {team.school} is in the playoff as the No. {s} seed.")
        cp.state(league)["stories"][-1]["w"] = 55
    else:
        g = next((x for x in league.schedule.get(16, []) if team in (x.home, x.away) and x.game_type == "Bowl"), None)
        import committee
        out = [t for t in committee.order_for_selection(league) if t not in seeds][:4]
        if team in out:
            print(paint(f"   So close: you're No. {out.index(team) + 1} among the first four out.", C.BYELLOW, C.BOLD))
            cp._story(league, "landmark", f"Snubbed: {team.school} is among the first four out of the playoff.")
        if g:
            o = g.opponent_of(team)
            print(paint(f"   You're going bowling: the {g.bowl_name} vs {o.school} ({o.record}), {g.venue}.", C.BCYAN, C.BOLD))
        elif team.wins >= 6:
            print(paint("   Bowl eligible, but no bowl had room. The season's over.", C.BYELLOW))
        else:
            print(paint("   No bowl this year. The offseason starts now.", C.GRAY))


def _bracket(league, seeds, team):
    print(title_bar(f"{league.year} PLAYOFF BRACKET"))
    smap = {t: i + 1 for i, t in enumerate(seeds)}

    def nm(s):
        t = seeds[s - 1]
        txt = f"({s:>2}) {truncate(t.school, 17)}"
        return paint(pad(txt, 23), C.BGREEN if t is team else C.BWHITE, C.BOLD if t is team else "")
    print()
    for half in ((1, 4), (2, 3)):
        for q in half:
            a, b = PAIRS[q]
            fr = next((g for g in league.schedule.get(15, []) if {smap.get(g.home), smap.get(g.away)} == {a, b}), None)
            site = paint(f"at {seeds[a - 1].stadium}", C.GRAY) if fr else ""
            qf = getattr(fr, "next_game", None) or "quarterfinal"
            print(f"   {nm(a)}─┐")
            print(f"   {pad('', 23)} ├─ winner ─┐   {site}")
            print(f"   {nm(b)}─┘          │")
            print(f"   {nm(q)}────────────┴─ {paint(qf, C.BCYAN)}")
            print()
        print(paint(f"   ── semifinal: the No. {half[0]} and No. {half[1]} quarters meet ──\n", C.BYELLOW))
    print(paint("   The two semifinal winners play for the national title.", C.GRAY))


def _debate(league, seeds, order, champs, team):
    print(title_bar("THE DEBATE · LAST FOUR IN, FIRST FOUR OUT"))
    at_large = [t for t in seeds if t not in champs]
    last_in = at_large[-4:]
    first_out = order[:4]
    import carousel as cz
    print(paint(f"\n   {'':4}{'TEAM':<22}{'REC':<7}{'RANKED W':<10}{'BAD L':<7}{'SOS':<6}THE CASE", C.GRAY, C.BOLD))
    for label, rows, col in (("IN", last_in, C.BGREEN), ("OUT", first_out, C.BRED)):
        for t in rows:
            s = cz.season_line(league, t)
            bad = sum(1 for g in league.team_games(t) if g.played and g.winner is not t
                      and not (getattr(g, "ranks", None) or {}).get(g.opponent_of(t)))
            sr = _sos(league, t)
            why = ("beat the teams it had to" if s["t25w"] >= 2 and bad == 0 else
                   "the schedule carried it" if sr and sr <= 20 else
                   "the eye test" if label == "IN" else
                   "not enough on the résumé" if s["t25w"] <= 1 else "a loss it couldn't explain" if bad else "the numbers")
            me = t is team
            print(clip(f"   {paint(pad(label, 4), col, C.BOLD)}{paint(pad(truncate(t.school, 21), 22), C.BGREEN if me else C.BWHITE, C.BOLD if me else '')}"
                       f"{pad(t.record, 7)}{pad(str(s['t25w']), 10)}{pad(str(bad), 7)}{pad(str(sr or '—'), 6)}{paint(why, C.GRAY)}", WIDTH))
    if first_out:
        t = first_out[0]
        coach = getattr(t.coach, "name", "Their coach")
        print(paint(f"\n   {coach} ({t.school}): \"We did everything they asked. I'd like somebody to explain the difference "
                    "to my seniors.\"", C.BCYAN, C.ITALIC))


def _confs(league, seeds):
    print(title_bar("BIDS BY CONFERENCE"))
    by = {}
    for i, t in enumerate(seeds, 1):
        by.setdefault(t.conference, []).append((i, t))
    print()
    for conf, rows in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        print(clip(f"   {paint(pad(conf, 18), C.BWHITE, C.BOLD)}{paint(pad(str(len(rows)), 4), C.BYELLOW, C.BOLD)}"
                   + ", ".join(f"({i}) {t.school}" for i, t in rows), WIDTH))
    shut = sorted({t.conference for t in league.teams if not getattr(t, "fcs", False)} - set(by) - {"Independent"})
    if shut:
        print(paint(f"\n   Shut out: {', '.join(shut)}", C.GRAY))


def _bowls(league, team):
    print(title_bar(f"{league.year} BOWL SEASON"))
    bowls = sorted((g for g in league.schedule.get(16, []) if g.game_type == "Bowl"), key=lambda g: (getattr(g, "tier", 9), g.date))
    names = {1: "THE MAJOR BOWLS", 2: "THE SECOND TIER", 3: "THE EARLY BOWLS"}
    last = None
    for g in bowls[:34]:
        tier = getattr(g, "tier", 3)
        if tier != last:
            last = tier
            print(section(names.get(tier, "BOWLS"), C.BCYAN))
        me = team in (g.home, g.away)
        when = g.date.strftime("%b %-d") if getattr(g, "date", None) else ""
        print(clip(f"   {paint(pad(when, 7), C.GRAY)}{paint(pad(truncate(g.bowl_name, 24), 25), C.BGREEN if me else C.BWHITE)}"
                   f"{pad(truncate(g.away.school, 16) + ' ' + g.away.record, 24)}vs  {truncate(g.home.school, 16)} {g.home.record}"
                   + (paint("  ◀", C.BGREEN, C.BOLD) if me else ""), WIDTH))
    if len(bowls) > 34:
        print(paint(f"   …and {len(bowls) - 34} more. Tab 2 → [W] for every game.", C.GRAY))


def _p(league, a, b, site=0):
    import carousel as cz
    return cz.win_prob(a, b, site, league)


def _path(league, seeds, team):
    print(title_bar(f"YOUR PATH · {team.school.upper()}"))
    s = seeds.index(team) + 1
    q = QUARTER[s]
    steps = []
    if s > 4:
        a, b = PAIRS[q]
        opp = seeds[(b if s == a else a) - 1]
        steps.append(("First round", opp, 1 if s < (b if s == a else a) else -1))
        steps.append(("Quarterfinal", seeds[q - 1], 0))
    else:
        a, b = PAIRS[q]
        fav = seeds[a - 1] if _p(league, seeds[a - 1], seeds[b - 1], 1) >= 0.5 else seeds[b - 1]
        steps.append(("Quarterfinal", fav, 0))
    steps.append(("Semifinal", seeds[HALF[q] - 1], 0))
    other = [x for x in (1, 2, 3, 4) if x not in (q, HALF[q])]
    steps.append(("Title game", seeds[min(other) - 1], 0))
    odds = 1.0
    print()
    for rnd, opp, site in steps:
        p = _p(league, team, opp, site)
        odds *= p
        col = C.BGREEN if p >= 0.6 else C.BYELLOW if p >= 0.4 else C.BRED
        print(f"   {paint(pad(rnd, 14), C.GRAY)}{'likely ' if rnd in ('Semifinal', 'Title game') or (rnd == 'Quarterfinal' and s <= 4) else ''}"
              f"{pad(opp.school, 20)}{pad(opp.record, 7)}{paint(f'{p * 100:.0f}%', col, C.BOLD)}")
    print(paint(f"\n   Title odds, the way the bracket sits: {odds * 100:.1f}%"
                + ("  (a bye is worth a lot)" if s <= 4 else ""), C.BYELLOW, C.BOLD))


# ═══ The trip ═══════════════════════════════════════════════════════════════

DAYS = [
    ("Arrival", [("Team dinner on the bowl's dime", {"chem": 2}),
                 ("Install walkthrough before anybody unpacks", {"lift": 0.1, "team_morale": -1})]),
    ("Practice", [("Full pads, the whole game plan", {"lift": 0.25, "inj": 1.15}),
                  ("A normal week of work", {"lift": 0.1}),
                  ("Give the young guys the reps", {"lift": -0.05, "_young": 1.1})]),
    ("Community day", [("Children's hospital visit", {"chem": 2, "team_morale": 1}),
                       ("The title sponsor's event", {"money": 75_000, "money_what": "the bowl sponsor's appearance fee"}),
                       ("Skip it: extra film", {"lift": 0.1, "team_morale": -2})]),
    ("Media day", [("Give them nothing", {"clutch": 0.05}),
                   ("Say we're the better team", {"lift": 0.12, "opp_lift": 0.1}),
                   ("Praise the other side", {"opp_lift": -0.05})]),
    ("The last night", [("Curfew at ten", {"lift": 0.1, "team_morale": -2}),
                        ("Team night out", {"team_morale": 3, "chem": 1, "lift": -0.05}),
                        ("Let the seniors decide", {"chem": 2, "team_morale": 1})]),
]


def _history(league, school, bowl=None):
    """(wins, losses, last appearance in this bowl or None) from the archive."""
    import archive
    w = l_ = 0
    last = None
    for y in archive.seasons(league):
        for g in archive.games_for(league, y, school):
            if g.game_type != "Bowl":
                continue
            won = g.winner.school == school
            w += won
            l_ += not won
            if bowl and g.bowl_name == bowl and (last is None or y > last[0]):
                last = (y, won, g.opponent_of(g.home if g.home.school == school else g.away).school)
    return w, l_, last


def trip_week(league, g):
    cp = _cp()
    if not cp.mine(league) or g is None or g.week != league.week + 1:
        return
    if g.game_type != "Bowl" and g.game_type not in CFP[1:]:
        return
    st = cp.state(league)
    tag = f"trip:{league.year}:{g.game_type}"
    if tag in st["seen"] or (g.game_type == "Bowl" and f"bowl:{league.year}" in st["seen"]):
        return
    st["seen"].append(tag)
    team = league.user_team
    opp = g.opponent_of(team)
    name = getattr(g, "display_name", None) or g.bowl_name or g.game_type
    clear()
    print(title_bar(f"{'BOWL' if g.game_type == 'Bowl' else 'PLAYOFF'} WEEK · THE {name.upper()}", league.team_color(team)))
    when = g.date.strftime("%A, %B %-d") if getattr(g, "date", None) else ""
    rk_me, rk_o = league.rankings.rank_of(team), league.rankings.rank_of(opp)
    print(f"\n   {paint(('#' + str(rk_me) + ' ') if rk_me else '', C.BYELLOW)}{paint(team.school, C.BWHITE, C.BOLD)} ({team.record}) vs "
          f"{paint(('#' + str(rk_o) + ' ') if rk_o else '', C.BYELLOW)}{paint(opp.school, C.BWHITE, C.BOLD)} ({opp.record})"
          f"   {paint(g.venue, C.GRAY)}{paint('  ·  ' + when, C.GRAY) if when else ''}")
    try:
        import postseason as ps
        lore = ps.BOWL_LORE.get(g.bowl_name)
        if lore:
            for ln in textwrap.wrap(random.Random(f"lore:{league.year}:{g.bowl_name}").choice(lore), 92):
                print(paint("   " + ln, C.BCYAN, C.ITALIC))
    except Exception:                                   # noqa: BLE001, S110
        pass
    import scout
    p = _p(league, team, opp, 0)
    spread = -math.log(p / (1 - p)) * 6.5 if 0.01 < p < 0.99 else (-30 if p >= 0.99 else 30)
    line = f"{team.abbr} {spread:+.1f}".replace("+-", "-") if abs(spread) >= 0.5 else "pick 'em"
    left = [f"{paint('Offense', C.GRAY)}  {pad(scout.team(team.offense_ovr), 12)}vs their D {scout.team(opp.defense_ovr)}",
            f"{paint('Defense', C.GRAY)}  {pad(scout.team(team.defense_ovr), 12)}vs their O {scout.team(opp.offense_ovr)}",
            f"{paint('Win chance', C.GRAY)} {paint(f'{p * 100:.0f}%', C.BYELLOW, C.BOLD)}   {paint('Line', C.GRAY)} {line}",
            f"{paint('Their coach', C.GRAY)} {getattr(opp.coach, 'name', '?')}"]
    if g.game_type == "Bowl":
        w, l_, last = _history(league, team.school, g.bowl_name)
        ow, ol, olast = _history(league, opp.school, g.bowl_name)
        right = [f"{paint(team.school, C.BWHITE, C.BOLD)}: {w}-{l_} in bowls on record",
                 paint(f"  last here: {last[0]} ({'won' if last[1] else 'lost'} vs {last[2]})" if last else "  first trip to this bowl", C.GRAY),
                 f"{paint(opp.school, C.BWHITE, C.BOLD)}: {ow}-{ol} in bowls on record",
                 paint(f"  last here: {olast[0]} ({'won' if olast[1] else 'lost'} vs {olast[2]})" if olast else "  first trip to this bowl", C.GRAY)]
    else:
        right = [paint("The playoff. Neutral site, national TV,", C.GRAY), paint("and nothing after this if you lose.", C.GRAY)]
    stake = f"A win: {team.wins + 1} wins" + (f", and your {_bowl_wins(league) + 1}{_ord(_bowl_wins(league) + 1)} bowl win" if g.game_type == "Bowl" else "")
    right += ["", paint(stake, C.BGREEN)]
    for ln in columns(panel("THE MATCHUP", left, 52, height=6), panel("THE HISTORY", right, 47, height=6)):
        print(ln)
    print(section("WHO'S SITTING OUT", C.BRED))
    for t in (team, opp):
        outs = [x for x in t.roster if getattr(x, "inj_games", 0) > 0 and "opted out" in str(getattr(x, "inj_desc", ""))]
        hurt = [x for x in t.roster if getattr(x, "inj_games", 0) > 0 and x not in outs and cp._is_starter(t, x)]
        txt = (", ".join(f"{x.position} {x.name} (opt-out)" for x in outs[:4]) +
               ("; " if outs and hurt else "") + ", ".join(f"{x.position} {x.name} (hurt)" for x in hurt[:3])) or "Everybody's playing."
        print(clip(f"   {pad(t.school, 18)}{txt}", WIDTH))
    pause("Press Enter for the week...")
    _days(league, g, name)
    cp._log(league, (league.year, f"{'Bowl trip' if g.game_type == 'Bowl' else 'Playoff week'}: the {name} vs {opp.school}."))


def _ord(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _bowl_wins(league):
    try:
        import cp_ach
        return cp_ach.context(league)[0]["bowl_wins"]
    except Exception:                                   # noqa: BLE001
        return 0


def _days(league, g, name):
    import effects
    cp = _cp()
    team = league.user_team
    picks = []
    for i, (day, opts) in enumerate(DAYS, 1):
        clear()
        print(title_bar(f"THE {name.upper()} · DAY {i} OF {len(DAYS)} · {day.upper()}", league.team_color(team)))
        print()
        for j, (lab, fx) in enumerate(opts, 1):
            shown = {k: v for k, v in fx.items() if not k.startswith("_")}
            extra = paint(" · the freshmen get real reps (development)", C.BGREEN) if "_young" in fx else ""
            print(f"   {paint(f'[{j}]', C.BYELLOW, C.BOLD)} {paint(lab, C.BWHITE, C.BOLD)}")
            print(f"       {effects.hint(shown) if shown else ''}{extra}")
        c = ask("Your call (Enter = the first):").strip()
        k = int(c) - 1 if c.isdigit() and 1 <= int(c) <= len(opts) else 0
        lab, fx = opts[k]
        fx = dict(fx)
        if fx.pop("_young", None):
            young = sorted((p for p in team.roster if p.year <= 1), key=lambda p: -p.potential)[:4]
            fx["also"] = [{"who": p, "dev": 1.1} for p in young]
        out = effects.apply(league, fx, f"{name} week: {lab.lower()}") or []
        picks.append((day, lab))
        for ln in out:
            print(paint("   " + ln, C.GRAY))
    cp.state(league).setdefault("trips", {})[f"{league.year}:{g.game_type}"] = picks
    clear()
    print(title_bar(f"THE {name.upper()} · GAME DAY", league.team_color(team)))
    print()
    for day, lab in picks:
        print(f"   {paint(pad(day, 16), C.GRAY)}{lab}")
    print(paint("\n   The week's done. Everything you chose is on the game-day plan.", C.BGREEN))
    pause()
