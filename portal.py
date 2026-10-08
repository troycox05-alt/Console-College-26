"""
portal.py — The transfer portal.

Recruiting is a program selling a future. The portal is a player calling the
bluff. Every offseason, players who aren't getting what they were promised —
buried on the depth chart, stuck at a school that was a bad fit from the day
they signed, not developing, losing every Saturday — put their name in and
let the market decide.

WHO LEAVES
  Not the stars. The two-deep. A backup with talent and no snaps is the
  classic portal entrant, and so is a former four-star who picked the wrong
  school. Seniors with a year left leave for a last chance to play, and
  nobody on a winning team with a starting job goes anywhere.

WHO GETS TAKEN
  Teams shop the portal the way they recruit, using the same pitches, but
  with one enormous difference: a transfer plays *now*. So the market prices
  immediate help. A program with a hole at quarterback will pay far above a
  player's rating to fill it, and a player who is better than the guy
  currently starting is the most valuable thing in the portal.

WHO LANDS NOWHERE
  Most of them. The portal is not a guarantee, and the players who enter
  without leverage — low rated, buried for a reason — go undrafted by the
  market and out of the sport. That risk is what makes entering it a real
  decision instead of a free upgrade.

TIMING
  It runs in the offseason, after the old class graduates and everybody
  develops, but before the freshman class arrives — so a team that loses its
  starting quarterback to the portal still has a window to replace him.
"""
import random
from collections import Counter, defaultdict

from recruiting import clamp, pitch_scores
from traits import mod as trait_mod
from roster import ROSTER_SIZE

STARTER_DEPTH = {"QB": 1, "RB": 2, "WR": 3, "TE": 2, "OL": 5, "DL": 4, "LB": 3, "CB": 3, "S": 2,
                 "K": 1, "P": 1}
ROUNDS = 3                       # the window reopens: standards drop each time through
LAND_RATE = 0.88                 # by the end, most of the portal has found somewhere
MAX_INCOMING = 8                 # a staff can only rebuild so much in one window
USER_PULL = 0.95                 # how much a coach's portal work (pitches, visit) moves his decision


class PortalEntry:
    """A player in the portal, and what he's looking for."""

    __slots__ = ("player", "origin", "reason", "depth", "suitors", "destination", "priority")

    def __init__(self, player, origin, reason, depth):
        self.player = player
        self.origin = origin
        self.reason = reason          # short phrase for the news feed
        self.depth = depth            # where he sat on his old depth chart
        self.suitors = []
        self.destination = None
        self.priority = priority_for(reason, player)

    def __setstate__(self, state):          # older saves: entries without a priority
        slots = state[1] if isinstance(state, tuple) else state
        for k, v in (slots or {}).items():
            setattr(self, k, v)
        if not hasattr(self, "priority"):
            self.priority = priority_for(getattr(self, "reason", ""), self.player)

    @property
    def position(self):
        return self.player.position

    @property
    def overall(self):
        return self.player.overall


# What he's shopping for. It decides most of where he goes — pitch to it.
PRIORITY_WORD = {"playing_time": "a starting job", "winning": "a winner", "money": "the best NIL deal",
                 "scheme_fit": "the right scheme", "proximity": "closer to home", "development": "getting to the NFL",
                 "program": "a big-time program"}
PORTAL_STYLE_WORD = {"reload": "Reload (buys starters)", "rebuild": "Rebuild (volume, young players)",
                     "hs": "High-school first (rarely shops)", "balanced": "Balanced"}


def priority_for(reason, player):
    r = (reason or "").lower()
    if "nil" in r or "money" in r or "paid" in r:
        return "money"
    if "losing" in r or "direction" in r or "lost him" in r:
        return "winning"
    if "scheme" in r or "system" in r or "coach" in r:
        return "scheme_fit"
    if "family" in r or "home" in r:
        return "proximity"
    if getattr(player, "overall", 0) >= 78 and getattr(player, "year", 0) >= 2:
        return "development"
    return "playing_time"


