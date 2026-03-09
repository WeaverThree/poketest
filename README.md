# It's a prototype!

This is an early prototype of a MUSH/MUCK game built on the [evennia](https://github.com/evennia/evennia/) engine.
Not much here for public consumption as of yet.
I'm just making this public to make things easier.

---Weaver

# Todo list!

- Probably need to customize all of the emitting functions anyway.
    - Third person command output for everyone
    - Name colors on command output (partial)
    - Spoof command
    - Change RP trap system to use time since someone emitted text into a room rather than their unidle presence
    - Implement separate comms idle time perhaps
    - Restyle chan, chan/all
    - track wordcount emitted into the world
- ConnectInfo is leaking peoples IPs and shit
- Character creation system

- Stats.
    - Pokémon 6 stats
        - EVs
    - Known moves
    - Equipped moves
    - IC Wordcount
    - Affiliation
        - Faction (Guild, Rogue, Merc, Unaffiliated)
        - Rank
        - Subfaction
    - Abilities
    - Pronouns
    - Orientation
- Dice roller
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

- XP gain:


- Player character death 
    - returned to home after time period with 1hp and 

- uppercase names required

- In character home. Home takes you there
- see unlogged characters
- unlogged characters go home after 24 hours
- rooms that you can home in

- bitch at you if room desc is too short

- start in AUP room
    - staff list command. shows offline staff, with tag about what they do


- must be builder to build. might be able to desc owned rooms but not build from them

- refit helper to plot runner
    - minor powers to make NPCs
- helper / plotrunner
    - can make NPCs and puppets and stuff
    - can't build, modify descs

- authorization keyring object
- room claim system, lockable doors, auto updating exit names

- ooc nexus
    -master room not needed
    -character home
    -nexus room
        -ic portal
    -staff home
    -jail
    