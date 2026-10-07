"""
tailgate.py — TODAY'S TAILGATE.

Every Saturday the crew sends Boom out into the lots with one job: find the best
tailgate on campus. He comes back with one person and a plate. It's a short,
silly interview — what's on the grill, how long they've been doing this, the
secret, the prediction — with the desk heckling from the set.

What they're cooking comes from where they are and who's coming to town:

  EAT THE OPPONENT   a long, proud tradition: fans cook the other team's
                     mascot. Playing the Gars? Blackened redfish. The Mules?
                     Mule-kick chili. The Twisters? Pretzel twists.
  HOME COOKING       what that part of the country makes best — brats and cheese
                     curds in Madison, boudin in Baton Rouge, brisket in Texas,
                     pepperoni rolls in Morgantown, crab cakes in College Park.
  THE CLASSICS       everything else a lot can produce, from smoked queso to
                     a four-layer banana pudding.

Plus dessert, because there's always dessert. To add food, add a line.
"""
from names import FIRST_NAMES, LAST_NAMES

# ── Eat the opponent: the visiting team's mascot, on a plate ─────────────────
# nickname -> (dish, how they tell it)
EAT_THE_OPPONENT = {
    'Cottonmouths': ('snake-shaped sausage rolls', "Close enough to snake. It's sausage. Don't tell the kids."),
    'Gars': ('blackened redfish tacos', "Gar's too bony, so we went with redfish. Same energy."),
    'Mules': ('mule-kick chili', "Three-alarm chili. One bowl and you'll feel kicked."),
    'Stallions': ('horseshoe sandwiches', 'Open-face, fries on top, cheese sauce. Shaped like a horseshoe.'),
    'Thoroughbreds': ('horseshoe sandwiches', "Fries, cheese sauce, shaped like a horseshoe. Winner's circle food."),
    'Twisters': ('pretzel twists', 'Two hundred soft pretzels. We twisted the Twisters.'),
    'Stampede': ('a sixteen-hour brisket', 'Salt, pepper, post oak, sixteen hours. The Stampede stops here.'),
    'Cattlemen': ('a sixteen-hour brisket', 'Salt, pepper, post oak. The herd got thinned.'),
    'Wranglers': ('lasso onion rings', "Rings the size of a rope loop. We roped 'em."),
    'Troubadours': ('hot chicken with a song', 'Hot chicken, and the loser sings for it.'),
    'Prairie Fire': ('fire-roasted elote', 'Charred corn, lime, cotija. We put out the fire by eating it.'),
    'Firebrands': ('fire-roasted elote', 'Charred corn, lime, cotija. Firebrands, extinguished.'),
    'Wildfire': ('fire-roasted elote', 'Charred over a wood fire. Wildfire contained.'),
    'Harvesters': ('grilled street corn', 'Shucked forty ears this morning. Harvested the harvest.'),
    'Sodbusters': ('grilled street corn', 'Forty ears. We busted the Sodbusters.'),
    'Watermen': ('crab cakes', "All lump, barely any filler. The Watermen's catch is our lunch."),
    'Voyageurs': ('canoe-sized pasties', 'Meat pies as long as a paddle.'),
    'Foresters': ('a Yule log cake', 'Chocolate log, buttercream bark. Timber!'),
    'Loggers': ('a Yule log cake', 'Chocolate log, buttercream bark. Log jam.'),
    'Lumber Barons': ('a Yule log cake', 'Chocolate log, buttercream bark. The Barons got sawed.'),
    'Timberjacks': ('a Yule log cake', 'Chocolate bark and all. Timber!'),
    'Blizzard': ('snow cones', 'Every flavor. The Blizzard melts by halftime.'),
    'Rainmakers': ('rain-barrel punch', "Big cooler of punch. We call it the Rainmaker. It's mostly juice, officer."),
    'Riveters': ('iron-skillet cornbread', 'Riveted to the pan, like it should be.'),
    'Riptide': ('fish and chips', "Pulled 'em out of the tide and fried 'em."),
    'Breakers': ('fish and chips', "Caught 'em off the breakwater. Fried 'em."),
    'Evergreens': ('pine-nut pesto pasta', 'From the tree, onto the plate.'),
    'Redwoods': ('pine-nut pesto pasta', 'From the tree, onto the plate. Redwoods, chopped.'),
    'Sequoias': ('pine-nut pesto pasta', 'The big trees go down easy with garlic bread.'),
    'Charter Oaks': ('acorn squash, roasted', "Oaks make acorns. We roasted 'em."),
    'Lamplighters': ('lamb lollipops', "Lamp, lamb. Look, it's early."),
    'Prospectors': ('gold-dusted mac and cheese', 'Struck gold in a hotel pan.'),
    'Goldminers': ('gold-dusted mac and cheese', 'Dug deep. Found cheese.'),
    'Comstocks': ('silver-dollar pancakes', "Two hundred of 'em. We mined the Comstocks."),
    'Hellcats': ('four dozen deviled eggs', 'Smoked paprika, a little bacon. Deviled. Get it.'),
    'Phantoms': ('ghost-pepper wings', "You won't see 'em coming. Then you'll feel 'em."),
    'Dust Devils': ('dirt pudding cups', 'Cookie dirt, gummy worms. We ate the dust.'),
    'Barracudas': ('a fish fry', 'We caught the opponent. We fried the opponent.'),
    'Tarpons': ('a fish fry', 'Silver Kings? Silver platter.'),
    'Snook': ('a fish fry', 'Snook, cornmeal, hot oil. Nothing personal.'),
    'Stingrays': ('grilled skate wings', "It's a ray. We grilled it. Lemon butter."),
    'Keepers': ('a lighthouse layer cake', 'Six layers, red-and-white stripes. Tall enough to keep a light.'),
    'Smelters': ('cast-iron steaks', 'Seared in iron. Fitting.'),
    'Ironmasters': ('cast-iron steaks', 'Seared in iron. The Ironmasters got mastered.'),
    'Ironclads': ('cast-iron steaks', 'Seared in iron. Seemed appropriate.'),
    'Wildcatters': ('burnt ends', 'Black gold, cubed and sauced.'),
    'Gushers': ('burnt ends', 'Black gold, sauced. We struck it.'),
    'Riggers': ('burnt ends', 'Black gold. The rig is down.'),
    'Saltmen': ('salt-crusted potatoes', 'We salted the Saltmen.'),
    'Gila Monsters': ('jalapeño poppers', "They bite back. Like the visitors won't."),
    'Scorpions': ('jalapeño poppers', 'Sting in every bite.'),
    'Sidewinders': ('rattlesnake chili', "Mostly beef. Some snake. Don't ask."),
    'Mammoths': ('giant beef ribs', 'Ribs the size of tusks. Prehistoric.'),
    'Bighorns': ('venison chili', 'Big game, big pot.'),
    'Elk': ('elk burgers', 'Ground elk, smashed thin. The herd gets thinned.'),
    'Pronghorns': ('venison sliders', 'Fastest thing on the plains, slowest thing on my grill.'),
    'Peregrines': ('smoked wings', 'Two hundred wings. The falcons were unavailable.'),
    'Kestrels': ('smoked wings', 'Wings. Little hawk, big platter.'),
    'Harriers': ('hot wings', 'Hawk wings. Well — chicken wings.'),
    'Egrets': ('lemon-pepper wings', "White birds, white sauce. That's the whole joke."),
    'Herons': ('lemon-pepper wings', 'Long legs, short life on this grill.'),
    'Riverhawks': ('hot wings', "Riverhawk wings, extra hot. They shouldn't have come here."),
    'Ironhawks': ('cast-iron wings', 'Wings, fried in iron. Ironhawks.'),
    'Aviators': ('smoked wings', 'Two hundred wings. Grounded.'),
    'Firebirds': ('flaming-hot wings', 'Extra hot. The Firebirds got burned.'),
    'Torchbearers': ('flaming-hot wings', 'We passed the torch. To the grill.'),
    'Sovereigns': ('a king cake', "There's a little baby in it. Whoever finds it buys next week."),
    'Statesmen': ('a king cake', "There's a baby in it. Whoever finds it buys next week."),
    'Founders': ('cheesesteaks', "Chopped, wit' onions. Founded right here in the lot."),
    'Thunderheads': ('thunder cake', 'Chocolate tomato cake. Grandma swears by it.'),
    'Thunderbolts': ('thunder cake', 'Chocolate tomato cake. Strikes twice.'),
    'Rocketeers': ('rocket pops', 'Red, white and blue. Launched straight into my mouth.'),
    'Airships': ('rocket pops', 'Up, up, and into my mouth.'),
    'Rockslides': ('rocky road brownies', 'The slide stops here.'),
    'Highlanders': ('Scotch eggs', 'Sausage-wrapped and fried. The Highlands are delicious.'),
    'Pharaohs': ('pyramid nachos', 'Stacked four feet high. A wonder of the world.'),
    'Javelinas': ('a whole roasted pig', 'In the ground since three this morning.'),
    'Vulcans': ('hammered pork tenderloins', 'Pounded thin on an anvil. Mostly a cutting board.'),
    'Brass': ('trumpet-shaped corn dogs', "They're corn dogs. We bent 'em. Don't ask."),
    'Copperheads': ('copper-pot jambalaya', "Cooked in copper. The Copperheads didn't make it."),
    'Chiles': ('green-chile cheeseburgers', 'Roasted this morning. You can smell it from the lot.'),
    'Sea Lions': ('fish tacos', "Caught 'em off the pier. Sort of."),
    'Ridgerunners': ('moonshine-glazed ribs', 'The glaze is legal. Mostly.'),
    'Glassmen': ('glass candy', 'Shatters like their defense.'),
    'Gaslights': ('roller-grill hot dogs, upgraded', 'A tribute to the gas station. Better buns.'),
    'Neon': ('neon gelatin cups', 'Every color on the Strip. Family friendly.'),
    'Gales': ('a wind-chill chili', 'You need something warm off that lake. Theirs, not ours.'),
    'Northmen': ('beer brats', 'Brats in a beer bath. Pillaged the Northmen.'),
    'Lake Effect': ('snowball cookies', 'Powdered sugar everywhere. Lake effect.'),
    'Quarrymen': ('rock candy', 'We broke rock. Then we ate it.'),
    'Bladesmiths': ('a carving station', 'Whole brisket, carved to order. Brought my own blade.'),
    'Longleafs': ('pine-smoked chicken', 'Smoked over pine. The Longleafs got cooked.'),
    'Marauders': ("a pirate's feast", 'Turkey legs and grog. Arr. The grog is sweet tea.'),
    'Frontiersmen': ('campfire beans', 'Beans, bacon, a cast-iron pot. Frontier food.'),
    'Rivermen': ('fried catfish', 'Caught in the river. Fried in the lot.'),
}

