"""
compliance.py — Rules, rule-breaking, and the people who catch it.

Every program in the country lives with a quiet risk: somebody, somewhere, bends a
rule. A booster's dealership leases cars for nothing. An assistant texts a recruit
in a dead period. A collective's "appearance" deal pays a starter for no appearance.
A tutor writes a paper. Most of it never comes out, or comes out small. Some of it
becomes the story of a decade.

THE PIPELINE  (every program, every year; your own included)
  HIDDEN       a violation has happened and nobody outside knows. Each week it can be
               self-reported by a strong compliance office, or found: a whistleblower,
               a reporter, a rival's tip, a disgruntled former player.
  RUMOR        a report runs. The program answers (or doesn't). Some stories die; some
               bring the CAB.
  INQUIRY      the enforcement staff is in the building. How the school cooperates
               matters: open books, outside counsel, or the minimum.
  ALLEGATIONS  the Notice of Allegations. Accept, negotiate, contest, or punish yourself first.
  RULED        the Committee on Infractions decides. Appeal if you dare.

SEVERITY  Level III (minor)  ·  Level II (significant)  ·  Level I (severe breach).
  Cooperation, self-reporting and a strong office shrink the penalty. Stonewalling and
  cover-ups grow it — and a cover-up that comes out moves a case up a level.

PENALTIES  fines (out of next year's pool), probation, postseason bans, scholarship cuts
  (a smaller signing class), fewer recruiting hours, NIL/booster restrictions, vacated
  wins, players held out, and heat on the head coach's seat. A postseason ban and the
  recruiting penalty use the same `team.sanctions` record the rest of the game reads.

ACADEMICS  Every player has a GPA (never shown as a number in career mode — words).
  Midterms and finals decide who is eligible; the team's APR (Academic Progress Rate)
  decides whether the school is penalized. 930 is the line. Academic support spending
  moves both.

OFF THE FIELD  arrests, failed tests, conduct-code cases, a post that goes viral, sports
  wagering. Your program's reputation (integrity) moves with how they're handled, and
  recruits and your AD notice.

A note on people: the personal wrongdoing here belongs to made-up boosters, staffers and
players. Real head coaches are never accused of anything: the head coach is answerable
for the program (his seat heats up), the way the rules say he is.

State lives on the league (league.compliance) and on each team (team.comp); every read
has a default, so saves from before this system load fine.
"""
import random

START_YEAR = 2026                    # the world you inherit is clean; nothing happens in the burn-in years

LEVEL_WORD = {1: "Level I", 2: "Level II", 3: "Level III"}
LEVEL_BLURB = {1: "severe breach", 2: "significant violation", 3: "minor (secondary) violation"}

KINDS = {
    "benefits":    {"label": "Impermissible benefits", "why": "impermissible benefits from boosters", "w": 24,
                    "players": True},
    "recruiting":  {"label": "Recruiting violations", "why": "recruiting violations", "w": 25, "players": False},
    "nil":         {"label": "NIL / pay-for-play", "why": "a pay-for-play scheme run through a collective", "w": 19,
                    "players": True},
    "academic":    {"label": "Academic misconduct", "why": "academic misconduct", "w": 10, "players": True},
    "tampering":   {"label": "Transfer tampering", "why": "tampering with transfer-portal players", "w": 14,
                    "players": False},
    "eligibility": {"label": "Ineligible player", "why": "playing an ineligible player", "w": 8, "players": True},
    "apr":         {"label": "Academic Progress Rate", "why": "academic performance (APR)", "w": 0, "players": False},
}
KIND_ORDER = tuple(KINDS)

TEMPLATES = {
    "benefits": ["a booster's dealership leased cars to several players at far below market",
                 "a booster covered a recruit's family's travel and lodging on an unofficial visit",
                 "an alum arranged no-show jobs for a handful of players",
                 "a booster handed cash to a starter after a big win",
                 "a booster-owned restaurant let players eat free, all season"],
    "recruiting": ["an assistant coach made off-campus contact with a top target during a dead period",
                   "the staff ran a private camp for a recruit's travel team in violation of contact rules",
                   "a staffer's texts to a prospect's family ran well past what the rules allow",
                   "a staff member sent messages to a recruit through an intermediary before the permitted date",
                   "an assistant hosted a prospect on a visit that was never logged"],
    "nil": ["a collective's deals with two starters were tied to enrollment and performance, not to real work",
            "a collective promised a recruit's family a payment that depended on his signing",
            "a booster-funded 'appearance' deal paid a player far above market for appearances he never made",
            "a collective paid an incoming transfer before he'd enrolled"],
    "academic": ["a tutor completed coursework for several athletes",
                 "an academic advisor steered players into a no-show course to keep them eligible",
                 "grade changes for a few players were approved outside normal procedures"],
    "tampering": ["an assistant coach contacted a transfer target on another roster before he entered the portal",
                  "a booster reached out to a rival's starter about a deal to transfer",
                  "a staffer worked a player's family through a third party while he was still under contract elsewhere"],
    "apr": ["the team's Academic Progress Rate stayed below the line"],
    "eligibility": ["a player was allowed to compete after his eligibility had run out",
                    "a transfer suited up for several games before his paperwork cleared",
                    "a player's academic certification was signed off on incomplete records"],
}

# Where the tip came from, for the headline.
LEAKS = {
    "report": ["A newspaper investigation reports that {what}.",
               "A national outlet has documents showing {what}.",
               "A sports-radio host breaks it: {what}."],
    "whistle": ["A former staffer tells reporters {what}.",
                "A player who transferred out says {what}.",
                "A booster who fell out with the program tells the press {what}."],
    "tip": ["The CAB has received a tip that {what}.",
            "A complaint from a rival program alleges {what}."],
}

OFFICE_TIER = {"lean": (-14, -0.0020, "Lean"), "standard": (0, 0.0, "Standard"),
               "robust": (13, 0.0040, "Robust")}
SUPPORT_TIER = {"lean": (-0.05, -0.0020, "Lean"), "standard": (0.0, 0.0, "Standard"),
                "elite": (0.09, 0.0050, "Elite")}

APR_LINE = 930
GPA_LINE = 2.0
BASE_TICK = 0.0085                   # chance per program per week that something gets bent
CLASS_BASE = 25


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ═══ State ══════════════════════════════════════════════════════════════════

def active(league):
    if league.year < START_YEAR:
        return False
    import commissioner
    return commissioner.allows(league, "sanctions")     # Commissioner Mode can switch the whole system off


def root(league):
    r = league.__dict__.get("compliance")
    if r is None:
        r = league.compliance = {"cases": [], "news": [], "seq": 0, "aprs": {}, "audit": {}}
    for k, v in (("cases", []), ("news", []), ("seq", 0), ("aprs", {}), ("audit", {})):
        r.setdefault(k, v)
    return r


