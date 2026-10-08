"""
committee_screens.py — The Playoff Rankings and the people who make them.

  playoff_rankings()   the committee's Top 25, blended with the poll
  members_screen()     the twelve members: who they are, how they vote
  member_ballot()      one member's own Top 25 next to the committee's
  team_votes()         where every member put one team
"""
import committee as cm
from ui import C, ask, bar, clear, pad, paint, pause, rule, section, title_bar, truncate


def _move(now, before):
    if before is None:
        return paint("NEW", C.BCYAN)
    d = before - now
    if d > 0:
        return paint(f"▲{d}", C.BGREEN)
    if d < 0:
        return paint(f"▼{-d}", C.BRED)
    return paint("—", C.GRAY)


def _field(league):
    """Who's in: the real field after Selection Day, a projection before it."""
    if getattr(league, "playoff_seeds", None):
        return {t: i + 1 for i, t in enumerate(league.playoff_seeds)}, set(getattr(league, "conf_champs", {}).values())
    import media_center
    field, auto, _ = media_center.projection(league)
    return {t: i + 1 for i, t in enumerate(field)}, auto


def playoff_rankings(league):
    c = cm.get(league)
    while True:
        clear()
        if not c.released or c.year != league.year:
            print(title_bar(f"{league.year} COLLEGE FOOTBALL PLAYOFF RANKINGS"))
            print()
            print(paint(f"   The Selection Committee releases its first rankings after week {cm.FIRST_RELEASE}.", C.BYELLOW))
            print(paint("   Until then, the Media Top 25 is the only ranking there is — and it doesn't pick the playoff.", C.GRAY))
            print()
            print(paint("   [M] meet the committee   [B] back", C.GRAY))
            if ask("Select:").strip().lower() == "m":
                members_screen(league)
                continue
            return
        final = c.week >= cm.LAST_WEEK
        label = "FINAL RANKINGS · SELECTION DAY" if final else f"AFTER WEEK {c.week}"
        print(title_bar(f"{league.year} NP RANKINGS  ·  {label}"))
        print(paint(f"   Twelve members rank the country; their average ballot counts {int(cm.COMMITTEE_WEIGHT * 100)}%, "
                    f"the media poll {100 - int(cm.COMMITTEE_WEIGHT * 100)}%. Head-to-head breaks near-ties.", C.GRAY))
        seeds, auto = _field(league)
        tag = "SEED" if getattr(league, "playoff_seeds", None) else "PROJ"
        print(paint(f"   {'RK':<4}{'TEAM':<24}{'CONF':<14}{'REC':<7}{'MOVE':<6}{'COMM AVG':>8}  {'#1':>3}  "
                    f"{'POLL':>4}  {tag:>5}", C.GRAY, C.BOLD))
        ballots = c.ballots.get(c.week, {})
        order = c.order[:25]
        for i, t in enumerate(order, 1):
            col = league.conference_color(t.conference)
            firsts = sum(1 for b in ballots.values() if b and b[0] is t)
            ap = league.rankings.rank_of(t)
            s = seeds.get(t)
            seed = paint(f"({s})" + ("*" if t in auto else " "), C.BGREEN, C.BOLD) if s else ""
            print(f"   {paint(pad(str(i), 4), C.BYELLOW if i <= 4 else C.BWHITE)}"
                  f"{pad(paint(truncate(t.school, 22), col, C.BOLD), 24)}{paint(pad(t.conference, 14), C.GRAY)}"
                  f"{pad(t.record, 7)}{pad(_move(i, c.previous_rank(t)), 6)}"
                  f"{pad(f'{c.avg.get(t, 0):.1f}', 8, 'right')}  {pad(str(firsts) if firsts else '', 3, 'right')}  "
                  f"{pad('#' + str(ap) if ap else 'NR', 4, 'right')}  {pad(seed, 5, 'right')}")
        out = [t for t in c.order[25:31]]
        if out:
            print(paint("   Next up: " + ", ".join(f"{t.school} ({t.record})" for t in out), C.GRAY))
        print(paint(f"   {tag}: {'the seeded field' if tag == 'SEED' else 'the field if the season ended today'}"
                    f"; * = conference champion's automatic bid.  #1 = first-place ballots.", C.GRAY))
        print(rule())
        print(paint("   [#] how every member ranked that team   [M] the committee   [E] edit these rankings   [B] back", C.GRAY))
        import webview
        if webview.on():
            try:
                me = getattr(league, "user_team", None)
                webview.emit("cfp", {"title": f"{league.year} NP Rankings", "label": label.title(), "tag": tag,
                                     "weight": int(cm.COMMITTEE_WEIGHT * 100), "rows": [
                    {"rank": i, "school": t.school, "conf": t.conference, "record": t.record,
                     "move": None if c.previous_rank(t) is None else c.previous_rank(t) - i, "new": c.previous_rank(t) is None,
                     "avg": round(c.avg.get(t, 0), 1), "firsts": sum(1 for b in ballots.values() if b and b[0] is t),
                     "poll": league.rankings.rank_of(t), "seed": seeds.get(t), "auto": t in auto, "me": t is me,
                     "color": webview._color(league, t)} for i, t in enumerate(order, 1)],
                    "next": [f"{t.school} ({t.record})" for t in out]})
            except Exception:
                pass
        choice = ask("Select:").strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(order):
            team_votes(league, order[int(choice) - 1])
        elif choice == "e":
            import ranking_editor
            ranking_editor.edit(league, "cfp")
        elif choice == "m":
            members_screen(league)
        else:
            return


