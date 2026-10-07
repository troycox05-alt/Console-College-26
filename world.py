"""
world.py — The handful of names the game's rules care about.

Most of what makes a world (teams, coaches, rivalries, bowls, lore) lives in the
data tables, and a universe file (universe.py) can replace any of them. A few
rules need to know which conferences are the Power leagues or which independent
is the national brand; they read those names from here, at the moment they need
them, so a universe can rename them too.

TERMS is display-only: a universe can ask for a word the game prints to be shown
as another (the built-in world has none). See universe.py.
"""

POWER = ("SCC", "Continental", "Seaboard", "Meridian")    # the four Power conferences, richest first
BIG_TWO = ("SCC", "Continental")                          # the two that pay the most and get the best TV slots
NIGHT_CONF = "SCC"                                         # owns Saturday night on the big network
WEEKNIGHT_CONF = "Lake Country"                            # Tuesday/Wednesday games in November
WEST_COAST_CONF = "Golden West"                            # small TV bump for the late window
FLAGSHIP_INDEPENDENT = "South Bend"                        # the independent that's treated like a Power program
MAYO_BOWL = "Grandma Pearl's Mayo Bowl"                    # the bowl that dumps mayonnaise on the winning coach
SHOW_NAME = "Campus Countdown"                             # the Saturday-morning show
UNIVERSE_NAME = "Console College"                          # shown on the title and settings screens

TERMS = {}                                                 # display word -> word shown instead (universe files)


def is_power(team):
    """A Power-conference program, or the flagship independent."""
    return team.conference in POWER or team.school == FLAGSHIP_INDEPENDENT
