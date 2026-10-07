"""
rivalries.py — Every meeting between two FBS programs, kept for good.

Your world starts in 2026, so the record book it keeps starts there too: every
game two FBS teams play is written into a ledger the moment it ends. From that
ledger come series records, streaks, the last meeting, the biggest blowout, the
closest finish — and who has the trophy.

    league.series = {"Iowa|Minnesota": [Meeting, ...], ...}     (oldest first)

The booth reads it. Before kickoff the crew knows the series since 2026 and the
streak, and when two teams met last year (or in a bowl three years ago) they
bring up what happened, including who hurt whom that day. After the final they
tell you who keeps the Saw, who takes back the Pitcher, and whose streak just died.

Trophy games come from the universe's trophy table. The holder is whoever won the last meeting in
your world; until a trophy game has been played in your save, it's "up for
grabs".
"""
from collections import namedtuple

from ui import C, ask, clear, pad, paint, pause, rule, section, title_bar, truncate

Meeting = namedtuple("Meeting", "year week winner loser wscore lscore home label star")
#   home   the home school, or None at a neutral site
#   label  "Regular Season", or the bowl / playoff / title game name
#   star   "J. Smith ran for 182 yards" — the winner's best player that day, or ""

# ── The trophies (pairs must use teams_data.py's school names) ───────────────
TROPHIES = {
    frozenset(('Michigan', 'Minnesota')): 'the Old Copper Pitcher',
    frozenset(('Minnesota', 'Wisconsin')): 'the Northwoods Saw',
    frozenset(('Iowa', 'Minnesota')): 'the Bronze Heifer',
    frozenset(('Indiana', 'Tippecanoe')): 'the Copper Kettle',
    frozenset(('Michigan', 'Michigan State')): 'the Mitten',
    frozenset(('Iowa', 'Nebraska')): 'the Missouri Crossing Trophy',
    frozenset(('Illinois', 'Lakeshore')): 'the Prairie State Lantern',
    frozenset(('Indiana', 'Michigan State')): 'the Old Tin Lunchbox',
    frozenset(('Iowa', 'Wisconsin')): 'the Driftless Trophy',
    frozenset(('Nebraska', 'Wisconsin')): 'the Silo',
    frozenset(('Minnesota', 'Pennsylvania')): 'the Iron Range Bell',
    frozenset(('Michigan State', 'Pennsylvania')): "the Founders' Plow",
    frozenset(('Minnesota', 'Nebraska')): 'the Broken Bleacher Plank',
    frozenset(('Illinois', 'Tippecanoe')): 'the Wabash Musket',
    frozenset(('Iowa', 'Iowa State')): 'the Tall Corn Trophy',
    frozenset(('Mississippi', 'Mississippi State')): 'the Magnolia Cup',
    frozenset(('Arkansas', 'Bayou State')): 'the Cottonwood Crown',
    frozenset(('Kentucky', 'Louisville')): 'the Bluegrass Bell',
    frozenset(('Georgia', 'Atlanta')): 'the Red Clay Cup',
    frozenset(('Oklahoma', 'Texas')): 'the Fairground Spur',
    frozenset(('Florida', 'Georgia')): 'the Border Lantern',
    frozenset(('Oklahoma', 'Oklahoma State')): 'the Red Dirt Bell',
    frozenset(('Arizona', 'Arizona State')): 'the Canyon State Cup',
    frozenset(('California', 'Palo Alto')): 'the Golden Gate Gavel',
    frozenset(('Los Angeles', 'Southern California')): 'the Sunset Bell',
    frozenset(('Durham', 'North Carolina')): 'the Piedmont Lantern',
    frozenset(('Washington', 'Washington State')): 'the Snoqualmie Cup',
    frozenset(('Oregon', 'Oregon State')): 'the River Otter Trophy',
    frozenset(('South Bend', 'Southern California')): 'the Coast-to-Lake Compass',
    frozenset(('Michigan State', 'South Bend')): 'the Lantern of the Lakes',
    frozenset(('South Bend', 'Tippecanoe')): 'the Two Rivers Trophy',
    frozenset(('Virginia', 'Blacksburg')): 'the Blue Ridge Cup',
    frozenset(('Dallas', 'Fort Worth')): 'the Trinity Spur',
    frozenset(('Houston', 'Montrose')): 'the Bayou City Canteen',
    frozenset(('Cincinnati', 'Louisville')): 'the Paddlewheel',
    frozenset(('Southern Miss', 'New Orleans')): 'the Pine Belt Bell',
    frozenset(('Bowling Green', 'Toledo')): 'the Black Swamp Trophy',
    frozenset(('Akron', 'Kent State')): 'the Canal Lock',
    frozenset(('Central Michigan', 'Western Michigan')): 'the Mill Saw',
    frozenset(('Boise State', 'Fresno State')): 'the Ore Cart',
    frozenset(('Fresno State', 'San Diego State')): 'the Copper Pot',
    frozenset(('Nevada', 'Las Vegas')): 'the Silver State Howitzer',
    frozenset(('Arkansas', 'Missouri')): 'the Ozark Line Trophy',
    frozenset(('Kansas', 'Kansas State')): 'the Kaw Valley Cup',
    frozenset(('Fort Worth', 'Lubbock')): 'the Panhandle Spurs',
    frozenset(('Colorado', 'Colorado State')): 'the Rocky Summit Cup',
    frozenset(('Colorado State', 'Wyoming')): 'the Iron Stirrup',
    frozenset(('Utah State', 'Wyoming')): 'the Rendezvous Rifle',
}


