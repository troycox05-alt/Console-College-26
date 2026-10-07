"""
recruiting.py — Recruiting as persuasion, not shopping.

You don't buy recruits with points. Every prospect wants three specific
things, and your program is either good at those things or it isn't. A staff
gets a limited number of hours each week, so the real game is triage: chase
the five-star everybody wants, or spend the week evaluating film and find the
three-star nobody else has figured out.

WHAT A RECRUIT IS
  Real ratings, hidden. A public star rating that is national *opinion* —
  generated from the real ratings plus noise, so it is wrong often enough that
  busts and steals are normal. Three hidden priorities. A personality that
  decides how he reacts when his school loses or another program comes calling.

HOW INTEREST MOVES
  Effort helps most when it lines up with what he cares about — selling
  facilities to a kid who wants the ball on Saturday barely registers. Gains
  shrink as interest climbs, interest decays every week you go quiet, and
  nothing gets past a hard ceiling until you actually offer. Campus visits are
  tied to the real schedule: he comes to a home game, and a night win over a
  ranked team is worth far more than a blowout of an FCS opponent.

WHAT YOU SEE
  A range, not a rating. A word, not a number. Scouting narrows the range;
  it buys information and no interest at all, which is the trade-off the
  whole system turns on.

WHAT IT PAYS OFF
  Players who picked a school that matched their priorities develop faster
  (see fit_bonus, used by development.py). Recruiting three years ago is why
  a team is good now.
"""
import bisect
from collections import Counter, defaultdict
from netplay import capture

from recruiting_data import (ACTIONS, CLASS_SIZE, INTEREST_DECAY, NATIONAL_POOL, OFFER_CEILING,
                             PERSONALITIES, PRIORITIES, PRIORITY_LABELS, PRIORITY_WEIGHTS,
                             REGION_NEIGHBORS, SCHOLARSHIP_CAP, STATES, TALENT, TEAM_STATES)

from roster import ROSTER_SIZE, STAR_TALENT, make_prospect
from traits import mod as trait_mod


def class_cap(team, league):
    """Signing-class size for this program: 25, less any scholarships the CAB took (compliance.py)."""
    import compliance
    return compliance.class_cap(team, league)

PICK_EXP = 4.0            # signing day: how hard the undecided lean to the school they like most
IN_RUNNING = 0.35         # ...among schools within this share of his top school (the rest aren't in it)
REPEAT_FALLOFF = (1.0, 0.6, 0.35, 0.2)   # interest gained by the 1st, 2nd, 3rd, 4th+ pitch to one kid in a week
COMMITS_PER_WEEK_IN_SEASON = 2           # most commitments a program can land in one regular-season week
COMMITS_PER_WEEK_LATE = 3                # after the season, when kids are deciding

# Matches the roster template, so the national pool supplies roughly what the
# country actually needs at each spot. Kickers and punters stay scarce on
# purpose — most of them walk on, the way they do in real life.
POSITION_MIX = {"QB": 6, "RB": 8, "WR": 14, "TE": 6, "OL": 20, "DL": 18, "LB": 14, "CB": 12,
                "S": 8, "K": 1, "P": 1}

DEV_KEY = {"QB": "passing_dev", "WR": "passing_dev", "RB": "offense_dev", "TE": "offense_dev",
           "OL": "trench_dev", "DL": "trench_dev", "LB": "db_dev", "CB": "db_dev", "S": "db_dev",
           "K": "special_dev", "P": "special_dev"}

# Which positions each scheme sells hardest to.
OFF_SCHEME_FIT = {
    "Air Raid": {"QB": 12, "WR": 14, "TE": -4, "OL": -3, "RB": -8},
    "Veer & Shoot": {"QB": 10, "WR": 12, "RB": -4, "TE": -6},
    "Spread RPO": {"QB": 8, "WR": 6, "RB": 4, "TE": -2},
    "Power Spread": {"QB": 5, "RB": 8, "OL": 8, "TE": 4, "WR": 2},
    "Pro Style": {"QB": 4, "TE": 8, "OL": 6, "RB": 4, "WR": 2},
    "West Coast": {"QB": 4, "WR": 6, "TE": 6, "RB": 4},
    "Smashmouth": {"OL": 12, "TE": 10, "RB": 10, "WR": -10, "QB": -6},
    "Triple Option": {"RB": 10, "OL": 10, "TE": 2, "WR": -14, "QB": -4},
}
DEF_SCHEME_FIT = {
    "4-3 Zone": {"DL": 6, "LB": 6, "S": 2},
    "4-2-5 Quarters": {"CB": 8, "S": 8, "DL": 4, "LB": -2},
    "Pressure 3-4": {"DL": 10, "LB": 10, "CB": 2},
    "3-3-5 Stack": {"LB": 8, "S": 8, "CB": 4, "DL": -2},
    "Multiple Man": {"CB": 10, "S": 6, "DL": 4},
    "Tite Front": {"DL": 10, "LB": 6, "S": 4},
}
OFFENSE_POS = {"QB", "RB", "WR", "TE", "OL"}

# Room sizes a scheme wants, relative to the standard roster: an Air Raid carries
# more receivers and fewer backs; an option team carries more backs and linemen.
SCHEME_ROOMS = {
    "Air Raid": {"WR": 3, "TE": -2, "RB": -1}, "Veer & Shoot": {"WR": 3, "TE": -2},
    "Spread RPO": {"WR": 1, "TE": -1}, "Power Spread": {"OL": 1, "TE": 1, "WR": -1},
    "Smashmouth": {"OL": 2, "TE": 2, "RB": 1, "WR": -3}, "Triple Option": {"RB": 3, "OL": 2, "WR": -4, "TE": -1},
    "4-2-5 Quarters": {"S": 2, "LB": -1}, "3-3-5 Stack": {"S": 2, "LB": 1, "DL": -2},
    "Pressure 3-4": {"LB": 2, "DL": -1}, "Multiple Man": {"CB": 2, "LB": -1}, "Tite Front": {"DL": 1, "S": -1},
}


def _schemes(team):
    """The offense and defense this program actually runs (the play-callers' schemes)."""
    try:
        import staff
        return staff.called_schemes(team)
    except Exception:
        c = team.coach
        return (c.offense_scheme, c.defense_scheme) if c else (None, None)


def _fac_pitch(team):
    import facilities
    return facilities.pitch_value(team)


def scheme_room_shift(team):
    off, df = _schemes(team)
    out = Counter()
    for k in (off, df):
        for pos, n in SCHEME_ROOMS.get(k, {}).items():
            out[pos] += n
    return out