# ── Home cooking: what a region makes best ───────────────────────────────────
# state -> [(dish, how they tell it)]
HOME_COOKING = {
    "LA": [("a gumbo you could stand a spoon in", "Dark roux, took me an hour and a half to stir. Andouille, chicken, and the trinity."),
           ("boudin balls", "Boudin, rolled and fried. My cousin makes the boudin, I make the balls. Division of labor."),
           ("a crawfish boil", "Forty pounds of crawfish, corn, potatoes, and enough cayenne to clear your sinuses into next week.")],
    "TX": [("a sixteen-hour brisket", "Salt, pepper, post oak. That's it. Anything else is a cover-up."),
           ("breakfast tacos", "Egg, potato, chorizo, and salsa verde my wife won't let me put on the internet."),
           ("smoked queso", "Queso, sausage, canned tomatoes and chiles, straight on the smoker in a cast-iron pan.")],
    "WI": [("beer brats and cheese curds", "Brats simmered in beer and onions, then on the grill. Curds so fresh they squeak.")],
    "MN": [("a tater tot hotdish", "Tater tot hotdish in a roaster the size of a canoe. Ope, let me just squeeze past ya.")],
    "ND": [("a tater tot hotdish", "It's hotdish. You don't ask what's in hotdish. You just have seconds.")],
    "KS": [("burnt ends", "Brisket point, cubed, sauced, back in the smoker. Kansas City candy.")],
    "MO": [("burnt ends and toasted ravioli", "Burnt ends from the smoker and toasted ravs for the kids. Both sides of the state represented.")],
    "MD": [("crab cakes", "All lump, barely any filler, and a whole can of crab seasoning. There's crab seasoning on my shoes.")],
    "WV": [("pepperoni rolls", "Pepperoni rolls, three hundred of 'em. It's the official food of the state as far as I'm concerned.")],
    "OH": [("Cincinnati chili, five-way", "Spaghetti, chili, beans, onions, and a mountain of cheese. Five-way. Don't ask about the cinnamon.")],
    "GA": [("peach cobbler", "Georgia peaches, brown butter crust, and a scoop of vanilla on the side.")],
    "AL": [("smoked chicken with white sauce", "Smoked half-chickens dunked in Alabama white sauce. Mayo, vinegar, black pepper. Don't knock it.")],
    "TN": [("Nashville hot chicken", "Hot chicken on white bread with pickles. We've got a mild for the cowards.")],
    "KY": [("hot browns", "Open-faced turkey, bacon, tomato and Mornay sauce, broiled on a sheet pan on the tailgate.")],
    "IA": [("breaded pork tenderloins", "Pork tenderloin pounded bigger than the bun. The bun is decorative.")],
    "IN": [("breaded pork tenderloins and sugar cream pie", "Tenderloins bigger than your face, and sugar cream pie, the Hoosier pie.")],
    "NE": [("homemade runzas", "Beef, cabbage, onion in bread. You grow up here, you grow up on these.")],
    "MI": [("coney dogs", "Coney dogs, Detroit style, with the chili and the onions and the mustard."),],
    "PA": [("pierogies and kielbasa", "Pierogies pan-fried in butter and onions, and kielbasa off the grill.")],
    "SC": [("shrimp and grits", "Stone-ground grits, local shrimp, a little tasso gravy.")],
    "NC": [("whole-hog barbecue", "Whole hog, chopped, with an Eastern vinegar sauce. Don't bring tomatoes near it.")],
    "VA": [("ham biscuits", "Country ham on buttermilk biscuits. That's the whole menu. It's perfect.")],
    "FL": [("Cuban sandwiches and key lime pie", "Cubanos pressed on the grill with a brick, and key lime pie from my aunt.")],
    "MS": [("fried catfish with comeback sauce", "Catfish fried in cornmeal, and comeback sauce, 'cause you'll come back for it.")],
    "AR": [("cheese dip", "A crockpot of cheese dip. This is a cheese dip state. We will fight about this.")],
    "OK": [("fried onion burgers", "Onions smashed right into the patty on the flattop. Depression-era burger. Still undefeated.")],
    "HI": [("kalua pig and luncheon-meat musubi", "Kalua pig from the imu and two trays of luncheon-meat musubi. Aloha.")],
    "UT": [("funeral potatoes and fry sauce", "Cheesy potato casserole with corn flakes on top, and fry sauce for everything.")],
    "NM": [("green chile cheeseburgers", "Hatch green chile, roasted this morning. That smell is the smell of home.")],
    "AZ": [("Sonoran hot dogs", "Bacon-wrapped dogs, beans, jalapeños, and mayo. On a bolillo.")],
    "CA": [("tri-tip sandwiches", "Santa Maria tri-tip over red oak. Garlic bread. Salsa.")],
    "OR": [("marionberry pie", "Marionberry pie. You can only get these berries here. Everybody should be jealous.")],
    "WA": [("cedar-plank salmon", "Salmon on cedar planks with brown sugar and dill.")],
    "CO": [("green chile smothered burritos", "Pork green chile, smothered everything. We brought the Rocky Mountain oysters too. Don't ask.")],
    "NY": [("salt potatoes and chicken spiedies", "Salt potatoes drowned in butter and chicken spiedies off the grill.")],
    "MA": [("lobster rolls", "Lobster, butter, toasted bun. Maybe a little mayo. The mayo is a whole argument.")],
    "NJ": [("pork roll, egg and cheese", "Pork roll. Not Taylor ham. I will not be taking questions.")],
    "CT": [("New Haven clam pizza", "Clam pie off the pizza oven in the back of my truck.")],
    "IL": [("Italian beef, dipped", "Italian beef, dipped, with hot giardiniera. You'll need a lot of napkins.")],
    "NV": [("a prime rib buffet", "Prime rib, twenty-four ounces, because that's how Nevada does a buffet.")],
    "WY": [("bison chili", "Bison chili with cornbread. Cold out here in November. This fixes it.")],
    "ID": [("loaded baked potatoes", "Idaho potatoes, the size of footballs, with everything on 'em.")],
    "SD": [("chislic", "Cubed lamb, fried, garlic salt, toothpicks. South Dakota's gift to the world.")],
    "DE": [("scrapple sandwiches", "Scrapple, fried crispy. Don't ask what's in it. Just eat it.")],
}
SCHOOL_COOKING = {
    'Buffalo': ('real Buffalo wings', "Wings, hot sauce and butter, blue cheese. If you bring ranch I'm calling security."),
    'Memphis': ('dry-rub ribs', 'Memphis dry rub, no sauce. Sauce is for people with something to hide.'),
    'Waco': ('cherry-cola-glazed ribs', 'Ribs glazed with cherry cola. It works, I promise.'),
    'Pittsburgh': ('a pierogi and fries sandwich bar', "Sandwiches with the fries and slaw right on 'em. Pittsburgh style."),
    'Fresno State': ('Santa Maria tri-tip', 'Tri-tip, red oak, and a whole flat of Central Valley peaches.'),
    "Hawai'i": ('kalua pig and poke', "Kalua pig and fresh poke from this morning's market."),
    'Bayou State': ('jambalaya in a paddle pot', 'Jambalaya stirred with a boat paddle in a pot big enough to bathe in. Feeds two hundred.'),
    'Wisconsin': ('beer brats and fried cheese curds', 'Brats in a beer-and-onion bath, then on the grill. Curds so fresh they squeak.'),
    'Maryland': ('crab cakes with all the seasoning', 'Jumbo lump, broiled, not fried, and crab seasoning on literally everything.'),
    'West Virginia': ('pepperoni rolls and a pot of beans', 'Pepperoni rolls and soup beans with cornbread. Mountain food.'),
    'Cincinnati': ('Cincinnati-style chili dip', "Cream cheese, chili, cheddar, broiled. Scoop it with crackers and don't look back."),
    'Atlanta': ('drive-in chili dogs', "Chili dogs and onion rings. Drive-in style, like my dad made 'em."),
    'Kansas State': ('burnt ends and bierocks', "Burnt ends, and bierocks — beef and cabbage buns — my grandma's Volga German recipe."),
}