SECOND_CHOICES = ("playing_time", "winning", "money", "scheme_fit", "proximity", "development", "program")


def second_priority(entry):
    """The other thing he cares about. Not public: contact or a visit finds it out."""
    first = getattr(entry, "priority", None)
    p = entry.player
    r = random.Random(f"portal2nd:{p.first_name}:{p.last_name}:{getattr(p, 'home_state', '')}")
    opts = [k for k in SECOND_CHOICES if k != first]
    w = [1.0] * len(opts)
    for i, k in enumerate(opts):
        if k == "money" and "mercenary" in getattr(p, "traits", []):
            w[i] = 3.0
        if k == "development" and getattr(p, "overall", 0) >= 75:
            w[i] = 2.0
        if k == "proximity" and "family" in (getattr(entry, "reason", "") or ""):
            w[i] = 3.0
    return r.choices(opts, weights=w)[0]


class _Mid:
    """An rng that always rolls the middle — for a staff's read of a decision, not the decision itself."""
    @staticmethod
    def uniform(a, b):
        return (a + b) / 2

    @staticmethod
    def random():
        return 0.5


def user_mult(team, interest):
    """What a coach's work on a transfer is worth. A small program's pitch has to work harder."""
    return 1 + USER_PULL * interest * (0.7 + 0.3 * min(1.0, getattr(team, "prestige", 60) / 70))


def steady_choice(league, team, entry):
    return player_choice(league, league.recruiting, team, entry, _Mid)


def portal_style(team):
    """How a staff uses the portal this year."""
    wp = getattr(team, "win_pct", 0.5)
    if team.prestige >= 72 and wp >= 0.6:
        return "reload"
    if wp < 0.4:
        return "rebuild"
    if getattr(team.coach, "personality", "") in ("builder", "homebody") and team.prestige >= 60:
        return "hs"
    return "balanced"


class PortalReport:
    def __init__(self, year):
        self.year = year
        self.entries = []
        self.moves = []               # (entry, new_team)
        self.unsigned = []
        self.by_team_in = defaultdict(list)
        self.by_team_out = defaultdict(list)
        self.nil = {}                 # (team, entry) -> NIL a year offered in the window
        self.deals = {}               # entry -> the NIL he signed for


def depth_chart_rank(team, player):
    """Where he sits in his position room, best first."""
    room = sorted((p for p in team.roster if p.position == player.position),
                  key=lambda p: -p.overall)
    return room.index(player) + 1 if player in room else 99


def entry_odds(team, player, rank):
    """How likely this player is to put his name in: the depth chart, then the person."""
    import personalities
    import poscoach
    odds = personalities.portal_odds(team, player, _entry_odds(team, player, rank)) * poscoach.portal_mult(team, player)
    # In-season retention work is real, but not magic: a conversation fades and
    # a role promise only helps if actual Saturday usage backs it up.
    try:
        import retention
        odds *= retention.portal_modifier(player)
    except Exception:
        pass
    t = tampered(player)
    if t:
        odds = odds * (1 + t["s"] * 2.5) + t["s"] * 0.1      # somebody's been in his ear
    return clamp(odds, 0.0, 0.6)


