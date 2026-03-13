# It's a prototype!

This is an early prototype of a MUSH/MUCK game built on the [evennia](https://github.com/evennia/evennia/) engine.
Not much here for public consumption as of yet.
I'm just making this public to make things easier.

---Weaver

# Todo list!

- Probably need to customize all of the emitting functions anyway.
    - Implement separate comms idle time perhaps
    - Restyle chan, chan/all
- ConnectInfo is leaking peoples IPs and shit
- Character creation system

- Stats.
    - EVs
    - Affiliation
        - Faction (Guild, Rogue, Merc, Unaffiliated)
        - Rank
        - Subfaction
    - Abilities
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

    delevling: remove 1 EV from random stat 6 times

    follow command
    find command
    special abilities

- Player character death 
    - returned to home after time period with 1hp and 

- In character home. Home takes you there
- see unlogged characters
- unlogged characters go home after 24 hours
- rooms that you can home in

- start in AUP room

- System for denying unlogged player target of commands.

- must be builder to build. might be able to desc owned rooms but not build from them

- refit helper to plot runner
    - minor powers to make NPCs
- helper / plotrunner
    - can make NPCs and puppets and stuff
    - can't build, modify descs
    
- ooc nexus
    -master room not needed
    -character home
    -nexus room
        -ic portal
    -staff home
    -jail
        - jail command

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