def members_screen(league):
    c = cm.get(league)
    while True:
        clear()
        print(title_bar(f"COLLEGE FOOTBALL PLAYOFF SELECTION COMMITTEE  ·  {league.year}"))
        print(paint("   Three-year terms, a few seats turning over each winter. Recently retired coaches fill them.",
                    C.GRAY))
        print(paint("   Nobody votes on a school he's tied to.", C.GRAY))
        print()
        for i, m in enumerate(c.members, 1):
            new = paint("  NEW", C.BCYAN, C.BOLD) if m.since == league.year else ""
            print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {pad(paint(m.name, C.BWHITE, C.BOLD), 24)}"
                  f"{pad(truncate(m.background, 38), 40)}{paint(f'{m.since}–{m.term_end}', C.GRAY)}{new}")
            print(paint(f"        {m.lean} voter — {m.notes()}", C.GRAY))
        changes = c.changes.get(league.year)
        if changes:
            print()
            print(paint("   This year: " + "; ".join(f"{new} replaces {old}" for old, new in changes), C.BCYAN))
        print(rule())
        print(paint("   [#] his ballot and how he weighs things   [P] past members   [B] back", C.GRAY))
        choice = ask("Select:").strip().lower()
        if choice.isdigit() and 1 <= int(choice) <= len(c.members):
            member_ballot(league, c.members[int(choice) - 1])
        elif choice == "p":
            past_members(league)
        else:
            return