def _entry_odds(team, player, rank):
    starters = STARTER_DEPTH.get(player.position, 2)
    buried = max(0, rank - starters)
    if buried == 0:
        # A starter only leaves a program that's falling apart, and a genuinely
        # good starter doesn't leave at all.
        if player.overall >= 68 or team.win_pct >= 0.4:
            return 0.0
        return 0.02
    odds = 0.03
    odds += buried * 0.085                           # the further down the chart, the louder it gets
    if player.year in (1, 2):
        odds *= 1.5                                  # the classic portal years
    elif player.year == 0:
        odds *= 0.55                                 # true freshmen usually give it a year
    else:
        odds *= 1.15                                 # seniors chasing one last chance to play
    fit = getattr(player, "fit_bonus", 1.0)
    if fit < 1.0:
        odds *= 1.8                                  # he picked wrong out of high school
    elif fit >= 1.08:
        odds *= 0.6
    if getattr(player, "walk_on", False):
        odds *= 0.5                                  # nowhere better to go
    if team.win_pct < 0.34:
        odds *= 1.5
    elif team.win_pct > 0.75:
        odds *= 0.7
    odds *= trait_mod(player, "portal")
    odds /= trait_mod(team.coach, "portal_hold")
    promise = getattr(player, "promise", None)
    if promise == "made":
        odds = odds * 0.4 if buried <= 1 else min(0.9, odds * 2.5 + 0.2)   # kept (or close): he stays; broken: he's gone
    elif promise == "ignored":
        odds *= 1.3
    elif promise == "role":
        odds *= 0.7                                  # a real role now and a shot in the spring
    if getattr(player, "bond", None) is not None:
        odds *= 0.5                                  # he knows you went to bat for him
    if getattr(team, "coach_changed", False):
        odds *= 1 + 0.35 / trait_mod(player, "loyalty")   # the staff that recruited him is gone
    if player.hs_stars >= 4 and buried:
        odds *= 1.6                                  # highly-rated and not playing: he's gone
    return clamp(odds, 0.0, 0.6)


def reason_for(team, player, rank, rng):
    import personalities
    why = personalities.portal_reason(player)
    if why:
        return why
    starters = STARTER_DEPTH.get(player.position, 2)
    buried = rank - starters
    if getattr(player, "fit_bonus", 1.0) < 1.0 and rng.random() < 0.5:
        return rng.choice(("never fit the scheme", "wrong system for his game",
                           "picked the wrong school out of high school"))
    if getattr(team, "coach_changed", False) and rng.random() < 0.35:
        return rng.choice(("the coach who recruited him is gone", "doesn't fit the new staff's system",
                           "coaching change"))
    if team.win_pct < 0.34 and rng.random() < 0.55:
        return rng.choice(("wants out of a losing program", "no faith in the direction",
                           "coaching staff lost him"))
    if buried > 2:
        return rng.choice(("buried on the depth chart", "fourth string and going nowhere",
                           "passed over again", "no path to the field here"))
    if buried > 0:
        return rng.choice(("looking for playing time", "wants a starting job",
                           "tired of waiting his turn", "lost the position battle"))
    if player.year >= 3:
        return rng.choice(("one last shot at starting", "graduate transfer"))
    return rng.choice(("seeking a bigger role", "wants a fresh start", "family reasons"))


def open_portal(league, rng, report):
    """Everybody who puts their name in."""
    for team in league.teams:
        for player in list(team.roster):
            rank = depth_chart_rank(team, player)
            if rng.random() < entry_odds(team, player, rank):
                if team is not getattr(league, "user_team", None) and rank <= STARTER_DEPTH.get(player.position, 2) \
                        and not tampered(player) and rng.random() < 0.3:
                    player.nil = int((getattr(player, "nil", 0) or 0) * 1.15) + 25_000    # his staff keeps him
                    report.__dict__.setdefault("retained", []).append((player, team))
                    continue
                entry = PortalEntry(player, team, reason_for(team, player, rank, rng), rank)
                report.entries.append(entry)
                report.by_team_out[team].append(entry)
                team.roster.remove(player)
                player.team = None
                player.nil_before_portal = getattr(player, "nil", 0)
                player.nil = 0                   # his NIL deal was with that school; it ends here
    for team in league.teams:
        for p in team.roster:
            p.__dict__.pop("promise", None)          # promises are for one season
            p.__dict__.pop("bond", None)
    report.entries.sort(key=lambda e: -e.overall)
    return report.entries