def scheme_type(scheme, player):
    """0.8–1.3: does this kid's body and game fit what the scheme asks of his position?"""
    f = player.fundamentals
    pos = player.position
    sp, q, s, iq, pm = (f.get(k, 50) for k in ("speed", "quickness", "strength", "iq", "playmaker"))
    score = 0.0
    if pos == "QB":
        if scheme in ("Triple Option",):
            score = (sp + q) / 2 - 60 + (iq - 60) * 0.5          # a runner who reads it right
        elif scheme in ("Spread RPO", "Power Spread"):
            score = (sp - 60) * 0.5 + (iq - 60) * 0.5
        elif scheme in ("Air Raid", "West Coast", "Veer & Shoot", "Pro Style"):
            score = (iq + pm) / 2 - 60                             # a thrower
    elif pos == "WR" and scheme in ("Air Raid", "West Coast", "Veer & Shoot"):
        score = (q + pm) / 2 - 60
    elif pos == "RB" and scheme in ("Smashmouth", "Triple Option", "Power Spread"):
        score = s - 60 if scheme == "Smashmouth" else (s + sp) / 2 - 60
    elif pos == "OL" and scheme in ("Smashmouth", "Triple Option", "Power Spread"):
        score = (q - 60) * 0.5 + (s - 60) * 0.5
    elif pos in ("LB", "S") and scheme in ("3-3-5 Stack", "4-2-5 Quarters"):
        score = (sp - 60) * 0.6
    elif pos == "DL" and scheme in ("Pressure 3-4", "Tite Front"):
        score = s - 60
    return max(0.8, min(1.3, 1 + score / 60))


def scheme_pull(team, recruit):
    """How much a staff wants this prospect for its schemes: the positions its schemes
    sell to, and — once it has scouted him — whether his game fits what it runs."""
    off, df = _schemes(team)
    pos = recruit.position
    fit = OFF_SCHEME_FIT.get(off, {}).get(pos, 0) if pos in OFFENSE_POS else DEF_SCHEME_FIT.get(df, {}).get(pos, 0)
    pull = 1 + fit / 40                                              # ±0.35 at the extremes
    known = min(3, recruit.scout[team]) / 3                          # you only know his game if you've seen the film
    kind = scheme_type(off if pos in OFFENSE_POS else df, recruit.player)
    return pull * (1 + (kind - 1) * (0.3 + 0.7 * known))

