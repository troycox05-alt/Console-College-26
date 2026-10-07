"""
Console College — an immersion-first college football simulation.

Run:  python main.py
"""
import sys

if sys.version_info < (3, 8):
    sys.exit("Console College needs Python 3.8 or newer.")

from league import League
import saves
from screens import main_menu
from ui import C, init_console, paint, pause


def new_world(custom=None, player_db=None, world_rules=None):
    import title
    import settings
    import universe
    for msg in universe.apply(settings.load().get("universe", universe.DEFAULT)):   # the universe new worlds use
        print(paint(f"   {msg}", C.BYELLOW))
    league = League(year=2026, progress=title.building_screen(), custom=custom)   # four-season history sim finishes here
    league.universe = universe.current()
    import world_rules as _world_rules
    _world_rules.install(league, world_rules)
    # Custom real-player databases belong to the world the user actually inherits.
    # Apply them only AFTER the 2022-25 burn-in so imported players cannot graduate,
    # transfer or be drafted during the history simulation.
    if player_db:
        try:
            import player_database
            imported, warnings = player_database.apply(league, player_db)
            import depth
            depth.preseason(league)
            print(paint(f"\n   Player database: imported {len(imported)} player{'s' if len(imported) != 1 else ''} after the four-season history simulation.", C.BGREEN, C.BOLD))
            for w in warnings[:8]:
                print(paint(f"   · {w}", C.BYELLOW))
            if len(warnings) > 8:
                print(paint(f"   · …and {len(warnings)-8} more import notes.", C.GRAY))
            pause()
        except Exception as e:
            print(paint(f"\n   Player database import failed: {e}", C.BRED, C.BOLD))
            print(paint("   The generated world is still intact.", C.GRAY))
            pause()
    title.world_ready(league)
    problems = league.validate()
    if problems:
        print(paint("\n  Data check found problems:", C.BRED, C.BOLD))
        for msg in problems:
            print(paint(f"   • {msg}", C.BRED))
        pause()
    return league


def main():
    init_console()
    import settings
    import universe
    universe.apply(settings.load().get("universe", universe.DEFAULT))
    import screen_copy
    screen_copy.install()                            # records the screen; copies it when "Auto copy output" is on
    import theme
    theme.init()
    import title
    try:
        while True:
            action, league = title.main_menu_screen()  # continue / new / load / settings / manual / quit
            if action == "quit":
                break
            if action == "online":
                from netplay import lobby
                lobby.run()                                # host or join; back here when you leave
                continue
            if action == "new":
                import career
                mode = career.pick_mode()              # before the world is built: backing out is free
                if mode is None:
                    continue
                rules = career.customize_universe()
                if rules is None:
                    continue
                import team_builder
                from ui import ask as _ask
                n = len(__import__("custom_teams").list_files())
                files = f" ({n} team file{'s' if n != 1 else ''} ready)" if n else ""
                custom = None
                player_db = None
                while True:
                    extra = f"   Player DB: {player_db}\n" if player_db else ""
                    pick = _ask(paint(f"\n{extra}   [Enter] build the world   [C] add custom programs{files}   [P] choose custom player database:", C.BYELLOW)).strip().lower()
                    if pick == "c":
                        custom = team_builder.new_world_setup()
                        if custom is None:
                            continue
                        continue
                    if pick == "p":
                        import player_database
                        path = player_database.choose_path()
                        if path:
                            player_db = path
                        continue
                    break
                league = new_world(custom, player_db=player_db, world_rules=rules)
                career.start_mode(league, mode)
                import guide
                guide.start(league)                      # the guided first week (Settings -> [G])
                saves.autosave(league)                   # half a minute of world-building, kept
            import commissioner
            if commissioner.active(league):            # Commissioner Mode: the desk, not the dashboard
                import commissioner_desk
                if commissioner_desk.desk(league) != "menu":
                    break
                continue
            if main_menu(league) != "menu":            # the dashboard, until you leave
                break
        title.goodbye()
    except (KeyboardInterrupt, EOFError):
        print(paint("\n\n  See you on Saturday.\n", C.BYELLOW))


if __name__ == "__main__":
    main()
