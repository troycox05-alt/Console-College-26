"""
booth_banter.py — What the booth talks about when it isn't calling a play.

Each entry is a short exchange: a list of (speaker, line) pairs, "P" for the
play-by-play voice and "A" for the analyst. The narrator fills in:
  {P} {A}            the two broadcasters' last names
  {home} {away}      school names, {hnick} {anick} nicknames
  {stadium}          where the game is, {state} the home state
  {month}            the month the game is played in
  {hcoach} {acoach}  head coaches

Nothing here changes the game. It's the stuff that fills a broadcast between
snaps: food, travel, weather, old stories, the sport itself.
"""

# Off-topic and loosely-related conversation.
BANTER = [
    [("P", "{A}, I saw you in the press box dining room before the game. Be honest — how many hot dogs?"),
     ("A", "Two. And a brownie. It's a long broadcast, {P}. You have to fuel up."),
     ("P", "Professional preparation.")],
    [("A", "I'll tell you what, the tailgates outside {stadium} this morning were something else."),
     ("P", "You make it around the lots?"),
     ("A", "Somebody handed me a plate of ribs before I could say no. I didn't say no.")],
    [("P", "It's {month} football, {A}. Is there anything better?"),
     ("A", "Not a thing. I've been doing this a long time and I still get chills walking into a stadium like this.")],
    [("A", "You know what I miss about playing? The bus ride to the stadium. Nobody talks. Everybody's locked in."),
     ("P", "What'd you listen to?"),
     ("A", "Same album every week for four years. I'm not telling you which one."),
     ("P", "We'll find out.")],
    [("P", "The {home} band has been fantastic today."),
     ("A", "They're always good here. That drumline at halftime is going to be worth staying in your seat for.")],
    [("A", "I got a text from my mom at the start of the second quarter. She wants me to stop saying 'physicality.'"),
     ("P", "Is she going to get her wish?"),
     ("A", "No. It's a very physical game.")],
    [("P", "Quick reminder, folks — our producer tells me the coffee in the booth has run out."),
     ("A", "That explains a lot about the last few minutes."),
     ("P", "We'll soldier on.")],
    [("A", "I walked past the {away} locker room before the game. Music was loud. They're loose."),
     ("P", "Is that a good sign or a bad sign?"),
     ("A", "Depends who you ask. Young teams play better loose. Veteran teams play better quiet.")],
    [("P", "{A}, you coached against a lot of these staffs. Who's the best pregame speech you ever heard?"),
     ("A", "Honestly? A backup quarterback who never played a snap. Stood up the night before a rivalry game and "
           "had the whole room crying. Best one I ever heard.")],
    [("A", "You know the hardest part of this job? Not yelling when something great happens."),
     ("P", "You yell plenty."),
     ("A", "I'm working on it.")],
    [("P", "The flyover before kickoff today was spectacular."),
     ("A", "Those pilots were right over the top of us. I felt it in my chest.")],
    [("A", "One thing I'll never get used to — how young these kids are. Half of them were in high school two "
           "years ago."),
     ("P", "And they're playing in front of this many people."),
     ("A", "That's the part that gets me. I'd have been terrified.")],
    [("P", "Somebody in the front row behind the {away} bench has a sign that says 'I skipped my wedding for this.'"),
     ("A", "I hope that's a joke."),
     ("P", "I really hope that's a joke.")],
    [("A", "The grounds crew here deserves a mention. That field looks like a putting green."),
     ("P", "They were out here at six this morning painting the end zones by hand.")],
    [("P", "We had a viewer email in this week asking what you eat before a broadcast, {A}."),
     ("A", "Nothing. I'm too nervous. Then I eat everything at halftime."),
     ("P", "That's true. I've seen it.")],
    [("A", "You ever notice how every stadium smells a little different?"),
     ("P", "I can't say I've catalogued it."),
     ("A", "This one's popcorn and cut grass. Perfect football smell.")],
    [("P", "What's the best road environment you ever played in, {A}?"),
     ("A", "A night game where you couldn't hear your own thoughts. Our quarterback was using hand signals for "
           "everything. We lost by three and I still think about it."),
     ("P", "Places like this one?"),
     ("A", "Places exactly like this one.")],
    [("A", "I've got a nephew who's a freshman walk-on back home. He texts me after every game asking what I "
           "thought of his special teams reps."),
     ("P", "What do you tell him?"),
     ("A", "That he's the best gunner in America. Every week.")],
    [("P", "Our stats crew up here has been sharp today — shout out to them."),
     ("A", "They keep me honest. I'd be making up numbers without them.")],
    [("A", "I'll say this about this sport — nowhere else do you get this kind of pageantry. Bands, mascots, "
           "traditions going back a hundred years."),
     ("P", "It's why we do it."),
     ("A", "It's why everybody does it.")],
    [("P", "The {home} mascot runs a flag the length of the field after every score. Every single one?"),
     ("A", "Every single one. I'm told he's a mechanical engineering major."),
     ("P", "Good cardio for an engineer.")],
    [("A", "I tried to call a play for our production truck during warmups. They didn't take it."),
     ("P", "What was it?"),
     ("A", "Flea flicker. They said no. Cowards.")],
    [("P", "Long road trip for {away} this week?"),
     ("A", "Flew in Friday, walked through the stadium, early night. Coaches want those routines to be the same "
           "every week so nothing feels different on Saturday.")],
    [("A", "You know who has the toughest job in the stadium? The kid holding the sideline phone cord for the "
           "coach."),
     ("P", "That's a real job?"),
     ("A", "Every coach has a guy. If the coach sprints down the sideline and the cord gets tangled, that kid "
           "hears about it all week.")],
    [("P", "It's been a while since you had a day off, {A}."),
     ("A", "Monday. I'm going to sleep until noon and watch this game again."),
     ("P", "Of course you are.")],
    [("A", "Every kid on that {home} sideline grew up watching games in this building. That's something you can't "
           "coach."),
     ("P", "And every kid on the {away} sideline wants to ruin it for them."),
     ("A", "That's the fun of it.")],
    [("P", "If you're just joining us, welcome in. It's {away} and {home} from {stadium}."),
     ("A", "And you picked a good one to tune into.")],
    [("A", "{P}, I'm going to say something controversial."),
     ("P", "Go ahead."),
     ("A", "The best part of college football is the band's fourth-quarter song. Not the games. The song."),
     ("P", "I'm going to allow it.")],
]

