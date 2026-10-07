"""
playbook.py — Routes, offensive plays, defensive calls, coaching schemes,
and the play-calling brain.

Every head coach has an offensive scheme (which plays he likes, how often he
runs, what personnel he uses, his tempo), a defensive scheme (which coverages
and pressures he likes), and an aggression rating (4th downs, blitz rate).

Play calling reads the whole situation: down, distance, field position,
quarter, clock, score, timeouts, and the personnel the offense sends out.
"""
import zlib
from dataclasses import dataclass

# ═══ Routes ═════════════════════════════════════════════════════════════════
# depth: yards downfield at the catch point · brk: seconds after the snap the
# route breaks (when the QB can throw it) · area: which coverage level it
# attacks · yac: yards-after-catch potential · sideline: breaks toward the boundary


@dataclass(frozen=True)
class Route:
    name: str
    depth: int
    brk: float
    area: str
    yac: float
    sideline: bool


ROUTES = {r.name: r for r in (
    Route("screen", -2, 0.7, "behind", 1.5, False),
    Route("bubble", -1, 0.5, "flat", 1.3, True),
    Route("swing", 0, 0.9, "flat", 1.2, True),
    Route("flat", 2, 1.0, "flat", 1.1, True),
    Route("drag", 3, 1.3, "short", 1.3, False),
    Route("slant", 5, 1.0, "short", 1.2, False),
    Route("quick out", 5, 1.1, "short", 0.6, True),
    Route("hitch", 6, 1.2, "short", 0.7, False),
    Route("stick", 6, 1.3, "short", 0.7, False),
    Route("sit", 8, 1.6, "short", 0.7, False),
    Route("curl", 12, 2.0, "mid", 0.6, False),
    Route("out", 12, 2.1, "mid", 0.5, True),
    Route("cross", 12, 2.3, "mid", 1.2, False),
    Route("dig", 14, 2.3, "mid", 0.9, False),
    Route("comeback", 15, 2.5, "mid", 0.4, True),
    Route("corner", 18, 2.7, "deep", 0.8, True),
    Route("post", 20, 2.8, "deep", 1.0, False),
    Route("seam", 20, 2.6, "deep", 0.9, False),
    Route("wheel", 20, 2.9, "deep", 0.9, True),
    Route("fade", 24, 3.0, "deep", 0.6, True),
    Route("go", 30, 3.1, "deep", 1.0, True),
    Route("angle", 4, 1.5, "short", 1.2, False),     # RB option route back inside
    Route("snag", 6, 1.4, "short", 0.6, False),      # slot settles in the window
    Route("whip", 5, 1.5, "short", 1.0, True),       # fake in, snap back out
    Route("pop", 10, 1.4, "mid", 0.9, False),        # quick seam off an RPO
    Route("leak", 14, 2.6, "mid", 1.1, False),       # TE slips out late after play-action
    Route("deep out", 16, 2.6, "mid", 0.4, True),
    Route("sluggo", 26, 3.3, "deep", 1.1, True),     # slant-and-go double move
)}

CROSSERS = {"drag", "cross", "slant", "whip", "angle"}
DOUBLE_MOVES = {"sluggo"}      # pick up rubs vs man coverage

# ═══ Offensive plays ═══════════════════════════════════════════════════════
# Receiver roles: X (split end, left) · Z (flanker, right) · SLOT · Y (tight
# end / 4th WR) · RB. Personnel decides who fills each role.


@dataclass(frozen=True)
class OffPlay:
    name: str
    kind: str                      # run | pass | kneel
    concept: str = ""              # run concept
    routes: tuple = ()             # ((role, route), ...)
    progression: tuple = ()        # QB's read order
    drop: str = "normal"           # quick | normal | deep
    protection: int = 5            # 5 = OL only, 6 = + RB, 7 = + RB + Y
    play_action: bool = False
    rpo: bool = False
    screen: bool = False
    tags: tuple = ()
    needs: tuple = ()              # "FB" or "SLOT_WR"
    trick: bool = False
    passer: str = "QB"             # who throws it (HB pass: "RB")

    @property
    def route_map(self):
        return dict(self.routes)

    @property
    def max_depth(self):
        return max((ROUTES[r].depth for _, r in self.routes), default=0)


def _p(name, routes, prog, drop="normal", **kw):
    return OffPlay(name, "pass", routes=tuple(routes.items()), progression=tuple(prog), drop=drop, **kw)


RUN_PLAYS = [
    OffPlay("Inside Zone", "run", "inside_zone", tags=("base", "short", "goal")),
    OffPlay("Outside Zone", "run", "outside_zone", tags=("base",)),
    OffPlay("Power", "run", "power", tags=("short", "goal")),
    OffPlay("Counter", "run", "counter", tags=("base",)),
    OffPlay("Iso", "run", "iso", tags=("short", "goal"), needs=("FB",)),
    OffPlay("Toss Sweep", "run", "toss", tags=("base",)),
    OffPlay("Draw", "run", "draw", tags=("long",)),
    OffPlay("QB Sneak", "run", "qb_sneak", tags=("inches",)),
    OffPlay("Zone Read", "run", "zone_read", tags=("base",)),
    OffPlay("QB Power", "run", "qb_power", tags=("short", "goal")),
    OffPlay("Jet Sweep", "run", "jet", tags=("base",), needs=("SLOT_WR",)),
    OffPlay("Triple Option", "run", "triple", tags=("base", "short"), needs=("FB",)),
    OffPlay("Duo", "run", "duo", tags=("base", "short", "goal")),
    OffPlay("Trap", "run", "trap", tags=("base", "short")),
    OffPlay("Pin-Pull Sweep", "run", "pin_pull", tags=("base",)),
    OffPlay("Speed Option", "run", "speed_option", tags=("base",)),
    OffPlay("Midline Option", "run", "midline", tags=("short", "base")),
    OffPlay("QB Draw", "run", "qb_draw", tags=("long", "red")),
    OffPlay("Crack Toss", "run", "crack_toss", tags=("base",), needs=("SLOT_WR",)),
    OffPlay("Reverse", "run", "reverse", tags=("trick",), trick=True, needs=("SLOT_WR",)),
]

