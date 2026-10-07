"""
subprof.py — Sub-position proficiencies: what a player is actually good at.

A quarterback's proficiency (1.02, say) says how well he plays quarterback.
Sub-proficiencies say *how*: he might be 1.06 on short throws, 1.02 in the
intermediate game, 0.90 throwing deep, and 1.10 as a runner. Every
sub-proficiency is used by the game engine on the plays it names — a deep
ball uses his deep number, a scramble uses his dual-threat number, a corner
covering a go route uses his deep-coverage number.

  QB   short accuracy · medium accuracy · deep ball · under pressure · dual threat
  RB   inside running · outside running · receiving · pass protection · ball security
  WR   short routes · deep routes · hands · after the catch
  TE   run blocking · route running · hands · after the catch
  OL   run blocking · pass protection · pulling and space
  DL   pass rush · run defense · pursuit
  LB   run fits · blitzing · coverage · tackling
  CB   short coverage · deep coverage · ball skills · tackling
  S    deep help · short/man coverage · run support · ball skills
  K    accuracy · range           P    distance · placement

STORED AS OFFSETS from his position proficiency (+0.04 = 4% better than his
proficiency on those plays), so they rise as he develops. Shaped by who he is:
a strong-armed QB throws a better deep ball, a fast back is better outside, a
quick corner is better in short coverage. Every player in the world has them,
generated the first time they're needed (old saves included).

IN THE GAME ENGINE a play sets its moment — inside run, outside run, pass,
after the catch, scramble, kick — and every player's skills on that play are
multiplied by the matching sub-proficiencies (see CTX below). Throw depth,
route depth and kick distance are applied right where they're decided.

WORDS  (what Coach Career shows)
  horrible  < 0.80    bad  0.80-0.90    below average  0.90-0.97
  average  0.97-1.03    good  1.03-1.08    great  1.08-1.13    elite  1.13+
"""
import random

SUBS = {
    "QB": [("short", "Short accuracy"), ("medium", "Medium accuracy"), ("deep", "Deep ball"),
           ("pressure", "Under pressure"), ("dual", "Dual threat")],
    "RB": [("inside", "Inside running"), ("outside", "Outside running"), ("receiving", "Receiving"),
           ("pass_pro", "Pass protection"), ("security", "Ball security")],
    "WR": [("short_routes", "Short routes"), ("deep_routes", "Deep routes"), ("hands", "Hands"),
           ("yac", "After the catch")],
    "TE": [("run_block", "Run blocking"), ("routes", "Route running"), ("hands", "Hands"), ("yac", "After the catch")],
    "OL": [("run_block", "Run blocking"), ("pass_pro", "Pass protection"), ("space", "Pulling and space")],
    "DL": [("pass_rush", "Pass rush"), ("run_def", "Run defense"), ("pursuit", "Pursuit")],
    "LB": [("run_fits", "Run fits"), ("blitz", "Blitzing"), ("coverage", "Coverage"), ("tackling", "Tackling")],
    "CB": [("short_cover", "Short coverage"), ("deep_cover", "Deep coverage"), ("ball_skills", "Ball skills"),
           ("tackling", "Tackling")],
    "S":  [("deep_help", "Deep help"), ("man_cover", "Short/man coverage"), ("run_support", "Run support"),
           ("ball_skills", "Ball skills")],
    "K":  [("accuracy", "Accuracy"), ("range", "Range")],
    "P":  [("distance", "Distance"), ("placement", "Placement")],
}
LABEL = {pos: dict(v) for pos, v in SUBS.items()}

