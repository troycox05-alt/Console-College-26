"""
committee.py — The National Playoff Selection Committee and its rankings.

The Top 25 (rankings.py) is the poll: sticky, media voters who move teams in
steps. The Playoff Rankings are something else, and they are what decides
who plays for the title and who goes to which bowl.

THE COMMITTEE
  Twelve members: former coaches, former athletic directors, former players,
  a conference administrator or two. Each one serves a three-year term,
  staggered so a few seats turn over every winter; the open seats go to
  coaches who have just retired in this world (a generated former coach if
  nobody has). A member never votes on a school he's tied to — he's recused.

HOW A MEMBER VOTES
  Every member looks at the same résumé for every team:
      record            wins against losses
      schedule          how good the opponents were (talent and record)
      quality wins      wins over ranked teams, and over winning teams
      bad losses        losses to teams that shouldn't beat you
      margin            how convincingly a team wins (capped — no credit for running it up)
      titles            conference champions (once the title games are played)
      eye test          how good the roster actually is
      form              the last four games
      Group of Five     how skeptical he is of a schedule outside the Power leagues
  ...but weighs them his own way. Weights are procedural — every member leans
  on one or two things more than the rest — and every ranking stays sane,
  because every weight is a tilt on the same sensible base rather than a
  coin flip. A former coach's style carries into his ballot: an aggressive
  coach trusts margin and the eye test, a conservative one wants a clean
  record, a coach who won outside the Power leagues isn't skeptical of it.

THE RANKINGS
  Each member ranks every team and hands in a Top 25. The committee's number
  is each team's average ballot position (off the ballot counts as 30). That
  is blended with the media poll — committee 70%, poll 30% — then head-to-head
  settles near-ties: a team that beat the team one or two spots above it, and
  has no more losses, moves ahead.

  Week to week the committee is consistent with itself: a team that lost drops at
  least a few spots, a team that won doesn't fall far, and nobody leaps ten spots
  in one week (four or five for a big win, six for beating a top-five team).
  Head-to-head settles the rest.

  First release: after week 9. Updated every week after that; the final
  rankings, after the conference title games, seed the 12-team field and
  send teams to the bowls.
"""
import world
import random

from names import FIRST_NAMES, LAST_NAMES

SEATS = 12
TERM = 3
FIRST_RELEASE = 9           # the committee's first rankings come out after this week
LAST_WEEK = 14              # its final rankings: after the conference championships
COMMITTEE_WEIGHT = 0.70
OFF_BALLOT = 30
POWER = world.POWER

CRITERIA = ("record", "schedule", "quality", "bad_losses", "margin", "titles", "eye_test", "form", "g5")
LABELS = {"record": "record", "schedule": "strength of schedule", "quality": "quality wins",
          "bad_losses": "bad losses", "margin": "margin of victory", "titles": "conference titles",
          "eye_test": "the eye test", "form": "how a team is playing lately", "g5": "Group of Five schedules"}
# The committee's shared sense of what matters. Every member starts here.
BASE = {"record": 1.80, "schedule": 0.45, "quality": 0.55, "bad_losses": 0.45, "margin": 0.30,
        "titles": 0.30, "eye_test": 0.30, "form": 0.20, "g5": 0.45}
# Kinds of voter. Each leans on a couple of criteria.
LEANS = {
    "Résumé":       ("schedule", "quality"),
    "Win-loss":     ("record", "bad_losses"),
    "Eye test":     ("eye_test", "margin"),
    "Old school":   ("titles", "record"),
    "Analytics":    ("margin", "schedule"),
    "Hot hand":     ("form", "quality"),
    "Power-league": ("g5", "schedule"),
    "Big-tent":     ("record", "form"),
}
BACKGROUNDS = ("Former head coach", "Former head coach", "Former head coach", "Former athletic director",
               "Former athletic director", "Former player", "Former player", "Conference administrator",
               "Former sportswriter", "University president")