def _key(a, b):
    a, b = sorted((a, b))
    return f"{a}|{b}"


def _school(x):
    return x if isinstance(x, str) else x.school


def ledger(league):
    return league.__dict__.setdefault("series", {})


def trophy(a, b):
    return TROPHIES.get(frozenset((_school(a), _school(b))))


def rivalry_name(a, b):
    from commentary import rivalry_name as rn
    class _S:                                   # rivalry_name wants objects with .school
        def __init__(self, s):
            self.school = s
    return rn(_S(_school(a)), _S(_school(b)))


def is_rivalry(a, b):
    a, b = _school(a), _school(b)
    if trophy(a, b) or rivalry_name(a, b):
        return True
    from carousel import PRIMARY_RIVAL, PROTECTED
    from season import RIVALRY_WEEK
    pair = frozenset((a, b))
    return (PRIMARY_RIVAL.get(a) == b or PRIMARY_RIVAL.get(b) == a
            or pair in {frozenset(p) for p in PROTECTED} or pair in {frozenset(p) for p in RIVALRY_WEEK})


# ═══ Writing the ledger ════════════════════════════════════════════════════

def _label(g):
    gt = getattr(g, "game_type", "Regular Season")
    if gt == "Regular Season":
        return gt
    return getattr(g, "display_name", None) or getattr(g, "bowl_name", None) or gt


def _star_line(box, winner):
    """The winner's best player that day, in a phrase the booth can say."""
    if box is None:
        return ""
    try:
        from impact import game_impact
        best, score = None, -1
        for p, c in box.stats.items():
            if box.team_of(p) is not winner and getattr(box.team_of(p), "school", None) != winner.school:
                continue
            v = game_impact(c)
            if v > score:
                best, score = (p, c), v
        if best is None:
            return ""
        p, c = best
        name = f"{p.first_name[0]}. {p.last_name}"
        if c["pass_yds"] >= 200:
            return f"{name} threw for {c['pass_yds']} yards and {c['pass_td']} touchdown{'s' if c['pass_td'] != 1 else ''}"
        if c["rush_yds"] >= 100:
            return f"{name} ran for {c['rush_yds']} yards"
        if c["rec_yds"] >= 100:
            return f"{name} caught {c['rec']} balls for {c['rec_yds']} yards"
        if c["sack"] >= 2:
            return f"{name} had {c['sack']:g} sacks"
        if c["int"] >= 1:
            return f"{name} picked off {c['int']} pass{'es' if c['int'] != 1 else ''}"
        if c["tkl"] >= 10:
            return f"{name} made {c['tkl']} tackles"
        if c["fg_made"] >= 3:
            return f"{name} kicked {c['fg_made']} field goals"
    except Exception:
        return ""
    return ""


def _meeting(g, year):
    w, l = g.winner, g.loser
    home = None if getattr(g, "neutral", False) else g.home.school
    return Meeting(year, g.week, w.school, l.school, g.score_for(w), g.score_for(l), home, _label(g),
                   _star_line(getattr(g, "box", None), w))