PASS_PLAYS = [
    _p("Slants", {"X": "slant", "Z": "slant", "SLOT": "flat", "Y": "sit", "RB": "flat"},
       ("X", "SLOT", "Z", "Y", "RB"), "quick", tags=("short", "red", "quick")),
    _p("Stick", {"X": "fade", "Z": "hitch", "SLOT": "stick", "Y": "flat", "RB": "swing"},
       ("SLOT", "Y", "Z", "RB", "X"), "quick", tags=("short", "quick")),
    _p("Quick Outs", {"X": "quick out", "Z": "quick out", "SLOT": "quick out", "Y": "sit", "RB": "flat"},
       ("X", "Z", "SLOT", "Y"), "quick", tags=("hurry", "sideline", "quick")),
    _p("Mesh", {"X": "corner", "Z": "drag", "SLOT": "drag", "Y": "sit", "RB": "swing"},
       ("Z", "SLOT", "Y", "RB", "X"), tags=("base", "medium")),
    _p("Curl-Flat", {"X": "curl", "Z": "curl", "SLOT": "flat", "Y": "seam", "RB": "flat"},
       ("X", "SLOT", "Z", "Y", "RB"), tags=("base", "medium")),
    _p("Smash", {"X": "hitch", "Z": "hitch", "SLOT": "corner", "Y": "sit", "RB": "flat"},
       ("SLOT", "X", "Y", "RB"), tags=("medium", "red")),
    _p("Dagger", {"X": "dig", "Z": "go", "SLOT": "seam", "Y": "sit", "RB": "flat"},
       ("X", "SLOT", "Z", "Y"), "deep", tags=("long", "medium")),
    _p("Y-Cross", {"X": "post", "Z": "comeback", "SLOT": "drag", "Y": "cross", "RB": "flat"},
       ("Y", "X", "Z", "SLOT", "RB"), "deep", tags=("long", "medium")),
    _p("Levels", {"X": "dig", "Z": "go", "SLOT": "drag", "Y": "curl", "RB": "flat"},
       ("X", "SLOT", "Y", "RB"), tags=("medium",)),
    _p("Sail", {"X": "post", "Z": "go", "SLOT": "out", "Y": "flat", "RB": "swing"},
       ("SLOT", "Y", "Z", "RB"), tags=("sideline", "medium", "hurry")),
    _p("Four Verticals", {"X": "go", "Z": "go", "SLOT": "seam", "Y": "seam", "RB": "flat"},
       ("SLOT", "Y", "X", "Z", "RB"), "deep", tags=("long", "hurry", "shot")),
    _p("Post-Wheel", {"X": "post", "Z": "dig", "SLOT": "wheel", "Y": "sit", "RB": "flat"},
       ("X", "SLOT", "Z", "Y"), "deep", tags=("shot", "long")),
    _p("Sideline Comebacks", {"X": "comeback", "Z": "out", "SLOT": "out", "Y": "sit", "RB": "flat"},
       ("X", "Z", "SLOT", "Y"), tags=("hurry", "sideline", "long")),
    _p("PA Boot", {"X": "corner", "Z": "post", "SLOT": "flat", "Y": "cross", "RB": "flat"},
       ("Y", "RB", "X", "SLOT"), "deep", play_action=True, tags=("base", "medium")),
    _p("PA Deep Shot", {"X": "post", "Z": "go", "SLOT": "dig", "Y": "seam"},
       ("Z", "X", "SLOT", "Y"), "deep", protection=6, play_action=True, tags=("shot",)),
    _p("RB Screen", {"X": "go", "Z": "go", "SLOT": "drag", "Y": "sit", "RB": "screen"},
       ("RB",), "quick", screen=True, tags=("long", "base")),
    _p("WR Screen", {"X": "screen", "Z": "go", "SLOT": "go", "Y": "sit"},
       ("X",), "quick", screen=True, tags=("base",)),
    _p("Bubble Screen", {"X": "hitch", "Z": "hitch", "SLOT": "bubble", "Y": "sit"},
       ("SLOT", "X"), "quick", screen=True, tags=("base",)),
    _p("Glance RPO", {"X": "slant", "SLOT": "bubble"},
       ("X", "SLOT"), "quick", rpo=True, tags=("base",)),
    _p("Red Zone Fade", {"X": "fade", "Z": "slant", "SLOT": "flat", "Y": "sit", "RB": "flat"},
       ("X", "Z", "SLOT", "Y"), "quick", tags=("red", "goal")),
    _p("Drive", {"X": "dig", "Z": "go", "SLOT": "drag", "Y": "flat", "RB": "swing"},
       ("SLOT", "X", "Y", "RB"), tags=("base", "medium")),
    _p("Flood", {"X": "post", "Z": "go", "SLOT": "deep out", "Y": "flat", "RB": "swing"},
       ("SLOT", "Y", "Z", "RB"), tags=("medium", "sideline", "long")),
    _p("Snag", {"X": "fade", "Z": "snag", "SLOT": "corner", "Y": "flat", "RB": "swing"},
       ("SLOT", "Z", "Y", "RB"), "quick", tags=("short", "red")),
    _p("Spacing", {"X": "hitch", "Z": "hitch", "SLOT": "snag", "Y": "sit", "RB": "swing"},
       ("SLOT", "Y", "X", "Z", "RB"), "quick", tags=("short", "quick")),
    _p("Texas", {"X": "curl", "Z": "curl", "SLOT": "flat", "Y": "seam", "RB": "angle"},
       ("Y", "RB", "X", "SLOT"), tags=("medium", "red")),
    _p("Double Moves", {"X": "sluggo", "Z": "sluggo", "SLOT": "drag", "Y": "sit"},
       ("X", "Z", "SLOT", "Y"), "deep", protection=6, tags=("shot",)),
    _p("Shallow Cross", {"X": "dig", "Z": "post", "SLOT": "drag", "Y": "sit", "RB": "flat"},
       ("SLOT", "X", "Z", "Y", "RB"), tags=("base", "medium")),
    _p("PA Leak", {"X": "post", "Z": "comeback", "SLOT": "flat", "Y": "leak", "RB": "flat"},
       ("X", "Y", "Z", "RB"), "deep", play_action=True, tags=("base", "red")),
    _p("Pop Pass RPO", {"Y": "pop", "SLOT": "bubble"},
       ("Y", "SLOT"), "quick", rpo=True, tags=("base",)),
    _p("Whip Option", {"X": "fade", "Z": "slant", "SLOT": "whip", "Y": "whip", "RB": "flat"},
       ("SLOT", "Y", "Z", "RB"), "quick", tags=("short", "inches")),
    _p("Flea Flicker", {"X": "post", "Z": "go", "Y": "seam", "SLOT": "dig"},
       ("Z", "X", "Y", "SLOT"), "deep", protection=6, play_action=True, trick=True, tags=("trick",)),
    _p("HB Pass", {"X": "go", "Z": "post", "Y": "seam", "SLOT": "flat"},
       ("X", "Z", "Y", "SLOT"), "deep", trick=True, passer="RB", tags=("trick",)),
    _p("Hail Mary", {"X": "go", "Z": "go", "SLOT": "go", "Y": "seam"},
       ("Z", "X", "SLOT", "Y"), "deep", protection=6, tags=("hail",)),
]

SCREEN_NAMES = {"RB Screen", "WR Screen", "Bubble Screen"}
KNEEL = OffPlay("Victory Formation", "kneel")
HAIL_MARY = next(p for p in PASS_PLAYS if p.name == "Hail Mary")
ALL_PLAYS = {p.name: p for p in RUN_PLAYS + PASS_PLAYS}

# ═══ Defensive calls ═══════════════════════════════════════════════════════


@dataclass(frozen=True)
class DefCall:
    name: str
    personnel: str      # base (4-3) | nickel (4-2-5) | dime (4-1-6) | goal
    rush: int           # pass rushers
    coverage: str       # man | zone
    shell: int          # deep safeties helping over the top
    box: int            # defenders committed to the run box
    blitzers: tuple = ()
    zone: str = ""      # zone family
    tags: tuple = ()