def team_needs(team, commits=()):
    """Holes on the roster, weighted by how badly they'd hurt on Saturday. Committed recruits
    at a position count as bodies already in the room (they arrive with the class)."""
    needs = {}
    incoming = {}
    for r in commits:
        incoming[r.position] = incoming.get(r.position, 0) + 1
    for pos, size in ROSTER_SIZE.items():
        room = sorted((p.overall for p in team.roster if p.position == pos), reverse=True)
        room += [0] * incoming.get(pos, 0)
        starters = STARTER_DEPTH.get(pos, 2)
        have = room[:starters]
        shortfall = starters - len(have)
        quality = sum(have) / len(have) if have else 0
        needs[pos] = (shortfall, quality, len(room))
    return needs


def transfer_value(league, team, entry, needs):
    """What this player is worth to this specific team.

    The portal prices immediate help, so being better than the man currently
    starting is worth more than raw rating."""
    pos = entry.position
    shortfall, quality, roomsize = needs[pos]
    if roomsize >= ROSTER_SIZE[pos]:
        return 0.0
    value = entry.overall - 45                        # replacement level
    if roomsize < ROSTER_SIZE[pos]:
        value += 10 * (ROSTER_SIZE[pos] - roomsize)   # an empty locker is worth filling
    if shortfall > 0:
        value += 28 * shortfall                       # an actual hole in the starting lineup
    upgrade = entry.overall - quality
    if upgrade > 0:
        value += upgrade * 2.4                        # he'd start here tomorrow
    else:
        value += upgrade * 0.8
    if pos == "QB":
        value *= 1.2                                  # quarterbacks move the market
    if entry.player.year >= 2:
        value += 6                                    # ready now, no projection needed
    return max(0.0, value)


def player_choice(league, cycle, team, entry, rng):
    """How appealing that program is to him — the same pitches recruiting uses,
    but playing time is what he left for, so it dominates."""
    pitches = pitch_scores(league, team, _as_recruit(entry))
    weights = {"playing_time": 2.2, "winning": 2.2, "development": 1.5, "proximity": 0.8,
               "scheme_fit": 0.9, "facilities": 0.6, "tradition": 0.7, "campus": 0.3,
               "academics": 0.3, "relationship": 0.0}
    pri = getattr(entry, "priority", None)
    if pri in weights:
        weights = dict(weights)
        weights[pri] *= 2.5                           # what he left for matters most
    score = sum(pitches[k] * w for k, w in weights.items()) / sum(weights.values())
    # The better the player, the more the name on the helmet matters: good
    # players in the portal move up, or at worst sideways.
    leverage = clamp((entry.overall - 55) / 30, 0.0, 1.0)
    score *= 1 + leverage * (team.prestige - 60) / 110
    # He follows the coach who recruited him: the staff that left his school this winter.
    if team.coach is not None and team.coach.name == _old_coach(entry.origin):
        score *= 1.4
    return score * rng.uniform(0.88, 1.12)


def _film_read(team, entry):
    """A staff's evaluation miss on this player, steady for the whole window (same team, same player)."""
    import random as _r

    import staff
    eye = staff.recruiting_rating(team)
    rng = _r.Random(f"film:{team.school}:{entry.player.name}:{getattr(entry.player, 'number', 0)}")
    return rng.gauss(0, max(2.0, (100 - eye) / 7))


def _old_coach(origin):
    """The head coach a school just lost (its coaching change this winter), or None."""
    if not getattr(origin, "coach_changed", False):
        return None
    log = getattr(origin, "coach_log", []) or []
    return log[-2][1] if len(log) >= 2 else None


class _RecruitView:
    """Adapter so portal players can reuse the recruiting pitch calculations."""
    __slots__ = ("player", "position", "home_state", "region", "_proj")

    def __init__(self, player):
        self.player = player
        self.position = player.position
        self.home_state = getattr(player, "home_state", None) or "TX"
        from recruiting_data import STATES
        self.region = STATES[self.home_state][1]
        self._proj = player.overall

    def projection(self):
        return self._proj


def _as_recruit(entry):
    return _RecruitView(entry.player)