# ── The classics: anything a parking lot can produce ─────────────────────────
CLASSICS = [
    ("smoked queso", "processed cheese, pepper jack, sausage, canned tomatoes and chiles, and three hours of hickory smoke."),
    ("a triple-decker nacho tower", "Nachos in three layers so every chip gets cheese. That's engineering."),
    ("jalapeño poppers wrapped in bacon", "Cream cheese, cheddar, and a bacon wrap, on a special rack I welded myself."),
    ("pulled pork sliders", "Pork shoulder since midnight. Vinegar slaw on top. Two hundred sliders."),
    ("a low-country boil", "Shrimp, sausage, corn and potatoes, dumped straight onto newspaper on the table."),
    ("bratwurst in a beer bath", "Brats on the grill, then into the beer and onions to stay happy all day."),
    ("chili in a turkey fryer", "Eight gallons of chili. We cook it in a turkey fryer because we don't own a pot that big."),
    ("smash burgers on a flattop", "Two patties, smashed thin, American cheese, and the onions go right into the meat."),
    ("buffalo chicken dip", "Buffalo chicken dip in a slow cooker we plug into the truck."),
    ("pig shots", "Smoked sausage rounds wrapped in bacon and filled with cream cheese. Little pig shot glasses."),
    ("corn chip pie", "corn chips, chili, cheese, onions, right in the bag. Walking tacos for grown-ups."),
    ("a seafood paella", "A paella pan the size of a manhole cover. Shrimp, mussels, chorizo, saffron."),
    ("birria tacos with consommé", "Birria, twelve hours, and you dunk the tacos in the consommé."),
    ("bulgogi sliders", "Bulgogi on Hawaiian rolls with kimchi slaw. My mom's marinade."),
    ("jerk chicken", "Jerk chicken over a drum grill. Scotch bonnets, allspice, thyme. My dad's from Kingston."),
    ("a charcuterie board shaped like the field", "Salami yard lines, cheese end zones, and a pretzel-rod goalpost."),
    ("smoked mac and cheese", "Five cheeses, smoked for an hour so it gets a crust on top. The crust is the prize."),
    ("fried pickles", "Dill chips, cornmeal batter, and a spicy ranch."),
    ("carne asada", "Skirt steak, citrus marinade, tortillas off the comal, salsa roja."),
    ("stuffed pork loin on the rotisserie", "A rotisserie on a trailer. It spins. People stare. It's glorious."),
    ("shrimp po'boys", "Fried shrimp, dressed, on French bread. Dressed means lettuce, tomato, pickle, mayo."),
    ("breakfast burritos", "Eggs, chorizo, potatoes, cheese. We start at 6 a.m. and we don't stop."),
    ("a whole smoked turkey", "Injected with Cajun butter and smoked over pecan. It's Thanksgiving every Saturday."),
    ("a pizza oven in a trailer", "Wood-fired pizzas, ninety seconds each. We've done three hundred today."),
    ("pastrami on rye", "I cure and smoke my own pastrami. Took ten days. Worth every one."),
    ("lamb kebabs", "Lamb kebabs with a yogurt sauce. My family's been making these since before any of us liked football."),
    ("chicken spiedies", "Marinated three days. The marinade is the secret. The secret is the marinade."),
    ("a hot dog bar with 31 toppings", "Thirty-one toppings. I counted. One of them is breakfast cereal and it works."),
    ("deep-fried sandwich cookies", "sandwich cookies, pancake batter, fryer, powdered sugar. The line's been forty deep since nine."),
    ("pimento cheese sandwiches", "Pimento cheese from my grandmother's recipe, on white bread, crusts off."),
]