def record(league, g):
    """Write a finished game into the ledger (FBS against FBS only)."""
    if not getattr(g, "played", False) or g.winner is None:
        return
    if getattr(g.home, "fcs", False) or getattr(g.away, "fcs", False):
        return
    rows = ledger(league).setdefault(_key(g.home.school, g.away.school), [])
    m = _meeting(g, league.year)
    if rows and rows[-1][:4] == m[:4]:
        return                                            # already written (a replayed save, say)
    rows.append(m)


def rebuild(league):
    """For older saves: read every archived season (and this one) into the ledger."""
    if getattr(league, "series", None):
        return
    book = ledger(league)
    fbs = {t.school for t in league.teams}
    for year in sorted(getattr(league, "archive", {})):
        for g in league.archive[year]:
            if g.home.school in fbs and g.away.school in fbs and not getattr(g.home, "fcs", False) \
                    and not getattr(g.away, "fcs", False):
                book.setdefault(_key(g.home.school, g.away.school), []).append(_meeting(g, year))
    for w in sorted(getattr(league, "schedule", {})):
        for g in league.schedule[w]:
            if g.played:
                record(league, g)


# ═══ Reading it ═══════════════════════════════════════════════════════════

def meetings(league, a, b):
    return list(ledger(league).get(_key(_school(a), _school(b)), []))


class Series:
    def __init__(self, league, a, b):
        self.a, self.b = _school(a), _school(b)
        self.games = meetings(league, a, b)
        self.wins = {self.a: 0, self.b: 0}
        for m in self.games:
            if m.winner in self.wins:
                self.wins[m.winner] += 1
        self.trophy = trophy(self.a, self.b)
        self.name = rivalry_name(self.a, self.b)
        self.rival = is_rivalry(self.a, self.b)

    @property
    def n(self):
        return len(self.games)

    @property
    def last(self):
        return self.games[-1] if self.games else None

    @property
    def since(self):
        return self.games[0].year if self.games else None

    @property
    def leader(self):
        wa, wb = self.wins[self.a], self.wins[self.b]
        return None if wa == wb else (self.a if wa > wb else self.b)

    def record_str(self, school=None):
        """'Iowa leads 5-3' / 'tied 2-2' — or, from one side, '5-3'."""
        if school is not None:
            other = self.b if school == self.a else self.a
            return f"{self.wins.get(school, 0)}-{self.wins.get(other, 0)}"
        if self.leader is None:
            return f"tied {self.wins[self.a]}-{self.wins[self.b]}"
        other = self.b if self.leader == self.a else self.a
        return f"{self.leader} leads {self.wins[self.leader]}-{self.wins[other]}"

    @property
    def streak(self):
        """(school, n) — the current run."""
        if not self.games:
            return None, 0
        who, n = self.games[-1].winner, 0
        for m in reversed(self.games):
            if m.winner != who:
                break
            n += 1
        return who, n

    @property
    def longest(self):
        best, who, run, cur = 0, None, 0, None
        for m in self.games:
            run = run + 1 if m.winner == cur else 1
            cur = m.winner
            if run > best:
                best, who = run, cur
        return who, best

    @property
    def holder(self):
        if not self.trophy or not self.games:
            return None
        return self.games[-1].winner

    def held_since(self):
        """The year the current holder took the trophy (or first won it in your world)."""
        who, n = self.streak
        if not who:
            return None
        return self.games[-n].year

    @property
    def biggest(self):
        return max(self.games, key=lambda m: (m.wscore - m.lscore, m.year), default=None)

    @property
    def closest(self):
        return min(self.games, key=lambda m: (m.wscore - m.lscore, -m.year), default=None)

    def title(self):
        if self.trophy:
            return f"{self.a}–{self.b} · {self.trophy[4:] if self.trophy.startswith('the ') else self.trophy}"
        if self.name:
            return f"{self.a}–{self.b} · {self.name[4:] if self.name.startswith('the ') else self.name}"
        return f"{self.a}–{self.b}"


def series(league, a, b):
    return Series(league, a, b)


def _cap(s):
    return s[0].upper() + s[1:] if s else s


