"""
recruiting_data.py — The static tables recruiting runs on.

Where players come from (states and how much talent each produces), where
every program sits on the map, what recruits actually care about, the
personality types that decide how they behave when things go wrong, and what
each recruiting action costs a staff in hours.

No logic here. Just the furniture.
"""

# ═══ Geography ══════════════════════════════════════════════════════════════
# state -> (name, region)
STATES = {
    "AL": ("Alabama", "Southeast"), "AR": ("Arkansas", "South Central"), "AZ": ("Arizona", "Mountain"),
    "CA": ("California", "West"), "CO": ("Colorado", "Mountain"), "CT": ("Connecticut", "Northeast"),
    "DE": ("Delaware", "Northeast"), "FL": ("Florida", "Southeast"), "GA": ("Georgia", "Southeast"),
    "HI": ("Hawai'i", "West"), "IA": ("Iowa", "Midwest"), "ID": ("Idaho", "Mountain"),
    "IL": ("Illinois", "Midwest"), "IN": ("Indiana", "Midwest"), "KS": ("Kansas", "Midwest"),
    "KY": ("Kentucky", "Southeast"), "LA": ("Louisiana", "South Central"), "MA": ("Massachusetts", "Northeast"),
    "MD": ("Maryland", "Northeast"), "ME": ("Maine", "Northeast"), "MI": ("Michigan", "Midwest"),
    "MN": ("Minnesota", "Midwest"), "MO": ("Missouri", "Midwest"), "MS": ("Mississippi", "Southeast"),
    "MT": ("Montana", "Mountain"), "NC": ("North Carolina", "Southeast"), "ND": ("North Dakota", "Midwest"),
    "NE": ("Nebraska", "Midwest"), "NH": ("New Hampshire", "Northeast"), "NJ": ("New Jersey", "Northeast"),
    "NM": ("New Mexico", "Mountain"), "NV": ("Nevada", "West"), "NY": ("New York", "Northeast"),
    "OH": ("Ohio", "Midwest"), "OK": ("Oklahoma", "South Central"), "OR": ("Oregon", "West"),
    "PA": ("Pennsylvania", "Northeast"), "RI": ("Rhode Island", "Northeast"), "SC": ("South Carolina", "Southeast"),
    "SD": ("South Dakota", "Midwest"), "TN": ("Tennessee", "Southeast"), "TX": ("Texas", "South Central"),
    "UT": ("Utah", "Mountain"), "VA": ("Virginia", "Southeast"), "VT": ("Vermont", "Northeast"),
    "WA": ("Washington", "West"), "WI": ("Wisconsin", "Midwest"), "WV": ("West Virginia", "Northeast"),
    "WY": ("Wyoming", "Mountain"),
}

REGION_NEIGHBORS = {
    "Southeast": {"South Central", "Northeast", "Midwest"},
    "South Central": {"Southeast", "Midwest", "Mountain"},
    "Midwest": {"Northeast", "Southeast", "South Central", "Mountain"},
    "Northeast": {"Southeast", "Midwest"},
    "Mountain": {"West", "Midwest", "South Central"},
    "West": {"Mountain"},
}

# Roughly how much high school football talent each state produces.
TALENT = {
    "TX": 3.0, "FL": 2.9, "CA": 2.8, "GA": 2.5, "OH": 1.7, "PA": 1.3, "NC": 1.2, "AL": 1.2, "LA": 1.2,
    "NJ": 1.0, "VA": 1.0, "MI": 1.0, "IL": 1.0, "TN": 0.9, "SC": 0.9, "MD": 0.8, "MS": 0.7, "AZ": 0.7,
    "WA": 0.7, "MO": 0.6, "IN": 0.6, "OK": 0.6, "CO": 0.5, "UT": 0.5, "NY": 0.5, "WI": 0.5, "MN": 0.4,
    "KY": 0.4, "AR": 0.4, "IA": 0.4, "NV": 0.35, "KS": 0.3, "CT": 0.25, "NE": 0.25, "OR": 0.25,
    "MA": 0.25, "WV": 0.2, "NM": 0.2, "HI": 0.2, "DE": 0.15, "ID": 0.15, "RI": 0.1, "NH": 0.1,
    "ME": 0.1, "MT": 0.1, "SD": 0.1, "ND": 0.1, "WY": 0.1, "VT": 0.05,
}

