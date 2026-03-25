# It's a prototype!

This is an early prototype of a MUSH/MUCK game built on the [evennia](https://github.com/evennia/evennia/) engine.
Not much here for public consumption as of yet.
I'm just making this public to make things easier.

---Weaver

# Todo list! - MVP

- Way to set faction/rank

- skill swapper object

- vote for offline people? idle people? talk IC inside the last hour maybe?

- special teleport command for teleport users
    - other movement abilities?

- prune unused zones (no name no rooms no desc) on @zoneinfo

- modify AUP room for minimal jail use

- change setinfo and other commands that use target=var,data or target=var:data to use target/var=data, like @set does.

- Figure out what we're going to do about UTF characters
- Test other mu clients

# Todo List - Future

- jail command

- DARK players? Admin+ anyway?

- In character home. Home takes you there
- rooms that you can home in

- authorization keyring object
- room claim system, lockable doors, auto updating exit names
- must be builder to build. might be able to desc owned rooms but not build from them

- Roll percent for percent moves
- but no statistical move implementation

- refit helper to plot runner
    - minor powers to make NPCs
- helper / plotrunner
    - can make NPCs and puppets and stuff
    - can't build, modify descs
    - createnpc command
    - checknpc command
    - access to admin chargen but only allow targeting NPCs

- total pp shown on moves used and staff levels 

- Player character death 
    - returned to home after time period with 1hp and delevling: remove 4 EV from random stat 6 times
    
- Economy
    - Consumables
        - Reusable item references?
    - Inventory
        - 6 Items Equipped
        - Rest are considered banked
    - Room rent for rogues?
    - Rank based rooms for guild?
    - Shop / business ownership, for rogues?

- Subfaction

# Notes

- Max ability len = 16 characters
- Max move len = 27 characters "Soul-Stealing 7-Star Strike", a Z-move
- Max move len w/o specials = 16 characters "Parabolic Charge"

- Issue with the table used in InventoryCmd. I think it's because a single character is colored at
  the start of the line in the table its using. I worked around this by putting item quantities in
  parens for now. . . . Same problem happens with EvTable. I got around it by using an ASCII Null \000

- 1 vote a day should be about a year and a half of real time, but being involved in a lot of big scenes should be more like 6 months.