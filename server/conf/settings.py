r"""
Evennia settings file.

The available options are found in the default settings file found here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to change; this will make sure that you don't overload
upstream updates unnecessarily.

When changing a setting requiring a file system path (like path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to
reference your game folder and the Evennia library folders respectively. Python paths (path.to.module) should be given
relative to the game's root folder (typeclasses.foo) whereas paths within the Evennia library needs to be given
explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can put secret game- or server-specific settings in
secret_settings.py.

"""

import math

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# MonMU specific settings
######################################################################

# Currently only applies to newly species-set characters
CHARACTER_IV_TOKEN_BUDGET = math.ceil((6 * 16) / 3)

STARTING_MOVES = 3
MAX_EQUIPPED_MOVES = 6


RP_TRAP_MOVE_DELAY = 15 # Seconds
RP_TRAP_IDLE_TIME = 60 * 5 
GENERAL_IDLE_TIME = 60 * 10 # How long until names go dim from idle
TALKERS_LIST_HOLD_TIME = 60 * 60 * 6 # 6 hours

OUR_WIDTH = 74 # This controls monmu customized stuff, not evennia default
DESIRED_MIN_DESC = 255 # Bitch when descriptions are shorter

# Valid room types for @setspecialroom

VALID_ROOM_TAGS = [
    "defaulthome",
    "jail",
    "ooctarget",
    "sleeperhome",
    "spawn",
]

# System will use these tagged rooms if they exist over START_LOCATION and DEFAULT_HOME, which can
# be left set to #2 as a final fallback

TAG_DEFAULT_HOME = "defaulthome"
TAG_JAIL_LOCATION = "jail"
TAG_OOC_TARGET = "ooctarget"
TAG_SLEEPER_SWEEPER_DEST = "sleeperhome"
TAG_START_LOCATION = "spawn"

REGISTRATION_PASSTOKEN = None # Please put me in secret_settings.py - string with no spaces

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "Pokémorph Below 2.0α"
BASE_CHARACTER_TYPECLASS = "typeclasses.characters.PlayerCharacter"
COMMAND_DEFAULT_CLASS = "commands.command.MuxCommand"


# Global scripts started here will be available through 'evennia.GLOBAL_SCRIPTS.key'. The scripts
# will survive a reload and be recreated automatically if deleted. Each entry must have the script
# keys, whereas all other fields in the specification are optional. If 'typeclass' is not given,
# BASE_SCRIPT_TYPECLASS will be assumed.  Note that if you change typeclass for the same key, a new
# Script will replace the old one on `evennia.GLOBAL_SCRIPTS`.
GLOBAL_SCRIPTS = {
    # 'key': {'typeclass': 'typeclass.path.here',
    #         'repeats': -1, 'interval': 50, 'desc': 'Example script'},
    'mondata': {'typeclass': 'typeclasses.scripts.mondata.MonData',},
    'crons': {'typeclass': 'typeclasses.scripts.crons.Crons',},
}



WEBSERVER_ENABLED = True
NEW_ACCOUNT_REGISTRATION_ENABLED = False


TIME_ZONE = "America/Los_Angeles"
TIME_FACTOR = 1.0
MAX_CHAR_LIMIT = 20000
IDLE_TIMEOUT = 60 * 60 # 1 hour


# Different Multisession modes allow a player (=account) to connect to the
# game simultaneously with multiple clients (=sessions).
#  0 - single session per account (if reconnecting, disconnect old session)
#  1 - multiple sessions per account, all sessions share output
#  2 - multiple sessions per account, one session allowed per puppet
#  3 - multiple sessions per account, multiple sessions per puppet (share output)
#      session getting the same data.
MULTISESSION_MODE = 0


CMD_IGNORE_PREFIXES = ""

# --- Channel Settings ---

# The mudinfo channel is a read-only channel used by Evennia to replay status messages, connection info etc to staff.
# The superuser will automatically be subscribed to this channel. If set to None, the channel is disabled and status
# messages will only be logged (not recommended).
CHANNEL_MUDINFO = {
    "key": "MudInfo",
    "aliases": "",
    "desc": "Status log",
    "locks": "control:perm(Developer);listen:perm(Admin);send:none()",
}
# Optional channel (same form as CHANNEL_MUDINFO) that will receive connection messages like ("<account> has
# (dis)connected"). While the MudInfo channel will also receieve this info, this channel is meant for non-staffers. If
# None, this information will only be logged.
CHANNEL_CONNECTINFO = {
    "key": "ConnectInfo",
    "aliases": "",
    "desc": "Connection log",
    "locks": "control:perm(Developer);listen:all();send:none()",
}
# New accounts will auto-sub to the default channels given below (but they can unsub at any time). Traditionally, at
# least 'public' should exist. Entries will be (re)created on the next reload, but removing or updating a same-key
# channel from this list will NOT automatically change/remove it in the game, that needs to be done manually. Note: To
# create other, non-auto-subbed channels, create them manually in server/conf/at_initial_setup.py.
DEFAULT_CHANNELS = [
    {
        "key": "Staff",
        "aliases": (),
        "desc": "Staff channel",
        "locks": "control:perm(Admin);listen:perm(Builder);send:perm(Builder)",
    },
    {
        "key": "Public",
        "aliases": ("pub",),
        "desc": "Public discussion, general OOC",
        "locks": "control:perm(Admin);listen:attr(accepted_rules);send:attr(accepted_rules)",
    },
    {
        "key": "Guild",
        "aliases": (),
        "desc": "Guild OOC",
        "locks": "control:perm(Admin);listen:attr(approved);send:attr(approved)",
    },
    {
        "key": "Rogue",
        "aliases": (),
        "desc": "Rogue OOC",
        "locks": "control:perm(Admin);listen:attr(approved);send:attr(approved)",
    },
    {
        "key": "Mercenary",
        "aliases": ("merc",),
        "desc": "Mercenary OOC",
        "locks": "control:perm(Admin);listen:attr(approved);send:attr(approved)",
    },
    {
        "key": "Incoming",
        "aliases": ("inc",),
        "desc": "Players Before Accepting",
        "locks": "control:perm(Admin);listen:attr(accepted_rules, False) or perm(Admin);send:attr(accepted_rules, False) or perm(Admin)",
    },
]

STARTING_CHANNELS = ["Incoming"]
REMOVE_ON_ACCEPT_CHANNELS = ["Incoming"]
ADD_ON_ACCEPT_CHANNELS = ["Public"]
ADD_ON_AUTHORIZE_CHANNELS = ["Guild", "Rogue", "Mercenary"]





######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
