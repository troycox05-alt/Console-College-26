"""
weather.py — Saturday's weather: what it's going to be, what it is, and what it does.

Every game is played in real weather built from where and when it kicks off:

  CLIMATE     each state (and a few towns with their own weather) has a September
              and a December normal, a rain rate, a wind, humidity and a snow factor.
              The season cools week by week; night games are colder than noon kicks.
  THE WEEK    weather comes in systems: each region gets the same warm spell, cold snap
              or wet week, so a front can soak the whole Continental on one Saturday. Now and
              then a tropical storm comes ashore on the Gulf or the Atlantic coast.
  THE GAME    conditions change quarter by quarter: rain moves in or clears out, a
              front drops the temperature and turns up the wind, the sun goes down,
              snow piles up, the field gets slick. Thunderstorms can bring a lightning
              delay. Teams switch ends every quarter, so the wind helps one side, then
              the other.
  FORECASTS   the forecast is honest but uncertain: three weeks out it's the climate,
              the week of the game it's close. "40% chance of rain" means it rains in
              about four of every ten of those games.

What it does on the field (for both teams, in every sim):
  rain / snow    passes are less accurate, balls are harder to catch, more fumbles and
                 muffed kicks, kickers lose distance and footing
  wind           deep balls and kicks move; into the wind a 45-yarder is a long shot,
                 with it a 55-yarder is in range; crosswinds push kicks wide
  cold           the ball is a rock: fewer catches, shorter kicks; warm-weather teams
                 wilt a little in the cold
  heat           in the second half, teams that don't live in it feel it
  altitude       kicks fly farther; visitors from sea level tire late
  the field      a wet grass field gets sloppy (speed matters less, big runs dry up);
                 heated hybrid grass (a stadium part) shrugs off snow
Coaches adapt: run more, take fewer deep shots, punt instead of kicking into a gale.
A team that spent the week on "Weather prep" (practice focus) feels half the effects.
Domes and closed roofs have no weather at all.
"""
import math
import random
from datetime import date, timedelta