# ── Dessert and the confections ──────────────────────────────────────────────
CONFECTIONS = [
    "a four-layer banana pudding", "Texas sheet cake", "homemade marshmallow pies", "fried peach hand pies",
    "a chess pie", "pecan pie bars", "whoopie pies in team colors", "funnel cake", "sopapilla cheesecake bars",
    "a red velvet cake shaped like the stadium", "crispy rice treats cut like footballs", "a strawberry pretzel salad",
    "puppy chow by the gallon", "a cola cake", "hummingbird cake", "caramel apples dipped in team-color sprinkles",
    "kolaches", "churros with cajeta", "beignets", "a banana pudding in a cooler", "s'mores dip in a skillet",
    "buckeye brownies", "lemon bars", "chocolate chip cookie cake with the logo piped on", "pralines",
    "a peach cobbler in a Dutch oven", "homemade ice cream, hand-cranked", "Tres leches cake", "a dirt cake with gummy worms",
    "cinnamon rolls the size of a hubcap", "sweet potato pie", "cake pops shaped like helmets", "blondies",
    "fried snack cakes", "a gelatin mold in the shape of the mascot", "baklava", "a peanut butter pie",
    "gooey butter cake", "an icebox pie", "bread pudding with bourbon sauce", "oatmeal cream pies",
]