def resolve_portal(league, rng, report):
    """Teams shop, players choose, and the rest of the portal goes home.

    The window runs in rounds. The first is the feeding frenzy at the top of
    the board; by the third, staffs are filling out a two-deep with whoever is
    left rather than handing the spot to a walk-on."""
    landed = 0
    target = int(len(report.entries) * LAND_RATE)
    incoming = Counter()
    for rnd in range(ROUNDS):
        remaining = [e for e in report.entries if e.destination is None]
        if not remaining or landed >= target:
            break
        landed += _portal_round(league, rng, report, remaining, incoming, target - landed, rnd)
    report.unsigned = [e for e in report.entries if e.destination is None]
    return report


def _portal_round(league, rng, report, remaining, incoming, room_left, rnd):
    import finance
    cycle = league.recruiting
    landed = 0
    report.__dict__.setdefault("nil", {})
    report.__dict__.setdefault("deals", {})
    money_left = {t: finance.portal_room(league, t, report) for t in league.teams}   # NIL each staff has for transfers
    # Needs are worked out once per round, not once per player: recomputing a
    # whole league's depth charts for every entrant was most of the offseason.
    cyc = league.recruiting
    need_cache = {id(t): team_needs(t, cyc._class_of(t)) for t in league.teams}
    dirty = set()
    # Later rounds: teams look past the starters and take depth.
    floor = (0.0, -12.0, -30.0)[min(rnd, 2)]
    style_cache = {}
    for entry in remaining:
        if landed >= room_left:
            break
        bidders = []
        users = _users(report)
        for team in league.teams:
            if incoming[team] >= MAX_INCOMING or len(team.roster) >= sum(ROSTER_SIZE.values()):
                continue
            if team in users:
                if entry not in users[team]["offers"]:
                    continue                          # you only land players you offered a spot
                bidders.append((1e6, team))           # you're always on his shortlist
                continue
            if id(team) in dirty:
                need_cache[id(team)] = team_needs(team, cyc._class_of(team))
                dirty.discard(id(team))
            value = transfer_value(league, team, entry, need_cache[id(team)])
            # Nobody sees a transfer's true rating: staffs read film, and better staffs read it better.
            value += _film_read(team, entry)
            if value <= floor:
                continue
            # A staff's pull in the portal scales with what it can offer.
            import staff
            appeal = value * (0.6 + staff.recruiting_rating(team) / 200) * (0.7 + team.prestige / 140)
            appeal *= trait_mod(team.coach, "portal_shop")     # Portal Kings work the phones harder
            style = style_cache.setdefault(id(team), portal_style(team))
            if style == "reload":
                appeal *= 1.25 if entry.overall > need_cache[id(team)][entry.position][1] else 0.55
            elif style == "rebuild":
                appeal *= 1.2 if entry.player.year <= 2 else 1.0
            elif style == "hs":
                appeal *= 0.65
            bidders.append((appeal, team))
        if not bidders:
            continue
        bidders.sort(key=lambda x: -x[0])
        shortlist = [t for _, t in bidders[:6]]
        # Money on the table: yours is what you offered in the window; every other staff bids what its budget allows.
        cash = {}
        for appeal, t in bidders[:6]:
            if t in users:
                cash[t] = report.nil.get((t, entry), 0)
            else:
                cash[t] = finance.ai_portal_offer(league, t, entry, appeal, money_left[t], rng)
        best = max(cash.values(), default=0)
        money_x = 2.0 if getattr(entry, "priority", None) == "money" else 1.0
        scores = [(player_choice(league, cycle, t, entry, rng)
                   * (user_mult(t, users[t]["interest"].get(entry, 0)) if t in users else 1)
                   * finance.portal_pull(cash[t], best, entry.player) ** money_x
                   * (1 + tamper_pull(entry, t)), t)
                  for t in shortlist]
        scores.sort(key=lambda x: -x[0])
        pick = scores[0][1]
        if pick not in users:
            money_left[pick] -= cash.get(pick, 0)
        sign(report, entry, pick, cash.get(pick, 0), suitors=[t for _, t in scores[:4]])
        incoming[pick] += 1
        dirty.add(id(pick))
        landed += 1
    return landed