class Member:
    def __init__(self, name, background, since, term_end, weights, lean, school=None, coach=None):
        self.name = name
        self.background = background
        self.since = since
        self.term_end = term_end
        self.weights = weights            # criterion -> weight
        self.lean = lean                  # the kind of voter he is
        self.school = school              # recused from this school
        self.coach = coach                # the Coach object, if he coached in this world

    def leans_on(self, n=2):
        keys = sorted((k for k in CRITERIA if k not in ("g5", "bad_losses")),
                      key=lambda k: -self.weights[k] / BASE[k])
        return [LABELS[k] for k in keys[:n]]

    def notes(self):
        """What kind of voter he is, in words."""
        bits = [f"leans on {' and '.join(self.leans_on())}"]
        g5 = self.weights["g5"] / BASE["g5"]
        if g5 >= 1.35:
            bits.append("hard on Group of Five schedules")
        elif g5 <= 0.6:
            bits.append("gives the Group of Five a fair shake")
        bl = self.weights["bad_losses"] / BASE["bad_losses"]
        if bl >= 1.35:
            bits.append("won't forgive a bad loss")
        elif bl <= 0.6:
            bits.append("forgives a bad loss")
        return "; ".join(bits)


def _weights(rng, lean, tilt=None):
    w = {k: BASE[k] * rng.uniform(0.7, 1.3) for k in CRITERIA}
    for k in LEANS[lean]:
        w[k] *= rng.uniform(1.5, 2.0)
    for k, m in (tilt or {}).items():
        w[k] *= m
    w["record"] = max(w["record"], 1.3)          # nobody on the committee ignores wins and losses
    return w


def _coach_member(league, coach, rng, year):
    """A retired coach joins the committee. How he coached is how he votes."""
    tilt = {}
    if getattr(coach, "aggression", 50) >= 65:
        tilt.update(margin=1.3, eye_test=1.2)
    elif getattr(coach, "aggression", 50) <= 35:
        tilt.update(record=1.15, bad_losses=1.25)
    power = [s for s in coach.history if s.get("conf") in POWER]
    if coach.history and len(power) < len(coach.history) / 2:
        tilt["g5"] = 0.5                                        # he won outside the Power leagues
    elif len(power) >= 5:
        tilt["g5"] = 1.3
    if any(s.get("title") or s.get("cfp") for s in coach.history):
        tilt["quality"] = tilt.get("quality", 1) * 1.2
    lean = rng.choice(list(LEANS))
    school = coach.history[-1]["school"] if coach.history else None
    return Member(coach.name, "Former head coach" + (f" ({school})" if school else ""), year, year + TERM - 1,
                  _weights(rng, lean, tilt), lean, school=school, coach=coach)


def _generated_member(league, rng, year, term_end, background=None):
    background = background or rng.choice(BACKGROUNDS)
    school = rng.choice(league.teams).school if background != "Former sportswriter" else None
    lean = rng.choice(list(LEANS))
    tilt = {}
    if background.startswith("Former athletic director"):
        tilt.update(schedule=1.15, titles=1.15)
    elif background == "Former player":
        tilt.update(eye_test=1.25)
    elif background == "Conference administrator":
        tilt.update(titles=1.3)
        if school and next((t for t in league.teams if t.school == school), None) is not None:
            conf = next(t for t in league.teams if t.school == school).conference
            if conf not in POWER:
                tilt["g5"] = 0.5
    from names import full_name
    name = full_name(rng)
    label = background + (f" ({school})" if school and background != "Former sportswriter" else "")
    return Member(name, label, term_end - TERM + 1, term_end, _weights(rng, lean, tilt), lean, school=school)