def st(team):
    s = team.__dict__.get("comp")
    if s is None:
        rng = random.Random(f"comp:{team.school}")
        ad = team.ratings.get("athletic_director", 50)
        acad = team.ratings.get("academics", 50)
        s = team.comp = {
            "office": int(clamp(round(ad * 0.62 + 22 + rng.gauss(0, 6)), 22, 92)),
            "rep": float(clamp(round(66 + (acad - 50) * 0.12 + rng.gauss(0, 5)), 40, 90)),
            "tier": "standard", "support": "standard",
            "penalties": [], "apr": {}, "history": [], "vacated": [],
            "hc_susp": 0, "incidents": 0, "audit_year": None,
        }
    return s


def _tables_ok(s):
    for k, v in (("penalties", []), ("apr", {}), ("history", []), ("vacated", []), ("hc_susp", 0),
                 ("incidents", 0), ("audit_year", None), ("tier", "standard"), ("support", "standard")):
        s.setdefault(k, v)
    return s


def office_eff(team):
    s = _tables_ok(st(team))
    return int(clamp(s["office"] + OFFICE_TIER[s["tier"]][0], 10, 98))


def office_word(v):
    return ("elite" if v >= 82 else "strong" if v >= 66 else "solid" if v >= 50 else "thin" if v >= 36 else "a skeleton crew")


def rep(team):
    return st(team)["rep"]


def rep_word(v):
    return ("a model program" if v >= 82 else "well regarded" if v >= 68 else "no complaints" if v >= 54
            else "a cloud over it" if v >= 40 else "toxic")


def rep_nudge(team, d):
    s = st(team)
    s["rep"] = float(clamp(s["rep"] + d, 5, 98))


def rep_pull(team):
    """A few points on the recruiting pull (±2): families notice who runs a clean shop."""
    if getattr(team, "fcs", False):
        return 0.0
    return (st(team)["rep"] - 66) / 34.0 * 2.0


def ad_style(team):
    ad = getattr(team, "ad", None)
    return ad.get("style") if isinstance(ad, dict) else None


def mine(league):
    """The program the human is responsible for (a coach's, or an AD's), if any."""
    try:
        if getattr(league, "autosim", False):
            return None
        if getattr(league, "mode", None) == "career":
            me = getattr(league, "user_coach", None)
            return me.team if me is not None and me.team is not None else None
        if getattr(league, "mode", None) == "ad":
            import ad_mode
            return ad_mode.my_team(league) if ad_mode.active(league) else None
    except Exception:
        return None
    return None


def _by_school(league, school):
    for t in league.teams:
        if t.school == school:
            return t
    return None


def _rng(league, salt):
    return random.Random(f"comp:{league.seed}:{league.year}:{league.week}:{salt}")


# ═══ News ═══════════════════════════════════════════════════════════════════

def news(league, kind, text, school=None, level=None):
    r = root(league)
    r["news"].append({"year": league.year, "week": league.week, "kind": kind, "text": text,
                      "school": school, "level": level})
    del r["news"][:-260]
    return text


def recent_news(league, n=12, school=None, year=None):
    items = [x for x in root(league)["news"]
             if (school is None or x.get("school") == school) and (year is None or x["year"] == year)]
    return list(reversed(items))[:n]


# ═══ Cases ══════════════════════════════════════════════════════════════════

def cases(league, school=None, open_only=False):
    out = root(league)["cases"]
    if school is not None:
        out = [c for c in out if c["school"] == school]
    if open_only:
        out = [c for c in out if not c["closed"]]
    return out


def case_by_id(league, cid):
    for c in root(league)["cases"]:
        if c["id"] == cid:
            return c
    return None


def public_cases(league, team=None):
    """Cases the world knows about (not hidden)."""
    return [c for c in root(league)["cases"] if c["status"] != "hidden" and not c["closed"]
            and (team is None or c["school"] == team.school)]


def hidden_cases(league, team):
    return [c for c in root(league)["cases"] if c["school"] == team.school and c["status"] == "hidden"]


STAGE_WORD = {"hidden": "undiscovered", "rumor": "media reports", "inquiry": "CAB inquiry",
              "allegations": "Notice of Allegations", "ruled": "penalties announced",
              "appeal": "under appeal", "closed": "closed"}


def stage_label(c):
    if c["closed"]:
        return "closed"
    return STAGE_WORD.get(c["status"], c["status"])


def _pick_players(team, kind, rng):
    if not KINDS[kind]["players"] or not team.roster:
        return []
    pool = [p for p in team.roster if p.year <= 3]
    weights = [max(1, p.overall - 35) + (25 if p.overall >= 72 else 0) for p in pool]
    n = rng.choice((1, 1, 2, 2, 3))
    out = []
    for _ in range(min(n, len(pool))):
        p = rng.choices(pool, weights=weights)[0]
        if p not in out:
            out.append(p)
    return out


def new_case(league, team, kind, level, rng, *, user=False, cover=False, evidence=None, text=None,
             players=None, source=None, status="hidden"):
    r = root(league)
    r["seq"] += 1
    players = _pick_players(team, kind, rng) if players is None else players
    c = {"id": r["seq"], "school": team.school, "kind": kind, "level": level, "year": league.year,
         "week": league.week, "text": text or rng.choice(TEMPLATES[kind]), "status": status,
         "stage_age": 0, "age": 0, "found": None, "how": None, "coop": 0, "self_reported": False,
         "cover": cover, "counsel": False, "contest": None, "self_imposed": False, "appeal": False,
         "user": user, "evidence": evidence if evidence is not None else rng.randint(35, 95),
         "players": list(players), "pnames": [p.name for p in players], "closed": False, "outcome": None,
         "ruling": None, "seasons": [league.year], "source": source or "", "prompted": set(),
         "public": True, "press": None}
    r["cases"].append(c)
    return c


def risk(league, team):
    """How likely this program is to bend a rule this week, against an average one (=1.0)."""
    s = _tables_ok(st(team))
    r = 1.0
    r *= {"booster": 1.45, "win_now": 1.3, "brand": 1.15, "big_game": 1.1, "patient": 0.85,
          "traditionalist": 0.8, "analytics": 0.9}.get(ad_style(team), 1.0)
    r *= 1.6 - office_eff(team) / 100 * 1.25
    r *= 1.25 - s["rep"] / 100 * 0.5
    r *= 0.85 + team.prestige / 100 * 0.5
    if active_probation(league, team):
        r *= 0.7
    c = team.coach
    pers = getattr(c, "personality", None) if c is not None else None
    r *= {"mercenary": 1.15, "climber": 1.1, "blue_blood": 1.1, "loyalist": 0.9, "lifer": 0.9}.get(pers, 1.0)
    r *= 1 + s.get("heat", 0.0)
    return clamp(r, 0.2, 3.4)