# ═══ Climate ════════════════════════════════════════════════════════════════
# state: (Sept avg high °F, Dec avg high °F, wet: chance a fall Saturday gets rain,
#         wind: typical mph, humid 0-2, snowy 0-2)
CLIMATE = {
    "AL": (89, 58, .20, 7, 2, 0.0), "AR": (86, 51, .20, 7, 2, 0.2), "AZ": (99, 66, .05, 6, 0, 0.0),
    "CA": (82, 60, .07, 8, 0, 0.0), "CO": (78, 45, .10, 9, 0, 1.0), "CT": (75, 40, .22, 9, 1, 0.8),
    "DC": (80, 47, .20, 8, 1, 0.3), "DE": (79, 45, .21, 9, 1, 0.5), "FL": (90, 71, .26, 8, 2, 0.0),
    "GA": (87, 57, .20, 7, 2, 0.0), "HI": (87, 80, .20, 12, 2, 0.0), "IA": (78, 32, .18, 11, 1, 1.2),
    "ID": (80, 39, .08, 8, 0, 0.8), "IL": (79, 37, .20, 11, 1, 1.0), "IN": (80, 39, .21, 10, 1, 1.0),
    "KS": (82, 43, .15, 13, 1, 0.6), "KY": (83, 46, .21, 8, 2, 0.4), "LA": (89, 63, .24, 7, 2, 0.0),
    "MA": (73, 39, .22, 11, 1, 1.0), "MD": (80, 46, .21, 9, 1, 0.4), "ME": (70, 33, .22, 9, 1, 1.5),
    "MI": (74, 33, .22, 11, 1, 1.3), "MN": (72, 25, .19, 11, 1, 1.5), "MO": (82, 43, .19, 10, 1, 0.5),
    "MS": (89, 59, .22, 7, 2, 0.0), "MT": (73, 33, .10, 10, 0, 1.2), "NC": (83, 53, .20, 7, 2, 0.1),
    "ND": (72, 22, .15, 13, 1, 1.5), "NE": (80, 36, .15, 12, 1, 0.9), "NH": (72, 34, .22, 8, 1, 1.5),
    "NJ": (78, 44, .22, 10, 1, 0.5), "NM": (82, 49, .08, 9, 0, 0.3), "NV": (88, 53, .04, 8, 0, 0.2),
    "NY": (74, 37, .24, 10, 1, 1.2), "OH": (77, 38, .22, 10, 1, 1.0), "OK": (86, 50, .16, 13, 1, 0.3),
    "OR": (78, 47, .20, 7, 1, 0.1), "PA": (76, 40, .22, 9, 1, 0.9), "RI": (74, 40, .22, 11, 1, 0.8),
    "SC": (86, 58, .20, 7, 2, 0.0), "SD": (76, 29, .14, 12, 1, 1.3), "TN": (85, 50, .21, 7, 2, 0.2),
    "TX": (91, 63, .14, 10, 2, 0.0), "UT": (80, 39, .08, 8, 0, 1.0), "VA": (81, 48, .20, 8, 1, 0.3),
    "VT": (70, 31, .22, 8, 1, 1.5), "WA": (72, 45, .30, 8, 1, 0.2), "WI": (74, 29, .20, 11, 1, 1.4),
    "WV": (78, 42, .23, 7, 1, 0.7), "WY": (70, 36, .07, 16, 0, 1.4),
}
# Towns with weather of their own.
SCHOOL_CLIMATE = {
    "Fresno State": (92, 56, .03, 6, 0, 0.0), "San Diego State": (80, 66, .05, 7, 0, 0.0),
    "Los Angeles": (80, 67, .05, 6, 0, 0.0), "Southern California": (83, 68, .05, 6, 0, 0.0), "California": (73, 57, .10, 9, 0, 0.0),
    "Palo Alto": (78, 58, .08, 7, 0, 0.0), "San Jose State": (80, 59, .07, 7, 0, 0.0),
    "Washington": (71, 48, .32, 8, 1, 0.2), "Washington State": (75, 36, .12, 9, 0, 1.2),
    "Buffalo": (72, 34, .28, 12, 1, 2.0), "Hudson": (74, 38, .23, 9, 1, 1.0),
    "Lubbock": (84, 55, .10, 15, 0, 0.3), "El Paso": (90, 58, .05, 8, 0, 0.1), "North Texas": (91, 58, .13, 11, 1, 0.1),
    "Houston": (91, 66, .24, 8, 2, 0.0), "Montrose": (91, 66, .24, 8, 2, 0.0), "Texas State": (92, 63, .12, 8, 2, 0.0),
    "Nevada": (82, 46, .06, 8, 0, 0.7), "Las Vegas": (95, 58, .03, 8, 0, 0.0),
    "Wyoming": (70, 35, .07, 18, 0, 1.5), "Front Range": (74, 44, .08, 10, 0, 1.2), "Colorado": (78, 47, .09, 9, 0, 1.0),
    "Colorado State": (77, 43, .08, 9, 0, 1.0), "New Mexico": (81, 48, .07, 9, 0, 0.3),
    "New Mexico State": (87, 58, .05, 8, 0, 0.1), "Miami": (89, 77, .28, 9, 2, 0.0), "Biscayne": (89, 77, .28, 9, 2, 0.0),
    "Florida Atlantic": (88, 76, .27, 9, 2, 0.0), "South Florida": (90, 74, .25, 8, 2, 0.0),
    "Northern Illinois": (78, 32, .20, 12, 1, 1.2), "Minnesota": (72, 25, .19, 11, 1, 1.5),
    "Iowa State": (78, 31, .18, 12, 1, 1.2), "Kansas State": (83, 42, .15, 14, 1, 0.6),
    "Appalachian State": (75, 45, .24, 9, 1, 0.8), "Appalachian State": (75, 45, .24, 9, 1, 0.8),
    "West Virginia": (76, 40, .24, 7, 1, 0.9), "Pennsylvania": (74, 36, .22, 9, 1, 1.1),
    "Oregon": (79, 47, .22, 6, 1, 0.1), "Oregon State": (79, 47, .24, 6, 1, 0.1),
}
ALTITUDE = {
    "Wyoming": 7220, "Front Range": 7250, "Colorado": 5360, "Colorado State": 5000, "New Mexico": 5100,
    "Utah": 4650, "Provo": 4550, "Utah State": 4700, "Nevada": 4500, "El Paso": 3900, "New Mexico State": 3900,
    "Lubbock": 3250, "Boise State": 2700, "Las Vegas": 2000, "Arizona": 2400, "Washington State": 2350,
    "Montana": 3200, "Montana State": 4800, "Northern Colorado": 4700, "Idaho": 2600, "Weber State": 4400,
    "Idaho State": 4450, "Northern Arizona": 7000, "Southern Utah": 5800,
}
STATE_ALT = {"CO": 5000, "WY": 6500, "UT": 4500, "NM": 4500, "NV": 3000, "MT": 3500, "ID": 2500, "AZ": 1500}
# The neutral-site cities that don't carry a state in the venue name.
CITY_STATE = {"Atlanta": "GA", "Tampa": "FL", "Jacksonville": "FL", "Dallas": "TX", "East Rutherford": "NJ",
              "Philadelphia": "PA", "Charlotte": "NC", "Indianapolis": "IN", "Arlington": "TX", "Detroit": "MI",
              "Las Vegas": "NV", "Orlando": "FL", "Houston": "TX", "Nashville": "TN", "Baltimore": "MD",
              "Chicago": "IL", "New Orleans": "LA", "Glendale": "AZ", "Pasadena": "CA", "Miami Gardens": "FL",
              "Memphis": "TN", "San Antonio": "TX", "Boston": "MA", "Bronx": "NY", "Annapolis": "MD"}
CITY_CLIMATE = {"Pasadena": (86, 67, .05, 6, 0, 0.0), "San Diego": (78, 66, .05, 7, 0, 0.0),
                "Inglewood": (82, 67, .05, 7, 0, 0.0), "El Paso": (90, 58, .05, 8, 0, 0.1),
                "Boise": (80, 39, .08, 8, 0, 0.8), "Tucson": (98, 66, .05, 6, 0, 0.0),
                "Albuquerque": (81, 48, .07, 9, 0, 0.3), "Honolulu": (88, 80, .18, 12, 2, 0.0),
                "Miami Gardens": (89, 77, .28, 9, 2, 0.0), "Bronx": (75, 40, .22, 11, 1, 1.0)}
CITY_ALT = {"El Paso": 3900, "Albuquerque": 5100, "Boise": 2700, "Tucson": 2400}
INDOOR = ("Dome", "Arena", "South Loop Stadium", "Inglewood Stadium", "Spring Mountain Stadium", "Phoenix Ballpark")
REGION_OF = {}
try:
    from recruiting_data import STATES as _ST
    REGION_OF = {k: v[1] for k, v in _ST.items()}
except Exception:
    pass
REGION_OF.setdefault("DC", "Northeast")

TROPICAL_COASTS = (("TX", "LA"), ("LA", "MS", "AL"), ("AL", "FL"), ("FL",), ("FL", "GA", "SC"), ("SC", "NC"),
                   ("NC", "VA"))
STORM_NAMES = ("Alberto", "Beryl", "Chris", "Debby", "Ernesto", "Francine", "Gordon", "Helene", "Isaac", "Joyce",
               "Kirk", "Leslie", "Milton", "Nadine", "Oscar", "Patty", "Rafael", "Sara", "Tony", "Valerie",
               "Andrea", "Barry", "Chantal", "Dexter", "Erin", "Fernand", "Gabrielle", "Humberto", "Imelda",
               "Jerry", "Karen", "Lorenzo", "Melissa", "Nestor", "Olga", "Pablo", "Rebekah", "Sebastien")
COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
PRECIP_WORD = {0: "", 1: "light", 2: "steady", 3: "heavy"}

_LG = [None]                   # the league, for the seed (set by attach / bind)
_CACHE = {}


def bind(league):
    _LG[0] = league


def _seed():
    lg = _LG[0]
    return getattr(lg, "seed", 0) if lg is not None else 0


# ═══ Where and when ═════════════════════════════════════════════════════════

def _venue(game):
    """The venue string the game is played at (neutral sites and the postseason say it)."""
    if getattr(game, "neutral", False) or getattr(game, "game_type", "Regular Season") != "Regular Season":
        return getattr(game, "venue", None) or game.home.stadium
    return game.home.stadium


def indoor(game):
    v = _venue(game) or ""
    return any(d in v for d in INDOOR)


def _campus(game):
    """True when the game is at the home team's own stadium."""
    v = _venue(game) or ""
    return (not getattr(game, "neutral", False)) and (v.split(",")[0].strip() == game.home.stadium)


def place(game):
    """(climate tuple, state code, altitude ft, place key, city) for where the game is played."""
    h = game.home
    if _campus(game):
        st = getattr(h, "home_state", None) or "TX"
        clim = SCHOOL_CLIMATE.get(h.school) or CLIMATE.get(st) or CLIMATE["TX"]
        alt = ALTITUDE.get(h.school, min(STATE_ALT.get(st, 500), 2000))
        try:
            import campus_towns
            city = campus_towns.TOWNS.get(h.school, "").split(",")[0]
        except Exception:
            city = ""
        return clim, st, alt, h.school, city
    v = _venue(game) or ""
    bits = [b.strip() for b in v.split(",")]
    st, city = None, bits[1] if len(bits) >= 2 else ""
    if len(bits) >= 3 and len(bits[-1]) == 2:
        st = bits[-1]
    elif city in CITY_STATE:
        st = CITY_STATE[city]
    st = st or getattr(h, "home_state", None) or "TX"
    clim = CITY_CLIMATE.get(city) or CLIMATE.get(st) or CLIMATE["TX"]
    alt = CITY_ALT.get(city, 500)
    return clim, st, alt, city or v, city


def team_climate(team):
    st = getattr(team, "home_state", None) or "TX"
    return SCHOOL_CLIMATE.get(team.school) or CLIMATE.get(st) or CLIMATE["TX"]


def team_altitude(team):
    return ALTITUDE.get(team.school, min(STATE_ALT.get(getattr(team, "home_state", None), 500), 2000))


def game_date(game, league=None):
    d = getattr(game, "date", None)
    if d is not None:
        return d
    import broadcast
    lg = league or _LG[0]
    year = getattr(lg, "year", 2026) if lg is not None else 2026
    try:
        return broadcast.season_saturday(year, min(game.week, 16))
    except Exception:
        return date(year, 10, 1)


def kick_minutes(game):
    k = getattr(game, "kick", None)
    if k is not None:
        return k
    if getattr(game, "game_type", "") in ("National Championship", "NP Semifinal", "NP Quarterfinal"):
        return 19 * 60 + 30
    return 15 * 60 + 30


def _normal_high(clim, d):
    sep, dec = clim[0], clim[1]
    days = (d - date(d.year if d.month >= 8 else d.year - 1, 9, 1)).days
    frac = max(-0.1, min(1.18, days / 112))
    return sep + (dec - sep) * frac


def _diurnal(kick, clim):
    dry = 1.35 if clim[4] == 0 else 1.0
    h = kick / 60
    if h < 12.5:
        off = -4
    elif h < 14.5:
        off = -1.5
    elif h < 17:
        off = 0
    elif h < 19:
        off = -5
    elif h < 21:
        off = -8
    else:
        off = -11
    return off * dry


# ═══ The week's weather systems ═════════════════════════════════════════════

def _region_pattern(year, week, region):
    key = ("rp", _seed(), year, week, region)
    if key in _CACHE:
        return _CACHE[key]
    rng = random.Random(f"wxr:{_seed()}:{year}:{week}:{region}")
    # a warm spell or a cold snap, a wet week or a dry one, a windy one
    pat = {"temp": rng.gauss(0, 6.0), "wet": math.exp(rng.gauss(0, 0.55)), "wind": math.exp(rng.gauss(0, 0.3))}
    if rng.random() < 0.18:                          # a front comes through on Saturday
        pat["front"] = rng.choice((1, 2, 3, 4))       # the quarter it arrives in
        pat["wet"] *= 1.6
    _CACHE[key] = pat
    return pat


def tropical(year):
    """This season's landfalling tropical systems: [(week, name, states)]."""
    key = ("trop", _seed(), year)
    if key in _CACHE:
        return _CACHE[key]
    rng = random.Random(f"wxt:{_seed()}:{year}")
    out = []
    names = list(STORM_NAMES)
    rng.shuffle(names)
    n = rng.choices((0, 1, 2), weights=(45, 42, 13))[0]
    weeks = rng.sample(range(1, 9), n)
    for i, wk in enumerate(sorted(weeks)):
        out.append((wk, names[i], rng.choice(TROPICAL_COASTS)))
    _CACHE[key] = out
    return out


def _storm_for(year, week, st):
    for wk, name, states in tropical(year):
        if wk == week and st in states:
            return name
    return None


# ═══ The truth: the weather this game will actually have ════════════════════