DEF_CALLS = {c.name: c for c in (
    DefCall("Cover 3 Sky", "base", 4, "zone", 1, 7, zone="cover3"),
    DefCall("Cover 2", "nickel", 4, "zone", 2, 6, zone="cover2"),
    DefCall("Tampa 2", "base", 4, "zone", 2, 6, zone="tampa2"),
    DefCall("Cover 4 Quarters", "nickel", 4, "zone", 2, 7, zone="cover4"),
    DefCall("Cover 1 Man", "base", 4, "man", 1, 7),
    DefCall("Cover 2 Man", "nickel", 4, "man", 2, 6),
    DefCall("Cover 0 Blitz", "base", 6, "man", 0, 8, ("LB", "S")),
    DefCall("Fire Zone", "nickel", 5, "zone", 1, 7, ("LB",), zone="firezone"),
    DefCall("Nickel Blitz", "nickel", 5, "man", 1, 6, ("NB",)),
    DefCall("Run Blitz", "base", 5, "man", 1, 8, ("LB",), tags=("run",)),
    DefCall("Goal Line", "goal", 5, "man", 0, 9, ("LB",), tags=("run", "goal")),
    DefCall("Dime Quarters", "dime", 4, "zone", 2, 5, zone="cover4"),
    DefCall("Prevent", "dime", 3, "zone", 2, 4, zone="prevent"),
    DefCall("Cover 6", "nickel", 4, "zone", 2, 7, zone="cover6"),
    DefCall("Cover 3 Buzz", "base", 4, "zone", 1, 8, zone="cover3buzz"),
    DefCall("Cover 1 Robber", "nickel", 4, "man", 1, 7, tags=("robber",)),
    DefCall("Sim Pressure", "nickel", 4, "zone", 1, 7, ("LB",), zone="firezone", tags=("sim",)),
    DefCall("QB Spy", "nickel", 4, "man", 1, 6, tags=("spy",)),
    DefCall("Bracket", "nickel", 4, "man", 2, 6, tags=("bracket",)),
    DefCall("Bear Front", "base", 4, "zone", 1, 8, zone="cover3", tags=("run",)),
)}

# How much each zone family leaves open at each level (+ = softer).
ZONE_MOD = {
    "cover3":   {"behind": 0.3, "flat": 0.9, "short": 0.2, "mid": 0.4, "deep": -0.5},
    "cover2":   {"behind": 0.2, "flat": -0.6, "short": 0.4, "mid": 0.2, "deep": 0.3},
    "tampa2":   {"behind": 0.2, "flat": -0.5, "short": 0.3, "mid": -0.1, "deep": 0.0},
    "cover4":   {"behind": 0.5, "flat": 0.9, "short": 0.8, "mid": -0.3, "deep": -1.0},
    "firezone": {"behind": -0.3, "flat": 0.5, "short": 0.4, "mid": 0.3, "deep": -0.4},
    "prevent":  {"behind": 1.2, "flat": 1.4, "short": 1.4, "mid": 0.2, "deep": -1.6},
    "cover6":   {"behind": 0.3, "flat": 0.2, "short": 0.6, "mid": -0.1, "deep": -0.5},
    "cover3buzz": {"behind": 0.3, "flat": 0.5, "short": -0.2, "mid": 0.2, "deep": -0.5},
}
# Classic route-vs-coverage beaters.
ROUTE_BEATERS = {
    ("seam", "cover3"): 0.7, ("curl", "cover3"): 0.3, ("flat", "cover3"): 0.3,
    ("corner", "cover2"): 0.8, ("post", "cover2"): 0.5, ("seam", "cover2"): 0.4,
    ("seam", "tampa2"): -0.4, ("dig", "cover4"): 0.5, ("drag", "cover4"): 0.4,
    ("out", "cover3"): 0.3, ("comeback", "cover3"): 0.4, ("wheel", "cover2"): 0.4,
    ("snag", "cover3"): 0.4, ("deep out", "cover3"): 0.4, ("pop", "cover3"): 0.5,
    ("angle", "cover4"): 0.5, ("seam", "cover3buzz"): 0.6, ("flat", "cover3buzz"): 0.3,
    ("dig", "cover6"): 0.3, ("corner", "cover6"): 0.3, ("leak", "cover3"): 0.4,
}

# ═══ Schemes ═══════════════════════════════════════════════════════════════

OFFENSE_SCHEMES = {
    "Air Raid": dict(run=0.30, tempo=22, personnel={"10": .35, "11": .60, "12": .05}, plays={
        "Mesh": 5, "Four Verticals": 4, "Y-Cross": 4, "Stick": 4, "Slants": 3, "Sail": 3, "Quick Outs": 2,
        "Curl-Flat": 2, "Smash": 2, "RB Screen": 2, "Bubble Screen": 2, "Dagger": 2, "Levels": 2,
        "Inside Zone": 5, "Draw": 4, "Outside Zone": 2, "Zone Read": 1,
        "Shallow Cross": 3, "Drive": 2, "Snag": 2, "Spacing": 2, "Texas": 1, "QB Draw": 1}),
    "Spread RPO": dict(run=0.50, tempo=24, personnel={"10": .10, "11": .75, "12": .15}, plays={
        "Inside Zone": 5, "Zone Read": 5, "Glance RPO": 5, "Outside Zone": 3, "Counter": 2, "QB Power": 2,
        "Jet Sweep": 2, "Bubble Screen": 3, "Slants": 3, "Stick": 3, "Four Verticals": 2, "Dagger": 2,
        "Mesh": 2, "PA Deep Shot": 2, "RB Screen": 2, "Curl-Flat": 2, "Post-Wheel": 1,
        "Pop Pass RPO": 3, "Speed Option": 2, "QB Draw": 2, "Crack Toss": 2, "Snag": 2, "Duo": 1}),
    "Pro Style": dict(run=0.55, tempo=31, personnel={"11": .45, "12": .35, "21": .20}, plays={
        "Inside Zone": 4, "Power": 4, "Outside Zone": 4, "Iso": 3, "Counter": 2, "Toss Sweep": 2, "Draw": 2,
        "PA Boot": 4, "PA Deep Shot": 3, "Curl-Flat": 4, "Dagger": 3, "Y-Cross": 3, "Smash": 3,
        "Slants": 2, "Stick": 2, "Sail": 2, "RB Screen": 2, "Levels": 2,
        "Duo": 3, "Trap": 2, "Pin-Pull Sweep": 2, "PA Leak": 3, "Flood": 2, "Texas": 2, "Drive": 2}),
    "West Coast": dict(run=0.47, tempo=28, personnel={"11": .60, "12": .25, "21": .15}, plays={
        "Inside Zone": 4, "Outside Zone": 4, "Draw": 2, "Toss Sweep": 2, "Slants": 4, "Stick": 4,
        "Curl-Flat": 4, "Mesh": 3, "Levels": 3, "RB Screen": 3, "WR Screen": 2, "Y-Cross": 2, "PA Boot": 3,
        "Spacing": 3, "Drive": 3, "Texas": 3, "Shallow Cross": 3, "Snag": 2, "Pin-Pull Sweep": 2}),
    "Smashmouth": dict(run=0.70, tempo=34, personnel={"11": .10, "12": .40, "21": .35, "22": .15}, plays={
        "Power": 5, "Iso": 4, "Counter": 4, "Inside Zone": 4, "Toss Sweep": 3, "Outside Zone": 2,
        "PA Boot": 4, "PA Deep Shot": 3, "Curl-Flat": 2, "Y-Cross": 2, "Smash": 1,
        "Duo": 4, "Trap": 3, "Pin-Pull Sweep": 2, "PA Leak": 3, "Whip Option": 1}),
    "Triple Option": dict(run=0.86, tempo=36, personnel={"12": .10, "21": .60, "22": .30}, plays={
        "Triple Option": 12, "Midline Option": 7, "Speed Option": 3, "QB Power": 3, "Iso": 2, "Trap": 2,
        "Toss Sweep": 1, "Counter": 1, "Inside Zone": 1,
        "PA Deep Shot": 4, "PA Boot": 2, "Post-Wheel": 1}),
    "Power Spread": dict(run=0.52, tempo=24, personnel={"10": .10, "11": .60, "12": .30}, plays={
        "Power": 4, "Counter": 4, "Duo": 4, "QB Power": 3, "Inside Zone": 3, "Speed Option": 2, "Crack Toss": 2,
        "Glance RPO": 3, "Pop Pass RPO": 3, "Bubble Screen": 2, "Four Verticals": 2, "Post-Wheel": 2,
        "Double Moves": 1, "Stick": 2, "Snag": 2, "PA Deep Shot": 2, "Dagger": 2}),
    "Veer & Shoot": dict(run=0.45, tempo=18, personnel={"10": .30, "11": .70}, plays={
        "Inside Zone": 4, "Outside Zone": 3, "Zone Read": 3, "Draw": 2, "Speed Option": 2,
        "Four Verticals": 4, "Double Moves": 2, "Post-Wheel": 3, "Sideline Comebacks": 3, "Snag": 2,
        "Bubble Screen": 3, "WR Screen": 3, "Glance RPO": 3, "Flood": 2}),
}