class Committee:
    def __init__(self, league):
        rng = random.Random(f"committee:{league.seed}")
        self.members = []
        self.past = []                    # (name, background, since, left)
        for i in range(SEATS):
            end = league.year + (i % TERM)                     # staggered terms
            self.members.append(_generated_member(league, rng, league.year, end))
        self.ballots = {}                 # week -> {member name: [teams]}
        self.order = []                   # full ranking, best first
        self.last_order = []
        self.avg = {}                     # team -> committee average ballot position
        self.week = 0
        self.year = league.year
        self.history = {}                 # year -> [school names], the final Top 25
        self.changes = {}                 # year -> [(out name, in name)]

    # ── the numbers every member reads ──────────────────────────────────
    def _resume(self, league):
        teams = [t for t in league.teams if t.wins + t.losses]
        ap = {t: league.rankings.rank_of(t) for t in league.teams}
        champs = set(getattr(league, "conf_champs", {}).values())
        ccg_winners, ccg_losers = set(), set()
        for g in league.schedule.get(14, []):
            if g.game_type == "Conference Championship" and g.played:
                ccg_winners.add(g.winner)
                ccg_losers.add(g.loser)
        raw = {}
        for t in teams:
            games = [g for g in league.team_games(t) if g.played]
            n = len(games) or 1
            opps = [g.opponent_of(t) for g in games]
            opp_q = [(40 if getattr(o, "fcs", False) else o.team_ovr) + 25 * (o.win_pct if not getattr(o, "fcs", False) else 0.3)
                     for o in opps]
            quality = bad = margin = 0.0
            for g in games:
                o = g.opponent_of(t)
                won = g.winner is t
                diff = g.score_for(t) - g.score_for(o)
                margin += max(-21, min(21, diff))
                if getattr(o, "fcs", False):
                    if not won:
                        bad += 3.0
                    continue
                r = ap.get(o)
                if won:
                    if r:
                        quality += 1.0 + (26 - r) / 25
                    elif o.win_pct > 0.5:
                        quality += 0.35
                elif not r:
                    bad += 1.0 + max(0, (70 - o.team_ovr) / 15) + max(0, 0.5 - o.win_pct)
            last = games[-4:]
            raw[t] = {
                # the loss column, read in tiers: each loss costs more than the one before it
                "record": t.wins - 2.2 * t.losses - 1.3 * max(0, t.losses - 1) ** 1.25
                          + (2.0 if t.losses == 0 and n >= 3 else 0),
                "schedule": sum(opp_q) / n if opp_q else 60,
                "quality": quality ** 0.5,                   # the fifth good win adds less than the first
                "bad_losses": bad,
                "margin": margin / n,
                # a Power title is worth more than a Group of Five one
                "titles": ((1.0 if (t.conference in POWER or t.school == world.FLAGSHIP_INDEPENDENT) else 0.45)
                           if t in champs or t in ccg_winners else (0.2 if t in ccg_losers else 0.0)),
                "eye_test": t.team_ovr,
                "form": sum(1 for g in last if g.winner is t) / len(last) if last else 0.5,
                "g5": 0.0 if (t.conference in POWER or t.school == world.FLAGSHIP_INDEPENDENT) else 1.0,
            }
        z = {}
        for k in CRITERIA:
            if k in ("g5", "titles"):
                continue                                   # yes/no things stay yes/no
            vals = [raw[t][k] for t in teams]
            mean = sum(vals) / len(vals)
            sd = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5 or 1.0
            cap = 2.6 if k == "record" else 2.0              # one freakish number can't carry a résumé
            for t in teams:
                z.setdefault(t, {})[k] = max(-cap, min(cap, (raw[t][k] - mean) / sd))
        for t in teams:
            z[t]["g5"] = raw[t]["g5"]
            z[t]["titles"] = raw[t]["titles"] * 1.2
        return z, raw

    def _ballot(self, m, resume):
        def score(t):
            r = resume[t]
            s = 0.0
            for k in CRITERIA:
                if k == "bad_losses":
                    s -= m.weights[k] * r[k]
                elif k == "g5":
                    s -= m.weights[k] * r[k] * 2.2
                else:
                    s += m.weights[k] * r[k]
            return s
        teams = [t for t in resume if t.school != m.school]      # recused from his own school
        return sorted(teams, key=lambda t: -score(t))[:25]

    # ── the week ────────────────────────────────────────────────────────
    def update(self, league, week):
        if week < FIRST_RELEASE or week > LAST_WEEK:
            return
        resume, _ = self._resume(league)
        if not resume:
            return
        ballots = {m.name: self._ballot(m, resume) for m in self.members}
        self.ballots[week] = ballots
        avg = {}
        for t in resume:
            spots, voters = 0, 0
            for m in self.members:
                if m.school == t.school:
                    continue                                       # recused
                b = ballots[m.name]
                spots += b.index(t) + 1 if t in b else OFF_BALLOT
                voters += 1
            avg[t] = spots / max(1, voters)
        full_ap = {t: i + 1 for i, t in enumerate(league.rankings.order)}
        blend = {t: COMMITTEE_WEIGHT * avg[t] + (1 - COMMITTEE_WEIGHT) * min(40, full_ap.get(t, 40)) for t in avg}
        order = sorted(avg, key=lambda t: (blend[t], avg[t]))
        if self.week and self.year == league.year and self.order:
            order = self._steady(league, week, order)
        order = self._head_to_head(league, order)
        rest = [t for t in league.teams if t not in order]
        self.last_order = list(self.order) if self.week else []
        self.order = order + sorted(rest, key=lambda t: full_ap.get(t, 999))
        self.avg, self.blend, self.week, self.year = avg, blend, week, league.year
        if week == LAST_WEEK:
            self.history[league.year] = [t.school for t in self.order[:25]]

    def _steady(self, league, week, order):
        """The committee says it starts fresh every week, and mostly it does — but a team that
        lost doesn't climb, and a team that won doesn't fall more than a few spots."""
        prev = {t: i + 1 for i, t in enumerate(self.order[:40])}
        result, beat = {}, {}
        for g in league.schedule.get(week, []):
            if g.played and g.winner is not None:
                result[g.winner], result[g.loser] = "W", "L"
                beat[g.winner] = g.loser
        key = {}
        for i, t in enumerate(order, 1):
            p = prev.get(t)
            k = i
            if p and result.get(t) == "L":
                k = max(i, p + 3.0)                         # a loss costs at least a few spots
            elif p and result.get(t) == "W":
                o = prev.get(beat.get(t))
                climb = 6 if o and o <= 5 else 4.5 if o and o <= 12 else 3
                k = max(min(i, p + 2.5), p - climb)         # no ten-spot leaps, even on title weekend
            key[t] = k
        return sorted(order, key=lambda t: (key[t], order.index(t)))

    @staticmethod
    def _head_to_head(league, order):
        beat = set()
        for week in range(1, LAST_WEEK + 1):
            for g in league.schedule.get(week, []):
                if g.played and g.winner is not None:
                    beat.add((g.winner, g.loser))
        order = list(order)
        for _ in range(2):
            for i in range(min(30, len(order)) - 1, 0, -1):
                for gap in (1, 2):
                    j = i - gap
                    if j < 0:
                        continue
                    lo, hi = order[i], order[j]
                    if (lo, hi) in beat and (hi, lo) not in beat and lo.losses <= hi.losses:
                        order.insert(j, order.pop(i))
                        break
        return order

    # ── what the rest of the game reads ─────────────────────────────────
    @property
    def released(self):
        return self.week >= FIRST_RELEASE and bool(self.order)

    def rank_of(self, team):
        if not self.released:
            return None
        try:
            i = self.order.index(team)
        except ValueError:
            return None
        return i + 1 if i < 25 else None

    def previous_rank(self, team):
        try:
            i = self.last_order.index(team)
        except ValueError:
            return None
        return i + 1 if i < 25 else None

    def member_rank(self, member, team, week=None):
        b = self.ballots.get(week or self.week, {}).get(member.name, [])
        return b.index(team) + 1 if team in b else None

    # ── the offseason ───────────────────────────────────────────────────
    def new_season(self, league, year):
        """Terms end; retired coaches take the open seats. Called once a year,
        with the season that's about to start."""
        rng = random.Random(f"committee:{league.seed}:{year}")
        seated = {m.name for m in self.members}
        outs, ins = [], []
        keep = []
        for m in self.members:
            if m.term_end < year:
                outs.append(m)
                self.past.append((m.name, m.background, m.since, year - 1))
            else:
                keep.append(m)
        pool = [c for c in reversed(getattr(league, "retired_coaches", []))
                if c.name not in seated and c.history and not getattr(c, "is_user", False)
                and getattr(c, "origin", "") != "left for the Pro League"]
        for _ in outs:
            if pool:
                c = pool.pop(0)
                new = _coach_member(league, c, rng, year)
            else:
                new = _generated_member(league, rng, year, year + TERM - 1, background="Former head coach")
            keep.append(new)
            ins.append(new)
        self.members = keep
        self.changes[year] = [(o.name, i.name) for o, i in zip(outs, ins)]
        self.ballots, self.order, self.last_order, self.avg, self.week = {}, [], [], {}, 0


def get(league):
    c = getattr(league, "committee", None)
    if c is None:
        c = league.committee = Committee(league)
    return c


def order_for_selection(league):
    """The order that seeds the playoff and fills the bowls: the committee's
    when it has spoken, the poll otherwise."""
    c = getattr(league, "committee", None)
    if c is not None and c.released and c.year == league.year:
        return c.order
    return league.rankings.order