def _where(m):
    if m.label != "Regular Season":
        return f"in the {m.year} {m.label}" if not m.label.startswith(("NP", "National")) else \
            f"in the {m.year} {m.label}"
    if m.home is None:
        return f"at a neutral site in {m.year}"
    return f"in {m.year} at {m.home}" if m.home else f"in {m.year}"


def _ago(league, m):
    d = league.year - m.year
    return "last year" if d == 1 else "earlier this season" if d == 0 else f"back in {m.year}"


def last_meeting_line(league, a, b):
    """'The last time these two met, in the 2028 Grove Bowl, Iowa won 24-17 — K. Smith ran for 131 yards.'"""
    s = series(league, a, b)
    m = s.last
    if m is None:
        return None
    when = _ago(league, m)
    where = f" in the {m.label}" if m.label != "Regular Season" else (f" at {m.home}" if m.home else "")
    star = f" — {m.star}" if m.star else ""
    return f"The last time these two met, {when}{where}, {m.winner} won {m.wscore}-{m.lscore}{star}."


# ═══ The booth ═════════════════════════════════════════════════════════════

def pregame_lines(league, away, home, rng):
    """What the crew says about the history before kickoff: [(speaker, text)]."""
    if league is None:
        return []
    s = series(league, away, home)
    out = []
    label = s.name or (s.trophy and f"the battle for {s.trophy}") or "this series"
    if s.trophy and s.n == 0:
        out.append(("P", f"{_cap(s.trophy)} is on the line today."))
    if s.n == 0:
        if s.rival:
            out.append(("A", "First meeting in this rivalry since this world began, so nobody in either locker "
                             "room has a score to settle yet. That starts today."))
        return out
    if s.trophy and s.holder:
        yrs = league.year - s.held_since()
        hold = (f"{s.holder} has had it since {s.held_since()}" if yrs >= 2
                else f"{s.holder} took it home last time")
        out.append(("P", f"{_cap(s.trophy)} is on the line. {hold}."))
    if s.rival or s.n >= 3:
        rec = s.record_str()
        out.append(("P", f"In {label}, {rec} since {s.since}." if s.leader else
                         f"{_cap(label)} is dead even since {s.since}, {rec[5:]}."))
        who, n = s.streak
        if n >= 3:
            other = s.b if who == s.a else s.a
            out.append(("A", rng.choice((f"{who} has won {n} straight in this one. {other} is sick of hearing about it.",
                                         f"{n} in a row for {who}. That's the storyline all week in {other}.",
                                         f"{other} hasn't beaten {who} in {n} tries. You know that's on the whiteboard."))))
    line = last_meeting_line(league, away, home)
    if line and (s.rival or league.year - s.last.year <= 3):
        out.append(("A", line))
        m = s.last
        if m.wscore - m.lscore <= 3 and rng.random() < 0.7:
            out.append(("A", f"{m.wscore}-{m.lscore}. {m.loser} has been waiting a long time for this one."))
        elif m.wscore - m.lscore >= 24 and rng.random() < 0.7:
            out.append(("A", f"{m.wscore}-{m.lscore}. That one got out of hand, and {m.loser} hasn't forgotten."))
    return out


def ingame_line(league, sim, rng):
    """A mid-game callback to an older meeting, or None."""
    s = series(league, sim.away, sim.home)
    if s.n == 0:
        return None
    pick = []
    b = s.biggest
    if b is not None and b.wscore - b.lscore >= 21 and s.n >= 2:
        pick.append(("A", f"Biggest blowout in this series since {s.since}: {b.winner} {b.wscore}, "
                          f"{b.loser} {b.lscore}, back in {b.year}."))
    c = s.closest
    if c is not None and c.wscore - c.lscore <= 3 and s.n >= 2:
        pick.append(("A", f"Remember {c.year}? {c.winner} {c.wscore}, {c.loser} {c.lscore}. These two tend to "
                          f"go down to the wire."))
    who, best = s.longest
    if best >= 4:
        pick.append(("P", f"Longest streak in this series since {s.since}: {best} straight by {who}."))
    stars = [m for m in s.games if m.star and m.year < league.year]
    if stars:
        m = rng.choice(stars)
        pick.append(("A", f"{_cap(_ago(league, m))}, {m.star} against {m.loser}. They still talk about that one."))
    return rng.choice(pick) if pick else None


