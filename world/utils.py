import re

from django.conf import settings
import evennia
from evennia.utils import display_len, logger



_MU_NEWLINE_RE = re.compile(r"%[rRnN]", re.MULTILINE)
_MU_TAB_RE = re.compile(r"%[tT]", re.MULTILINE)
_MU_BLANK_RE = re.compile(r"%[bB]", re.MULTILINE)

_MULTI_NEWLINE_RE = re.compile(r"\|/|\n")

def replace_mush_escapes(msg):
    """
    Handle MUSH special characters with evennia ones. Replaces %r->|/, %b->|_, %t->|-.
    
    Does not handle escaping %'s or anything, it's a pretty dumb function. 
    """
    msg = _MU_NEWLINE_RE.sub("|/", msg)
    msg = _MU_TAB_RE.sub("|-", msg)
    msg = _MU_BLANK_RE.sub("|_", msg)
    return msg


def split_on_all_newlines(text):
    """Splits the incoming text on |/ and newline characters. More will be added if nessecary."""
    return _MULTI_NEWLINE_RE.split(text)


def get_wordcount(text):
    total = 0
    for para in split_on_all_newlines(text):
        total += len(para.strip().split())
    return total


def anyone_notice(target, message):
    """Error message for anyone to see. Registers for display after command."""
    target.register_post_command_message(f"|[r|X Reminder |n|r {message}|n")

def builder_notice(target, message):
    """Error message for builder+ accounts to see. Registers for display after command."""
    if target.permissions.check("Builder"):
        target.register_post_command_message(f"|[r|X Builder Notice |n|r {message}|n")

def dev_notice(target, message):
    """Error message for devloper accounts to see. Registers for display after command."""
    if target.permissions.check("Developer"):
        target.register_post_command_message(f"|[r|X Dev Notice |n|r {message}|n")


def header_two_slot(width, slot1, slot2=None, headercolor="|R", color1="|w", color2="|w"):
    """
    Fill width characters with a header line wrapped around slot1 (left) and slot2 (right).
    Slot2 is optional. If given something false, it won't be given a space.
    """

    if slot2:
        header_left = f"{headercolor}--< {color1}{slot1} {headercolor}>-"
        header_right = f"{headercolor}-< {color2}{slot2} {headercolor}>--|n"
        fill = width - display_len(header_left) - display_len(header_right)
    else:
        header_left = f"{headercolor}--< {color1}{slot1} {headercolor}>-"
        header_right = "|n"
        fill = width - display_len(header_left) + display_len(headercolor)


    return "".join((header_left, "-" * fill, header_right))


def get_specialroom(tag):
    """Gets the room as set by @setspecialroom."""

    objs = evennia.search_tag(tag, category="SpecialRoom")
    if len(objs) > 1:
        logger.warn(f"Too many {tag} rooms, using {objs[0]}.")
    room = objs[0] if objs else None
    if room and not room.is_typeclass("typeclasses.rooms.Room"):
        logger.error(f"Special Room {room} is not a room!")
        return None # So we don't call Room things on another object type elsewhere
    else:
        return room

def get_defaulthome():
    """Get the default home room. Searches for tagged home first then falls back to DBREF setting."""
    
    home = get_specialroom(settings.TAG_DEFAULT_HOME)
    if not home:
        logger.warn(f"No default home has been tagged. Use '@setspecialroom {settings.TAG_DEFAULT_HOME}' somewhere.")
        objs = evennia.search_object(settings.DEAFULT_HOME)
        if not objs:
            logger.error("NO FALLBACK DEFAULT HOME! This will probably cause errors.")
            return None
        home = objs[0]
    return home


def is_unpuppted_pc(obj):
    """To filter out player characters that are logged out against most modifying commands with a custom message."""
    return obj and obj.is_typeclass("typeclasses.characters.PlayerCharacter") and not obj.has_account