def truth(game, league=None):
    """Everything about the game's weather, quarter by quarter. Deterministic: the same game
    always gets the same weather, so forecasts can be made from it before it happens."""
    if getattr(game, "wx", None):
        return game.wx
    if league is not None:
        bind(league)
    lg = league or _LG[0]
    year = getattr(lg, "year", 2026) if lg is not None else 2026
    d = game_date(game, lg)
    kick = kick_minutes(game)
    key = ("t", _seed(), year, game.week, game.home.school, game.away.school, kick, d)
    if key in _CACHE:
        return _CACHE[key]
    if indoor(game):
        wx = {"indoor": True, "temp": 72, "kick_temp": 72, "q": [_calm(72)] * 5, "pop": 0, "kind": "indoor",
              "summary": "Indoors", "venue": (_venue(game) or "").split(",")[0], "alt": place(game)[2],
              "delay": None, "storm": None, "surface": 2}
        _CACHE[key] = wx
        return wx
    clim, st, alt, pkey, city = place(game)
    rng = random.Random(f"wx:{_seed()}:{year}:{game.week}:{game.home.school}:{game.away.school}")
    pat = _region_pattern(year, game.week, REGION_OF.get(st, "South"))
    storm = _storm_for(year, game.week, st) if game.week <= 13 else None
    base = _normal_high(clim, d) + pat["temp"] * (0.6 if clim[4] == 2 and clim[1] >= 60 else 1.0)
    kick_temp = base + _diurnal(kick, clim) + rng.gauss(0, 2.0)
    humid = clim[4]
    if clim[1] >= 65:
        kick_temp = max(kick_temp, 58)                    # Florida and Hawai'i don't get cold
    # Precipitation: how likely, and whether it happens.
    wet = clim[2] * pat["wet"] * 0.82
    if kick_temp < 36:
        wet *= 0.8 + clim[5] * 0.45                       # lake effect and upslope snow
    pop = max(0.02, min(0.92, wet))
    if storm:
        pop = 0.93
    wind0 = clim[3] * pat["wind"] * math.exp(rng.gauss(0, 0.28))
    if storm:
        wind0 = max(wind0, rng.uniform(22, 38))
    front_q = pat.get("front")
    axis = random.Random(f"axis:{pkey}").uniform(0, 360)   # which way the field runs
    wdir = rng.uniform(0, 360)
    # ── quarter by quarter ──
    rains = rng.random() < pop
    q_int = [0, 0, 0, 0, 0]
    kind = "clear"
    delay = None
    if rains:
        convective = kick_temp >= 68 and humid >= 1 and not storm and rng.random() < 0.5
        if storm:
            peak = 3
            start, dur = 0, 5
        elif convective:
            peak = rng.choice((2, 3, 3))
            start = rng.choices((0, 1, 2, 3, 4), weights=(20, 25, 25, 18, 12))[0]
            dur = rng.choice((1, 1, 2))
        else:
            peak = rng.choices((1, 2, 3), weights=(45, 40, 15))[0]
            start = front_q if front_q and rng.random() < 0.6 else \
                rng.choices((0, 1, 2, 3, 4), weights=(38, 18, 16, 15, 13))[0]
            dur = rng.choice((1, 2, 3, 4, 5, 5))
        for q in range(5):
            qq = q + 1
            if start <= qq <= start + dur - 1 or (start == 0 and qq <= dur):
                edge = (qq == start or qq == start + dur - 1) and dur >= 3
                q_int[q] = max(1, peak - (1 if edge else 0))
        if start == 0 and q_int[0] == 0:
            q_int[0] = peak
        if convective and rng.random() < 0.5:
            dq = next((i + 1 for i, v in enumerate(q_int[:4]) if v >= 2), None)
            if dq:
                delay = {"q": dq, "clock": rng.randint(90, 780), "mins": rng.choice((30, 35, 45, 50, 60, 75, 90)),
                         "done": False}
        kind = "storms" if (convective or storm) else "rain"
    # Temperatures through the game.
    temps = []
    t = kick_temp
    for q in range(5):
        temps.append(t)
        night = kick + (q + 1) * 50 >= _sunset(d) * 60
        drift = (-2.2 if clim[4] == 0 else -1.6) if night else (0.4 if d.month == 9 else -0.4)
        if front_q and q + 1 == front_q:
            drift -= rng.uniform(6, 12)
        t += drift
    winds, surface = [], _surface(game)
    field_wet, snow_cover = (0.8 if rains and q_int[0] else 0.0), 0.0
    if rng.random() < pop * 0.35 and not q_int[0]:
        field_wet = 0.6                                   # it rained this morning
    quarters = []
    for q in range(5):
        w = wind0 * math.exp(rng.gauss(0, 0.12))
        if front_q and q + 1 >= front_q:
            w *= 1.35
        if storm:
            w = max(w, 20)
        wdir = (wdir + rng.gauss(0, 12)) % 360
        if front_q and q + 1 == front_q:
            wdir = (wdir + rng.uniform(40, 90)) % 360       # the wind swings around behind the front
        temp = temps[q]
        inten = q_int[q]
        ptype = ""
        if inten:
            cold_day = kick_temp <= 44
            ptype = "snow" if temp <= 32 and cold_day else "mix" if temp <= 36 and kick_temp <= 48 else "rain"
        # the field
        if ptype == "snow":
            if surface < 4:
                snow_cover += inten * 0.7
            field_wet += inten * 0.2
        elif inten:
            field_wet += inten * (1.0 if surface == 3 else 0.7)
        drain = {1: 0.45, 2: 0.6, 3: 0.3, 4: 0.55}.get(surface, 0.5)
        field_wet = max(0.0, field_wet - (drain if not inten else drain * 0.3))
        if temp > 35:
            snow_cover = max(0.0, snow_cover - 0.4)
        rel = math.radians(wdir - axis)
        quarters.append({"temp": int(round(temp)), "p": inten, "type": ptype, "wind": int(round(w)),
                         "gust": int(round(w * rng.uniform(1.3, 1.6))), "dir": int(wdir), "along": w * math.cos(rel),
                         "cross": abs(w * math.sin(rel)), "wet": round(field_wet, 2), "snow": round(snow_cover, 2),
                         "surface": surface, "humid": humid})
        winds.append(w)
    q1 = quarters[0]
    if any(x["type"] == "snow" for x in quarters):
        kind = "snow"
    elif any(x["type"] == "mix" for x in quarters) and kind == "rain":
        kind = "mix"
    wx = {"indoor": False, "kick_temp": int(round(kick_temp)), "temp": q1["temp"], "q": quarters,
          "pop": int(round(pop * 100)), "kind": kind, "storm": storm, "front": front_q, "delay": delay,
          "alt": alt, "humid": humid, "state": st, "city": city, "surface": surface, "axis": axis,
          "normal": int(round(_normal_high(clim, d) + _diurnal(kick, clim))), "wind": int(round(sum(winds) / 5)),
          "sky": _sky(rng, pop, q1["p"], kick, d)}
    wx["summary"] = summary(wx)
    _CACHE[key] = wx
    if len(_CACHE) > 6000:
        _CACHE.clear()
    return wx