# Stories an analyst tells, keyed by what he used to do.
WAR_STORIES = {
    "linebacker": [
        [("A", "When I played linebacker, our coordinator used to say: see ball, get ball. That's the whole job. "
               "Everything else is details."),
         ("P", "Is it that simple?"),
         ("A", "It's that simple and it's that hard.")],
        [("A", "My sophomore year I missed a fit on the first play of a rivalry game. Seventy-yard touchdown. My "
               "position coach didn't say a word to me. Worst silence of my life."),
         ("P", "How'd the rest of the game go?"),
         ("A", "Fourteen tackles. Never missed another fit that year.")],
        [("A", "The thing people don't understand about playing inside linebacker — you get hit on every snap. "
               "Guards, fullbacks, tight ends. By November your whole body is one big bruise.")],
    ],
    "quarterback": [
        [("A", "When I was calling plays, the hardest thing was getting your quarterback to throw it away. They "
               "all think they can make the play."),
         ("P", "Did you think that when you played?"),
         ("A", "Every single snap. That's why I became a coach — I finally understood what I put them through.")],
        [("A", "My first college start, I threw an interception on my first pass. Came to the sideline and our "
               "head coach just said, 'Good. Now it's out of your system.' Best thing anybody ever told me."),
         ("P", "Did it work?"),
         ("A", "Threw two more that day. But the fourth quarter was great.")],
        [("A", "Quarterbacks will tell you the game slows down around year three. For me it was year four. "
               "Some guys never get there.")],
    ],
    "reporter": [
        [("A", "When I was on the sideline, I learned more from what coaches said to each other walking to the "
               "locker room than any press conference."),
         ("P", "Anything you can repeat on air?"),
         ("A", "Absolutely not.")],
        [("A", "Best interview I ever did was a kicker. Nobody ever talks to the kicker. He had thoughts on "
               "everything — wind, turf, the history of the drop kick."),
         ("P", "Kickers are the philosophers of the sport."),
         ("A", "They have a lot of time to think.")],
        [("A", "Sideline reporting teaches you one thing fast: coaches do not want to talk at halftime. "
               "You get fifteen seconds and two clichés, and you're grateful.")],
    ],
    "lineman": [
        [("A", "Offensive linemen are the only players who know they did their job right and never hear about "
               "it. You only hear your name when you mess up."),
         ("P", "So we should say their names more."),
         ("A", "Please. Every play if you can.")],
        [("A", "I played at about three-oh-five. Now I'm told I'd be undersized for this era. These guys are "
               "enormous."),
         ("P", "And they move."),
         ("A", "That's the part that scares me. They move like tight ends.")],
        [("A", "The o-line room always has the best food. Every week somebody's mom sends something. That's "
               "the secret to a great offensive line — the moms.")],
    ],
    "coordinator": [
        [("A", "When I was calling the defense, the worst feeling in the world was knowing the offense had "
               "the right play on before the ball was snapped."),
         ("P", "Could you tell?"),
         ("A", "Every time. You just stand there and wait for it to happen.")],
        [("A", "People think coordinators sleep in the office. We do. I had a pull-out couch and a toothbrush "
               "in my desk drawer for eleven years."),
         ("P", "That sounds miserable."),
         ("A", "It was the best job I ever had.")],
        [("A", "The halftime adjustment everybody talks about? It's usually one thing. You find one thing "
               "they're doing to you and you take it away.")],
    ],
    "safety": [
        [("A", "Playing safety, you're the last line. If you miss, everybody in the stadium sees it."),
         ("P", "That's a lot of pressure on one guy."),
         ("A", "You either love that or it eats you alive. I loved it.")],
        [("A", "I had a coach who made us count the steps on our backpedal. Every rep. For two years. "
               "I still count them walking to my car."),
         ("P", "How many to your car today?"),
         ("A", "Two hundred and twelve. Not that I was counting.")],
        [("A", "The best safeties talk constantly before the snap. If your safety is quiet, something is "
               "wrong back there.")],
    ],
}