# Which fundamentals tilt each sub (per point above/below 60).
TILT = {
    ("QB", "short"): {"quickness": 1, "iq": 1}, ("QB", "medium"): {"iq": 1.5},
    ("QB", "deep"): {"strength": 2.5, "iq": -0.5}, ("QB", "pressure"): {"iq": 1.5, "quickness": 1},
    ("QB", "dual"): {"speed": 3, "quickness": 1, "iq": -0.5},
    ("RB", "inside"): {"strength": 2, "iq": 0.5}, ("RB", "outside"): {"speed": 2.5, "strength": -0.5},
    ("RB", "receiving"): {"playmaker": 1.5, "quickness": 1}, ("RB", "pass_pro"): {"strength": 1.5, "iq": 1.5},
    ("RB", "security"): {"strength": 1, "iq": 1},
    ("WR", "short_routes"): {"quickness": 2, "iq": 0.5}, ("WR", "deep_routes"): {"speed": 2.5},
    ("WR", "hands"): {"playmaker": 2}, ("WR", "yac"): {"quickness": 1.5, "strength": 1},
    ("TE", "run_block"): {"strength": 2.5, "speed": -0.5}, ("TE", "routes"): {"quickness": 1.5, "speed": 1},
    ("TE", "hands"): {"playmaker": 2}, ("TE", "yac"): {"strength": 1, "speed": 1},
    ("OL", "run_block"): {"strength": 2.5}, ("OL", "pass_pro"): {"quickness": 1.5, "iq": 1.5},
    ("OL", "space"): {"speed": 2.5, "strength": -0.5},
    ("DL", "pass_rush"): {"quickness": 2, "speed": 1}, ("DL", "run_def"): {"strength": 2.5},
    ("DL", "pursuit"): {"speed": 2.5},
    ("LB", "run_fits"): {"iq": 1.5, "strength": 1}, ("LB", "blitz"): {"quickness": 2},
    ("LB", "coverage"): {"speed": 2, "iq": 0.5}, ("LB", "tackling"): {"strength": 1.5},
    ("CB", "short_cover"): {"quickness": 2, "iq": 0.5}, ("CB", "deep_cover"): {"speed": 2.5},
    ("CB", "ball_skills"): {"playmaker": 2}, ("CB", "tackling"): {"strength": 2},
    ("S", "deep_help"): {"speed": 1.5, "iq": 1.5}, ("S", "man_cover"): {"quickness": 2},
    ("S", "run_support"): {"strength": 2}, ("S", "ball_skills"): {"playmaker": 2},
    ("K", "accuracy"): {"iq": 2}, ("K", "range"): {"strength": 2.5},
    ("P", "distance"): {"strength": 2.5}, ("P", "placement"): {"iq": 2},
}
LO, HI = -0.24, 0.20

# ═══ Game-engine contexts ═══════════════════════════════════════════════════
# ctx -> position -> [(sub, composites it multiplies)]
_RUN_D = {"DL": [("run_def", ("run_stop",)), ("pursuit", ("tackle",))],
          "LB": [("run_fits", ("fit",)), ("tackling", ("tackle",))],
          "CB": [("tackling", ("tackle",))],
          "S":  [("run_support", ("fit", "tackle"))]}
CTX = {
    "run_in": {"QB": [("dual", ("elusive", "power", "speed", "vision"))],
               "RB": [("inside", ("elusive", "power", "vision")), ("security", ("security",))],
               "TE": [("run_block", ("block",))], "OL": [("run_block", ("block",))], **_RUN_D},
    "run_out": {"QB": [("dual", ("elusive", "power", "speed", "vision"))],
                "RB": [("outside", ("speed", "elusive")), ("security", ("security",))],
                "WR": [("yac", ("speed", "elusive"))],
                "TE": [("run_block", ("block",))], "OL": [("space", ("block",))],
                "DL": [("run_def", ("run_stop",)), ("pursuit", ("tackle", "speed"))],
                "LB": [("run_fits", ("fit",)), ("tackling", ("tackle",))],
                "CB": [("tackling", ("tackle",))], "S": [("run_support", ("fit", "tackle"))]},
    "pass": {"QB": [("pressure", ("pocket",))],
             "RB": [("pass_pro", ("pass_block",)), ("receiving", ("route", "catch"))],
             "WR": [("hands", ("catch",))],
             "TE": [("routes", ("route",)), ("hands", ("catch",))],
             "OL": [("pass_pro", ("pass_block",))],
             "DL": [("pass_rush", ("rush",))],
             "LB": [("blitz", ("rush",)), ("coverage", ("cover",)), ("tackling", ("tackle",))],
             "CB": [("ball_skills", ("playmaker",)), ("tackling", ("tackle",))],
             "S":  [("ball_skills", ("playmaker",))]},                   # S coverage: by route depth (engine)
    "yac": {"RB": [("receiving", ("elusive",))], "WR": [("yac", ("elusive", "speed", "power"))],
            "TE": [("yac", ("elusive", "speed", "power"))],
            "LB": [("tackling", ("tackle",))], "CB": [("tackling", ("tackle",))],
            "S": [("run_support", ("tackle",))], "DL": [("pursuit", ("tackle", "speed"))]},
    "scramble": {"QB": [("dual", ("speed", "elusive", "power"))],
                 "LB": [("tackling", ("tackle",))], "S": [("run_support", ("tackle",))]},
    "screen": {"OL": [("space", ("block",))], "RB": [("receiving", ("catch", "elusive"))],
               "WR": [("yac", ("elusive", "speed"))], "TE": [("yac", ("elusive", "speed"))],
               "DL": [("pursuit", ("tackle", "speed"))], "LB": [("tackling", ("tackle",))],
               "CB": [("tackling", ("tackle",))], "S": [("run_support", ("tackle",))]},
    "kick": {"K": [("accuracy", ("kick_acc",)), ("range", ("kick_power",))],
             "P": [("distance", ("kick_power",)), ("placement", ("kick_acc",))]},
}