PERSONAS = [
    "a retired high school chemistry teacher", "a dentist who has missed two home games in thirty years",
    "a long-haul trucker who plans every route around the schedule", "a pediatric nurse on a rare Saturday off",
    "three brothers who share one season ticket and a lot of opinions", "a grandmother of eleven",
    "a man who drives a converted school bus painted in school colors", "a pair of newlyweds who met at this exact spot",
    "a former walk-on who never saw the field and hasn't missed a game since", "a family of six in matching overalls",
    "an accountant who keeps a spreadsheet of every tailgate menu since 2003", "a firefighter and his whole engine company",
    "a mother-daughter team from three states away", "a retired Marine who runs this tailgate like a mess hall",
    "a veterinarian with a very well-behaved dog", "a backyard legend the whole street calls 'the Pitmaster,' unironically",
    "a group of eight college roommates, now in their fifties", "a barber who gives free haircuts at halftime",
    "a husband and wife who haven't agreed on a single play call in thirty years", "a preacher who keeps the sermon short on game days",
    "a farmer who brought the corn, the hog and the tractor", "a couple who got married in the parking lot",
]
WOMEN = ["Linda", "Tammy", "Denise", "Brenda", "Kathy", "Shonda", "Marisol", "Deb", "Carla", "Renee", "Tonya",
         "Gloria", "Patrice", "Jolene", "Maria", "Keisha", "Barb", "Janet", "Rhonda", "Tina", "Yolanda", "Carol"]