def _calm(t):
    return {"temp": t, "p": 0, "type": "", "wind": 0, "gust": 0, "dir": 0, "along": 0.0, "cross": 0.0,
            "wet": 0.0, "snow": 0.0, "surface": 2, "humid": 0}


def _sunset(d):
    """Rough sunset hour (Eastern-ish) through the season."""
    days = (d - date(d.year if d.month >= 8 else d.year - 1, 9, 1)).days
    return max(16.8, 19.5 - days * 0.022)


def _sky(rng, pop, p_now, kick, d):
    if p_now:
        return "overcast"
    night = kick / 60 >= _sunset(d)
    if pop >= 0.5:
        return "cloudy"
    if pop >= 0.25:
        return "partly cloudy" if not night else "a few clouds"
    return rng.choice(("clear", "clear skies") if night else ("sunny", "clear", "mostly sunny"))


def _surface(game):
    if not _campus(game) or getattr(game.home, "fcs", False):
        return 2
    try:
        import stadium
        return stadium.parts(game.home).get("surface", 2)
    except Exception:
        return 2


def compass(deg):
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


# ═══ Words ══════════════════════════════════════════════════════════════════

def precip_words(q):
    if not q["p"]:
        return ""
    word = {"snow": "snow", "mix": "sleet", "rain": "rain"}[q["type"]]
    return f"{PRECIP_WORD[q['p']]} {word}".strip()


def field_words(q):
    if q["snow"] >= 1.5:
        return "snow-covered"
    if q["snow"] >= 0.5:
        return "a dusting of snow"
    w = q["wet"]
    if w >= 3.0:
        return "muddy" if q["surface"] == 3 else "sloppy"
    if w >= 1.6:
        return "sloppy" if q["surface"] == 3 else "wet"
    if w >= 0.6:
        return "damp"
    return "dry"


def feels(q):
    t = q["temp"]
    if t >= 80 and q.get("humid", 0) >= 2:
        return t + int((t - 78) * 0.6)
    if t <= 45 and q["wind"] >= 8:
        return int(t - (q["wind"] - 5) * 0.55)
    return t


def summary(wx, q=None):
    """'38° · steady rain · wind NW 18' (a quarter's conditions, or kickoff's)."""
    if wx.get("indoor"):
        return "Indoors · 72°"
    c = wx["q"][q or 0]
    bits = [f"{c['temp']}°"]
    pw = precip_words(c)
    bits.append(pw if pw else wx.get("sky", "clear"))
    if c["wind"] >= 10:
        bits.append(f"wind {compass(c['dir'])} {c['wind']}")
    fl = field_words(c)
    if fl not in ("dry", "damp") and pw:
        bits.append(f"field {fl}")
    return " · ".join(bits)


def label(wx):
    """One or two words for tables: 'Snow', 'Rain', 'Windy', 'Hot', 'Cold', 'Nice'."""
    if wx.get("indoor"):
        return "Indoors"
    if wx.get("storm"):
        return "Tropical storm"
    k = wx.get("kind")
    if k == "snow":
        return "Snow"
    if k == "mix":
        return "Sleet"
    if k == "storms":
        return "Storms"
    if k == "rain":
        return "Rain"
    t = wx["q"][0]["temp"]
    if wx.get("wind", 0) >= 20:
        return "Windy"
    if t >= 90 or feels(wx["q"][0]) >= 93:
        return "Hot"
    if t <= 32:
        return "Frigid"
    if t <= 42:
        return "Cold"
    return "Nice" if 58 <= t <= 80 else "Cool" if t < 58 else "Warm"


def severity(wx):
    """0 (nothing to it) .. 4 (a weather game people will talk about)."""
    if wx.get("indoor"):
        return 0
    qs = wx["q"][:4]
    s = 0.0
    s += max(x["p"] for x in qs) * 0.8 + sum(1 for x in qs if x["p"]) * 0.2
    s += 1.0 if any(x["type"] == "snow" for x in qs) else 0
    s += max(0, max(x["wind"] for x in qs) - 12) / 8
    t = min(x["temp"] for x in qs)
    s += max(0, 35 - t) / 10 + max(0, max(x["temp"] for x in qs) - 90) / 6
    if wx.get("storm"):
        s += 1.5
    if wx.get("delay"):
        s += 0.5
    return int(max(0, min(4, round(s))))


