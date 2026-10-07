"""
ranking_editor.py — Edit the media Top 25 and the NP Playoff Rankings by hand.

Your edits replace the current poll or rankings. They hold until the next vote, after a week of games, and
that vote starts from your order. Voters still move teams a step at a time, so your order carries into the
next week. If you edit the final Playoff Rankings after the field is set, you're asked whether to seed the
playoff and the bowls again from your order.
"""
import committee as cm
from rankings import TOP_N
from ui import C, ask, clear, confirm, pad, paint, pause, rule, title_bar, truncate

SHOW = 30


def _log(league, which, text):
    league.__dict__.setdefault("ranking_edits", []).append((league.year, league.week, which, text))


def edited(league, which):
    """Has this year's poll ('ap') or ranking ('cfp') been edited by hand?"""
    return any(y == league.year and w == which for y, _, w, _ in getattr(league, "ranking_edits", []))


def _find(league, order, text):
    """A team from a rank number or part of its name."""
    text = text.strip()
    if not text:
        return None
    if text.isdigit():
        i = int(text)
        return order[i - 1] if 1 <= i <= len(order) else None
    low = text.lower()
    exact = [t for t in league.teams if t.school.lower() == low]
    if exact:
        return exact[0]
    hits = [t for t in league.teams if low in t.school.lower() or low in f"{t.school} {t.nickname}".lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        print(paint(f"   No team matches '{text}'.", C.BRED))
        return None
    hits.sort(key=lambda t: order.index(t) if t in order else 999)
    for i, t in enumerate(hits[:9], 1):
        print(f"   {paint(f'[{i}]', C.BYELLOW, C.BOLD)} {t.school} {t.nickname} ({t.record})")
    pick = ask("Which one?").strip()
    return hits[int(pick) - 1] if pick.isdigit() and 1 <= int(pick) <= min(9, len(hits)) else None


def _rank(text, top):
    text = text.strip()
    return int(text) if text.isdigit() and 1 <= int(text) <= top else None


# ── applying an order ─────────────────────────────────────────────────

def _apply_ap(league, order):
    r = league.rankings
    rest = [t for t in r.order if t not in order] + [t for t in league.teams if t not in r.order and t not in order]
    full = list(order) + rest
    pts = sorted((r.points.get(t, 0) for t in league.teams), reverse=True) if getattr(r, "points", None) else []
    if pts:
        r.points = {t: pts[i] for i, t in enumerate(full) if pts[i] > 0}
        firsts = sum(getattr(r, "first_place", {}).values()) if getattr(r, "first_place", None) else 0
        if firsts:
            r.first_place = {full[0]: firsts}          # your No. 1 gets the first-place votes
        r.others = [(t, r.points[t]) for t in full[TOP_N:] if r.points.get(t, 0) > 0]
    r.order = full


def _apply_cfp(league, order):
    c = cm.get(league)
    rest = [t for t in c.order if t not in order] + [t for t in league.teams if t not in c.order and t not in order]
    c.order = list(order) + rest
    if c.week >= cm.LAST_WEEK:
        c.history[league.year] = [t.school for t in c.order[:25]]


# ── re-seeding ────────────────────────────────────────────────────────

def can_reseed(league):
    """The field is set but nobody has played a playoff or bowl game yet."""
    if not getattr(league, "playoff_seeds", None) or league.week >= 15:
        return False
    return not any(g.played for wk in (15, 16) for g in league.schedule.get(wk, []))


def reseed(league):
    """Run Selection Day again from the current Playoff Rankings: the field, the seeds and the bowls."""
    import season
    for t in league.playoff_seeds or []:
        if "NP Appearance" in t.achievements:
            t.achievements.reverse()
            t.achievements.remove("NP Appearance")
            t.achievements.reverse()
    for conf, t in (getattr(league, "conf_champs", None) or {}).items():
        tag = f"{conf} Champion"
        if tag in t.achievements:
            t.achievements.reverse()
            t.achievements.remove(tag)
            t.achievements.reverse()
    league.schedule[15], league.schedule[16] = [], []
    league.playoff_seeds, league.playoff_seed_map = [], {}
    season.generate_postseason_week(league, 15)
    return league.playoff_seeds


# ── the screen ────────────────────────────────────────────────────────

def _draw(league, which, order, orig):
    clear()
    name = "MEDIA TOP 25" if which == "ap" else "NP PLAYOFF RANKINGS"
    print(title_bar(f"{league.year} · EDIT THE {name}"))
    was = {t: i for i, t in enumerate(orig, 1)}
    seeds = {t: i for i, t in enumerate(getattr(league, "playoff_seeds", None) or [], 1)} if which == "cfp" else {}
    print(paint(f"   {'RK':<4}{'TEAM':<26}{'CONF':<15}{'REC':<7}{'WAS':>4}", C.GRAY))
    for i, t in enumerate(order[:SHOW], 1):
        if i == TOP_N + 1:
            print(paint("   ── outside the top 25 ──", C.GRAY))
        w = was.get(t)
        moved = "" if w == i else (paint(f"{w:>4}", C.BYELLOW) if w and w <= SHOW else paint("  NR", C.BYELLOW))
        seed = paint(f"  seed {seeds[t]}", C.BGREEN) if t in seeds else ""
        print(f"   {paint(pad(str(i), 4), C.BWHITE if i <= TOP_N else C.GRAY)}"
              f"{pad(paint(truncate(t.school, 24), league.conference_color(t.conference), C.BOLD), 26)}"
              f"{paint(pad(t.conference, 15), C.GRAY)}{pad(t.record, 7)}{moved}{seed}")
    print(rule())
    print(f"   {paint('[M]', C.BYELLOW, C.BOLD)} Move a team   {paint('[S]', C.BYELLOW, C.BOLD)} Swap two   "
          f"{paint('[A]', C.BYELLOW, C.BOLD)} Add an unranked team   {paint('[D]', C.BYELLOW, C.BOLD)} Drop from the top 25")
    print(f"   {paint('[U]', C.BYELLOW, C.BOLD)} Undo my changes   {paint('[V]', C.BGREEN, C.BOLD)} Save   "
          f"{paint('[B]', C.GRAY)} Back without saving")
    print(paint("   Pick a team by its rank or by name.", C.GRAY))


def edit(league, which):
    """which: 'ap' (the media poll) or 'cfp' (the committee's Playoff Rankings)."""
    if which == "cfp":
        c = cm.get(league)
        if not c.released or c.year != league.year:
            clear()
            print(title_bar(f"{league.year} · EDIT THE NP PLAYOFF RANKINGS"))
            print(paint(f"\n   The committee hasn't released its rankings yet (first release after week {cm.FIRST_RELEASE}).", C.BYELLOW))
            print(paint("   Until then the playoff reads the media poll, so edit that instead.", C.GRAY))
            pause()
            return False
        source = c.order
    else:
        source = league.rankings.order
    orig = list(source)
    order = list(source)
    while True:
        _draw(league, which, order, orig)
        ch = ask("Select:").strip().lower()
        if ch == "m":
            t = _find(league, order, ask("Team to move (rank or name):"))
            to = _rank(ask(f"New rank (1-{SHOW}):"), SHOW) if t else None
            if t and to:
                order.remove(t)
                order.insert(to - 1, t)
        elif ch == "s":
            a = _find(league, order, ask("First team (rank or name):"))
            b = _find(league, order, ask("Second team (rank or name):")) if a else None
            if a and b and a is not b:
                i, j = order.index(a), order.index(b)
                order[i], order[j] = b, a
        elif ch == "a":
            t = _find(league, order, ask("Team to add (name):"))
            to = _rank(ask(f"At rank (1-{TOP_N}):"), TOP_N) if t else None
            if t and to:
                order.remove(t)
                order.insert(to - 1, t)
        elif ch == "d":
            t = _find(league, order, ask("Team to drop (rank or name):"))
            if t and order.index(t) < TOP_N:
                order.remove(t)
                order.insert(TOP_N, t)                # first team out
        elif ch == "u":
            order = list(orig)
        elif ch == "v":
            if order == orig:
                return False
            moved = sum(1 for i, t in enumerate(order[:TOP_N]) if i >= len(orig) or orig[i] is not t)
            (_apply_ap if which == "ap" else _apply_cfp)(league, order)
            _log(league, which, f"{moved} spots changed")
            print(paint("   Saved.", C.BGREEN, C.BOLD))
            if which == "cfp" and can_reseed(league) and confirm(
                    "The playoff field is already set. Seed the playoff and the bowls again from your rankings?", True):
                seeds = reseed(league)
                print(paint("   New field: " + ", ".join(f"{i}. {t.school}" for i, t in enumerate(seeds, 1)), C.BGREEN))
            pause()
            return True
        elif ch in ("b", ""):
            if order == orig or confirm("Leave without saving your changes?", True):
                return False


def menu(league):
    """Pick which ranking to edit."""
    while True:
        clear()
        print(title_bar(f"{league.year} · EDIT THE RANKINGS"))
        print(paint("   Your order replaces this week's. The next vote, after a week of games, starts from it.", C.GRAY))
        print(paint("   Edit the final Playoff Rankings to change the playoff field before the first round.", C.GRAY))
        print()
        print(f"   {paint('[1]', C.BYELLOW, C.BOLD)} Media Top 25{paint('  (edited this year)', C.GRAY) if edited(league, 'ap') else ''}")
        print(f"   {paint('[2]', C.BYELLOW, C.BOLD)} NP Playoff Rankings{paint('  (edited this year)', C.GRAY) if edited(league, 'cfp') else ''}")
        print(f"   {paint('[B]', C.GRAY)} Back")
        ch = ask("Select:").strip().lower()
        if ch == "1":
            edit(league, "ap")
        elif ch == "2":
            edit(league, "cfp")
        else:
            return