# Every FBS program's home state.
TEAM_STATES = {
    "Alabama": "AL", "Arkansas": "AR", "East Alabama": "AL", "Florida": "FL", "Georgia": "GA", "Kentucky": "KY",
    "Bayou State": "LA", "Mississippi State": "MS", "Missouri": "MO", "Oklahoma": "OK", "Mississippi": "MS",
    "South Carolina": "SC", "Tennessee": "TN", "Texas": "TX", "Brazos": "TX", "Nashville": "TN",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Maryland": "MD", "Michigan": "MI",
    "Michigan State": "MI", "Minnesota": "MN", "Nebraska": "NE", "Lakeshore": "IL", "Ohio State": "OH",
    "Oregon": "OR", "Pennsylvania": "PA", "Tippecanoe": "IN", "New Jersey": "NJ", "Los Angeles": "CA", "Southern California": "CA",
    "Washington": "WA", "Wisconsin": "WI", "Boston": "MA", "California": "CA", "Upcountry": "SC",
    "Durham": "NC", "Florida State": "FL", "Atlanta": "GA", "Louisville": "KY", "Miami": "FL",
    "NC State": "NC", "North Carolina": "NC", "Pittsburgh": "PA", "Dallas": "TX", "Palo Alto": "CA",
    "Syracuse": "NY", "Virginia": "VA", "Blacksburg": "VA", "Winston-Salem": "NC", "Arizona": "AZ",
    "Arizona State": "AZ", "Waco": "TX", "Provo": "UT", "Cincinnati": "OH", "Colorado": "CO",
    "Houston": "TX", "Iowa State": "IA", "Kansas": "KS", "Kansas State": "KS", "Oklahoma State": "OK",
    "Fort Worth": "TX", "Lubbock": "TX", "Orlando": "FL", "Utah": "UT", "West Virginia": "WV", "Hudson": "NY",
    "Charlotte": "NC", "East Carolina": "NC", "Florida Atlantic": "FL", "Memphis": "TN", "Chesapeake": "MD",
    "North Texas": "TX", "Montrose": "TX", "South Florida": "FL", "Philadelphia": "PA", "New Orleans": "LA",
    "Tulsa": "OK", "Birmingham": "AL", "San Antonio": "TX", "Appalachian State": "NC", "Grand Strand": "SC",
    "Georgia Southern": "GA", "Georgia State": "GA", "Shenandoah": "VA", "Huntington": "WV",
    "Norfolk": "VA", "Arkansas State": "AR", "Louisiana": "LA", "Ruston": "LA", "Monroe": "LA",
    "South Alabama": "AL", "Southern Miss": "MS", "Troy": "AL", "Akron": "OH", "Muncie": "IN",
    "Bowling Green": "OH", "Buffalo": "NY", "Central Michigan": "MI", "Eastern Michigan": "MI",
    "Kent State": "OH", "Miami (OH)": "OH", "Ohio": "OH", "Sacramento State": "CA", "Toledo": "OH",
    "Massachusetts": "MA", "Western Michigan": "MI", "Delaware": "DE", "Biscayne": "FL", "Jacksonville State": "AL",
    "Kennesaw State": "GA", "Lynchburg": "VA", "Middle Tennessee": "TN", "Missouri State": "MO",
    "New Mexico State": "NM", "Huntsville": "TX", "Western Kentucky": "KY", "Boise State": "ID",
    "Colorado State": "CO", "Fresno State": "CA", "Oregon State": "OR", "San Diego State": "CA",
    "Texas State": "TX", "Utah State": "UT", "Washington State": "WA", "Front Range": "CO",
    "Hawai'i": "HI", "Nevada": "NV", "New Mexico": "NM", "North Dakota State": "ND",
    "Northern Illinois": "IL", "San Jose State": "CA", "Las Vegas": "NV", "El Paso": "TX", "Wyoming": "WY",
    "South Bend": "IN", "Connecticut": "CT",
}

# ═══ What recruits want ═════════════════════════════════════════════════════
PRIORITIES = ("playing_time", "development", "winning", "scheme_fit", "academics",
              "facilities", "proximity", "tradition", "campus", "relationship")

PRIORITY_LABELS = {
    "playing_time": "Early playing time", "development": "Develops pros", "winning": "Winning now",
    "scheme_fit": "Fits his game", "academics": "Academics", "facilities": "Facilities",
    "proximity": "Close to home", "tradition": "Tradition", "campus": "Campus life",
    "relationship": "Trusts the staff",
}

# How often each shows up as something a recruit cares about.
PRIORITY_WEIGHTS = {
    "playing_time": 20, "development": 16, "winning": 16, "scheme_fit": 10, "relationship": 11,
    "proximity": 10, "facilities": 6, "tradition": 5, "academics": 4, "campus": 2,
}

PERSONALITIES = {
    "loyal":        dict(decommit=0.35, decay=0.97, result_swing=0.6, commit_bias=-2, label="Loyal"),
    "front_runner": dict(decommit=1.7, decay=0.93, result_swing=1.8, commit_bias=2, label="Front-runner"),
    "showman":      dict(decommit=1.4, decay=0.94, result_swing=1.2, commit_bias=6, label="Showman"),
    "homebody":     dict(decommit=0.7, decay=0.95, result_swing=0.8, commit_bias=-3, label="Homebody"),
    "quiet":        dict(decommit=0.6, decay=0.95, result_swing=0.8, commit_bias=0, label="Quiet"),
    "family_first": dict(decommit=0.8, decay=0.95, result_swing=0.9, commit_bias=-1, label="Family-first"),
}

# ═══ What a staff can do with its week ══════════════════════════════════════
# key -> (label, hour cost, base interest effect, relationship gain, scouting gain)
ACTIONS = {
    "evaluate":       ("Evaluate film", 2, 0.0, 0, 1),
    "contact":        ("Call and text", 1, 4.0, 1, 0),
    "offer":          ("Extend an offer", 3, 9.0, 3, 0),
    "position_coach": ("Send the position coach", 4, 7.0, 5, 1),
    "campus_visit":   ("Host a campus visit", 6, 16.0, 6, 1),
    "in_home":        ("In-home visit", 8, 18.0, 10, 0),
    "close":          ("Push for a commitment", 4, 12.0, 4, 0),
}

CLASS_SIZE = 25
SCHOLARSHIP_CAP = 85
NATIONAL_POOL = 2450          # more prospects than FBS scholarships, as in life          # prospects generated per cycle
OFFER_CEILING = 45            # interest can't pass this without an offer
INTEREST_DECAY = 0.972