def sign(report, entry, team, nil=0, suitors=None):
    """He picks a school: the move, the deal and the paperwork. Used by the market's rounds and by a
    coach who closes him early (Push for a commitment in the portal window)."""
    entry.player.nil = nil or 0                       # the deal comes with the move
    report.__dict__.setdefault("deals", {})[entry] = entry.player.nil
    entry.suitors = list(suitors) if suitors else [team]
    entry.destination = team
    team.add_player(entry.player)
    entry.player.transfers = getattr(entry.player, "transfers", 0) + 1
    entry.player.prev_school = entry.origin.school
    entry.player.events[report.year].append(f"Transferred to {team.school} from {entry.origin.school}")
    entry.player.transfer_from = entry.origin.school
    # A fresh start counts for something: he chose this one himself.
    entry.player.fit_bonus = round(clamp(entry.player.fit_bonus + 0.03, 0.90, 1.14), 3)
    report.moves.append((entry, team))
    report.by_team_in[team].append(entry)


def fill_gaps(team, report, rng):
    """Late portal adds: a staff would rather take a transfer than a walk-on."""
    added = []
    leftovers = [e for e in report.entries if e.destination is None]
    if not leftovers:
        return added
    for pos, size in ROSTER_SIZE.items():
        short = size - len([p for p in team.roster if p.position == pos])
        if short <= 0:
            continue
        # Even a late add has to be worth a scholarship; the bottom of the
        # portal still goes unsigned.
        options = sorted((e for e in leftovers if e.position == pos and e.origin is not team
                          and e.overall >= 48), key=lambda e: -e.overall)
        for entry in options[:short]:
            entry.destination = team
            entry.player.transfers = getattr(entry.player, "transfers", 0) + 1
            entry.player.prev_school = entry.origin.school
            entry.player.events[report.year].append(f"Transferred to {team.school} from {entry.origin.school}")
            entry.player.transfer_from = entry.origin.school
            team.add_player(entry.player)
            report.moves.append((entry, team))
            report.by_team_in[team].append(entry)
            leftovers.remove(entry)
            added.append(entry)
    return added


def _users(report):
    """{team: window data} for every human who worked the window."""
    us = list(getattr(report, "users", None) or [])
    u = getattr(report, "user", None)
    if u is not None and all(u is not x for x in us):
        us.append(u)
    return {x["team"]: x for x in us}


def run_portal(league, rng, year, window=None):
    report = _run_portal(league, rng, year, window)
    import gray_area
    gray_area.after_portal(league, report)
    return report


def _run_portal(league, rng, year, window=None):
    """The whole window, start to finish. `window` is your turn: after everybody
    enters and before anybody lands, you contact, pitch, host visits, offer
    roster spots — and try to talk your own players out of leaving."""
    report = PortalReport(year)
    open_portal(league, rng, report)
    if window is not None:
        window(league, report)
    resolve_portal(league, rng, report)
    return report


def base_interest(league, team, entry):
    """0-1: where your program ranks among all his options, before you do anything."""
    rng = random.Random(f"interest:{entry.player.name}")
    mine = player_choice(league, league.recruiting, team, entry, rng)
    others = [player_choice(league, league.recruiting, t, entry, rng) for t in league.teams if t is not team]
    return sum(1 for x in others if x < mine) / max(1, len(others))



# ═══ Tampering (see gray_area.py) ════════════════════════════════════════════

def tampered(player):
    t = player.__dict__.get("tampered")
    return t if t and t.get("fresh", True) else None


def tamper_pull(entry, team):
    t = entry.player.__dict__.get("tampered")
    return t["s"] * 1.5 if t and t.get("school") == team.school else 0.0