DEFENSE_SCHEMES = {
    "4-3 Zone": {"Cover 3 Sky": 6, "Cover 2": 3, "Tampa 2": 3, "Cover 1 Man": 2, "Fire Zone": 2,
                 "Run Blitz": 1, "Cover 4 Quarters": 2, "Cover 3 Buzz": 3, "Bear Front": 1, "Cover 6": 1},
    "4-2-5 Quarters": {"Cover 4 Quarters": 6, "Cover 2": 3, "Cover 1 Man": 2, "Fire Zone": 2,
                       "Cover 2 Man": 2, "Cover 3 Sky": 2, "Nickel Blitz": 1,
                       "Cover 6": 4, "Sim Pressure": 2, "Bracket": 1, "Cover 1 Robber": 1},
    "Pressure 3-4": {"Fire Zone": 5, "Cover 0 Blitz": 3, "Cover 1 Man": 3, "Cover 3 Sky": 3,
                     "Run Blitz": 2, "Nickel Blitz": 2, "Cover 2 Man": 1, "Sim Pressure": 3, "Cover 1 Robber": 2},
    "3-3-5 Stack": {"Fire Zone": 4, "Cover 3 Sky": 4, "Cover 4 Quarters": 2, "Cover 1 Man": 2,
                    "Cover 0 Blitz": 1, "Run Blitz": 1, "Nickel Blitz": 2,
                    "Sim Pressure": 3, "Cover 3 Buzz": 2, "QB Spy": 1},
    "Multiple Man": {"Cover 1 Man": 5, "Cover 2 Man": 3, "Cover 0 Blitz": 2, "Cover 3 Sky": 2,
                     "Cover 4 Quarters": 2, "Fire Zone": 2, "Nickel Blitz": 1,
                     "Cover 1 Robber": 3, "Bracket": 2, "QB Spy": 1},
    "Tite Front": {"Cover 3 Buzz": 5, "Cover 6": 3, "Sim Pressure": 3, "Cover 1 Robber": 2, "Bear Front": 1,
                   "Fire Zone": 2, "Cover 4 Quarters": 2, "QB Spy": 1},
}

PERSONNEL_NAMES = {"10": "1 RB · 4 WR", "11": "1 RB · 1 TE · 3 WR", "12": "1 RB · 2 TE · 2 WR",
                   "21": "2 RB · 1 TE · 2 WR", "22": "2 RB · 2 TE · 1 WR"}


def play_fits_personnel(play, personnel):
    if "FB" in play.needs and personnel not in ("21", "22"):
        return False
    if "SLOT_WR" in play.needs and personnel not in ("10", "11"):
        return False
    return True


# ═══ Coach identity ═════════════════════════════════════════════════════════
# Two Air Raid coaches don't call the same game. Each coach carries a fixed,
# personal lean on every play and coverage (0.6x-1.5x), and a few become his
# signature calls (2.2x) that he goes to more than anyone in his scheme.

def coach_bias(coach, name):
    cache = coach.__dict__.setdefault("_bias", {})
    if name not in cache:
        h = zlib.crc32(f"{coach.name}|{name}".encode()) / 2 ** 32
        cache[name] = 2.2 if h > 0.93 else 0.6 + h * 0.9
    return cache[name]


def signature_plays(coach):
    """The coach's calling cards within his schemes (for display)."""
    off = [n for n in OFFENSE_SCHEMES[coach.offense_scheme]["plays"] if coach_bias(coach, n) >= 2]
    dfn = [n for n in DEFENSE_SCHEMES[coach.defense_scheme] if coach_bias(coach, n) >= 2]
    return off[:3], dfn[:2]


# ═══ In-game adaptation ═════════════════════════════════════════════════════

def successful(down, togo, yards, td=False):
    if td:
        return True
    need = {1: 0.45, 2: 0.6}.get(down, 1.0)
    return yards >= togo * need


INSIDE_RUNS = {"inside_zone", "power", "iso", "duo", "trap", "counter", "draw", "qb_sneak", "qb_power", "qb_draw",
               "midline", "triple", "zone_read"}
TAKEAWAYS = {"Interception", "Fumble", "Downs"}


def family(call):
    """Concept family, so what a coach learns about one play carries over to its cousins."""
    if call.kind == "run":
        return "run_inside" if call.concept in INSIDE_RUNS else "run_outside"
    if call.screen:
        return "screen"
    if call.play_action:
        return "play_action"
    if "quick" in call.tags:
        return "quick"
    if call.max_depth >= 18 or "shot" in call.tags:
        return "deep"
    return "intermediate"


def situation(down, togo, yardline):
    if 100 - yardline <= 20:
        return "red"
    if down == 1:
        return "1st"
    if down == 2:
        return "2nd_short" if togo <= 4 else "2nd_long"
    return "3rd_short" if togo <= 3 else "3rd_long"