def _level_roll(rng, r):
    w = (72, 21, 7) if r < 1.6 else (62, 27, 11)
    return rng.choices((3, 2, 1), weights=w)[0]


def _spawn(league, team, rng):
    r = risk(league, team)
    if rng.random() > BASE_TICK * r:
        return None
    kind = rng.choices(KIND_ORDER, weights=[KINDS[k]["w"] for k in KIND_ORDER])[0]
    return new_case(league, team, kind, _level_roll(rng, r), rng)


# ═══ Discovery ══════════════════════════════════════════════════════════════

def _disgruntled(team):
    return sum(1 for p in team.roster if getattr(p, "disgruntled", None) is not None)


def _discover_p(league, team, c):
    h = 0.010 + 0.006 * (4 - c["level"])
    h *= 0.7 + team.prestige / 100
    h *= min(1.6, 1 + 0.04 * _disgruntled(team))
    if c["age"] > 40:
        h *= 1.4
    if c["cover"]:
        h *= 1.3
    return h


def discover(league, c, how, rng):
    """A hidden violation stops being hidden."""
    team = _by_school(league, c["school"])
    if team is None:
        return
    c["found"] = (league.year, league.week)
    c["how"] = how
    c["stage_age"] = 0
    c["seasons"] = list(range(c["year"], league.year + 1))
    if c["cover"] and how not in ("self", "audit") and c["level"] > 1 and rng.random() < 0.6:
        c["level"] -= 1                                  # the cover-up is worse than the crime
        c["text"] = c["text"] + ", and the school sat on it"
        c["escalated"] = True
    lvl = c["level"]
    if how in ("self", "audit"):
        c["self_reported"] = True
        c["coop"] += 2
        c["status"] = "inquiry"
        rep_nudge(team, -1.0 * (4 - lvl))
        if lvl <= 2 or team.prestige >= 65:
            news(league, "self", f"{team.school} self-reports {'a possible major violation' if lvl <= 2 else 'a violation'} "
                                 f"to the CAB: {c['text']}.", team.school, lvl)
        else:
            c["public"] = False
    else:
        c["status"] = "rumor"
        rep_nudge(team, -(3 + (4 - lvl) * 2.2))
        c["public"] = lvl <= 2 or team.prestige >= 60 or mine(league) is team
        if c["public"]:
            text = rng.choice(LEAKS.get(how, LEAKS["report"])).format(what=c["text"])
            news(league, "report", f"{team.school}: {text}", team.school, lvl)
    _reactions(league, team, c, "found")
    import compliance_events as ev
    ev.stage_changed(league, team, c)


def _reactions(league, team, c, moment):
    """The heat on the program when something breaks: the seat, the AD, the fans."""
    lvl = c["level"]
    if moment == "found":
        heat = {1: 6, 2: 3, 3: 0}[lvl] * (0.5 if c["self_reported"] else 1.0)
        if heat:
            seat_hit(league, team, heat, "an investigation is in the news")
        if mine(league) is team:
            _ad_react(league, team, -{1: 6, 2: 3, 3: 1}[lvl] * (0.5 if c["self_reported"] else 1.0), "news of a violation")


def seat_hit(league, team, heat, why):
    c = team.coach
    if c is None or not heat:
        return
    c.__dict__.setdefault("seat_events", []).append((league.week, heat, why))
    c.seat = int(clamp(getattr(c, "seat", 40) + heat, 0, 100))
    if getattr(c, "is_user", False) or (mine(league) is team and getattr(league, "mode", None) == "career"):
        import ad_trust
        ad_trust.change(league, -abs(heat) * 1.2, why)


def _ad_react(league, team, amount, why):
    """The board, the fans and the boosters react (Athletic Director mode)."""
    try:
        import ad_mode
        if ad_mode.active(league) and ad_mode.is_mine(league, team):
            ad_mode.bump(league, "board", amount, why)
            ad_mode.bump(league, "fans", amount * 0.8, why)
    except Exception:
        pass


# ═══ The pipeline ═══════════════════════════════════════════════════════════

def _dur(c, rng):
    lvl = c["level"]
    if c["status"] == "rumor":
        return rng.randint(2, 4)
    if c["status"] == "inquiry":
        return {3: rng.randint(3, 5), 2: rng.randint(7, 12), 1: rng.randint(10, 18)}[lvl]
    if c["status"] == "allegations":
        return {3: 0, 2: rng.randint(8, 14), 1: rng.randint(10, 18)}[lvl]
    if c["status"] == "appeal":
        return rng.randint(5, 8)
    if c["status"] == "ruled":
        return 4                                  # the window to appeal stays open a few weeks
    return 99


def advance(league, c, rng, steps=1):
    """Move one case forward by a week (or a stretch of offseason)."""
    if c["closed"] or c["status"] == "hidden":
        return
    team = _by_school(league, c["school"])
    if team is None:
        c["closed"] = True
        return
    c["age"] += steps
    c["stage_age"] += steps
    need = c.setdefault("_dur", {}).setdefault(c["status"], _dur(c, rng))
    if c["stage_age"] < need:
        return
    old = c["status"]
    if old == "rumor":
        p_open = clamp(c["evidence"] / 100 * (0.55 + 0.15 * (4 - c["level"])) + c["coop"] * -0.04
                       + (0.12 if c["cover"] else 0.0), 0.05, 0.97)
        if c["press"] == "cooperate":
            p_open *= 0.92
        if rng.random() < p_open:
            c["status"] = "inquiry"
            c["stage_age"] = 0
            if c["public"] or c["user"]:
                news(league, "inquiry", f"The CAB opens an inquiry into {team.school}: {c['text']}.", team.school, c["level"])
        else:
            _close(league, team, c, "The story fades. The CAB takes no action.", cleared=True)
            return
    elif old == "inquiry":
        c["stage_age"] = 0
        if c["level"] == 3:
            _rule(league, team, c, rng)
            return
        c["status"] = "allegations"
        news(league, "allegations", f"CAB sends {team.school} a Notice of Allegations ({LEVEL_WORD[c['level']]}): "
                                    f"{c['text']}.", team.school, c["level"])
    elif old == "allegations":
        _rule(league, team, c, rng)
        return
    elif old == "appeal":
        _decide_appeal(league, team, c, rng)
        return
    elif old == "ruled":
        _finish(league, team, c)
        return
    import compliance_events as ev
    ev.stage_changed(league, team, c)


def _close(league, team, c, outcome, cleared=False):
    c["closed"] = True
    c["status"] = "closed"
    c["outcome"] = outcome
    if cleared:
        rep_nudge(team, 2.0 + (4 - c["level"]))
        news(league, "cleared", f"{team.school} is cleared: {outcome}", team.school, c["level"])
        st(team)["history"].append((league.year, f"Investigation closed with no action ({c['kind']})."))