# Weather, by conditions. Filled in from the game's kickoff setting.
WEATHER = {
    "dome": [
        [("P", "Nice and comfortable inside {stadium} today — no weather to worry about."),
         ("A", "Perfect conditions for both offenses. Kickers love it in here.")],
        [("A", "Indoors, fast track. Offenses should be able to do whatever they want as far as conditions go.")],
    ],
    "hot": [
        [("P", "It's warm today — {temp} degrees at kickoff."),
         ("A", "Watch the depth on the defensive line. They'll rotate a ton in this heat.")],
        [("A", "This heat is going to be a factor late. The team that's been conditioning in it all August has "
               "an edge."),
         ("P", "{temp} degrees on the field right now.")],
    ],
    "mild": [
        [("P", "Beautiful {tod} — {temp} degrees and {sky}."),
         ("A", "Honestly, you couldn't order up better football weather.")],
        [("A", "{temp} and {sky}. This is postcard college football weather."),
         ("P", "Somebody's getting a great photo for the brochure today.")],
    ],
    "cold": [
        [("P", "Bundle up — it's {temp} degrees here, and the wind's picked up."),
         ("A", "Ball gets hard in the cold. Watch for drops, and watch the kickers.")],
        [("A", "You can see the breath of the linemen at the line of scrimmage. It's cold out there."),
         ("P", "{temp} degrees at kickoff, and it's only getting colder.")],
    ],
    "rain": [
        [("P", "The rain's picked up a little. Slick conditions."),
         ("A", "Ball security goes to the top of the list. Every ball carrier needs two hands on it.")],
        [("A", "In weather like this, the team that runs it better usually wins. Nobody wants to throw a wet ball "
               "thirty yards downfield.")],
    ],
    "snow": [
        [("P", "The snow keeps coming down. You can barely see the yard lines."),
         ("A", "In this stuff, the offensive line decides it. Nobody's getting to the edge.")],
        [("A", "Look at the ball boys sweeping off the hash marks between plays. That's snow football."),
         ("P", "{temp} degrees, and it's a winter scene out there.")],
        [("P", "Snow globe in {stadium} right now."),
         ("A", "The receivers can't plant. Everything has to be thrown before the break.")],
    ],
    "storm": [
        [("P", "It is absolutely pouring."),
         ("A", "You can't throw it in this. You can barely hand it off in this.")],
        [("A", "The field is standing water in spots. Watch the ball on every exchange."),
         ("P", "Heavy rain and the wind whipping it sideways.")],
    ],
    "wind": [
        [("P", "The wind is howling — {dir} at {wind} miles an hour."),
         ("A", "Which way you're going matters. With it, you'll try a long one. Into it, you punt.")],
        [("A", "Watch the flags on the goalposts. That's the real kicking coach today."),
         ("P", "Winds out of the {dir} around {wind}.")],
        [("A", "Deep balls hang up in this wind. That's how you get a cornerback an interception."),
         ("P", "{wind}-mile-an-hour wind, and it's gusting.")],
    ],
}


# Before kickoff: what the weather IS (in-game lines above say what it's doing now).
WEATHER_OPEN = {
    "dome": WEATHER["dome"],
    "hot": WEATHER["hot"],
    "mild": WEATHER["mild"],
    "cold": WEATHER["cold"],
    "rain": [
        [("P", "A steady rain falling here at kickoff, {temp} degrees."),
         ("A", "Ball security goes to the top of the list. Every ball carrier needs two hands on it.")],
        [("A", "Wet night — and a wet ball. Watch the snaps, watch the kickers' footing."),
         ("P", "{temp} degrees and raining as we get set to go.")],
    ],
    "snow": [
        [("P", "Snow falling at {stadium} — {temp} degrees at kickoff. This is what college football looks like "
               "in {month}."),
         ("A", "Both teams will tell you it doesn't matter. It matters. Ball security wins today.")],
        [("A", "The grounds crew has been out there with leaf blowers clearing the lines."),
         ("P", "{temp} degrees, snow coming down, and a crowd that doesn't care one bit.")],
    ],
    "storm": [
        [("P", "The weather is going to be the story. Heavy rain, strong wind, right at kickoff."),
         ("A", "Hold on to the football. Whoever does that better probably wins this one.")],
        [("P", "It's a mess here tonight. Heavy rain, lightning off in the distance."),
         ("A", "If that lightning gets any closer, they'll clear the field. Keep an eye on it.")],
    ],
    "wind": [
        [("P", "Wind is going to be a factor — {dir} at {wind} miles an hour at kickoff."),
         ("A", "The coin toss mattered today. Whoever has the wind in the fourth quarter has a real edge.")],
        [("A", "I watched the kickers in warmups. Going one way, they were hitting from 55. The other way, 38."),
         ("P", "{wind}-mile-an-hour winds here.")],
    ],
}