CREWS = ["the Lot {n} Legends", "the Row {n} Regulars", "the Section {n} Smokehouse", "the Gate {n} Grill Squad",
         "Tent City, Row {n}", "the Space {n} Supper Club", "the Lot {n} Brisket Brotherhood"]

# What the desk says, reacting.
REACT_FOOD = {
    "coach": ["I'm not supposed to eat that. Send two.", "In my day we had a bologna sandwich and we liked it.",
              "That's more preparation than some teams put in this week.", "Discipline. I respect a sixteen-hour anything.",
              "My wife would kill me. Send it anyway."],
    "film": ["I'd like to see the tape on that smoker.", "The fundamentals are sound.", "That's a five-star recruit of a plate.",
             "I've been smelling that for an hour and I can't concentrate.", "That's elite. That's truly elite."],
    "defender": ["Nobody's stopping that. Double-team the plate.", "That's a turnover. That plate is mine.",
                 "Somebody block for me, I'm going out there.", "Man, I played four years and never ate like that on a Saturday."],
    "host": ["We're going to need plates at the desk. That's not a request.", "This segment is the best part of my week.",
             "I'm told we're not allowed to leave the set. I'm considering it."],
}
REACT_OPP = {
    "coach": ["Eating the other team's mascot. That's psychological warfare. I respect it.",
              "You play the game on the field. You also, apparently, play it on the grill."],
    "film": ["That's the most aggressive pregame I've seen all year.", "That's bulletin-board material. Delicious bulletin-board material."],
    "defender": ["That's a message. That's a whole message.", "If I'm the visitors, I'm walking past that and getting mad."],
    "boom": ["THEY'RE EATING THE OTHER TEAM, {host}!", "Tradition, baby! You eat the opponent!"],
}
HOW_LONG = [
    "Since {since}. My dad started it, and when he passed, I kept the spot.",
    "{years} years. Same spot. I've been offered money for this spot. No.",
    "Since {since}. We got here at four this morning. Somebody got here at 3:45 and we don't talk about it.",
    "{years} years. My kids grew up in this lot. My oldest learned to drive in this lot.",
    "We started in {since} with a card table. Now we have a generator and a satellite dish.",
    "{years} seasons. Never missed a home game. Missed my own birthday party twice.",
]
SECRETS = [
    "The secret? Patience and a little bit of bacon grease.", "My grandmother's recipe, and I will die with it.",
    "Low and slow. And I talk to the smoker. Out loud. People have noticed.",
    "The secret ingredient is love. The other secret ingredient is butter. Mostly butter.",
    "I'd tell you, but the guy two tents over has been trying to steal it since 2011.",
    "A splash of the good stuff. The good stuff is cherry cola.", "A little brown sugar. A lot of brown sugar.",
    "Honestly? We don't measure anything. We just feel it.",
]
BOOM_OPENERS = [
    "{host}, I walked every lot in {town} this morning. I ate things I can't describe on television. But there was a winner.",
    "I've been out in the lots since sunrise. I'm full. I'm emotional. And I found the best tailgate in America.",
    "{host}, you would not believe the lots out here. But one tailgate stood above the rest.",
    "I sampled forty-one tailgates. I have regrets. But not about this one.",
]
BOOM_INTROS = [
    "Everybody, this is {name}, {persona}, and the captain of {crew}.",
    "Meet {name}! {Persona}, and the head chef of {crew}.",
    "Say hi to {name} — {persona} — and the whole crew from {crew}!",
]