# ═══ Rulings ════════════════════════════════════════════════════════════════

def severity(c):
    base = {1: 1.0, 2: 0.6, 3: 0.25}[c["level"]]
    sev = base * (1 - 0.10 * clamp(c["coop"], -3, 3))
    if c["self_reported"]:
        sev *= 0.85
    if c["counsel"]:
        sev *= 0.95
    if c["self_imposed"]:
        sev *= 0.85
    if c["contest"] == "won":
        sev *= 0.70
    elif c["contest"] == "lost":
        sev *= 1.15
    if c["cover"]:
        sev *= 1.25
    return clamp(sev, 0.08, 1.8)


def build_ruling(league, team, c, rng):
    """What the Committee on Infractions decides."""
    sev = clamp(severity(c) * rng.uniform(0.8, 1.25), 0.08, 1.9)
    lvl = c["level"]
    y = league.year
    budget = _budget(team)
    ruling = {"year": y, "sev": round(sev, 2), "level": lvl, "case": c["id"], "kind": c["kind"],
              "why": KINDS[c["kind"]]["why"], "fine": 0, "probation": 0, "bans": [], "class_cut": {},
              "recruit_mult": 1.0, "recruit_until": y, "nil_mult": 1.0, "nil_until": y, "vacated": {},
              "player_holds": [], "hc_susp": 0, "seat": 0.0, "brand": 0.0, "lines": []}
    lines = ruling["lines"]
    if lvl == 3:
        ruling["fine"] = int(budget * (0.004 + 0.02 * sev))
        lines.append("public reprimand and censure")
        if sev >= 0.3:
            ruling["recruit_mult"] = 0.97
            ruling["recruit_until"] = y + 1
            lines.append("a limit on recruiting communication for a year")
        ruling["seat"] = 0.0 if sev < 0.3 else 2.0
        ruling["brand"] = 0.0
    else:
        ruling["fine"] = int(budget * (0.012 + 0.05 * sev))
        ruling["probation"] = min(4, 1 + int(sev * 3)) if lvl == 1 else 1 + (1 if sev >= 0.55 else 0)
        lines.append(f"{ruling['probation']} year{'s' if ruling['probation'] != 1 else ''} of probation")
        ban_at = 0.85 if lvl == 1 else 1.05
        if sev >= ban_at:
            n = 1 + (1 if sev >= 1.25 and lvl == 1 else 0)
            ruling["bans"] = [y + 1 + i for i in range(n)]
            lines.append("a postseason ban in " + " and ".join(str(b) for b in ruling["bans"]))
        cut = min(12, int(round(sev * (8 if lvl == 1 else 5))))
        if cut >= 1:
            if cut >= 3:
                a = (cut + 1) // 2
                ruling["class_cut"] = {str(y): a, str(y + 1): cut - a}
            else:
                ruling["class_cut"] = {str(y): cut}
            lines.append(f"{cut} scholarship{'s' if cut != 1 else ''} lost across the next signing "
                         f"class{'es' if len(ruling['class_cut']) > 1 else ''}")
        ruling["recruit_mult"] = round(1 - min(0.30, 0.22 * sev), 2)
        ruling["recruit_until"] = y + ruling["probation"]
        lines.append(f"fewer recruiting hours through {ruling['recruit_until']}")
        if c["kind"] in ("nil", "benefits") and lvl == 1:
            ruling["nil_mult"] = round(1 - 0.25 * sev, 2)
            ruling["nil_until"] = y + 2
            lines.append("booster and collective restrictions for two years")
        ruling["seat"] = (10 + 32 * sev) if lvl == 1 else (4 + 12 * sev)
        ruling["brand"] = -(4 + 14 * sev) if lvl == 1 else -(2 + 5 * sev)
        if lvl == 1 and sev >= 0.7:
            ruling["hc_susp"] = 1 + int(sev * 3)
            lines.append(f"the head coach is answerable: a {ruling['hc_susp']}-game sideline suspension")
    lines.append(f"a fine of {_money(ruling['fine'])}")
    # players
    if c["players"] and KINDS[c["kind"]]["players"]:
        g = {1: (3, 7), 2: (2, 4), 3: (1, 2)}[lvl]
        for p in c["players"]:
            if p in team.roster:
                n = rng.randint(*g)
                ruling["player_holds"].append((p, n))
        if ruling["player_holds"]:
            names = ", ".join(f"{p.short_name} ({n})" for p, n in ruling["player_holds"][:3])
            lines.append(f"players held out: {names}" + (" and others" if len(ruling["player_holds"]) > 3 else ""))
        if lvl <= 2 and c["kind"] in ("benefits", "nil", "academic", "eligibility"):
            played = _wins_in(team, c["seasons"])
            for yr, w in played.items():
                v = int(round(w * (0.5 if lvl == 1 else 0.25) * min(1.2, sev + 0.2)))
                if v >= 1:
                    ruling["vacated"][str(yr)] = v
            if ruling["vacated"]:
                lines.append("wins vacated: " + ", ".join(f"{v} in {yr}" for yr, v in ruling["vacated"].items()))
    return ruling


def _wins_in(team, seasons):
    """Wins in the seasons a violation touched: the archived records, plus this season so far."""
    out = {}
    for rec in team.historical_records:
        if rec[0] in seasons and rec[1] > 0:
            out[rec[0]] = rec[1]
    return out


def _budget(team):
    try:
        import finance
        return finance.budget(team)
    except Exception:
        return 40_000_000


def _money(x):
    try:
        import finance
        return finance.money(x)
    except Exception:
        return f"${x:,.0f}"


def _rule(league, team, c, rng):
    if c["contest"] == "pending":
        c["contest"] = "won" if rng.random() < 0.36 + 0.06 * clamp(c["coop"], -2, 2) - (0.1 if c["cover"] else 0) else "lost"
    ruling = build_ruling(league, team, c, rng)
    c["ruling"] = ruling
    c["status"] = "ruled"
    c["stage_age"] = 0
    apply_ruling(league, team, c, ruling)
    lvl = c["level"]
    head = (f"CAB: {team.school} penalized for {ruling['why']} ({LEVEL_WORD[lvl]}): "
            + "; ".join(ruling["lines"][:4]) + ".")
    if lvl == 3 and not (c["public"] or c["user"]):
        pass
    else:
        news(league, "ruling", head, team.school, lvl)
    st(team)["history"].append((league.year, f"{LEVEL_WORD[lvl]} ruling: {ruling['why']}. " + "; ".join(ruling["lines"][:3])))
    import compliance_events as ev
    ev.stage_changed(league, team, c)
    if lvl == 3 or not _appealable(league, team, c):
        _finish(league, team, c)
    else:
        appeal_odds = 0.45 if lvl == 1 else 0.2
        if mine(league) is not team and rng.random() < appeal_odds:
            c["appeal"] = True
            c["status"] = "appeal"
            c["stage_age"] = 0
            news(league, "appeal", f"{team.school} will appeal the CAB's ruling.", team.school, lvl)