def final_lines(league, winner, loser, ws, ls, rng):
    """After the final whistle, as if this game were already in the ledger."""
    if league is None:
        return []
    s = series(league, winner, loser)
    out = []
    before = s.streak
    wins_w = s.wins.get(winner.school, 0) + 1
    wins_l = s.wins.get(loser.school, 0)
    if s.trophy:
        holder = s.holder
        if holder == winner.school:
            out.append(("P", f"{winner.school} keeps {s.trophy}."))
        elif holder == loser.school:
            since = s.held_since()
            if since is not None and league.year - since >= 2:
                out.append(("P", f"{winner.school} takes back {s.trophy}! {loser.school} had held it since {since}."))
            else:
                out.append(("P", f"{winner.school} takes back {s.trophy}!"))
        else:
            out.append(("P", f"{winner.school} wins {s.trophy}."))
    if s.rival or s.n >= 2:
        if wins_w > wins_l:
            rec = f"{winner.school} leads the series {wins_w}-{wins_l} since {s.since or league.year}"
        elif wins_w == wins_l:
            rec = f"The series is tied {wins_w}-{wins_l} since {s.since or league.year}"
        else:
            rec = f"{loser.school} still leads the series {wins_l}-{wins_w} since {s.since or league.year}"
        who, n = before
        if who == winner.school and n + 1 >= 3:
            out.append(("A", f"That's {n + 1} straight for {winner.school} in this one. {rec}."))
        elif who == loser.school and n >= 3:
            out.append(("A", f"And that snaps a {n}-game losing streak to {loser.school}. {rec}."))
        else:
            out.append(("A", f"{rec}."))
    return out


# ═══ Screens ══════════════════════════════════════════════════════════════

def _row(s, school=None):
    who, n = s.streak
    streak = f"{who.split()[-1] if who else ''} W{n}" if n else "—"
    last = s.last
    last_s = f"{last.year} {last.winner} {last.wscore}-{last.lscore}" if last else "never met"
    rec = s.record_str(school) if school else s.record_str()
    return rec, streak, last_s


def team_rivalries(league, team):
    """A program's rivals, its trophies, and any opponent's full history."""
    while True:
        clear()
        print(title_bar(f"{team.school.upper()} · RIVALRIES & SERIES"))
        rivals = set()
        for pair in TROPHIES:
            if team.school in pair:
                rivals.add(next(iter(pair - {team.school})))
        from carousel import PRIMARY_RIVAL, PROTECTED
        from commentary import RIVALRIES
        for (x, y) in list(RIVALRIES) + list(PROTECTED):
            if team.school in (x, y):
                rivals.add(y if x == team.school else x)
        if PRIMARY_RIVAL.get(team.school):
            rivals.add(PRIMARY_RIVAL[team.school])
        fbs = {t.school for t in league.teams}
        rivals = sorted((r for r in rivals if r in fbs),
                        key=lambda r: (-series(league, team, r).n, r))
        print()
        print(paint(f"   {'OPPONENT':<22}{'SERIES':<10}{'STREAK':<14}{'TROPHY / NAME':<34}LAST MEETING", C.GRAY))
        for r in rivals:
            s = series(league, team, r)
            rec, streak, last_s = _row(s, team.school)
            name = s.trophy or s.name or ""
            holder = ""
            if s.trophy:
                holder = paint(" ★", C.BYELLOW) if s.holder == team.school else ""
            print(f"   {pad(truncate(r, 21), 22)}{pad(rec, 10)}{pad(streak, 14)}"
                  f"{pad(truncate(name, 31) + holder, 34)}{paint(last_s, C.GRAY)}")
        if not rivals:
            print(paint("   No listed rivals.", C.GRAY))
        # Everyone else they've played the most.
        others = []
        for key, rows in ledger(league).items():
            a, b = key.split("|")
            if team.school in (a, b):
                opp = b if a == team.school else a
                if opp not in rivals:
                    others.append((len(rows), opp))
        others.sort(key=lambda x: (-x[0], x[1]))
        if others:
            print()
            print(section("MOST-PLAYED OPPONENTS SINCE 2026", C.BCYAN))
            for n, opp in others[:10]:
                s = series(league, team, opp)
                rec, streak, last_s = _row(s, team.school)
                print(f"   {pad(truncate(opp, 21), 22)}{pad(rec, 10)}{pad(streak, 14)}{pad(str(n) + ' meetings', 34)}"
                      f"{paint(last_s, C.GRAY)}")
        print(paint("\n   ★ = holds the trophy. Records count games played in your world (2026 on).", C.GRAY))
        c = ask("Type a school for the full head-to-head (Enter = back):").strip()
        if not c:
            return
        found = league.search(c)
        if not found:
            continue
        head_to_head(league, team, found[0])