# ═══ The numbers ════════════════════════════════════════════════════════════

def _gen(p, pos):
    rng = random.Random(f"sub|{p.first_name}|{p.last_name}|{p.height}|{p.hs_stars}|{pos}")
    out = {}
    f = p.fundamentals
    for key, _ in SUBS[pos]:
        tilt = sum((f.get(k, 60) - 60) * w for k, w in TILT.get((pos, key), {}).items()) / 1000
        out[key] = round(max(LO, min(HI, rng.gauss(0, 0.045) + tilt)), 3)
    # Keep the average near zero: sub-proficiencies describe a shape, not a second rating.
    mean = sum(out.values()) / len(out)
    return {k: round(max(LO, min(HI, v - mean)), 3) for k, v in out.items()}


def offsets(p, pos=None):
    pos = pos or p.position
    book = p.__dict__.setdefault("subprof", {})
    if pos not in book:
        if pos not in SUBS:
            return {}
        book[pos] = _gen(p, pos)
    return book[pos]


def ratio(p, key, pos=None):
    """The multiplier the engine uses: 1 + his offset for this sub (1.0 if it doesn't apply)."""
    pos = pos or p.position
    return 1.0 + offsets(p, pos).get(key, 0.0) if pos in SUBS else 1.0


def value(p, key, pos=None):
    """The sub-proficiency itself (like 1.06): his position proficiency x (1 + offset)."""
    pos = pos or p.position
    return p.proficiency_at(pos) * ratio(p, key, pos)


def all_values(p, pos=None):
    pos = pos or p.position
    return [(key, label, value(p, key, pos)) for key, label in SUBS.get(pos, [])]


# ═══ Words ══════════════════════════════════════════════════════════════════

SCALE = ((0.80, "horrible"), (0.90, "bad"), (0.97, "below average"), (1.03, "average"), (1.08, "good"),
         (1.13, "great"), (9.9, "elite"))


def word(v):
    return next(w for cut, w in SCALE if v < cut)


def color(v):
    from ui import C
    return (C.BRED if v < 0.90 else C.BYELLOW if v < 0.97 else C.BWHITE if v < 1.03 else
            C.BGREEN if v < 1.13 else C.BMAGENTA)


def estimate(v, seed=""):
    """Scout's Eye: a range, not the number — about ±0.03 around the truth, a little off-center."""
    rng = random.Random(f"est|{seed}|{round(v, 3)}")
    mid = v + rng.uniform(-0.015, 0.015)
    return f"{mid - 0.03:.2f}–{mid + 0.03:.2f}"


# ═══ Growth ═════════════════════════════════════════════════════════════════

def develop(p, rng, scale=1.0):
    """Players shore up weaknesses over time — the smarter they are, the faster.
    Called with each development step (in season and in the offseason)."""
    pos = p.position
    if pos not in SUBS:
        return
    off = offsets(p, pos)
    iq = p.fundamentals.get("iq", 60) / 100
    for k, v in off.items():
        pull = (-v * 0.18 if v < 0 else -v * 0.04) * (0.6 + iq) * scale     # weak spots close faster
        off[k] = round(max(LO, min(HI, v + pull + rng.gauss(0, 0.008) * scale ** 0.5)), 4)