def headline(wx):
    """A sentence about the day: what a fan would say walking into the stadium."""
    if wx.get("indoor"):
        return f"Under the roof at {wx.get('venue', 'the dome')}. No weather."
    q = wx["q"]
    k = wx["kind"]
    t = q[0]["temp"]
    if wx.get("storm"):
        return f"Tropical Storm {wx['storm']} came ashore — wind and rain all game long."
    if k == "snow":
        return "A snow game." if q[0]["type"] == "snow" else "It turned to snow during the game."
    if k == "storms":
        return "Thunderstorms rolled through" + (" — and brought a lightning delay." if wx.get("delay") else ".")
    if k in ("rain", "mix"):
        if all(x["p"] for x in q[:4]):
            return "It rained from start to finish."
        if q[0]["p"]:
            return "Wet at kickoff, then it cleared."
        return "The rain came in during the game."
    if wx.get("front"):
        return "A cold front blew through mid-game — the wind picked up and the temperature fell."
    if max(x["wind"] for x in q[:4]) >= 20:
        return "A windy day — kickers and deep balls had to fight it."
    if t >= 90:
        return "Hot. Brutally hot."
    if t <= 32:
        return "Bitter cold."
    if t <= 42:
        return "A cold one."
    return "Beautiful football weather."


# ═══ Forecasts ══════════════════════════════════════════════════════════════

def forecast(game, league=None, lead=None):
    """What the forecasters say, {lead} weeks before the game (0 = this week).
    Honest but uncertain: the farther out, the closer it is to 'normal for the date'."""
    lg = league or _LG[0]
    if lead is None:
        lead = max(0, game.week - (getattr(lg, "week", 0) + 1)) if lg is not None else 0
    if getattr(game, "kick", None) is None and lg is not None and game.week == getattr(lg, "week", -9) + 1:
        ensure_slots(lg, game.week)                   # the TV slots are out: the forecast is for the real kickoff
    wx = truth(game, lg)
    if wx.get("indoor"):
        return {"indoor": True, "lead": lead, "temp": 72, "lo": 72, "hi": 72, "pop": 0, "ptype": "", "wind": (0, 0),
                "dir": "", "sky": "indoors", "headline": "Indoors — no weather", "text": "Indoors · 72°",
                "severity": 0, "confidence": "certain", "label": "Indoors"}
    year = getattr(lg, "year", 2026) if lg is not None else 2026
    rng = random.Random(f"wxf:{_seed()}:{year}:{game.week}:{game.home.school}:{game.away.school}:{min(lead, 3)}")
    w_true = (0.9, 0.62, 0.35, 0.12)[min(lead, 3)]
    sd_t = (2.0, 4.0, 6.0, 7.0)[min(lead, 3)]
    normal = wx["normal"]
    temp = int(round(normal + (wx["kick_temp"] - normal) * w_true + rng.gauss(0, sd_t * 0.6)))
    clim = place(game)[0]
    pop_clim = clim[2] * (1.2 if temp < 36 else 1.0)
    pop = pop_clim + (wx["pop"] / 100 - pop_clim) * w_true + rng.gauss(0, 0.05 + 0.04 * min(lead, 3))
    if wx.get("storm") and lead <= 1:
        pop = max(pop, 0.8)
    pop = int(max(0, min(95, round(pop * 100 / 5) * 5)))
    spread = (3, 5, 7, 9)[min(lead, 3)]
    wind = wx["wind"] * w_true + clim[3] * (1 - w_true) + rng.gauss(0, 2)
    wlo, whi = max(0, int(wind - 3)), int(wind + 5 + (8 if wx.get("front") and lead <= 1 else 0))
    ptype = "snow" if temp <= 32 else "mix" if temp <= 36 else ("storms" if temp >= 70 and clim[4] >= 1 else "rain")
    night = kick_minutes(game) / 60 >= _sunset(game_date(game, lg))
    sky = ("clear" if night else "sunny") if pop < 15 else "partly cloudy" if pop < 35 else "cloudy"
    bits = []
    if pop >= 60:
        bits.append({"snow": "Snow likely", "mix": "Sleet likely", "storms": "Thunderstorms likely"}.get(ptype, "Rain likely"))
    elif pop >= 30:
        bits.append({"snow": "Chance of snow", "mix": "Chance of sleet", "storms": "Scattered storms"}.get(ptype,
                                                                                                     "Chance of rain"))
    elif pop >= 15:
        bits.append({"snow": "Flurries possible", "storms": "A stray storm"}.get(ptype, "A stray shower"))
    else:
        bits.append("Dry")
    if whi >= 22:
        bits.append("windy")
    elif whi >= 15:
        bits.append("breezy")
    if temp >= 90:
        bits.append("hot")
    elif temp <= 30:
        bits.append("bitter cold")
    elif temp <= 40:
        bits.append("cold")
    if wx.get("storm") and lead <= 1:
        bits = [f"Tropical Storm {wx['storm']} on the way"]
    elif wx.get("front") and lead == 0:
        bits.append("a front moves through")
    head = ", ".join(bits)
    head = head[:1].upper() + head[1:]
    conf = ("high", "fair", "low", "climate outlook")[min(lead, 3)]
    fake = {"indoor": False, "q": [{"temp": temp, "p": 2 if pop >= 50 else 0, "type": "snow" if ptype == "snow" else
                                    "rain", "wind": whi, "gust": whi, "dir": 0, "along": 0, "cross": 0, "wet": 0,
                                    "snow": 0, "surface": 2, "humid": clim[4]}] * 4, "kind":
            ("snow" if ptype == "snow" else "rain") if pop >= 50 else "clear", "wind": whi, "storm":
            wx.get("storm") if lead <= 1 else None, "delay": None}
    return {"indoor": False, "lead": lead, "temp": temp, "lo": temp - spread, "hi": temp + spread, "pop": pop,
            "ptype": ptype, "wind": (wlo, whi), "dir": compass(wx["q"][0]["dir"]) if lead <= 1 else "",
            "sky": sky, "headline": head, "severity": severity(fake), "confidence": conf,
            "text": f"{temp}° · {pop}% {ptype if ptype != 'mix' else 'sleet'} · wind {wlo}-{whi}",
            "label": label(fake) if lead <= 2 else "Outlook"}