def _plural(food):
    """'kolaches' → True, 'banana pudding' → False, 'a pecan pie' → False."""
    w = food.strip().split()[-1].lower() if food.strip() else ""
    return w.endswith("s") and not w.endswith(("ss", "us", "is")) and not food.lower().startswith(("a ", "an ", "one "))


def _name(rng, women_share=0.4, avoid=()):
    from names import surname
    first = rng.choice(WOMEN) if rng.random() < women_share else rng.choice(FIRST_NAMES)
    last = surname(rng, avoid=set(avoid) | {first})
    return f"{first} {last}"


def pick_menu(show, home, away):
    """(dish, how they tell it, kind) — kind is 'opponent', 'home', or 'classic'."""
    rng = show.rng
    opp = EAT_THE_OPPONENT.get(away.nickname)
    if opp and rng.random() < 0.7:
        return opp[0], opp[1], "opponent"
    if home.school in SCHOOL_COOKING and rng.random() < 0.55:
        d, how = SCHOOL_COOKING[home.school]
        return d, how, "home"
    local = HOME_COOKING.get(getattr(home, "home_state", None) or "")
    if local and rng.random() < 0.5:
        d, how = show.fresh(local, f"tg_home:{home.home_state}", reuse=True)
        return d, how, "home"
    d, how = show.fresh(CLASSICS, "tg_classic", reuse=True)
    return d, how, "classic"