def _appealable(league, team, c):
    return c["level"] <= 2 and not c.get("appeal_done")


def _finish(league, team, c):
    c["closed"] = True
    c["outcome"] = "; ".join((c.get("ruling") or {}).get("lines", [])[:3]) or "penalties served"


def _decide_appeal(league, team, c, rng):
    c["appeal_done"] = True
    win = rng.random() < 0.32
    ruling = c["ruling"]
    if win:
        soften_ruling(league, team, c, 0.72)
        news(league, "appeal", f"{team.school}'s appeal succeeds in part: the CAB reduces the penalties.", team.school, c["level"])
        c["outcome"] = "appeal upheld in part"
    else:
        news(league, "appeal", f"The CAB denies {team.school}'s appeal. The penalties stand.", team.school, c["level"])
        c["outcome"] = "appeal denied"
        rep_nudge(team, -1.5)
    c["status"] = "closed"
    c["closed"] = True
    rebuild_sanctions(league, team)


def soften_ruling(league, team, c, factor):
    ruling = c["ruling"]
    if not ruling:
        return
    pen = next((p for p in st(team)["penalties"] if p.get("case") == c["id"]), None)
    if pen is None:
        return
    if pen["bans"]:
        pen["bans"] = pen["bans"][:-1]
    pen["class_cut"] = {k: int(v * factor) for k, v in pen["class_cut"].items()}
    pen["recruit_mult"] = round(1 - (1 - pen["recruit_mult"]) * factor, 2)
    pen["nil_mult"] = round(1 - (1 - pen["nil_mult"]) * factor, 2)
    pen["until"] = max(pen["until"] - 1, league.year)
    rebuild_sanctions(league, team)


def apply_ruling(league, team, c, ruling):
    s = _tables_ok(st(team))
    y = league.year
    until = max([y + ruling["probation"], ruling["recruit_until"], ruling["nil_until"]] + list(ruling["bans"])
                + [int(k) for k in ruling["class_cut"]] + [y])
    s["penalties"].append({"case": c["id"], "why": ruling["why"], "level": ruling["level"], "year": y,
                           "until": until, "probation_until": y + ruling["probation"] if ruling["probation"] else None,
                           "bans": list(ruling["bans"]), "class_cut": dict(ruling["class_cut"]),
                           "recruit_mult": ruling["recruit_mult"], "recruit_until": ruling["recruit_until"],
                           "nil_mult": ruling["nil_mult"], "nil_until": ruling["nil_until"],
                           "lines": list(ruling["lines"])})
    if ruling["fine"]:
        team.__dict__.setdefault("fac_spend", []).append((y + 1, int(ruling["fine"]), f"CAB fine: {ruling['why']}"))
    if ruling["vacated"]:
        s["vacated"].append({"case": c["id"], "years": dict(ruling["vacated"]), "done": False})
    for p, n in ruling["player_holds"]:
        p.__dict__["hold_games"] = max(p.__dict__.get("hold_games", 0), n)
        p.events[y].append(f"Held out {n} game{'s' if n != 1 else ''} after the CAB ruling")
    if ruling["hc_susp"] and mine(league) is team and getattr(league, "mode", None) == "career":
        s["hc_susp"] = max(s.get("hc_susp", 0), ruling["hc_susp"])
    if ruling["seat"]:
        seat_hit(league, team, ruling["seat"], f"CAB sanctions ({LEVEL_WORD[ruling['level']]})")
    b = team.__dict__.get("brand")
    if b is not None and ruling["brand"]:
        team.brand = float(clamp(b + ruling["brand"], 10.0, 99.0))
    rep_nudge(team, -(1 + (4 - ruling["level"]) * 2.5))
    if mine(league) is team:
        _ad_react(league, team, -{1: 12, 2: 6, 3: 1}[ruling["level"]], "CAB penalties")
    rebuild_sanctions(league, team)


def rebuild_sanctions(league, team):
    """Fold every active penalty into team.sanctions, the record the rest of the game reads."""
    s = _tables_ok(st(team))
    y = league.year
    active_p = [p for p in s["penalties"] if p["until"] >= y and (p["level"] <= 2 or p["bans"])]
    old = getattr(team, "sanctions", None)
    if not active_p:
        if old and old.get("cases") is not None:
            team.sanctions = None
        elif old and old.get("until", 0) < y:
            team.sanctions = None
        return
    bans = sorted({b for p in active_p for b in p["bans"] if b >= y})
    worst = min(active_p, key=lambda p: p["level"])
    rm = 1.0
    for p in active_p:
        if p["recruit_until"] >= y:
            rm *= p["recruit_mult"]
    probs = [p["probation_until"] for p in active_p if p.get("probation_until")]
    team.sanctions = {"year": min(p["year"] for p in active_p), "until": max(p["until"] for p in active_p),
                      "ban": bans[0] if bans else None, "bans": bans, "why": worst["why"],
                      "recruit_mult": round(max(0.5, rm), 2), "level": worst["level"],
                      "probation_until": max(probs) if probs else None,
                      "cases": [p["case"] for p in active_p]}


def active_probation(league, team):
    s = getattr(team, "sanctions", None)
    return bool(s) and (s.get("probation_until") or 0) >= league.year


def class_cut(team, league):
    s = team.__dict__.get("comp")
    if not s:
        return 0
    y = str(league.year)
    return sum(p["class_cut"].get(y, 0) for p in s["penalties"])


def class_cap(team, league):
    """Signing-class size: 25, less any scholarships the CAB took."""
    from recruiting_data import CLASS_SIZE
    return max(8, CLASS_SIZE - class_cut(team, league))


def nil_mult(league, team):
    s = team.__dict__.get("comp")
    if not s:
        return 1.0
    m = 1.0
    for p in s["penalties"]:
        if p["nil_until"] >= league.year and p["nil_mult"] < 1.0:
            m *= p["nil_mult"]
    return m


# ═══ Weekly / seasonal hooks ════════════════════════════════════════════════

def tick(league, steps=1, rng=None):
    """One week (or one stretch of offseason): new trouble, discoveries, the pipeline."""
    rng = rng or _rng(league, "tick")
    for team in league.teams:
        _tables_ok(st(team))
        for _ in range(steps):
            _spawn(league, team, rng)
        for c in hidden_cases(league, team):
            c["age"] += steps
            if league.year - c["year"] >= 4 and not c["user"]:
                c["closed"], c["status"], c["outcome"] = True, "closed", "never came out"
                continue
            sr = (office_eff(team) / 100) ** 2 * 0.09 * steps
            if not c["cover"] and not c["user"] and rng.random() < sr:
                discover(league, c, "self", rng)          # a strong office finds its own problems first
                continue
            if rng.random() < min(0.6, _discover_p(league, team, c) * steps):
                how = rng.choices(("report", "whistle", "tip"), weights=(45, 35, 20))[0]
                discover(league, c, how, rng)
    for c in list(root(league)["cases"]):
        if not c["closed"] and c["status"] != "hidden":
            advance(league, c, rng, steps)


