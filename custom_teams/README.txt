CUSTOM PROGRAMS — team files

Each .json file here is one program: identity, stadium, ratings, money, coaching staff, AD,
rival and trophy, lines for the broadcast booth, the tailgate dish, and (optionally) a whole
roster. EXAMPLE_sacramento_valley.json shows every field.

Use them:
  New world    Main menu -> New game -> pick a mode -> [C] add custom programs first
  In a save    Any team page -> [J] team builder -> [L] load a file over that program

Make them:
  Export any program: team page -> [J] -> [X] (roster and all), then edit the file.
  Or build one in the game: [J] -> [N], or [N] on the new-world custom programs screen.

Leave "roster" out (or null) and the program recruits and develops its own roster, matched
to its offense and defense ratings. Add "replaces": "Kent State" to take an existing program's
place (its conference, schedule slot, rivals and trophies); leave it out to join the
conference as a new program.

Anything missing is filled in and anything out of range is pulled back into range; the game
tells you what it changed. Manual chapter 31 has the details.