def member_ballot(league, m):
    c = cm.get(league)
    clear()
    print(title_bar(f"{m.name.upper()}  ·  SELECTION COMMITTEE"))
    print(f"   {paint(m.background, C.BWHITE)}   {paint(f'on the committee {m.since}–{m.term_end}', C.GRAY)}")
    print(paint(f"   {m.lean} voter — {m.notes()}.", C.GRAY))
    if m.school:
        print(paint(f"   Recused: {m.school}.", C.GRAY))
    if m.coach is not None and m.coach.history:
        w = sum(s["w"] for s in m.coach.history)
        l = sum(s["l"] for s in m.coach.history)
        print(paint(f"   Coached {w}-{l} in this world; last at {m.coach.history[-1]['school']}.", C.GRAY))
    print()
    print(section("HOW HE WEIGHS A RÉSUMÉ", C.BCYAN))
    top = max(m.weights.values())
    for k in cm.CRITERIA:
        v = m.weights[k]
        rel = v / cm.BASE[k]
        word = "more than most" if rel >= 1.35 else "less than most" if rel <= 0.75 else ""
        label = {"bad_losses": "penalty: bad losses", "g5": "penalty: G5 schedule"}.get(k, cm.LABELS[k])
        print(f"   {pad(label, 30)}{bar(v / top * 100, 24)}  {paint(word, C.BYELLOW if rel >= 1.35 else C.GRAY)}")
    print()
    ballot = c.ballots.get(c.week, {}).get(m.name) if c.released and c.year == league.year else None
    if not ballot:
        print(paint(f"   No ballot yet this season — the committee first votes after week {cm.FIRST_RELEASE}.", C.GRAY))
        pause()
        return
    print(section(f"HIS BALLOT  ·  AFTER WEEK {c.week}", C.BCYAN))
    print(paint(f"   {'HIS':<5}{'TEAM':<22}{'REC':<7}{'NP':>4}  DIFF", C.GRAY, C.BOLD))
    rows = []
    for i, t in enumerate(ballot, 1):
        cr = c.rank_of(t)
        diff = "" if cr is None else (paint(f"+{cr - i}", C.BGREEN) if cr > i else
                                        paint(f"{cr - i}", C.BRED) if cr < i else paint("=", C.GRAY))
        rows.append(f"   {pad(str(i), 5)}{pad(truncate(t.school, 20), 22)}{pad(t.record, 7)}"
                    f"{pad('#' + str(cr) if cr else 'NR', 4, 'right')}  {diff}")
    half = (len(rows) + 1) // 2
    for a, b in zip(rows[:half], rows[half:] + [""]):
        print(pad(a, 50) + b.lstrip() if b else a)
    print(paint("   DIFF: + he has them higher than the committee does, - lower.", C.GRAY))
    pause()


def team_votes(league, team):
    c = cm.get(league)
    clear()
    rk = c.rank_of(team)
    print(title_bar(f"{team.school.upper()}  ·  NP #{rk}  ·  {team.record}"))
    print(paint(f"   Committee average {c.avg.get(team, 0):.1f}   ·   media poll "
                f"{'#' + str(league.rankings.rank_of(team)) if league.rankings.rank_of(team) else 'unranked'}", C.GRAY))
    print()
    _, raw = c._resume(league)
    r = raw.get(team)
    if r:
        print(section("THE RÉSUMÉ THEY'RE LOOKING AT", C.BCYAN))
        print(f"   Quality-win points {r['quality']:.1f}   ·   bad-loss points {r['bad_losses']:.1f}   ·   "
              f"avg margin {r['margin']:+.1f}   ·   last four {int(r['form'] * 4)}-{4 - int(r['form'] * 4)}   ·   "
              f"schedule index {r['schedule']:.0f}")
        print()
    print(section("EVERY BALLOT", C.BCYAN))
    for m in c.members:
        if m.school == team.school:
            spot = paint("recused", C.GRAY)
        else:
            mr = c.member_rank(m, team)
            spot = paint(f"#{mr}", C.BWHITE, C.BOLD) if mr else paint("off his ballot", C.GRAY)
        print(f"   {pad(m.name, 24)}{pad(spot, 16)}{paint(m.lean + ' voter', C.GRAY)}")
    pause()


def past_members(league):
    c = cm.get(league)
    clear()
    print(title_bar("SELECTION COMMITTEE  ·  FORMER MEMBERS"))
    if not c.past:
        print(paint("\n   Nobody has rotated off yet.", C.GRAY))
    for name, bg, since, left in reversed(c.past[-30:]):
        print(f"   {pad(name, 24)}{pad(truncate(bg, 40), 42)}{paint(f'{since}–{left}', C.GRAY)}")
    if c.history:
        print()
        print(section("FINAL TOP 4, EVERY YEAR", C.BCYAN))
        for yr in sorted(c.history, reverse=True):
            print(f"   {yr}   " + ", ".join(c.history[yr][:4]))
    pause()