# ═══ Academics ══════════════════════════════════════════════════════════════

GOOD_HABITS = {"film_junkie", "grinder", "coachable", "gym_rat", "quiet_pro", "humble", "captain"}
BAD_HABITS = {"coaster", "diva", "hothead", "headcase", "spotlight", "mercenary", "showman"}


def gpa(p):
    """A player's GPA. Made from where he plays, how sharp he is, and who he is; then it drifts."""
    g = p.__dict__.get("gpa")
    if g is None:
        t = getattr(p, "team", None)
        acad = t.ratings.get("academics", 50) if t is not None and not getattr(t, "fcs", False) else 50
        base = 2.55 + (acad - 50) / 100 * 0.55 + (p.fundamentals.get("iq", 55) - 55) / 100 * 0.9
        if getattr(p, "walk_on", False):
            base += 0.12
        rng = random.Random(f"gpa:{p.first_name}:{p.last_name}:{p.number}:{getattr(t, 'school', '')}")
        g = round(clamp(rng.gauss(base, 0.32), 1.2, 4.0), 2)
        p.__dict__["gpa"] = g
        p.__dict__["gpa_base"] = g
    return g


def gpa_word(g):
    return ("Dean's list" if g >= 3.4 else "solid" if g >= 2.8 else "borderline" if g >= 2.3
            else "at risk" if g >= GPA_LINE else "failing")


def gpa_color(g):
    from ui import C
    return C.BGREEN if g >= 3.0 else C.BWHITE if g >= 2.5 else C.BYELLOW if g >= GPA_LINE else C.BRED


def _hold(league, p, games, why, week=None):
    p.inj_games = max(getattr(p, "inj_games", 0), games)
    p.inj_desc = why
    p.inj_week = league.week if week is None else week
    p.suspended = True
    p.events[league.year].append(f"Out {games if games < 99 else 'for the year'}"
                                 f"{' game' + ('s' if games != 1 else '') if games < 99 else ''} ({why})")


def watch_list(team, line=2.35):
    return sorted((p for p in team.roster if gpa(p) < line and p.year < 4), key=gpa)


def academic_term(league, final=False, rng=None):
    """Midterms (week 7) and finals (the offseason). Grades move; the weak lose eligibility."""
    rng = rng or _rng(league, "term")
    for team in league.teams:
        s = _tables_ok(st(team))
        sd = SUPPORT_TIER[s["support"]][0]
        acad = team.ratings.get("academics", 50)
        for p in team.roster:
            g = gpa(p)
            base = p.__dict__.get("gpa_base", g)
            tr = set(getattr(p, "traits", []) or [])
            d = (base - g) * 0.30 + rng.gauss(0, 0.17) + sd + (acad - 60) / 900
            d += 0.05 * len(tr & GOOD_HABITS) - 0.05 * len(tr & BAD_HABITS)
            if p.__dict__.pop("tutored", None) == league.year:
                d += 0.20
            p.__dict__["gpa"] = round(clamp(g + d, 1.0, 4.0), 2)
        for p in team.roster:
            g = gpa(p)
            if p.year >= 3 and final:
                continue
            if not final and g < 1.95 and rng.random() < 0.55 and getattr(p, "inj_games", 0) < 99:
                _hold(league, p, 99, "academically ineligible")
                if team.roster and (p.overall >= 74 or mine(league) is team):
                    news(league, "academic", f"{team.school}'s {p.position} {p.name} is academically ineligible for the "
                                             f"rest of the season.", team.school, 3)
                s["incidents"] += 1
            elif final and g < GPA_LINE:
                games = int(clamp(3 + (GPA_LINE - g) * 12, 3, 12))
                p.__dict__["acad_hold"] = games


def compute_apr(league, team, rng):
    s = _tables_ok(st(team))
    acad = team.ratings.get("academics", 50)
    inel = sum(1 for p in team.roster if p.year < 3 and gpa(p) < GPA_LINE)
    apr = 943 + (acad - 50) * 0.55 + SUPPORT_TIER[s["support"]][0] * 90
    apr -= inel * 2.6 + min(12, s.get("incidents", 0) * 1.4)
    apr += rng.gauss(0, 9)
    return int(clamp(round(apr), 880, 1000))


def apr_of(team):
    s = st(team)
    if not s["apr"]:
        return None
    return s["apr"][max(s["apr"])]


def _apr_consequences(league, team, apr, rng):
    s = _tables_ok(st(team))
    s["apr"][league.year] = apr
    root(league)["aprs"].setdefault(league.year, {})[team.school] = apr
    if apr >= APR_LINE:
        s["apr_low"] = 0
        return
    s["apr_low"] = s.get("apr_low", 0) + 1
    rep_nudge(team, -3.0)
    seat_hit(league, team, 2.0, "the team's APR fell below the line")
    if s["apr_low"] >= 2 or apr < 905:
        c = new_case(league, team, "apr", 2, rng, status="ruled", text="the team's Academic Progress Rate stayed below 930",
                     players=[], evidence=100)
        c["found"] = (league.year, league.week)
        ruling = {"year": league.year, "sev": 0.6, "level": 2, "case": c["id"], "kind": "apr",
                  "why": KINDS["apr"]["why"], "fine": 0, "probation": 0, "bans": [league.year + 1], "class_cut": {},
                  "recruit_mult": 0.94, "recruit_until": league.year + 1, "nil_mult": 1.0, "nil_until": league.year,
                  "vacated": {}, "player_holds": [], "hc_susp": 0, "seat": 6.0, "brand": -2.0,
                  "lines": ["a postseason ban in %d for academic performance" % (league.year + 1),
                            "reduced practice time and recruiting contact"]}
        c["ruling"] = ruling
        apply_ruling(league, team, c, ruling)
        _finish(league, team, c)
        c["public"] = True
        news(league, "ruling", f"CAB: {team.school} is barred from the {league.year + 1} postseason after a second straight "
                               f"APR below {APR_LINE} ({apr}).", team.school, 2)
    else:
        news(league, "apr", f"{team.school}'s APR falls to {apr}, below the {APR_LINE} line. A second year and the postseason is gone.",
             team.school, 3)
    st(team)["history"].append((league.year, f"APR {apr} (below {APR_LINE})."))


# ═══ Off the field ══════════════════════════════════════════════════════════

