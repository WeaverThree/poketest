# It's a prototype!

This is an early prototype of a MUSH/MUCK game built on the [evennia](https://github.com/evennia/evennia/) engine.
Not much here for public consumption as of yet.
I'm just making this public to make things easier.

---Weaver

# Todo list!

- ConnectInfo is leaking peoples IPs and shit
- Character creation system

- Stats.
    - EVs
    - Affiliation
        - Faction (Guild, Rogue, Merc, Unaffiliated)
        - Rank
        - Subfaction
    - Shortdesc
    - Orientation
    - Player
- +ic +ooc
- skill swapper object

- RP vote system
    - number of votes per day
    - vote for someone once per day
        - if they aren't idle
    - gives passive XP gain
    - vote values
        -125 1st in a day
        -150 2nd in a day
        -150 3rd in a day
        -150 4th in a day
        etc.
    1 vote a day should be about a year and a half of real time, but being involved in a lot of big scenes should be more like 6 months.

    2 votes a day every day for a week = two tokens - 1 token = 1000 points

- 255 character desc size

- follow command
- find command
- special abilities

- Player character death 
    - returned to home after time period with 1hp and delevling: remove 4 EV from random stat 6 times

- In character home. Home takes you there
- unlogged characters go home after 24 hours
- rooms that you can home in

- must be builder to build. might be able to desc owned rooms but not build from them

- refit helper to plot runner
    - minor powers to make NPCs
- helper / plotrunner
    - can make NPCs and puppets and stuff
    - can't build, modify descs
    
    - jail command

- DARK players? Admin+ anyway?

- Zone DB with names and descs

- Feature field dictionary for players and locations
    - "'s" look feature
- +use command for moves
- Roll percent for percent moves
- but no statistical move implementation

- special teleport command for teleport users
    - other movement abilities?

- daily refresh
- 24-hour sleepers


- Figure out what we're going to do about UTF characters
- Test other mu clients


- Better exceptions for reading csv files in mondata?

- Move validation inside chargen functions in Character? Probably not but thought.

- authorization keyring object
- room claim system, lockable doors, auto updating exit names

- Economy
    - Consumables
        - Reusable item references?
    - Inventory
        - 6 Items Equipped
        - Rest are considered banked
    - Room rent for rogues?
    - Rank based rooms for guild?
    - Shop / business ownership, for rogues?


# Notes

- Max ability len = 16 characters
- Max move len = 27 characters "Soul-Stealing 7-Star Strike", a Z-move
- Max move len w/o specials = 16 characters "Parabolic Charge"

- Issue with the table used in InventoryCmd. I think it's because a single character is colored at
  the start of the line in the table its using. I worked around this by putting item quantities in
  parens for now. . . . Same problem happens with EvTable. I got around it by using an ASCII Null \000