def ensure_slots(league, week):
    """Kickoff times for the coming week (the same ones the week will use when it starts)."""
    games = league.schedule.get(week, [])
    if not games or all(getattr(g, "kick", None) is not None for g in games):
        return
    try:
        import broadcast
        from season import matchup_order
        broadcast.assign(league, week, matchup_order(games))
    except Exception:
        pass


def short(game, league=None):
    """A few words for a schedule line: '41° rain 60%' before, '28° snow' after."""
    if getattr(game, "home_score", None) is not None:
        wx = getattr(game, "wx", None)
        if not wx:
            return ""
        if wx.get("indoor"):
            return "indoors"
        lab = label(wx).lower()
        return f"{wx['q'][0]['temp']}° {lab}"
    lg = league or _LG[0]
    lead = max(0, game.week - (getattr(lg, "week", 0) + 1)) if lg is not None else 0
    if lead > 2:
        return ""
    f = forecast(game, lg, lead)
    if f["indoor"]:
        return "indoors"
    p = f" {f['pop']}%" if f["pop"] >= 20 else ""
    w = {"snow": "snow", "mix": "sleet", "storms": "storms", "rain": "rain"}[f["ptype"]] if f["pop"] >= 20 else \
        ("windy" if f["wind"][1] >= 20 else f["sky"].replace("partly cloudy", "p.cloudy"))
    return f"fcst {f['temp']}° {w}{p}"


# ═══ Attaching to a game ════════════════════════════════════════════════════

def attach(league, game):
    """At kickoff: the weather is what it is. Stored on the game for the box score and the book."""
    bind(league)
    if getattr(game, "wx", None):
        return game.wx
    wx = truth(game, league)
    game.wx = dict(wx)
    game.wx["q"] = [dict(q) for q in wx["q"]]
    if wx.get("delay"):
        game.wx["delay"] = dict(wx["delay"])
    try:
        f = forecast(game, league, 0)
        game.wx["forecast"] = f["headline"] + f" ({f['pop']}%)" if not f["indoor"] else ""
    except Exception:
        pass
    return game.wx


def record(league, game):
    """The weather book: every team's games in real weather."""
    wx = getattr(game, "wx", None)
    if not wx or wx.get("indoor") or not game.played:
        return
    sev = severity(wx)
    t = min(x["temp"] for x in wx["q"][:4])
    hot = max(x["temp"] for x in wx["q"][:4])
    if sev < 2 and 36 < t and hot < 92:
        return
    book = league.__dict__.setdefault("wx_book", {})
    for team in (game.home, game.away):
        if getattr(team, "fcs", False):
            continue
        opp = game.opponent_of(team)
        won = game.winner is team
        book.setdefault(team.school, []).append(
            (league.year, game.week, opp.school, "vs" if game.home is team or game.neutral else "at", won,
             game.score_for(team), game.score_for(opp), label(wx), t, hot, wx.get("storm"), sev))
        del book[team.school][:-60]


def turnout_hit(wx, canopy=0):
    """How much of the usual crowd the weather keeps home (0 .. ~0.15). A roof over the stands helps."""
    c = wx["q"][0]
    rain = (c["p"] + (1 if wx.get("storm") else 0)) * 0.028 * (1 - 0.35 * canopy)
    cold = max(0, 36 - feels(c)) * 0.004
    heat = max(0, feels(c) - 94) * 0.004
    return min(0.18, rain + cold + heat)


# ═══ On the field ═══════════════════════════════════════════════════════════

def now(sim):
    """This quarter's conditions (or None indoors / no weather)."""
    wx = getattr(sim, "wx", None)
    if not wx or wx.get("indoor"):
        return None
    return wx["q"][min(4, max(1, sim.quarter)) - 1]


def _prep(sim, team):
    """Weather prep this week: half the effect."""
    wp = getattr(team, "week_prep", None) or {}
    return 0.5 if wp.get("focus") == "weather" else 1.0


def heading(sim, team):
    """+1 if the team is moving with the wind's along-field direction this quarter, -1 against.
    Teams switch ends every quarter; the home team starts toward the 'far' goal in Q1 and Q3."""
    q = sim.quarter
    home_far = q in (1, 3) or (q > 4 and q % 2 == 1)
    return 1 if (team is sim.home) == home_far else -1


def tail(sim, team):
    """Along-field wind in mph for the team (positive = at its back)."""
    c = now(sim)
    if c is None:
        return 0.0
    return c["along"] * heading(sim, team)


def slick(c):
    return min(1.2, c["wet"] * 0.2 + c["snow"] * 0.3)


def pass_penalty(sim, team, depth):
    """(accuracy points off, catch points off, drop multiplier) for a throw of this depth."""
    c = now(sim)
    if c is None:
        return 0.0, 0.0, 1.0
    p = c["p"]
    rain = p if c["type"] == "rain" else p * 0.8 if c["type"] == "mix" else 0
    snow = p if c["type"] == "snow" else p * 0.4 if c["type"] == "mix" else 0
    band = 0.4 if depth <= 7 else 0.8 if depth <= 17 else 1.5
    acc = rain * 2.2 + snow * 2.8 + max(0, c["wind"] - 8) * 0.30 * band
    t = tail(sim, team)
    if depth > 17 and t < 0:
        acc += -t * 0.15
    elif depth > 17 and t > 0:
        acc -= t * 0.05
    if c["temp"] < 30:
        acc += (30 - c["temp"]) * 0.08
    catch = rain * 2.5 + snow * 2.0 + max(0, 35 - c["temp"]) * 0.15
    drop = 1 + rain * 0.25 + snow * 0.2
    k = _prep(sim, team)
    return acc * k, catch * k, 1 + (drop - 1) * k