INCIDENTS = {
    "arrest":  {"w": 26, "games": (1, 3), "rep": -3.0, "line": "{p} is arrested on a misdemeanor charge"},
    "dui":     {"w": 12, "games": (2, 4), "rep": -4.0, "line": "{p} is cited for driving under the influence"},
    "drugs":   {"w": 16, "games": (2, 4), "rep": -2.0, "line": "{p} fails a drug test"},
    "conduct": {"w": 20, "games": (2, 6), "rep": -3.0, "line": "{p} is suspended by the university for a conduct-code violation"},
    "social":  {"w": 18, "games": (0, 1), "rep": -2.0, "line": "an old post from {p} resurfaces and goes viral"},
    "wager":   {"w": 8,  "games": (3, 6), "rep": -2.0, "line": "{p} is found to have bet on college games"},
}
INCIDENT_KEYS = tuple(INCIDENTS)
INC_PER_WEEK = 0.011


def _trouble(team):
    import personalities as pe
    return sum(1 for p in team.roster if any(t in pe.TROUBLE_TRAITS for t in getattr(p, "traits", [])))


def _incidents(league, rng):
    import personalities as pe
    me = mine(league)
    for team in league.teams:
        s = _tables_ok(st(team))
        p_ev = INC_PER_WEEK * (1 + 0.16 * min(6, _trouble(team))) * (1.35 - s["rep"] / 100 * 0.6)
        if team is me:
            p_ev *= 2.0
        if rng.random() > p_ev:
            continue
        pool = [p for p in team.roster if getattr(p, "inj_games", 0) <= 0]
        if not pool:
            continue
        weights = [1 + sum(pe.TROUBLE_TRAITS.get(t, 0) for t in getattr(p, "traits", [])) * 1.6
                   + (0.5 if p.overall >= 70 else 0) for p in pool]
        p = rng.choices(pool, weights=weights)[0]
        kind = rng.choices(INCIDENT_KEYS, weights=[INCIDENTS[k]["w"] for k in INCIDENT_KEYS])[0]
        if team is me and getattr(league, "mode", None) == "career":
            import compliance_events as ev
            ev.incident_message(league, team, p, kind, rng)
        else:
            _resolve_ai_incident(league, team, p, kind, rng)


def incident_line(p, kind):
    return INCIDENTS[kind]["line"].format(p=f"{p.position} {p.name}")


def _resolve_ai_incident(league, team, p, kind, rng):
    inc = INCIDENTS[kind]
    lo, hi = inc["games"]
    n = rng.randint(lo, hi)
    style = ad_style(team)
    starter = p in {q for g in team.starters().values() for q in g}
    if style in ("win_now", "booster") and starter and n > 0:
        n = max(0, n - 1)
        rep_nudge(team, -1.0)
    repeat = p.__dict__.get("incidents", 0)
    p.__dict__["incidents"] = repeat + 1
    dismissed = (kind == "wager" and rng.random() < 0.12) or (repeat >= 1 and rng.random() < 0.45) or \
                (kind == "dui" and repeat >= 1)
    rep_nudge(team, inc["rep"] * (1.4 if starter else 1.0))
    _tables_ok(st(team))["incidents"] += 1
    public = (starter and p.overall >= 66) or (starter and team.prestige >= 62)
    if dismissed and p in team.roster:
        team.roster.remove(p)
        p.team = None
        p.nil = 0
        if public:
            news(league, "incident", f"{team.school} dismisses {p.position} {p.name}: {incident_line(p, kind)}.", team.school, 3)
    else:
        if n > 0:
            _hold(league, p, n, {"arrest": "arrested", "dui": "suspended (DUI)", "drugs": "suspended (failed test)",
                                 "conduct": "suspended (conduct code)", "social": "suspended (team rules)",
                                 "wager": "suspended (wagering)"}[kind])
        if public:
            tail = f" and is suspended {n} game{'s' if n != 1 else ''}" if n else ", and the team says it's handled"
            news(league, "incident", f"{team.school}: {incident_line(p, kind)}{tail}.", team.school, 3)


# ═══ Your decisions (the ops behind every inbox choice) ═════════════════════

def _pay(team, league, amount, what):
    if amount:
        team.__dict__.setdefault("fac_spend", []).append((league.year + 1, int(amount), what))


def apply_fx(league, team, cp, ref=None, who=None):
    """Apply the compliance part of a reply. cp is one op-dict or a list of them; returns result lines."""
    out = []
    for op in (cp if isinstance(cp, list) else [cp]):
        out.extend(_op(league, team, op, ref, who) or [])
    return out


def _op(league, team, op, ref, who):
    rng = _rng(league, f"op:{op.get('op')}:{op.get('case')}")
    kind = op.get("op")
    c = case_by_id(league, op["case"]) if op.get("case") is not None else None
    s = _tables_ok(st(team))
    if kind == "tempt":
        lvl = op.get("level", 2)
        text = op.get("text")
        case = new_case(league, team, op["kind"], lvl, rng, user=True, cover=False,
                        evidence=op.get("evidence", 80), text=text, players=[who] if who is not None else None)
        s["heat"] = s.get("heat", 0.0) + op.get("heat", 0.05)
        return []
    if kind == "rep":
        rep_nudge(team, op["d"])
        return []
    if kind == "heat":
        s["heat"] = max(0.0, s.get("heat", 0.0) + op["d"])
        return []
    if kind == "tutor" and who is not None:
        who.__dict__["gpa"] = round(clamp(gpa(who) + op.get("d", 0.25), 1.0, 4.0), 2)
        who.__dict__["tutored"] = league.year
        return [f"{who.first_name}'s grades start to come up."]
    if kind == "dismiss" and who is not None:
        if who in team.roster:
            team.roster.remove(who)
            who.team = None
            who.nil = 0
            who.events[league.year].append("Dismissed from the program")
            import personalities as pe
            pe._say(league, f"{team.school} dismisses {who.position} {who.name} from the program.")
            return [f"{who.name} is off the team. His scholarship and NIL are gone with him."]
        return []
    if kind == "audit":
        return internal_audit(league, team)[1]
    if c is None:
        return []
    if kind == "report":
        if c["status"] == "hidden":
            discover(league, c, "self", rng)
            c["coop"] -= 0 if not c["user"] else 1        # coming clean late earns a little less credit
            c["cover"] = False
            return ["You go to the CAB before anyone comes to you. Cooperation counts."]
        return []
    if kind == "bury":
        c["cover"] = True
        c["coop"] -= 1
        return []
    if kind == "probe":
        if rng.random() < 0.5:
            return _op(league, team, {"op": "report", "case": c["id"]}, ref, who) + \
                ["The review confirms it. You report it with a full write-up: the CAB notes the timing."]
        c["cover"] = True
        c["coop"] -= 1
        return ["The review drags. By the time you know enough, it looks like you sat on it."]
    if kind == "coop":
        c["coop"] += op.get("d", 1)
        if op.get("press"):
            c["press"] = op["press"]
        if op.get("rep"):
            rep_nudge(team, op["rep"])
        return []
    if kind == "counsel":
        c["counsel"] = True
        c["coop"] += 1
        _pay(team, league, op.get("cost", _budget(team) * 0.006), f"outside counsel: CAB case {c['id']}")
        return ["Outside counsel is retained. It isn't cheap."]
    if kind == "contest":
        c["contest"] = "pending"
        return []
    if kind == "accept":
        c["coop"] += 1
        c["contest"] = None
        return []
    if kind == "self_impose":
        c["self_imposed"] = True
        c["coop"] += 1
        _pay(team, league, _budget(team) * 0.008, f"self-imposed penalties: case {c['id']}")
        rep_nudge(team, 1.0)
        return ["You announce penalties before the CAB can. The committee will remember that."]
    if kind == "appeal":
        if c["status"] == "ruled" and not c.get("appeal_done"):
            c["appeal"] = True
            c["status"] = "appeal"
            c["closed"] = False
            c["stage_age"] = 0
            c["_dur"] = {}
            news(league, "appeal", f"{team.school} will appeal the CAB's ruling.", team.school, c["level"])
        return []
    return []