def head_to_head(league, a, b):
    s = series(league, a, b)
    clear()
    print(title_bar(truncate(s.title().upper(), 70)))
    print()
    if not s.n:
        print(paint(f"   {a.school} and {b.school} haven't met since 2026.", C.GRAY))
        if s.trophy:
            print(paint(f"   {_cap(s.trophy)} is up for grabs.", C.GRAY))
        pause()
        return
    print(f"   {paint('Series', C.GRAY):<20} {s.record_str()}  (since {s.since}, {s.n} meeting{'s' if s.n != 1 else ''})")
    who, n = s.streak
    print(f"   {paint('Streak', C.GRAY):<20} {who} has won {n}")
    lw, ln = s.longest
    print(f"   {paint('Longest streak', C.GRAY):<20} {ln} — {lw}")
    if s.trophy:
        print(f"   {paint('Trophy', C.GRAY):<20} {_cap(s.trophy)} — held by {s.holder} since {s.held_since()}")
    bg, cl = s.biggest, s.closest
    print(f"   {paint('Biggest win', C.GRAY):<20} {bg.year}: {bg.winner} {bg.wscore}-{bg.lscore}")
    print(f"   {paint('Closest game', C.GRAY):<20} {cl.year}: {cl.winner} {cl.wscore}-{cl.lscore}")
    print()
    print(section("EVERY MEETING", C.BYELLOW))
    for m in reversed(s.games):
        site = m.label if m.label != "Regular Season" else (f"at {m.home}" if m.home else "neutral site")
        print(f"   {paint(str(m.year), C.GRAY)}  {pad(paint(m.winner, C.BWHITE, C.BOLD), 22)}{m.wscore:>3}-{m.lscore:<3} "
              f"{pad(m.loser, 20)}{pad(paint(truncate(site, 26), C.GRAY), 28)}{paint(truncate(m.star, 40), C.GRAY)}")
    pause()


def trophy_room(league):
    """Media Center: every trophy game and who has it."""
    clear()
    print(title_bar("RIVALRY TROPHIES"))
    print()
    print(paint(f"   {'TROPHY':<36}{'SERIES':<30}{'HOLDER':<20}STREAK", C.GRAY))
    fbs = {t.school for t in league.teams}
    rows = []
    for pair, name in TROPHIES.items():
        a, b = sorted(pair)
        if a not in fbs or b not in fbs:
            continue
        s = series(league, a, b)
        rows.append((s.n == 0, name.replace("the ", "", 1) if name.startswith("the ") else name, s, True))
    # The great rivalries with no hardware (or none in this universe's table) count too.
    from commentary import RIVALRIES
    seen = {frozenset(p) for p in TROPHIES}
    for (a, b), name in RIVALRIES.items():
        if frozenset((a, b)) in seen or a not in fbs or b not in fbs:
            continue
        seen.add(frozenset((a, b)))
        s = series(league, a, b)
        nm = name.replace("the ", "", 1) if name.startswith("the ") else name
        rows.append((s.n == 0, nm, s, False))
    for _, name, s, cup in sorted(rows, key=lambda r: (r[0], r[1].lower())):
        who, n = s.streak
        if cup:
            holder = s.holder or paint("up for grabs", C.GRAY)
        else:
            last = s.last
            holder = paint(f"{last.winner} (last won)", C.GRAY) if last is not None else paint("not played yet", C.GRAY)
        print(f"   {pad(truncate(name[0].upper() + name[1:], 34), 36)}"
              f"{pad(truncate(s.record_str(), 32) if s.n else paint(truncate(f'{s.a}–{s.b}', 32), C.GRAY), 34)}"
              f"{pad(holder, 20)}{f'W{n}' if n else ''}")
    print(paint("\n   Trophy games show who holds the trophy; rivalries without one show who won the last meeting.\n"
                "   Open any team's page → [V] Rivalries for the full series.", C.GRAY))
    pause()