STANDING_WORDS = ((78, "LEADING"), (60, "IN GOOD SHAPE"), (42, "IN THE MIX"),
                  (25, "ON THE FRINGE"), (0, "LONG SHOT"))


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Recruit:
    """One prospect, his hidden truth, and what every program knows about him."""

    __slots__ = ("player", "position", "home_state", "region", "true_grade", "stars", "national_rank",
                 "priorities", "personality", "interest", "offers", "scout", "committed_to",
                 "commit_week", "signed", "attention",
                 # recruit_plus.py: his school, JUCO/international, commitment type, visits, what he's told you
                 "hs", "kind", "origin", "commit_kind", "silent", "early", "ov", "revealed")

    def __init__(self, player, home_state, stars, priorities, personality):
        self.player = player
        self.position = player.position
        self.home_state = home_state
        self.region = STATES[home_state][1]
        self.true_grade = player.overall
        self.stars = stars
        self.national_rank = None
        self.priorities = priorities          # ordered, most important first
        self.personality = personality
        self.interest = defaultdict(float)
        self.offers = set()
        self.scout = defaultdict(int)         # team -> 0..3
        self.committed_to = None
        self.commit_week = None
        self.signed = False
        self.attention = stars * 20

    # ── what a program can see ───────────────────────────────────────────
    @property
    def name(self):
        return self.player.name + (" ✦" if getattr(self.player, "generational", False) else "")

    def scouting_range(self, team):
        width = (22, 14, 8, 4)[clamp(self.scout[team], 0, 3)]
        low = max(20, self.true_grade - width // 2)
        return low, min(99, low + width)

    def known_priorities(self, team):
        """Priorities are revealed by doing the homework, one at a time."""
        return self.priorities[:clamp(self.scout[team], 0, 3)]

    def leader(self):
        if self.committed_to:
            return self.committed_to
        if not self.interest:
            return None
        return max(self.interest, key=lambda t: self.interest[t])

    def lead_margin(self):
        vals = sorted(self.interest.values(), reverse=True)
        if len(vals) < 2:
            return vals[0] if vals else 0.0
        return vals[0] - vals[1]

    def top_schools(self, n=5):
        return sorted(self.interest, key=lambda t: -self.interest[t])[:n]

    def standing(self, team):
        """Where you stand: how interested he is in you, and — early, before anyone has
        much of a hold on him — how you compare to the school in front. Leading a thin
        field is still leading."""
        score = self.interest.get(team, 0.0)
        words = [w for _, w in STANDING_WORDS]
        idx = next((i for i, (floor, _) in enumerate(STANDING_WORDS) if score >= floor), len(words) - 1)
        top = max(self.interest.values(), default=0.0)
        if score > 0 and top > 0 and self.committed_to is None:
            share = score / top
            rel = 2 if share >= 0.999 else 3 if share >= 0.8 else len(words) - 1   # IN THE MIX / ON THE FRINGE
            idx = min(idx, rel)
        return words[idx]

    def projection(self):
        """What a program assumes he'll be, based on his public stars."""
        return STAR_TALENT[self.stars]


# ═══ Pitches ════════════════════════════════════════════════════════════════

def depth_profile(team):
    """Sorted ratings of the young players already in each position room.

    Computed once per team per week: working it out per recruit meant
    re-rating entire rosters hundreds of thousands of times a season."""
    out = {}
    for p in team.roster:
        if p.year <= 2:
            out.setdefault(p.position, []).append(p.overall)
    for lst in out.values():
        lst.sort()
    return out


def _staff_dev(team, coach, pos):
    """The development pitch: the head coach, and the coordinator he'd play for."""
    import staff
    return staff.dev_rating(team, coach, pos)


def pitch_scores(league, team, recruit, profile=None):
    """How good this program's case is, on each of the ten things recruits weigh."""
    pos = recruit.position
    projection = recruit.projection()
    room = (profile if profile is not None else depth_profile(team)).get(pos, ())
    blocking = len(room) - bisect.bisect_left(room, projection)
    coach = team.coach
    rank = league.rankings.rank_of(team)
    if rank:
        winning = 100 - rank * 2
    else:
        last = team.last_win_pct if team.last_win_pct is not None else 0.4
        winning = 30 * team.win_pct + 45 * last

    off_s, def_s = _schemes(team)                  # what the play-callers run is what gets sold
    table = OFF_SCHEME_FIT.get(off_s, {}) if pos in OFFENSE_POS else DEF_SCHEME_FIT.get(def_s, {})
    home = TEAM_STATES.get(team.school)
    if home == recruit.home_state:
        proximity = 100
    elif home and STATES[home][1] == recruit.region:
        proximity = 72
    elif home and recruit.region in REGION_NEIGHBORS[STATES[home][1]]:
        proximity = 48
    else:
        proximity = 22

    import skills
    if skills.team_has(team, "national"):
        proximity = 100 - (100 - proximity) / 2                      # National Brand (coaching tree)
    fit = 60 + table.get(pos, 0) * 2.2
    if skills.team_has(team, "scheme_identity"):
        fit += 15                                                    # Scheme Identity (coaching tree)
    return {
        "playing_time": clamp(95 - 16 * blocking, 5, 100),
        "development": clamp(_staff_dev(team, coach, pos), 5, 100),
        "winning": clamp(winning, 5, 100),
        "scheme_fit": clamp(fit, 5, 100),
        "academics": team.ratings["academics"],
        "facilities": _fac_pitch(team),
        "proximity": proximity,
        "tradition": team.ratings["tradition"],
        "campus": team.ratings["campus"],
        "relationship": 0,        # earned, filled in by the cycle
    }


def priority_weight(recruit, key):
    if key not in recruit.priorities:
        return 0.75
    return (1.7, 1.4, 1.2)[recruit.priorities.index(key)]


# ═══ The cycle ══════════════════════════════════════════════════════════════

class RecruitingCycle:
    """One recruiting class, from summer evaluations to signing day."""

    def __init__(self, league):
        self.league = league
        self.rng = league.rng
        self.pool = []
        self.by_team = defaultdict(list)       # team -> targets it is working
        self.relationship = defaultdict(float)  # (team, recruit) -> earned trust
        self.pitch_cache = {}
        self.depth_cache = {}
        self.class_cache = defaultdict(list)
        self.board_week = {}
        self.news = []
        self.user_queue = []                   # (recruit, action) queued from the UI
        self.hours_used = Counter()
        self.generate_class()

    # ── building the class ───────────────────────────────────────────────
    def generate_class(self):
        rng = self.rng
        states = list(TALENT)
        weights = [TALENT[s] for s in states]
        positions = [p for p, n in POSITION_MIX.items() for _ in range(n)]
        used_names = set()
        for _ in range(NATIONAL_POOL):
            pos = rng.choice(positions)
            state = rng.choices(states, weights=weights)[0]
            stars = self._roll_stars(rng)
            if pos in ("K", "P") and stars >= 4:
                stars = 4 if rng.random() < 0.15 else 3       # a blue-chip kicker is rare; a five-star never
            player = make_prospect(rng, pos, stars, state, used_names)
            # Public opinion is mostly right and sometimes badly wrong. About one
            # prospect in six is rated a full star off what he actually is, which
            # is where busts and steals come from.
            public = stars
            if rng.random() < 0.17:
                public = clamp(stars + rng.choice((-1, 1)), 1, 5)
            priorities = self._roll_priorities(rng)
            personality = rng.choice(list(PERSONALITIES))
            r = Recruit(player, state, public, priorities, personality)
            player.hs_stars = public
            self.pool.append(r)
        gen = self._generational(rng)
        self.pool.sort(key=lambda r: (not getattr(r.player, "generational", False), -r.stars,
                                      -self.rng.random() - r.true_grade / 200))
        for i, r in enumerate(self.pool, 1):
            r.national_rank = i
            r.player.recruit_rank = i
        self._seed_interest()
        import recruit_plus
        recruit_plus.enrich(self)                  # high schools, JUCO transfers, international specialists
        if gen is not None:
            self._news(0, "commit", f"✦ A generational talent: {gen.player.name}, a {gen.position} from "
                                    f"{gen.home_state}. Scouts say you see one like him every few years.")

    GENERATIONAL_ODDS = 0.4          # about two classes in five have one

    def _generational(self, rng):
        """Every few years there's a kid who is simply different."""
        if rng.random() >= self.GENERATIONAL_ODDS:
            return None
        cands = [r for r in self.pool if r.stars == 5 and r.position in ("QB", "RB", "WR", "DL", "LB", "CB", "S", "TE")]
        if not cands:
            return None
        r = rng.choice(cands)
        p = r.player
        for f in p.fundamentals:
            if f != "injury":
                p.fundamentals[f] = int(min(99, p.fundamentals[f] + rng.randint(7, 12)))
        p.proficiency[p.position] = round(max(p.proficiency[p.position], rng.uniform(0.98, 1.06)), 2)
        p.prof_ceiling = 1.2
        p.potential = rng.randint(95, 99)
        p.generational = True
        r.true_grade = p.overall
        r.attention = 200                             # every staff in the country is on him
        return r

    @staticmethod
    def _roll_stars(rng):
        roll = rng.random()
        if roll < 0.017:
            return 5
        if roll < 0.155:
            return 4
        if roll < 0.73:
            return 3
        return 2

    @staticmethod
    def _roll_priorities(rng):
        keys = list(PRIORITY_WEIGHTS)
        weights = [PRIORITY_WEIGHTS[k] for k in keys]
        picked = []
        while len(picked) < 3:
            k = rng.choices(keys, weights=weights)[0]
            if k not in picked:
                picked.append(k)
        return picked

    def _seed_interest(self):
        """Programs start with a natural pull on players near home and in their tier."""
        teams = self.league.teams
        for r in self.pool:
            candidates = []
            for t in teams:
                home = TEAM_STATES.get(t.school)
                near = 2.4 if home == r.home_state else (1.5 if home and STATES[home][1] == r.region else 1.0)
                tier_gap = abs(t.prestige / 20 - r.stars)
                weight = near / (1 + tier_gap * 1.5)
                candidates.append((weight, t))
            candidates.sort(key=lambda x: -x[0] * (0.6 + self.rng.random()))
            for weight, t in candidates[:self.rng.randint(6, 12)]:
                r.interest[t] = clamp(self.rng.gauss(14, 6) + weight * 4, 2, 32)
            for t in r.top_schools(4):
                self.by_team[t].append(r)

    # ── weekly hours ─────────────────────────────────────────────────────
    def hours_parts(self, team):
        """(phase label, staff hours, recruiting-week bonus) — the pieces of this week's budget."""
        if self.league.week == 0 and not getattr(self, "compressed", False) \
                and getattr(self.league, "mode", None) == "career":
            # A real preseason contact period.  Everyone gets the same small
            # budget; only evaluation/contact/offers are legal until Week 1.
            return "Preseason contact", 18, 0
        import staff
        base = 46 + staff.recruiting_rating(team) * 0.45       # the head coach and both coordinators
        import dynasty
        base *= dynasty.recruiting_penalty(self.league, team)  # CAB sanctions cut the calendar
        phase = "Off-season"
        if not getattr(self, "compressed", False) and 1 <= self.league.week <= 13:
            base *= 0.65                       # Saturdays take the staff's time
            phase = "In-season"
        bonus = (getattr(team, "week_prep", None) or {}).get("hours", 0)   # a recruiting-focused practice week
        import ad_mode
        bonus += ad_mode.recruiting_hours(team, self.league)              # staffers the AD paid for
        return phase, int(base), int(bonus)

    def hours_for(self, team):
        _, base, bonus = self.hours_parts(team)
        import skills
        if skills.team_has(team, "machine"):
            base = int(base * 1.15)                                  # Machine (coaching tree)
        import gray_area
        return base + bonus + gray_area.bonus_hours(self, team)      # overtime, off the books

    def hours_explained(self, team, short=False):
        """One line that says where this week's hours came from, e.g.
        'In-season: 41 base + 8 recruiting week = 49 (game weeks cut staff time by a third)'."""
        phase, base, bonus = self.hours_parts(team)
        if short:
            return f"{phase}: {base}" + (f" + {bonus} rec wk" if bonus else " base")
        if phase == "Preseason contact":
            return f"Preseason contact period: {base} hours — evaluate, contact and offer; visits open in Week 1."
        txt = f"{phase}: {base} base" + (f" + {bonus} recruiting week = {base + bonus}" if bonus else "")
        if phase == "In-season":
            txt += " (game weeks cut staff recruiting time by about a third)"
        else:
            txt += " (full staff time — no games to coach)"
        return txt

    def remaining_hours(self, team):
        return max(0, self.hours_for(team) - self.hours_used[team])

    # ── pitches with relationship folded in ──────────────────────────────
    def pitches(self, team, recruit):
        key = (team, recruit)
        cached = self.pitch_cache.get(key)
        if cached is None:
            profile = self.depth_cache.get(team)
            if profile is None:
                profile = self.depth_cache[team] = depth_profile(team)
            cached = pitch_scores(self.league, team, recruit, profile)
            self.pitch_cache[key] = cached
        out = dict(cached)
        out["relationship"] = clamp(self.relationship[key], 0, 100)
        return out

    def fit_value(self, team, recruit):
        """How much this program's case would move this particular recruit."""
        p = self.pitches(team, recruit)
        return sum(p[k] * priority_weight(recruit, k) for k in recruit.priorities) / 3

    # ── actions ──────────────────────────────────────────────────────────
    @capture.hook("rec", "acts", capture.b_action)
    def apply_action(self, team, recruit, action, enforce=True, pitch=None, source=None):
        """Spend the hours and move the needle. Returns (ok, message).
        pitch: what you sold him on in a call or a visit (recruit_plus.pitch_mult) — "auto" is the best
        thing your staff knows he wants; None is a generic pitch (CPU staffs)."""
        label, cost, effect, rel, scout = ACTIONS[action]
        if self.league.week == 0 and not getattr(self, "compressed", False) \
                and getattr(self.league, "mode", None) == "career" \
                and action not in ("evaluate", "contact", "offer"):
            return False, "That action opens in Week 1. Preseason is limited to evaluation, contact and offers."
        import skills
        junkie = action == "evaluate" and skills.team_has(team, "film_junkie")
        if junkie:
            cost = 1                                                   # Film Junkie (coaching tree)
        if recruit.signed:
            return False, f"{recruit.name} has already signed."
        if enforce and self.remaining_hours(team) < cost:
            if self.league.week == 0 and self.hours_for(team) == 0:
                return False, "It's the preseason — no recruiting hours yet. Build your board; hours start in Week 1."
            return False, "Not enough hours left this week."
        if action == "offer" and team in recruit.offers:
            return False, f"{recruit.name} already holds an offer."
        if action != "evaluate" and action != "offer" and team not in recruit.offers:
            return False, "He won't take that meeting without an offer."
        if enforce:
            self.hours_used[team] += cost
        key = (team, recruit)
        self.relationship[key] = clamp(self.relationship[key] + rel * 3.5, 0, 100)
        if scout:
            gain = scout + (1 if trait_mod(team.coach, "recruit_eval") > 1.2
                            and self.rng.random() < 0.4 else 0)
            if junkie and self.rng.random() < 0.5:
                gain += 1
            recruit.scout[team] = clamp(recruit.scout[team] + gain, 0, 3)
        if action == "offer":
            recruit.offers.add(team)
            if team.prestige > 70:
                recruit.attention += 12
        touches = self.__dict__.setdefault("touches", Counter())
        touches[(team, recruit)] += 1
        if effect:
            import facilities
            multiplier = trait_mod(team.coach, "recruit_close") * facilities.recruiting_mult(team)
            # A kid can only absorb so much in one week: the third pitch lands softer than the first.
            multiplier *= REPEAT_FALLOFF[min(touches[(team, recruit)], len(REPEAT_FALLOFF)) - 1]
            import staff
            multiplier *= staff.region_pull(team, recruit)           # a coordinator from his part of the country
            for side in (getattr(team, "oc", None), getattr(team, "dc", None)):
                if side is not None:
                    multiplier *= 1 + 0.5 * (trait_mod(side, "recruit_close") - 1)
            if action == "campus_visit":
                import stadium
                multiplier = self._visit_multiplier(team) * stadium.visit_mult(team)   # the lounge, the atmosphere
            if action == "in_home" and recruit.personality == "family_first":
                multiplier *= 1.5
            if action == "close" and recruit.committed_to and recruit.committed_to is not team:
                multiplier *= 1.0 if skills.team_has(team, "flip_artist") else 0.7
            reaction = ""
            if pitch is not None and action in ("contact", "position_coach", "in_home", "campus_visit"):
                import recruit_plus
                pm, reaction = recruit_plus.pitch_mult(self, team, recruit, pitch)
                multiplier *= pm
                if reaction and pitch != "auto":
                    recruit_plus.say(self, team, recruit, reaction)
            self._add_interest(team, recruit, effect * multiplier)
            if reaction and pitch != "auto":
                if recruit not in self.by_team[team]:
                    self.by_team[team].append(recruit)
                self._log_action(team, recruit, action, cost, pitch, source if enforce else "auto-sim staff",
                                 f"{label} — {reaction}")
                return True, f"{label} — {reaction}"
        if recruit not in self.by_team[team]:
            self.by_team[team].append(recruit)
        self._log_action(team, recruit, action, cost, pitch, source if enforce else "auto-sim staff",
                         f"{label} — {recruit.name}.")
        return True, f"{label} — {recruit.name}."

    def _log_action(self, team, recruit, action, cost, pitch, source, msg):
        """Your own recruiting moves, kept for good (league.recruit_actions) so Export to Sheets can list
        every call, offer and visit you chose. Plain values only — no live objects in the save."""
        try:
            if team is not getattr(self.league, "user_team", None):
                return
            log = self.league.__dict__.setdefault("recruit_actions", [])
            log.append({"year": self.league.year, "week": self.league.week, "recruit": recruit.player.name,
                        "pos": recruit.position, "stars": recruit.stars, "rank": recruit.national_rank,
                        "action": ACTIONS[action][0], "hours": cost, "pitch": pitch or "",
                        "source": source or "you", "result": msg,
                        "interest": round(recruit.interest.get(team, 0.0), 1),
                        "relationship": round(self.relationship[(team, recruit)], 1)})
            del log[:-20000]
        except Exception:
            pass

    def _visit_multiplier(self, team):
        """A visit is only as good as the Saturday he sees."""
        for g in self.league.schedule.get(self.league.week, []):
            if g.home is team and g.played:
                opp_ranked = self.league.rankings.rank_of(g.away)
                won = g.winner is team
                if not won:
                    return 0.4
                if opp_ranked:
                    return 1.8
                return 0.9 if getattr(g.away, "fcs", False) else 1.2
        return 1.0

    def _add_interest(self, team, recruit, raw):
        import skills
        if skills.user_coach_of(team) is not None:                  # your coaching tree
            raw *= 1.08 if skills.team_has(team, "silver_tongue") else 1.0
            raw *= 1.10 if skills.team_has(team, "lightning_rod") else 1.0
            if skills.team_has(team, "hometown") and TEAM_STATES.get(team.school) == recruit.home_state:
                raw *= 1.15
            import difficulty
            raw *= difficulty.recruit(team)                         # your difficulty
        import poscoach
        raw *= poscoach.recruit_mult(team, recruit.position, recruit)          # his position coach
        import recruit_plus
        raw *= recruit_plus.crowded_mult(self, team, recruit)            # "you already have three QBs"
        raw *= recruit_plus.class_pull(self, team, recruit)               # recruits notice the class taking shape
        pipe = team.__dict__.get("pipelines")
        if pipe:
            raw *= 1 + pipe.get(recruit_plus.hs_key(recruit), 0) / 250   # his high school knows you
        p = self.pitches(team, recruit)
        gain = 0.0
        for key in PRIORITIES:
            gain += raw * priority_weight(recruit, key) * (p[key] / 60) / len(PRIORITIES)
        gain *= (1 - recruit.interest[team] / 120)
        recruit.interest[team] = clamp(recruit.interest[team] + gain, 0, 100)
        if team not in recruit.offers:
            recruit.interest[team] = min(recruit.interest[team], OFFER_CEILING)

    # ── the week ─────────────────────────────────────────────────────────
    def weekly_tick(self, week, user_team=None):
        import recruit_plus
        recruit_plus.before_tick(self, week, user_team)     # your standing orders, your coordinators, the visits
        import hotseat
        human = hotseat.humans(self.league) if user_team is not None else []
        import commissioner
        for team in self.league.teams:
            if team is user_team or any(team is h for h in human):
                continue
            if commissioner.is_player_team(self.league, team) and not commissioner.staff_recruits(self.league, team):
                continue                           # Commissioner Mode: a player's orders do his recruiting
            self.ai_allocate(team)
        self._result_shifts()
        self._decay()
        import finance
        finance.weekly(self)                   # NIL money keeps talking; dead offers come off the books
        self._commitments(week)
        self._decommits(week)
        recruit_plus.after_tick(self, week, user_team)       # silent commits, crystal balls, ratings, rivals, early signing
        self.hours_used.clear()
        self.__dict__.setdefault("touches", Counter()).clear()
        self.__dict__.setdefault("week_commits", Counter()).clear()
        self.pitch_cache.clear()
        self.depth_cache.clear()

    def ai_allocate(self, team):
        """A staff works its board two ways at once: offer broadly to keep options
        open, then spend the real hours on the recruits who are responding."""
        rng = self.rng
        budget = self.hours_for(team)
        needs = self._needs(team)
        board = self._ai_board(team, needs)
        committed = len(self._class_of(team))
        if committed >= class_cap(team, self.league):
            return

        # Breadth: get offers out to anyone who fits and doesn't have one yet.
        breadth = budget * 0.5
        for recruit in board:
            if breadth < ACTIONS["offer"][1] or recruit.signed:
                continue
            if team in recruit.offers or recruit.committed_to:
                continue
            if self.fit_value(team, recruit) < 38:
                continue
            breadth -= ACTIONS["offer"][1]
            budget -= ACTIONS["offer"][1]
            self.apply_action(team, recruit, "offer", enforce=False)

        # Depth: chase the ones who are warm, close the ones who are ready.
        def worth(r):
            lead = r.leader()
            share = r.interest[team] / max(1.0, r.interest[lead]) if lead is not None else 1.0
            locked = r.committed_to is not None and r.committed_to is not team and \
                getattr(r, "commit_kind", None) == "hard"
            return (r.interest[team] + r.stars * 4) * (0.5 + min(1.0, share)) * (0.3 if locked else 1.0)
        warm = sorted((r for r in board if not r.signed and team in r.offers), key=lambda r: -worth(r))[:18]
        for recruit in warm:
            if budget < 2:
                break
            if recruit.committed_to and (recruit.committed_to is team or recruit.interest[team] < 45):
                continue
            standing = recruit.interest[team]
            preseason_contact = (self.league.week == 0 and not getattr(self, "compressed", False)
                                 and getattr(self.league, "mode", None) == "career")
            if recruit.scout[team] == 0 and rng.random() < 0.35:
                action = "evaluate"
            elif preseason_contact:
                action = "contact"
            elif standing > 45 and recruit.leader() is team:
                action = "close"
            elif standing > 28:
                action = rng.choices(("campus_visit", "in_home", "position_coach", "contact"),
                                     weights=(5, 2, 3, 3))[0]
            else:
                action = rng.choices(("contact", "position_coach"), weights=(6, 2))[0]
            cost = ACTIONS[action][1]
            if cost > budget:
                action, cost = "contact", ACTIONS["contact"][1]
            budget -= cost
            self.apply_action(team, recruit, action, enforce=False)
        import recruit_plus
        recruit_plus.ai_visits(self, team, warm)               # official visits for the warmest targets

        # Money: put NIL behind the recruits worth it who are responding.
        import finance
        finance.ai_nil(self, team, board)

    def _needs(self, team):
        """Open spots in each room next season — and, where the room is full of bodies but
        nobody's good enough (a kicker in the 40s), one spot for a player who can start."""
        lg = getattr(self, "league", None)
        ck = (team.school, getattr(lg, "year", 0), getattr(lg, "week", 0), len(team.roster),
              sum(p.overall for p in team.roster))
        cache = self.__dict__.setdefault("_needs_cache", {})
        if cache.get(team.school, (None,))[0] == ck:
            return dict(cache[team.school][1])
        need = {}
        shift = scheme_room_shift(team)
        team_ovr = team.team_ovr if team.roster else 60
        for pos, size in ROSTER_SIZE.items():
            roster = [p for p in team.roster if p.position == pos]
            seniors = sum(1 for p in roster if p.year >= 3)
            need[pos] = max(0, size + shift.get(pos, 0) - len(roster) + seniors)
            back = [p.overall for p in roster if p.year < 3]
            if need[pos] == 0 and (not back or max(back) < team_ovr - 12):
                need[pos] = 1
        cache[team.school] = (ck, dict(need))
        return need

    def _ai_board(self, team, needs):
        """The prospects this staff would realistically chase this week.

        A staff doesn't recruit a wish list all year. If it's November and the
        class is three players with five receiver holes, it slides down the
        board to players it can actually land and starts filling rooms."""
        committed = self._class_of(team)
        cached = [r for r in self.by_team[team]
                  if not r.signed and not (r.committed_to and r.committed_to is not team)]
        # A staff re-scouts the country every few weeks, not every Monday.
        last = self.board_week.get(team)
        if cached and last is not None and self.league.week - last < 3:
            self.by_team[team] = cached
            return cached
        self.board_week[team] = self.league.week
        target = max(1, sum(needs.values()))
        filled = len(committed) / target
        pace = clamp(self.league.week / 13, 0, 1)
        behind = clamp(pace - filled, 0, 1)          # how far off schedule the class is

        # The window starts where this program belongs and slides down as it falls behind.
        start = int(clamp((90 - team.prestige) * 30 + behind * 700, 0, len(self.pool) - 650))
        window = self.pool[start:start + 650]
        pool = cached + [r for r in window if r not in cached and not r.signed]

        taken = Counter(r.position for r in committed)
        scored = []
        for r in pool[:220]:
            room = needs.get(r.position, 0) - taken.get(r.position, 0)
            if room <= 0:
                continue                              # that room is full
            landing = 0.3 + r.interest[team] / 90
            if r.committed_to is not None and r.committed_to is not team:
                landing *= 0.35
            reach = clamp(1.4 - abs(team.prestige / 20 - r.stars) * 0.35, 0.15, 1.3)
            need_pull = 1.0 + 0.35 * min(room, 3) + behind * 0.8 * min(room, 3)
            # Staffs recruit where they win: their high-school pipelines and their own backyard.
            pipe = 1.0 + _pipe(team, r) / 250
            home = TEAM_STATES.get(team.school)
            near = 1.15 if home == r.home_state else 1.06 if home and STATES[home][1] == r.region else 1.0
            # By November, a staff stops spending on kids who are clearly going somewhere else.
            lead = r.leader()
            if self.league.week >= 8 and lead is not None and lead is not team:
                gap = r.interest[lead] - r.interest[team]
                if gap > 25:
                    landing *= 0.55
            scored.append((r.stars * 12 * landing * reach * need_pull * scheme_pull(team, r) * pipe * near
                           + self.fit_value(team, r) * 0.25, r))
        scored.sort(key=lambda x: -x[0])
        board = [r for _, r in scored[:45]]
        self.by_team[team] = board
        return board

    def _result_shifts(self):
        """Winning recruits. So does losing, in the other direction."""
        week_games = [g for g in self.league.schedule.get(self.league.week, []) if g.played]
        bump = {}
        for g in week_games:
            for team in (g.home, g.away):
                if getattr(team, "fcs", False):
                    continue
                won = g.winner is team
                opp = g.opponent_of(team)
                ranked_opp = self.league.rankings.rank_of(opp) is not None
                if won:
                    bump[team] = 3.0 if ranked_opp else 1.2
                else:
                    bump[team] = -4.0 if not ranked_opp else -1.5
        for r in self.pool:
            if r.signed:
                continue
            swing = PERSONALITIES[r.personality]["result_swing"]
            for team, delta in bump.items():
                if team in r.interest:
                    r.interest[team] = clamp(r.interest[team] + delta * swing, 0, 100)

    def _decay(self):
        for r in self.pool:
            if r.signed:
                continue
            rate = PERSONALITIES[r.personality]["decay"] * INTEREST_DECAY / 0.94
            for team in list(r.interest):
                r.interest[team] *= min(0.99, rate)

    def _commitments(self, week):
        import recruit_plus
        for r in self.pool:
            if r.signed or r.committed_to or not r.interest:
                continue
            leader = r.leader()
            if leader is None:
                continue
            if leader not in r.offers:
                self._warn_blocked(leader, r, self._class_of(leader), week)
                continue
            bias = PERSONALITIES[r.personality]["commit_bias"]
            # Better prospects take longer to decide: a five-star wants more than a two-star.
            gen = 8 if getattr(r.player, "generational", False) else 0     # he takes his time; everybody wants him
            if r.interest[leader] < 45 + bias + (r.stars - 2) * 4 + gen:
                continue
            lead = r.lead_margin()
            if lead < 6 + max(0, r.stars - 3) * 2:
                continue
            klass = self._class_of(leader)
            if len(klass) >= class_cap(leader, self.league) or not _position_room(leader, klass, r):
                self._warn_blocked(leader, r, klass, week)
                continue
            wc = self.__dict__.setdefault("week_commits", Counter())
            if wc[leader] >= (COMMITS_PER_WEEK_IN_SEASON if 1 <= week <= 13 else COMMITS_PER_WEEK_LATE):
                continue                              # commitments trickle in; a class isn't built in a week
            # The bigger the class already is, the less urgency each new kid feels.
            fullness = len(klass) / class_cap(leader, self.league)
            p = min(0.55, (lead - 6) / 32 + (week / 24) ** 1.6) * (1 - 0.45 * fullness)
            # A class with buzz creates urgency, especially when the recruit knows somebody in it.
            connections = recruit_plus.class_connections(self, leader, r, 3)
            social = sum(x[0] for x in connections)
            momentum = recruit_plus.class_momentum(self, leader)
            p *= 1.0 + min(0.10, momentum / 1000.0) + min(0.10, social * 0.055)
            if self.rng.random() < min(0.68, p):
                wc[leader] += 1
                r.committed_to = leader
                r.commit_week = week
                self.class_cache[leader].append(r)
                if not recruit_plus.on_commit(self, r, leader, week):     # a silent commit makes no news
                    kind = getattr(r, "commit_kind", "soft")
                    self._news(week, "commit",
                               f"{r.stars}-star {r.position} {r.name} ({STATES[r.home_state][0]}) "
                               f"commits to {leader.school}" + (" — and says he's locked in." if kind == "hard"
                                                                 else "."), school=leader.school, stars=r.stars)

    def _warn_blocked(self, team, r, klass, week):
        """You lead for him but can't take him: say so (once a week per kid)."""
        if team is not getattr(self.league, "user_team", None) or r.stars < 3 or r.interest.get(team, 0) < 40:
            return
        why = block_reason(self.league, team, r, klass)
        if not why:
            return
        seen = self.__dict__.setdefault("_warned", {})
        if seen.get(id(r)) == week:
            return
        seen[id(r)] = week
        import recruit_plus
        recruit_plus.S(self)["weekly_note"][team].append(
            f"⚠ {r.stars}★ {r.position} {r.name} wants you, but he can't commit: {why}.")

    def _decommits(self, week):
        for r in self.pool:
            if r.signed or not r.committed_to:
                continue
            school = r.committed_to
            rival = max((t for t in r.interest if t is not school), key=lambda t: r.interest[t], default=None)
            if rival is None:
                continue
            gap = r.interest[rival] - r.interest[school]
            shaken = getattr(school, "coach_changed", False)   # the coach he committed to is gone
            if gap <= (-14 if shaken else -5):
                continue
            import recruit_plus
            odds = PERSONALITIES[r.personality]["decommit"] * (0.010 + max(0.0, gap) * 0.004) \
                * recruit_plus.decommit_mult(r)                           # hard commits hold; soft ones wobble
            if school.losses >= 6:
                odds *= 1.8
            if shaken:
                odds = odds * 2.5 + 0.02
            if self.rng.random() < odds:
                r.committed_to = None
                r.commit_week = None
                if r in self.class_cache[school]:
                    self.class_cache[school].remove(r)
                r.interest[school] *= 0.7
                r.silent = False
                self._news(week, "flip", f"{r.stars}-star {r.position} {r.name} has backed off his "
                                         f"pledge to {school.school}. {rival.school} is pushing hard.",
                           school=school.school, stars=r.stars)

    def _class_of(self, team):
        return self.class_cache[team]

    def _news(self, week, kind, text, school=None, stars=None):
        self.news.insert(0, (week, kind, text))
        del self.news[60:]
        meta = self.__dict__.setdefault("news_meta", {})
        meta[text] = (week, school, stars)                 # who it's about, for the headline desk
        if len(meta) > 200:
            keep = {t for _, _, t in self.news}
            self.news_meta = {t: m for t, m in meta.items() if t in keep}

    # ── user-facing helpers ──────────────────────────────────────────────
    def board_for(self, team):
        return sorted(team.recruiting_targets, key=lambda r: (r.committed_to is not team, r.national_rank))

    def add_target(self, team, recruit):
        if recruit not in team.recruiting_targets and len(team.recruiting_targets) < 40:
            team.recruiting_targets.append(recruit)
            return True
        return False

    def drop_target(self, team, recruit):
        if recruit in team.recruiting_targets:
            team.recruiting_targets.remove(recruit)

    def commitments(self, team):
        return list(self.class_cache[team])

    def class_rank(self, team):
        """National rank of the class — None until it has a commitment (an empty class isn't #26)."""
        if not self.commitments(team):
            return None
        scores = sorted(((t, self.class_score(t)) for t in self.league.teams if self.commitments(t)),
                        key=lambda x: -x[1])
        for i, (t, _) in enumerate(scores, 1):
            if t is team:
                return i
        return None

    def class_score(self, team):
        return class_points(self.commitments(team))


# ═══ Signing day ════════════════════════════════════════════════════════════

def _pipe(team, r):
    try:
        import recruit_plus
        return recruit_plus.pipeline_of(team, r)
    except Exception:                                    # noqa: BLE001
        return 0.0


def class_points(recruits):
    """Ranking points: the top of a class carries it, but depth still counts."""
    if not recruits:
        return 0.0
    ranked = sorted(recruits, key=lambda r: -r.stars)
    head = sum(r.stars ** 3.1 for r in ranked[:12])
    tail = sum(r.stars ** 1.6 for r in ranked[12:])
    avg = sum(r.stars for r in ranked) / len(ranked)
    return head + tail + avg * 25


class ClassReport:
    def __init__(self, year):
        self.year = year
        self.classes = defaultdict(list)     # team -> [Recruit]
        self.ranks = {}                      # team -> national class rank
        self.steals = []                     # notable signings away from the favorite
        self.flips = []                      # (recruit, from, to) — National Signing Day flips
        self.live = []                       # the hat ceremonies worth watching (your board, the national top 30)


def _position_room(team, signed, recruit, graduated=False):
    """Nobody signs six quarterbacks. Classes follow the depth chart. Signing day (graduated=True,
    after everyone has moved up a year) makes room for the new seniors; during the year the same
    room is projected from today's roster (this year's seniors and juniors), so a kid who can commit
    in October can sign in February."""
    pos = recruit.position
    roster = [p for p in team.roster if p.position == pos]
    leaving = sum(1 for p in roster if p.year >= (3 if graduated else 2))
    room = max(1, ROSTER_SIZE[pos] - len(roster) + leaving)
    taken = sum(1 for r in signed if r.position == pos)
    return taken < room


def block_reason(league, team, recruit, klass, graduated=False):
    """Why `team` can't sign this kid right now, or None. `klass` is who it has signed (or committed)."""
    if team not in recruit.offers:
        return "you never offered him a scholarship"
    cap = class_cap(team, league)
    if len(klass) >= cap and recruit not in klass:
        return f"your class was full ({len(klass)} of {cap})"
    if recruit not in klass and not _position_room(team, klass, recruit, graduated):
        pos = recruit.position
        taken = sum(1 for r in klass if r.position == pos)
        return f"you had no room left at {pos} ({taken} {pos}{'s' if taken != 1 else ''} already in the class)"
    if len(team.roster) + len(klass) >= SCHOLARSHIP_CAP and recruit not in klass:
        return f"you were at the {SCHOLARSHIP_CAP}-scholarship limit"
    return None


def _room_check(league, cycle, team, r, why, klass, leftovers):
    """Signing day, your call: he wants you, but you can't take him. Make room or let him go."""
    import recruit_ui
    return recruit_ui.room_check(league, cycle, team, r, why, klass, leftovers)


def signing_day(league, cycle, rng, next_year):
    """Commitments sign and the undecided pick. Nobody joins a roster here —
    the class comes on campus in attach_class, after the old seniors have
    graduated and everyone else has moved up a year."""
    report = ClassReport(next_year)
    signed_by = defaultdict(list)
    import recruit_plus
    import hotseat
    mine = getattr(league, "user_team", None)
    humans = hotseat.humans(league) or ([mine] if mine is not None else [])
    watch = {id(r) for t in humans for r in (getattr(t, "recruiting_targets", []) or [])} | \
        {id(r) for r in sorted(cycle.pool, key=lambda r: r.national_rank)[:30]}

    # 0. The early signing period already locked some in.
    for r in cycle.pool:
        if r.signed and getattr(r, "early", False) and r.committed_to is not None:
            signed_by[r.committed_to].append(r)

    # 1. Commitments sign — as long as the room is still there. A staff that
    #    over-recruited a position has to tell somebody to look elsewhere.
    #    A soft commit who's been listening to someone else can flip today.
    for r in cycle.pool:
        if r.committed_to and not r.signed:
            team = r.committed_to
            flip = recruit_plus.late_flip(cycle, r, rng)
            if flip is not None and len(signed_by[flip]) < class_cap(flip, league) and _position_room(flip, signed_by[flip], r, True):
                report.flips.append((r, team, flip))
                if id(r) in watch:
                    report.live.append({"r": r, "kind": "flip", "hats": [team, flip], "pick": flip, "fav": team})
                r.committed_to = flip
                team = flip
            if _position_room(team, signed_by[team], r, True) and len(signed_by[team]) < class_cap(team, league):
                r.signed = True
                signed_by[team].append(r)
                if id(r) in watch and not any(x["r"] is r for x in report.live):
                    report.live.append({"r": r, "kind": "signed", "hats": [team], "pick": team, "fav": team})
            else:
                why = block_reason(league, team, r, signed_by[team], True)
                if any(team is h for h in humans) and why:
                    report.__dict__.setdefault("cut", []).append((r, why))
                r.committed_to = None
                r.interest[team] *= 0.5
                recruit_plus.cut_at_signing(team, r)

    # 2. Late offers: staffs with room work the board right up to the deadline.
    for team in sorted(league.teams, key=lambda t: -t.recruiting_score):
        room = class_cap(team, league) - len(signed_by[team])
        if room <= 0:
            continue
        available = [r for r in cycle.pool if not r.signed and not r.committed_to
                     and team not in r.offers]
        available.sort(key=lambda r: -(r.stars * 10 + r.interest.get(team, 0) * 1.5
                                       + cycle.fit_value(team, r) * 0.2))
        for r in available[:room * 4]:
            if _position_room(team, signed_by[team], r, True):
                r.offers.add(team)
                r.interest[team] = r.interest.get(team, 0) + 10

    # 3. The undecided pick from whoever recruited them, weighted by interest.
    # The best prospects decide first: a five-star isn't waiting on a two-star to pick.
    leftovers = sorted((r for r in cycle.pool if not r.signed and r.interest), key=lambda r: r.national_rank)
    interactive_humans = humans if (getattr(league, "mode", None) in ("career", "online") and not getattr(league, "autosim", False)) else []
    report.blocked = []
    i = 0
    while i < len(leftovers):
        r = leftovers[i]
        i += 1
        if r.signed:
            continue
        favorite = r.leader()
        why = block_reason(league, favorite, r, signed_by[favorite], True) if favorite is not None else None
        if why and favorite is not None and any(favorite is h for h in interactive_humans):
            with hotseat.acting_as(league, favorite):
                if _room_check(league, cycle, favorite, r, why, signed_by[favorite], leftovers):
                    why = block_reason(league, favorite, r, signed_by[favorite], True)
        if why and favorite is not None:
            report.blocked.append((r, favorite, why))
        options = [(t, v) for t, v in r.interest.items()
                   if t in r.offers and len(signed_by[t]) < class_cap(t, league)
                   and len(t.roster) + len(signed_by[t]) < SCHOLARSHIP_CAP
                   and _position_room(t, signed_by[t], r, True)]
        if not options:
            continue
        top = max(v for _, v in options)
        options = [(t, v) for t, v in options if v >= top * IN_RUNNING]      # the schools actually in the running
        weights = [max(0.1, v) ** PICK_EXP for _, v in options]
        pick = rng.choices([t for t, _ in options], weights=weights)[0]
        if id(r) in watch:
            hats = [t for t, _ in sorted(options, key=lambda x: -x[1])[:3]]
            if pick not in hats:
                hats = hats[:2] + [pick]
            report.live.append({"r": r, "kind": "pick", "hats": hats, "pick": pick, "fav": favorite,
                                "why": why if favorite is not None and favorite is not pick else None})
        r.committed_to = pick
        r.signed = True
        signed_by[pick].append(r)
        if favorite is not None and favorite is not pick and r.stars >= 4:
            report.steals.append((pick, favorite, r))

    # Last call: a staff with holes left takes the best player still available
    # rather than hand the spot to a walk-on.
    for team in sorted(league.teams, key=lambda t: -t.recruiting_score):
        holes = sum(max(0, ROSTER_SIZE[pos] - len([p for p in team.roster if p.position == pos]))
                    for pos in ROSTER_SIZE)
        short = min(class_cap(team, league) - len(signed_by[team]), holes - len(signed_by[team]))
        if short <= 0:
            continue
        available = sorted((r for r in cycle.pool if not r.signed and not r.committed_to),
                           key=lambda r: -(r.stars * 10 + cycle.fit_value(team, r) * 0.3))
        for r in available:
            if short <= 0:
                break
            if not _position_room(team, signed_by[team], r, True):
                continue
            r.committed_to = team
            r.signed = True
            signed_by[team].append(r)
            short -= 1

    for team, recruits in signed_by.items():
        report.classes[team] = recruits
    import finance
    finance.signing_day_deals(league, cycle, report.classes)

    ordered = sorted(league.teams, key=lambda t: -class_points(report.classes.get(t, [])))
    for i, team in enumerate(ordered, 1):
        report.ranks[team] = i
    return report


def attach_class(team, recruits, cycle, rng, next_year):
    """The signed class arrives on campus as true freshmen."""
    used_numbers = {p.number for p in team.roster}
    from names import surname
    taken = {q.last_name for q in team.roster}
    taken |= {c.name.split()[-1] for c in (team.coach, getattr(team, "oc", None), getattr(team, "dc", None))
              if c is not None}
    league = getattr(cycle, "league", None)
    import hotseat
    human_teams = hotseat.humans(league) if league is not None else []
    mine = getattr(league, "user_team", None)
    if not human_teams and mine is not None:
        human_teams = [mine]
    board = {id(r) for t in human_teams for r in (getattr(t, "recruiting_targets", []) or [])}
    arrived = []
    for r in recruits:
        p = r.player
        if p.last_name in taken or p.first_name == p.last_name:
            # A second Brown in the room: while the world is being built (or for a quiet
            # signee nobody's been watching) he's given a different name. A recruit you've
            # followed keeps his; the broadcast tells the two apart by first name.
            quiet = getattr(cycle, "compressed", False) or (not any(team is h for h in human_teams) and r.stars <= 3 and id(r) not in board)
            if quiet:
                p.last_name = surname(rng, taken | {p.first_name})
        taken.add(p.last_name)
        p.number = _pick_number(rng, p.position, used_numbers)
        used_numbers.add(p.number)
        p.year = 0
        p.redshirt = False
        p.history.append((next_year, p.overall))
        p.events[next_year].append(f"Signed with {team.school} as a {r.stars}-star recruit")
        p.fit_bonus = _fit_bonus(cycle, team, r)
        import poscoach
        poscoach.tag_signee(team, p)                       # the coordinator and position coach who signed him
        import finance
        p.nil = int(finance.offer_to(cycle, team, r))      # his NIL deal comes with him, every year he stays
        if p.nil:
            p.events[next_year].append(f"NIL deal: {finance.money(p.nil)} a year")
        import promises
        promises.arrive(team, r, next_year)                # a promise you made him comes with him
        import recruit_plus
        recruit_plus.on_attach(team, r, p, next_year)      # pipelines, JUCO class, the signing book
        import skills
        if skills.team_has(team, "plug_and_play"):         # Plug and Play (coaching tree)
            for f in p.fundamentals:
                if f != "injury":
                    p.fundamentals[f] = min(99, p.fundamentals[f] + 3)
        team.add_player(p)
        arrived.append(p)
    return arrived


def _fit_bonus(cycle, team, recruit):
    """Players who got what they wanted develop better. Bad fits stagnate."""
    p = cycle.pitches(team, recruit)
    hits = sum(1 for k in recruit.priorities if p[k] >= 70)
    bonus = 1.0 + 0.04 * hits
    if p[recruit.priorities[0]] < 40:
        bonus -= 0.05
    return round(clamp(bonus, 0.90, 1.12), 3)


def _pick_number(rng, pos, used):
    from roster import NUMBERS
    for _ in range(60):
        lo, hi = rng.choice(NUMBERS[pos])
        n = rng.randint(lo, hi)
        if n not in used:
            return n
    n = 1
    while n in used:
        n += 1
    return n