def internal_audit(league, team):
    """Pay for an outside review of the program. Returns (found cases, result lines)."""
    s = _tables_ok(st(team))
    if s.get("audit_year") == league.year:
        return [], ["You've already had an audit this year."]
    s["audit_year"] = league.year
    _pay(team, league, _budget(team) * 0.0025, "internal compliance audit")
    rng = _rng(league, "audit")
    found = []
    for c in hidden_cases(league, team):
        if c["cover"] or c["user"]:
            continue                                       # what you chose to hide, an audit can't find
        if rng.random() < 0.55 + office_eff(team) / 250:
            discover(league, c, "audit", rng)
            found.append(c)
    if found:
        lines = [f"The audit turns up {len(found)} problem{'s' if len(found) != 1 else ''}. You're the one who found them, and "
                 f"you're reporting them: that counts."]
    else:
        lines = ["The audit comes back clean. As far as anyone can tell."]
        rep_nudge(team, 0.5)
    return found, lines


# ═══ The calendar's hooks ═══════════════════════════════════════════════════

def weekly(league, games):
    """After every week's games."""
    if not active(league) or league.week < 1:
        return
    rng = _rng(league, "weekly")
    tick(league, 1, rng)
    _incidents(league, rng)
    if league.week == 5:
        import compliance_events as ev
        ev.watch_message(league)
    if league.week == 7:
        academic_term(league, final=False, rng=rng)
    for team in league.teams:
        s = _tables_ok(st(team))
        s["rep"] += (s.get("rep_base", 66.0) - s["rep"]) * 0.012 if "rep_base" in s else 0.0
    _susp_boost(league)


def _susp_boost(league):
    team = mine(league)
    if team is None or getattr(league, "mode", None) != "career":
        return
    s = _tables_ok(st(team))
    if s.get("hc_susp", 0) > 0 and league.week <= 12:
        import effects as fx
        fx.boost(league, team, "next", lift=-0.5)
        s["hc_susp"] -= 1


def start_season(league):
    """Week 1: players held out by the CAB or the registrar sit their games."""
    if not active(league):
        return
    for team in league.teams:
        s = _tables_ok(st(team))
        s["incidents"] = 0
        s.setdefault("rep_base", s["rep"])
        for p in team.roster:
            n = max(p.__dict__.pop("hold_games", 0), p.__dict__.pop("acad_hold", 0))
            if n:
                _hold(league, p, n, "academically ineligible" if n and p.__dict__.get("gpa", 3) < GPA_LINE
                      else "held out by the CAB", week=0)
        if team is mine(league) and s.get("hc_susp"):
            pass


def offseason_pre(league, rng):
    """Winter, before the coaching carousel: finals, APR, and the stretch of the calendar where cases move."""
    if not active(league):
        return
    for team in league.teams:
        s = _tables_ok(st(team))
        s.setdefault("rep_base", s["rep"])
    academic_term(league, final=True, rng=rng)
    for team in league.teams:
        _apr_consequences(league, team, compute_apr(league, team, rng), rng)
    tick(league, 7, _rng(league, "offseason"))
    tick(league, 3, _rng(league, "offseason2"))              # a second look: a long winter moves a case a stage or two
    for team in league.teams:
        s = st(team)
        rebuild_sanctions(league, team)
        s["rep"] = float(clamp(s["rep"] + 1.2, 5, 98)) if not [c for c in public_cases(league, team)] else s["rep"]
        _charge_tiers(league, team)
    me = mine(league)
    if me is not None and getattr(league, "mode", None) == "career":
        s = st(me)
        if s.get("hc_susp", 0) > 0:
            import effects as fx
            fx.boost(league, me, "next", lift=-0.5)
            s["hc_susp"] -= 1


def _charge_tiers(league, team):
    if mine(league) is not team:
        return
    s = st(team)
    b = _budget(team)
    for label, tier, table in (("compliance office", s["tier"], OFFICE_TIER), ("academic support", s["support"], SUPPORT_TIER)):
        pct = table[tier][1]
        if pct:
            team.__dict__.setdefault("fac_spend", []).append(
                (league.year + 1, int(b * pct), f"{label}: {table[tier][2].lower()}"))


def offseason_post(league):
    """After the season is in the record books: vacated wins come off the books."""
    if not active(league):
        return
    for team in league.teams:
        s = st(team)
        for v in s.get("vacated", []):
            if v["done"]:
                continue
            done = True
            for yr, n in v["years"].items():
                yr = int(yr)
                for i, rec in enumerate(team.historical_records):
                    if rec[0] == yr:
                        rec = list(rec)
                        rec[1] = max(0, rec[1] - n)
                        ach = list(rec[5]) + [f"{n} wins vacated"]
                        rec[5] = ach
                        team.historical_records[i] = tuple(rec)
                        for ch in league.champions:
                            if ch.season == yr and ch.champion == team.school and "vacated" not in (ch.note or ""):
                                ch.note = ((ch.note or "") + " (title vacated)").strip()
                        break
                else:
                    done = False
            v["done"] = done
        rebuild_sanctions(league, team)


def migrate(league):
    """Older saves: nothing to convert. State appears the first time it's read."""
    root(league)
    for t in league.teams:
        s = getattr(t, "sanctions", None)
        if s and s.get("cases") is None and not t.__dict__.get("comp", {}).get("history"):
            _tables_ok(st(t))["history"].append((s.get("year", league.year), f"CAB sanctions ({s.get('why', 'violations')})."))