class GamePlan:
    """A coach's notebook for one game: what's working, what he's seeing,
    and what he's changed. Adjustments are logged in `notes` for the booth."""

    def __init__(self, coach=None, team=None):
        # How well this staff reads a game: an average coach (70) is 0.62, an elite
        # one (90) is 1.12. It scales how hard and how early they adjust. The
        # coordinators carry part of it on their side of the ball.
        ovr = getattr(coach, "overall", 70)
        off = def_ = ovr
        if team is not None and coach is not None:
            import staff
            off, def_ = staff.game_iq(team, "off"), staff.game_iq(team, "def")
        self.iq = max(0.2, min(1.3, (off - 45) / 40))          # offense
        self.def_iq = max(0.2, min(1.3, (def_ - 45) / 40))     # defense
        self.plays = {}                 # play -> [calls, successes]
        self.recent = []                # last few offensive calls
        self.kind = {"run": [0, 0], "pass": [0, 0]}
        self.faced = 0                  # offensive snaps vs this opponent
        self.blitzes_faced = 0
        self.heavy_boxes_faced = 0
        self.calls = {}                 # defensive call -> [calls, yards allowed]
        self.def_recent = []
        self.opp_runs = 0
        self.opp_snaps = 0
        self.tricks = 0
        # adaptive layer
        self.fam = {}                   # offense: family -> [n, successes, yards]
        self.sit_self = {}              # offense: situation -> [runs, plays] (self-scouting)
        self.sit_opp = {}               # defense: situation -> [opp runs, opp plays] (scouting them)
        self.fam_allowed = {}           # defense: family -> [n, yards, explosives]
        self.blitz = [0, 0, 0]          # defense when blitzing: [calls, yards, negative plays]
        self.shell = [0, 0, 0]          # defense when not blitzing
        self.stuffed_runs = 0           # consecutive runs of a yard or less
        self.sacks_taken = 0
        self.looks = {}                 # offense: situation -> [snaps, blitzes, man, two-high, 8+ box] (what they show)
        self.opp_fam_sit = {}           # defense: situation -> {family: n} (what they call)
        self.notes = []                 # [(snap, key, detail)] adjustments, newest last
        self._noted = {}
        self.half = 1

    def note(self, key, snap, detail=""):
        """Log an adjustment once per half (the booth reads these)."""
        if self._noted.get(key) == self.half:
            return
        self._noted[key] = self.half
        self.notes.append((snap, key, detail))

    def has(self, key):
        return self._noted.get(key) == self.half

    # offense
    def record_offense(self, call, dcall, down, togo, yards, td, r=None, yardline=50):
        ok = successful(down, togo, yards, td)
        rec = self.plays.setdefault(call.name, [0, 0])
        rec[0] += 1
        rec[1] += ok
        k = self.kind["run" if call.kind == "run" else "pass"]
        k[0] += 1
        k[1] += ok
        self.recent = (self.recent + [call.name])[-4:]
        self.faced += 1
        self.blitzes_faced += dcall.rush >= 5
        self.heavy_boxes_faced += dcall.box >= 8
        if call.trick:
            self.tricks += 1
        f = self.fam.setdefault(family(call), [0, 0, 0])
        f[0] += 1
        f[1] += ok
        f[2] += max(-5, min(40, yards))
        s_key = situation(down, togo, yardline)
        sit = self.sit_self.setdefault(s_key, [0, 0])
        sit[0] += call.kind == "run"
        sit[1] += 1
        lk = self.__dict__.setdefault("looks", {}).setdefault(s_key, [0, 0, 0, 0, 0])
        lk[0] += 1
        lk[1] += dcall.rush >= 5 and dcall.name != "Goal Line"
        lk[2] += dcall.coverage == "man"
        lk[3] += dcall.shell >= 2
        lk[4] += dcall.box >= 8
        if call.kind == "run":
            self.stuffed_runs = self.stuffed_runs + 1 if yards <= 1 else 0
        if r is not None and getattr(r, "sack", False):
            self.sacks_taken += 1

    def fam_mult(self, fam):
        rec = self.fam.get(fam)
        if not rec or rec[0] < 3:
            return 1.0
        rate = rec[1] / rec[0]
        raw = max(0.72, min(1.45, 0.62 + rate * 0.85))
        return 1 + (raw - 1) * min(1.2, self.iq)

    def tendency(self, sit):
        rec = self.sit_self.get(sit)
        if not rec or rec[1] < 6:
            return None
        return rec[0] / rec[1]

    def play_mult(self, name):
        m = 1.0
        rec = self.plays.get(name)
        if rec and rec[0] >= 2:
            m *= 0.65 + 0.7 * rec[1] / rec[0]        # go back to what works
        if self.recent and self.recent[-1] == name:
            m *= 0.35                                 # don't run it three times in a row
        elif name in self.recent:
            m *= 0.75
        return m

    def run_lean(self):
        r, pz = self.kind["run"], self.kind["pass"]
        if r[0] < 6 or pz[0] < 6:
            return 0.0
        return max(-0.12, min(0.12, 0.35 * min(1.2, self.iq) * (r[1] / r[0] - pz[1] / pz[0])))

    def blitz_rate(self):
        return self.blitzes_faced / self.faced if self.faced >= 8 else 0.0

    def heavy_box_rate(self):
        return self.heavy_boxes_faced / self.faced if self.faced >= 8 else 0.0

    # defense
    def record_defense(self, dcall, offense_kind, yards, call=None, r=None, down=1, togo=10, yardline=50):
        rec = self.calls.setdefault(dcall.name, [0, 0])
        rec[0] += 1
        rec[1] += max(-5, min(40, yards))
        self.def_recent = (self.def_recent + [dcall.name])[-3:]
        self.opp_snaps += 1
        self.opp_runs += offense_kind == "run"
        s_key = situation(down, togo, yardline)
        sit = self.sit_opp.setdefault(s_key, [0, 0])
        sit[0] += offense_kind == "run"
        sit[1] += 1
        if call is not None:
            fs = self.__dict__.setdefault("opp_fam_sit", {}).setdefault(s_key, {})
            fs[family(call)] = fs.get(family(call), 0) + 1
            f = self.fam_allowed.setdefault(family(call), [0, 0, 0])
            f[0] += 1
            f[1] += max(-5, min(40, yards))
            f[2] += yards >= 20
        bucket = self.blitz if dcall.rush >= 5 and dcall.name != "Goal Line" else self.shell
        bucket[0] += 1
        bucket[1] += max(-5, min(40, yards))
        bucket[2] += yards <= 0

    def call_mult(self, name):
        m = 1.0
        rec = self.calls.get(name)
        if rec and rec[0] >= 3:
            m *= max(0.6, min(1.3, 1.3 - (rec[1] / rec[0] - 5) / 10))
        if self.def_recent and self.def_recent[-1] == name:
            m *= 0.6
        return m

    def opp_run_rate(self, sit=None):
        if sit is not None:
            rec = self.sit_opp.get(sit)
            if rec and rec[1] >= 5:
                return rec[0] / rec[1]
        return self.opp_runs / self.opp_snaps if self.opp_snaps >= 10 else None

    def deep_trouble(self):
        """Getting beaten over the top?"""
        yds = sum(self.fam_allowed.get(f, [0, 0, 0])[1] for f in ("deep", "play_action"))
        n = sum(self.fam_allowed.get(f, [0, 0, 0])[0] for f in ("deep", "play_action"))
        big = sum(self.fam_allowed.get(f, [0, 0, 0])[2] for f in ("deep", "play_action"))
        return n >= 4 and (yds / n >= 13 or big >= 2)

    def run_trouble(self):
        n = sum(self.fam_allowed.get(f, [0, 0, 0])[0] for f in ("run_inside", "run_outside"))
        yds = sum(self.fam_allowed.get(f, [0, 0, 0])[1] for f in ("run_inside", "run_outside"))
        return n >= 8 and yds / n >= 5.5

    def blitz_verdict(self):
        """+1 blitz is paying off, -1 it's getting burned, 0 no read yet."""
        n, yds, neg = self.blitz
        if n < 5:
            return 0
        avg = yds / n
        base = self.shell[1] / self.shell[0] if self.shell[0] >= 5 else 5.5
        if avg <= base - 1.5 or neg / n >= 0.35:
            return 1
        if avg >= base + 2.5:
            return -1
        return 0

    def halftime(self):
        """Adjustments: first-half evidence counts half as much after the break,
        and the staff decides what to change."""
        r, pz = self.kind["run"], self.kind["pass"]
        if r[0] >= 8 and pz[0] >= 8:
            rr, pr = r[1] / r[0], pz[1] / pz[0]
            if rr - pr >= 0.15:
                self.notes.append((-1, "half_run", ""))
            elif pr - rr >= 0.15:
                self.notes.append((-1, "half_pass", ""))
        if self.blitz_verdict() == -1:
            self.notes.append((-1, "half_less_blitz", ""))
        elif self.deep_trouble():
            self.notes.append((-1, "half_two_high", ""))
        elif self.run_trouble():
            self.notes.append((-1, "half_box", ""))
        for d in (self.plays, self.calls):
            for rec in d.values():
                rec[0] = rec[0] // 2
                rec[1] = rec[1] / 2
        for k in self.kind.values():
            k[0] //= 2
            k[1] //= 2
        for d in (self.fam, self.fam_allowed):
            for rec in d.values():
                for i in range(len(rec)):
                    rec[i] = rec[i] // 2 if isinstance(rec[i], int) else rec[i] / 2
        self.blitz = [x // 2 for x in self.blitz]
        self.shell = [x // 2 for x in self.shell]
        self.half = 2


# ═══ Situation helpers ═════════════════════════════════════════════════════

def game_seconds_left(sim):
    if sim.quarter > 4:
        return 9999
    return (4 - sim.quarter) * 900 + sim.clock


def half_seconds_left(sim):
    if sim.quarter in (1, 3):
        return 900 + sim.clock
    return sim.clock


def score_diff(sim, team=None):
    team = team or sim.offense
    return sim.score[team] - sim.score[sim.other(team)]


def is_hurry(sim):
    """Two-minute drill / trailing late."""
    if sim.quarter > 4:
        return False
    d = score_diff(sim)
    if sim.quarter == 4 and d < 0 and sim.clock < 360:
        return True
    if sim.quarter == 4 and d <= -9 and sim.clock < 720:
        return True
    if sim.quarter == 2 and sim.clock < 120 and sim.yardline >= 20:
        return True
    return False


def is_milking(sim):
    if sim.quarter > 4:
        return False
    d = score_diff(sim)
    if sim.quarter == 4:
        return (d > 0 and sim.clock < 480) or d >= 17
    return (sim.quarter == 3 and d >= 21) or (sim.quarter == 2 and d >= 28)


def should_kneel(sim):
    if sim.quarter > 4:
        return False
    d = score_diff(sim)
    downs_left = 4 - sim.down          # kneels available before 4th down
    def_to = sim.timeouts[sim.defense]
    if sim.quarter == 4 and d > 0:
        burn = max(0, downs_left - def_to) * 40 + (downs_left > def_to) * 0
        return sim.clock <= burn + 2 and downs_left > 0
    if sim.quarter == 2 and d >= 0 and sim.clock < 35 and sim.yardline < 60:
        return True
    return False


FG_RANGE_BASE = 52           # longest try (yards) an average kicker's coach will send him out for


def fg_range(sim, team=None):
    k = sim.depth[team or sim.offense]["K"][0]
    import weather
    w_rng, w_acc = weather.fg_mods(sim, team or sim.offense)   # nobody kicks a 50-yarder into a gale
    return FG_RANGE_BASE + (sim.prof(k)["kick_power"] - 60) * 0.3 + w_rng + w_acc * 8


# ═══ Play calling ══════════════════════════════════════════════════════════

def choose_offense(sim, rng):
    """Returns ('play', OffPlay, personnel) | ('punt',) | ('fg',)."""
    coach = sim.offense.coach                       # fourth downs and fakes are the head coach's call
    import staff
    caller = staff.play_caller(sim.offense, "off")  # the plays are the play-caller's
    ytg_end = 100 - sim.yardline
    fg_dist = ytg_end + 17
    d = score_diff(sim)
    in_range = fg_dist <= fg_range(sim)

    if should_kneel(sim):
        return ("play", KNEEL, "22")

    # End-of-half / end-of-game kicks and heaves.
    if sim.quarter in (2, 4) and sim.clock <= 12:
        if in_range and (sim.quarter == 2 or -3 <= d <= 0):
            return ("fg",)
        if sim.quarter == 2 or d < 0:
            if 35 < ytg_end <= 65 and sim.clock <= 8:
                return ("play", HAIL_MARY, "10")

    # Sportsmanship: way ahead late, the backups just run it and give the ball back.
    if d >= 45 or (sim.quarter == 4 and d >= 28):
        if sim.down == 4 and ytg_end > 35:
            return ("punt",)
        if sim.quarter == 4 and sim.down < 4 and sim.clock <= (4 - sim.down) * 43:
            return ("play", KNEEL, "22")                          # only when the kneels really end it
        return ("play", ALL_PLAYS["Inside Zone"], "12")          # run it, keep the clock moving

    if sim.down == 4:
        decision = fourth_down(sim, in_range, fg_dist, d)
        aggr = coach.aggression
        if decision == "punt" and sim.togo <= 4 and 30 <= sim.yardline <= 55 and sim.quarter <= 4 \
                and rng.random() < 0.012 * aggr / 50:
            return ("fake_punt",)
        if decision == "fg" and sim.togo <= 3 and sim.quarter <= 4 and rng.random() < 0.008 * aggr / 50:
            return ("fake_fg",)
        if decision != "go":
            return (decision,)

    return ("play",) + _pick_play(sim, rng, caller, d, ytg_end)


def fourth_down(sim, in_range, fg_dist, d):
    togo, ytg_end = sim.togo, 100 - sim.yardline
    from traits import mod as trait_mod
    aggr = sim.offense.coach.aggression + trait_mod(sim.offense.coach, "aggression", 0.0)
    aggr += (getattr(sim.plan[sim.offense], "adj", None) or {}).get("aggr", 0)    # halftime call
    import sim_strategy
    aggr += sim_strategy.fourth_aggression(sim.offense)
    import skills
    if skills.team_has(sim.offense, "riverboat"):
        aggr += 20                                                  # Riverboat (coaching tree)

    if sim.quarter > 4:   # overtime
        if d < -3:
            return "go"
        if in_range and togo > 2:
            return "fg"
        return "go" if togo <= 2 or not in_range else "fg"

    left = game_seconds_left(sim)
    hopeless = sim.quarter == 4 and (d <= -25 or (d <= -17 and left < 360))
    if sim.quarter == 4 and d < 0 and not hopeless:
        if -3 <= d and in_range and left < 150:
            return "fg"
        if left < 300 and d < -3 or left < 150:
            return "go"
    if sim.quarter == 4 and d > 0 and left < 120 and not in_range:
        return "punt" if ytg_end > 40 else ("go" if togo <= 1 else "punt")

    if ytg_end <= 40:
        allowed = 3.0 if not in_range else 1.6
    elif ytg_end <= 55:
        allowed = 2.2
    elif ytg_end <= 65:
        allowed = 1.2
    else:
        allowed = 0.6
    if ytg_end <= 5:
        allowed += 1.5
    allowed *= 0.5 + aggr / 100
    mom = getattr(sim, "momentum", None)
    if mom is not None and mom.leader() is sim.offense:
        allowed += 0.5                                   # ride the wave
    if d < -14 and sim.quarter >= 3 and not hopeless:
        allowed += 2
    if togo <= allowed:
        return "go"
    if in_range:
        return "fg"
    return "punt"


# How hard every call is pulled back toward the scheme's run/pass identity. The
# identity offenses (option, Air Raid, smashmouth) are the least negotiable.
SCHEME_ANCHOR = {"Triple Option": 0.55, "Air Raid": 0.45, "Smashmouth": 0.4, "Veer & Shoot": 0.35}
SCHEME_ANCHOR_DEFAULT = 0.3


def _pick_play(sim, rng, coach, d, ytg_end):
    scheme = OFFENSE_SCHEMES[coach.offense_scheme]
    down, togo = sim.down, sim.togo
    hurry = is_hurry(sim)

    run_p = scheme["run"]
    if down == 1:
        run_p += 0.03
    elif down == 2:
        run_p += -0.12 if togo >= 8 else (0.10 if togo <= 3 else 0)
    else:
        # Third and long still looks like the scheme: an Air Raid throws, an option team
        # will run the midline on third-and-7 because that's what it does best.
        if togo >= 7:
            run_p = 0.04 + scheme["run"] ** 2 * 0.6
        elif togo >= 4:
            run_p = 0.10 + scheme["run"] ** 1.5 * 0.7
        elif togo <= 2:
            run_p = max(run_p + 0.25, 0.60)
    if ytg_end <= 5:
        run_p += 0.12
    if sim.yardline <= 5:
        run_p += 0.15
    if is_milking(sim):
        run_p += 0.25
    if hurry:
        run_p -= 0.35
    anchor = SCHEME_ANCHOR.get(coach.offense_scheme, SCHEME_ANCHOR_DEFAULT)
    trailing_big = sim.quarter >= 3 and d <= -17
    if trailing_big:
        # Down three scores, everybody throws more, but an identity offense bends
        # instead of breaking: a smashmouth team still runs it.
        run_p -= 0.25 * (1 - anchor)
    plan = sim.plan[sim.offense]
    snap = sim.plays_run
    sit = situation(down, togo, sim.yardline)
    if not hurry and not is_milking(sim):
        lean = plan.run_lean()
        run_p += lean                                # lean on whatever is working today
        if lean >= 0.08:
            plan.note("lean_run", snap)
        elif lean <= -0.08:
            plan.note("lean_pass", snap)
        if plan.heavy_box_rate() > 0.4:
            run_p -= 0.06                            # they're loading the box: throw it
            plan.note("beat_box", snap)
        if plan.stuffed_runs >= 3 and down <= 2 and rng.random() < 0.3 + 0.6 * plan.iq:
            run_p -= 0.14                            # three straight stuffs: go to the air
            plan.note("abandon_run", snap)
        tend = plan.tendency(sit)                    # self-scouting: don't be predictable
        if tend is not None and sit in ("1st", "2nd_long", "2nd_short") and rng.random() < 0.45 * plan.iq:
            if tend >= 0.72:
                run_p -= 0.10
                plan.note("break_tendency_pass", snap, sit)
            elif tend <= 0.28:
                run_p += 0.10
                plan.note("break_tendency_run", snap, sit)
    if not hurry and not is_milking(sim):
        # Identity: a coach goes back to what he is. Situation bends the call; the scheme anchors it.
        # Game script nudges it (half the pull when down three scores late), it doesn't flip it.
        a = anchor * (0.5 if trailing_big else 1.0)
        run_p = run_p * (1 - a) + scheme["run"] * a
    adj = getattr(plan, "adj", None) or {}           # the head coach's halftime call (halftime.py)
    import sideline
    sl_run, sl_fam = sideline.staff_lean(sim)        # your series orders and Friday's plan
    if not hurry:
        run_p += adj.get("run", 0.0) + sl_run
        import sim_strategy
        run_p += sim_strategy.run_shift(sim.offense, sim)
    import weather
    wx_run, wx_deep = weather.call_lean(sim, sim.offense)   # rain, snow, wind: keep it on the ground
    if not hurry:
        run_p += wx_run
    run_p = max(0.04, min(0.94, run_p))
    kind = "run" if rng.random() < run_p else "pass"

    personnel = _pick_personnel(rng, scheme, togo, ytg_end, hurry)

    tags = set()
    if hurry:
        tags.add("hurry")
    if ytg_end <= 20:
        tags.add("red")
    if ytg_end <= 5:
        tags.add("goal")
    if togo <= 1:
        tags.add("inches")
    if togo <= 3:
        tags.add("short")
    elif togo >= 8:
        tags.add("long")
    else:
        tags.add("medium")
    if down <= 2 and togo <= 10 and not hurry:
        tags.add("base")
    if down == 1 and 40 <= sim.yardline <= 75 and rng.random() < 0.3:
        tags.add("shot")
    # Sudden change: the first snap after a takeaway is a classic shot play.
    sudden = (sim.drive is not None and sim.drive.get("plays") == 0 and sim.drives
              and sim.drives[-1].get("result") in TAKEAWAYS and sim.drives[-1].get("team") is not sim.offense)
    if sudden and down == 1 and 30 <= sim.yardline <= 80 and rng.random() < 0.55:
        tags.add("shot")
        plan.note("sudden_change", snap)

    pool = RUN_PLAYS if kind == "run" else PASS_PLAYS
    qb_speed = sim.prof(sim.qb_of(sim.offense))["speed"]
    blitzy = plan.blitz_rate() > 0.35
    trailing = d < 0 or (d <= 7 and sim.quarter >= 3)
    mom = getattr(sim, "momentum", None)
    heat = plan.sacks_taken >= 3 and not hurry            # protection is breaking down
    if heat:
        plan.note("quick_game", snap)
    chase = sim.quarter >= 3 and d <= -10 and not hurry     # need chunks, not dinks
    scripted = plan.faced < 8                               # the opening script: show a bit of everything
    options, weights = [], []
    for play in pool:
        if play.name in ("Hail Mary",) or not play_fits_personnel(play, personnel):
            continue
        if play.trick:
            if plan.tricks >= 2 or hurry or ytg_end <= 5 or down > 2 or sim.quarter > 4:
                continue
            import staff
            w = 0.09 * (0.4 + staff.aggression(sim.offense, "off") / 100) * (1.8 if trailing else 1.0)
            w *= adj.get("trick", 1.0)
            import skills
            if skills.team_has(sim.offense, "riverboat"):
                w *= 1.5                                   # Riverboat (coaching tree)
            if mom is not None and mom.leader() is sim.defense:
                w *= 1.6                               # try to steal the momentum back
            if play.name in plan.plays:
                w *= 0.1
        else:
            w = scheme["plays"].get(play.name, 0.25 if kind == "pass" else 0.15)
        if play.concept == "qb_sneak":
            w = 6 if togo <= 1 else 0
        if play.concept in ("triple", "midline") and coach.offense_scheme != "Triple Option":
            w = 0
        if play.concept in ("zone_read", "qb_power", "qb_draw", "speed_option"):
            w *= max(0.25, min(2.0, (qb_speed - 45) / 25))   # statues don't run the read
        if play.screen and sum(1 for n in plan.recent[-3:] if n in SCREEN_NAMES) >= 2:
            w *= 0.15                                  # you can't live on screens
        if blitzy and (play.screen or "quick" in play.tags or play.concept == "draw"):
            w *= 1.6                                   # punish the blitz
        w *= coach_bias(coach, play.name) * plan.play_mult(play.name)
        fam = family(play)
        w *= plan.fam_mult(fam)                          # what's working carries over to similar plays
        w *= adj.get("fam", {}).get(fam, 1.0)
        w *= sl_fam.get(fam, 1.0)
        import sim_strategy
        w *= sim_strategy.family_mult(sim.offense, sim, plan, fam)
        if scripted and play.name not in plan.plays:
            w *= 1.35
        if heat:
            w *= {"quick": 1.45, "screen": 1.4, "deep": 0.65, "play_action": 0.8}.get(fam, 1.0)
        if chase:
            w *= {"deep": 1.3, "intermediate": 1.1, "screen": 0.8}.get(fam, 1.0)
        if fam == "deep" and wx_deep != 1.0:
            w *= wx_deep
        if tags.intersection(play.tags):
            w *= 2.2
        if kind == "pass":
            if down >= 3 and play.max_depth < togo and not play.screen:
                w *= 0.25
            if hurry and not ({"hurry", "sideline", "quick"} & set(play.tags)):
                w *= 0.45
            if ytg_end <= 12 and play.max_depth > ytg_end + 8 and "shot" in play.tags:
                w *= 0.3
        if w > 0:
            options.append(play)
            weights.append(w)
    play = rng.choices(options, weights=weights)[0]
    if not play_fits_personnel(play, personnel):
        personnel = "11"
    return play, personnel


def _pick_personnel(rng, scheme, togo, ytg_end, hurry):
    weights = dict(scheme["personnel"])
    if hurry or togo >= 8:
        for k in ("10", "11"):
            weights[k] = weights.get(k, 0.05) * 2.5
        for k in ("21", "22"):
            weights[k] = weights.get(k, 0) * 0.3
    if togo <= 2 or ytg_end <= 3:
        for k in ("12", "21", "22"):
            weights[k] = weights.get(k, 0.05) * 2.5
        weights["10"] = weights.get("10", 0) * 0.2
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def choose_defense(sim, rng, personnel):
    import staff
    coach = staff.play_caller(sim.defense, "def")
    weights = dict(DEFENSE_SCHEMES[coach.defense_scheme])
    down, togo = sim.down, sim.togo
    ytg_end = 100 - sim.yardline
    lead = -score_diff(sim)              # from the defense's perspective

    if down >= 2 and togo >= 8:
        for c, m in (("Cover 2", 2.0), ("Cover 4 Quarters", 2.0), ("Fire Zone", 1.5), ("Run Blitz", 0.1)):
            if c in weights or m > 1:
                weights[c] = weights.get(c, 1) * m
        weights["Dime Quarters"] = 3 if down >= 3 else 1
    if togo <= 2:
        weights["Run Blitz"] = weights.get("Run Blitz", 1) * 3
        weights["Cover 1 Man"] = weights.get("Cover 1 Man", 1) * 1.5
        weights["Cover 0 Blitz"] = weights.get("Cover 0 Blitz", 0.5) * 1.5
        weights.pop("Dime Quarters", None)
    if ytg_end <= 4:
        weights["Goal Line"] = 8 if togo <= 3 else 2
    late_q = sim.quarter in (2, 4)
    if late_q and 0 < lead <= 16 and sim.clock < 75 and ytg_end > 25:
        weights["Prevent"] = 12
    if is_hurry(sim):
        weights["Cover 2"] = weights.get("Cover 2", 1) * 1.8
        weights["Cover 4 Quarters"] = weights.get("Cover 4 Quarters", 1) * 1.8

    if personnel in ("21", "22"):
        weights["Run Blitz"] = weights.get("Run Blitz", 1) * 1.6
        for c in ("Dime Quarters", "Prevent"):
            if c in weights:
                weights[c] *= 0.3
    elif personnel == "10":
        weights["Dime Quarters"] = weights.get("Dime Quarters", 0.5) * 2

    import staff
    blitz_mult = 0.5 + staff.blitz(sim.defense) / 100                 # the DC's nerve, and the head coach's
    plan = sim.plan[sim.defense]
    snap = sim.plays_run
    sit = situation(down, togo, sim.yardline)
    rr = plan.opp_run_rate(sit)                  # they know what you like to do on this down
    verdict = plan.blitz_verdict()
    dadj = getattr(plan, "adj", None) or {}          # the head coach's halftime call
    blitz_mult *= dadj.get("blitz", 1.0)
    import sideline
    blitz_mult *= sideline.def_lean(sim)             # your orders and Friday's plan
    if verdict == 1:
        blitz_mult *= 1.3
        plan.note("blitz_more", snap)
    elif verdict == -1:
        blitz_mult *= 0.65
        plan.note("blitz_less", snap)
    sharp = rng.random() < 0.3 + 0.6 * getattr(plan, "def_iq", plan.iq)    # does this staff see it and adjust?
    deep = plan.deep_trouble() and sharp
    if deep:
        plan.note("two_high", snap)
    box = plan.run_trouble() and sharp
    if box:
        plan.note("load_box", snap)
    hot_wr, hot_yds = None, 0
    for p in sim.depth[sim.offense]["WR"][:3] + sim.depth[sim.offense]["TE"][:1]:
        y = sim.stats.get(p, {}).get("rec_yds", 0) if sim.stats.get(p) else 0
        if y > hot_yds:
            hot_wr, hot_yds = p, y
    if hot_yds >= 90 and "Bracket" not in weights and sim.quarter >= 2:
        weights["Bracket"] = 0.6
    if hot_yds >= 90 and "Bracket" in weights:
        weights["Bracket"] *= 1.8
        plan.note("bracket", snap, hot_wr.last_name if hot_wr else "")
    qb_speed = sim.prof(sim.qb_of(sim.offense))["speed"]
    top_wr = max(sim.prof(p)["route"] for p in sim.depth[sim.offense]["WR"][:2])
    if "QB Spy" in weights:
        weights["QB Spy"] *= max(0.2, min(3.0, (qb_speed - 58) / 6))
    if "Bracket" in weights:
        weights["Bracket"] *= max(0.3, min(2.5, 0.5 + (top_wr - 72) / 8))
    for name in list(weights):
        c = DEF_CALLS[name]
        if c.rush >= 5 and name != "Goal Line":
            weights[name] *= blitz_mult
        weights[name] *= coach_bias(coach, name) * plan.call_mult(name)
        if rr is not None and name not in ("Goal Line", "Prevent"):
            if c.box >= 8 or "run" in c.tags:
                weights[name] *= 0.6 + 0.8 * rr          # they keep running it: load up
            elif c.shell >= 2 or c.personnel == "dime":
                weights[name] *= 0.6 + 0.8 * (1 - rr)
        if name in ("Goal Line", "Prevent"):
            continue
        if dadj.get("shell") and c.shell >= 2:
            weights[name] *= dadj["shell"]
        if deep:
            weights[name] *= 1.35 if c.shell >= 2 else (0.6 if c.shell == 0 else 0.9)
        if box and (c.box >= 8 or "run" in c.tags):
            weights[name] *= 1.35
    names = list(weights)
    return DEF_CALLS[rng.choices(names, weights=[weights[n] for n in names])[0]]


def two_point_decision(sim, team):
    """College-chart style: go for two only when it clearly helps late."""
    if sim.quarter > 4:
        return sim.ot_round >= 2
    if sim.quarter < 4 or sim.clock > 600:
        return False
    d = sim.score[team] - sim.score[sim.other(team)]      # after the TD, before the try
    return d in (-10, -5, -2, 1, 5, 12)