def segment(show):
    """TODAY'S TAILGATE — one fan, one plate, a few questions."""
    if not show.segment("TODAY'S TAILGATE"):
        return
    rng = show.rng
    L, g = show.league, show.g
    home, away = g.home, g.away
    away_fan = not g.neutral and rng.random() < 0.18
    fan_team = away if away_fan else home
    if g.neutral:
        fan_team = rng.choice((home, away))
    name = _name(rng, avoid=getattr(show, "taken_surnames", ()))
    first = name.split()[0]
    persona = show.fresh(PERSONAS, "tg_persona", reuse=True)
    crew = rng.choice(CREWS).format(n=rng.randint(2, 48))
    years = rng.randint(6, 41)
    since = L.year - years
    dish, how, kind = pick_menu(show, fan_team, away if fan_team is home else home)
    dessert = show.fresh(CONFECTIONS, "tg_dessert", reuse=True)

    show.say("host", show.vary("tg_open", [
        "Time for Today's Tailgate. Every week we send {boom} out with one job: find the best tailgate on campus.",
        "It's that time — Today's Tailgate. {boom} has been out in the lots since dawn. {boom}, what'd you find?",
        "All right, the most important segment of the show. Today's Tailgate. {boom}?",
        "Today's Tailgate. {boom}, you've been gone for two hours and you have sauce on your shirt.",
    ]))
    show.say("boom", show.fill(rng.choice(BOOM_OPENERS)))
    intro = rng.choice(BOOM_INTROS).format(name=name, persona=persona, Persona=persona[0].upper() + persona[1:], crew=crew)
    if away_fan:
        from campus_towns import town
        art = "an" if away.school[0] in "AEIOU" else "a"
        intro += f" And get this — {art} {away.school} fan! Drove in from {town(away.school, full=False)}!"
    show.say("boom", intro)
    fan = f"{first.upper()}"
    show.say(fan, rng.choice((f"{fan_team.chant}", "Hi Mom!", f"Let's GO {fan_team.nickname}!",
                              "I can't believe I'm on TV right now.")), label=first)
    # 1. What are we eating?
    show.say("boom", rng.choice(("First question — what are we eating?", "Tell America what's on that grill.",
                                 "What did you make? Describe it slowly. I want to cry.")))
    lead = {"opponent": rng.choice((f"Well, {away.school if fan_team is home else home.school} is in town, so — ",
                                    "It's tradition. You eat the other team. So — ")),
            "home": rng.choice(("It's a home-cooking kind of day. ", "This is what we grew up on. ", "")),
            "classic": ""}[kind]
    # The same opponent comes back every year: the signature line gets a rest, so
    # "my grandmother taught me" isn't word for word every time the Irish visit.
    recent = show.league.gameday.setdefault("tg_lines", {})
    now = L.year * 100 + L.week
    if kind == "opponent" and (now - recent.get(how, -999) < 100 or rng.random() < 0.45):
        opp_nick = (away if fan_team is home else home).nickname
        how = rng.choice((f"We make it every time the {opp_nick} come to town.",
                          f"Only when the {opp_nick} visit. It's the rule.",
                          "Nothing fancy. Same as every year they come here.",
                          f"The {opp_nick} bring the team. We bring the menu."))
    recent[how] = now
    cap = not lead or lead.rstrip().endswith((".", "!", "?"))
    show.say(fan, f"{lead}{dish[0].upper() + dish[1:] if cap else dish}. {how}", label=first)
    if kind == "opponent":
        k = rng.choice(list(REACT_OPP))
        show.say(k, show.fill(rng.choice(REACT_OPP[k])))
    else:
        k = rng.choice(("coach", "film", "defender", "host"))
        show.say(k, rng.choice(REACT_FOOD[k]))
    # 2. How long?
    show.say("boom", rng.choice(("How long have you been doing this?", "How long has this spot been yours?",
                                 "How many years, and how early did you get here?")))
    show.say(fan, rng.choice(HOW_LONG).format(since=since, years=years), label=first)
    if years >= 30 and rng.random() < 0.6:
        show.say("coach", f"{years} years. That's longer than most coaching staffs last. Longer than some programs.")
    # 3. The secret — or the dessert
    if rng.random() < 0.55:
        show.say("boom", rng.choice(("What's the secret?", "What's the secret? Whisper it. I'll whisper it to America.",
                                     "Give me the secret. I won't tell anybody except millions of people.")))
        show.say(fan, rng.choice(SECRETS), label=first)
    show.say("boom", rng.choice(("And I'm told there's dessert.", "Now tell 'em about the dessert.",
                                 "And then — THEN — there's dessert.")))
    show.say(fan, rng.choice((f"{dessert[0].upper() + dessert[1:]}. My sister made 'em. She won't come on camera.",
                              f"{dessert[0].upper() + dessert[1:]}. We have a strict one-per-person rule that nobody follows.",
                              f"{dessert[0].upper() + dessert[1:]}. "
                              + ("They're" if _plural(dessert) else "It's") + " gone by kickoff every single time.",
                              f"{dessert[0].upper() + dessert[1:]}. Made at two this morning.")), label=first)
    show.say(rng.choice(("film", "defender", "host")), rng.choice((
        f"{dessert[0].upper() + dessert[1:]}. I'd like to formally request that.",
        "I'm sorry, did he say dessert? Is there enough?", "That's the best news I've heard all day.",
        "We need to talk to the producers about the catering budget.")))
    # 4. The prediction
    import rivalries
    s = rivalries.series(L, home, away)
    other = away if fan_team is home else home
    show.say("boom", rng.choice((f"Last one — prediction. {fan_team.school} and {other.school}. Go.",
                                 "Final question. Who wins, and by how much?", "Give me a score.")))
    w_pts = rng.randint(24, 45)
    l_pts = max(3, w_pts - rng.randint(3, 24))
    extra = ""
    if s.n and s.streak[0] == other.school and s.streak[1] >= 2:
        extra = f" {other.school}'s won {s.streak[1]} in a row. That ends today."
    elif s.trophy and s.holder == other.school:
        extra = f" And {s.trophy} comes home tonight."
    show.say(fan, f"{fan_team.school} {w_pts}, {other.school} {l_pts}.{extra}", label=first)
    k = rng.choice(("coach", "film", "defender"))
    mine = show.table.get((k, show.g))
    if mine is fan_team:
        react = ("I'm with you on that one.", "Same pick. Great minds.", "A homer pick — and I agree with it.",
                 "That's the most confident anyone's been on this set all year. I'm right there with you."
                 if L.week >= 4 else "That's confidence. I'm right there with you.")
    elif mine is not None:
        react = ("Bold. I've got the other side.", "I respect it. I don't agree with it.",
                 "A homer pick. I love it — I'm just not making it.", "I've seen worse picks. I've MADE worse picks.")
    else:
        react = ("Bold.", "A homer pick. I love it.")
    show.say(k, rng.choice(react))
    show.say("boom", rng.choice((f"{name}, everybody! Best tailgate in {show.F['town']}! Plates are on the way to the desk!",
                                 f"That's {crew}! Go find them in the lot! Bring an appetite!",
                                 f"{first}, you're a national treasure. Back to you, {show.F['host']}!")))
    show.say("host", rng.choice(("If those plates don't show up in ten minutes, I'm walking.",
                                 "We'll be right back. Some of us will be eating.",
                                 "Best segment in television. Don't @ me.")))