def fumble_mult(sim, team):
    c = now(sim)
    if c is None:
        return 1.0
    wetness = c["p"] * (0.28 if c["type"] == "rain" else 0.2 if c["type"] == "snow" else 0.3)
    m = wetness + slick(c) * 0.3 + max(0, 32 - c["temp"]) * 0.012
    return 1 + m * _prep(sim, team)


def muff_mult(sim, team):
    c = now(sim)
    if c is None:
        return 1.0
    m = c["p"] * 0.35 + c["wind"] / 40 + max(0, 30 - c["temp"]) * 0.01
    return 1 + m * _prep(sim, team)


def footing(sim):
    """(run-play modifier, speed-edge factor): a sloppy field takes speed out of the game."""
    c = now(sim)
    if c is None:
        return 0.0, 1.0
    s = slick(c)
    return -s * 0.22, max(0.45, 1 - s * 0.5)


def fg_mods(sim, team):
    """(range in yards +/-, accuracy logit +/-) for this team's kicker right now."""
    c = now(sim)
    wx = getattr(sim, "wx", None) or {}
    alt = wx.get("alt", 0) or 0
    rng_d = max(0, alt - 1000) / 1000 * 1.2
    if c is None:
        return rng_d, 0.0
    t = tail(sim, team)
    rng_d += t * 0.35 if t > 0 else t * 0.55
    rng_d -= max(0, 55 - c["temp"]) * 0.08
    snow = c["p"] if c["type"] == "snow" else 0
    rain = c["p"] if c["type"] in ("rain", "mix") else 0
    rng_d -= rain * 1.0 + snow * 1.5
    acc = -(c["cross"] * 0.035) - rain * 0.12 - snow * 0.2 - slick(c) * 0.15
    k = _prep(sim, team)
    return rng_d if rng_d > 0 else rng_d * k, acc * k


def punt_mod(sim, team):
    """(yards +/-, extra spread)."""
    c = now(sim)
    wx = getattr(sim, "wx", None) or {}
    d = max(0, (wx.get("alt", 0) or 0) - 1000) / 1000 * 0.9
    if c is None:
        return d, 0.0
    d += tail(sim, team) * 0.45 - c["p"] * 0.8 - max(0, 55 - c["temp"]) * 0.05
    return d, max(0, c["wind"] - 10) * 0.18


def kickoff_mod(sim, team):
    """Touchback logit +/-."""
    c = now(sim)
    wx = getattr(sim, "wx", None) or {}
    d = max(0, (wx.get("alt", 0) or 0) - 1000) / 1000 * 0.25
    if c is None:
        return d
    return d + tail(sim, team) * 0.05 - max(0, 55 - c["temp"]) * 0.02 - c["p"] * 0.1


def call_lean(sim, team):
    """(run probability +, deep-shot weight x): coaches adjust to the day."""
    c = now(sim)
    if c is None:
        return 0.0, 1.0
    rain = c["p"] if c["type"] in ("rain", "mix") else 0
    snow = c["p"] if c["type"] == "snow" else 0
    run = min(0.12, rain * 0.03 + snow * 0.035 + max(0, c["wind"] - 15) * 0.004 + slick(c) * 0.02)
    deep = 1 - min(0.5, rain * 0.08 + snow * 0.1 + max(0, c["wind"] - 12) * 0.02)
    t = tail(sim, team)
    if t >= 10:
        deep = min(1.15, deep + 0.15)                   # with a gale at your back, take the shot
    return run, deep


def form_shift(sim, team, second_half=False):
    """Acclimation: warm-weather teams in the cold, cool-weather teams in the heat, sea-level
    teams at altitude. Returns a form change (negative hurts)."""
    wx = getattr(sim, "wx", None)
    if not wx or wx.get("indoor") or getattr(team, "fcs", False):
        return 0.0
    c = wx["q"][2 if second_half else 0]
    home_clim = team_climate(team)
    d = 0.0
    fl = feels(c)
    if not second_half and c["temp"] <= 38 and home_clim[1] >= 56:
        d -= min(0.8, (38 - c["temp"]) * 0.035 + (home_clim[1] - 56) * 0.02)
    if not second_half and c["temp"] <= 38 and "Dome" in (team.stadium or ""):
        d -= 0.2
    if second_half and fl >= 90 and home_clim[0] < 84:
        d -= min(0.8, (fl - 88) * 0.05 + (84 - home_clim[0]) * 0.02)
    alt = wx.get("alt", 0) or 0
    if second_half and alt >= 4500 and team_altitude(team) < 2000 and team is not sim.home:
        d -= min(0.6, (alt - 4000) / 5000)
    return d * _prep(sim, team)


# ═══ The week: what the staff says ══════════════════════════════════════════

def staff_note(league, team, game):
    """A line from the staff about Saturday's weather, or ''."""
    f = forecast(game, league, 0)
    if f["indoor"]:
        return ""
    bits = []
    if f["pop"] >= 50 and f["ptype"] in ("rain", "storms"):
        bits.append("wet balls in practice all week")
    if f["ptype"] == "snow" and f["pop"] >= 40:
        bits.append("it might snow — get the ball security drills in")
    if f["wind"][1] >= 20:
        bits.append("the wind will be a factor in the kicking game")
    if f["temp"] <= 35 and team_climate(team)[1] >= 56:
        bits.append("our guys aren't used to the cold")
    if f["temp"] >= 90 and team_climate(team)[0] < 84:
        bits.append("the heat will be a factor in the second half")
    wx = truth(game, league)
    if (wx.get("alt", 0) or 0) >= 4500 and team_altitude(team) < 2000 and game.home is not team:
        bits.append("the altitude will get to us late")
    return ("Staff: " + "; ".join(bits) + ".") if bits else ""


def wants_prep(league, team, game):
    f = forecast(game, league, 0)
    return (not f["indoor"]) and (f["severity"] >= 2 or (f["pop"] >= 55 and f["ptype"] != "rain") or f["wind"][1] >= 24)
