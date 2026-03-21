
import time

from django.conf import settings

from .command import Command, MuxCommand
from world.utils import split_on_all_newlines, get_wordcount, get_defaulthome, get_specialroom
from typeclasses.characters import Character, PlayerCharacter

_TAG_OOC_TARGET = settings.TAG_OOC_TARGET

class CmdOOC(Command):
    """
    Talk or pose out of character in the current room.

    Usage:
        ooc <text>
         -> |Y<OOC>|n Yourname says, "text"
        ooc :<text>
         -> |Y<OOC>|n Yourname text
        ooc :'<text>
         -> |Y<OOC>|n Yourname'text
        ooc ;<text>
         -> |Y<OOC>|n Yournametext
    """

    key = "ooc"
    lock = "cmd:all()"
    help_category = "General"

    _usage = "Usage: ooc <text> -or- ooc :<text>. See help for more details"

    def func(self):

        args = str(self.args.strip())
        caller = self.caller
        
        if not args:
            self.caller.msg(self._usage)
            return
    
        location = caller.location
        if not location:
            caller.msg("|rYou don't seem to have a location. Contact staff.|n")
            return
        
        if not location.can_talk:
            caller.msg("|mYou can't talk here.|n")
            return

        firstline = "|Y<OOC>|n {sender}"
        otherline = "|Y<OOC>|n "
        
        saymode = False

        if args[0] == ":":
            if args[1] == "'":
                args = args[1:]
            else:
                args = f" {args[1:]}"
        elif args[0] == ";":
            args = args[1:]
        else:
            # We don't allow newlines in SAY type messages because they're wrapped in " " and we don't
            # want anything silly to happen with the formatting or anything...
            saymode = True
            args = split_on_all_newlines(args)
            out = [firstline + f' says, "{' '.join(args)}"']

        if not saymode:
            # For other message types 
            out = []
            lines = split_on_all_newlines(args)
            out.append(firstline + lines[0].rstrip())
            for line in lines[1:]:
                line.strip()
                out.append(otherline + line + " ({sender})" if line else "")
            
        location.msg_contents('\n'.join(out), mapping={'sender': self.caller}, from_obj=self.caller)


class CmdSpoof(Command):
    """
    Emit narration into the current room that does not setart with your name. This allows for many
    more choices in how to phrase things, but also lets you look like you're making someone else do
    something, so we append your name to the end of each paragraph in the text for clarity.

    Usage:
        spoof <Probably a lot of text.>
         -> Probably a lot of text. (Yourname)
    """

    key = "spoof"
    aliases = ['sp']
    lock = "cmd:all()"
    help_category = "General"

    _usage = "Usage: spoof <text>"

    def func(self):

        args = self.args.strip()
        caller = self.caller
        
        if not args:
            self.caller.msg(self._usage)
            return
        
        location = caller.location
        if not location:
            caller.msg("|rYou don't seem to have a location. Contact staff.|n")
            return
        
        if not location.can_talk:
            caller.msg("|mYou can't talk here.|n")
            return

        out = []
        paragraphs = split_on_all_newlines(args)

        for paragraph in paragraphs:
            if paragraph:
                paragraph += " ({sender})"

            out.append(paragraph)

        location.msg_contents('\n'.join(out), mapping={'sender': self.caller}, from_obj=self.caller)

        wordcount = get_wordcount(args)

        location.register_last_talk_time(self.caller)
        location.ic_wordcount_loc += wordcount
        if self.caller.location.is_ic_room:
            caller.last_ic_talk_time = time.time()
            caller.ic_wordcount += wordcount


class CmdStats(Command):
    """
    Get the stats of yourself, or compare yourself with another creature.
    (Or see the stats of another, if you're ADMIN+. Compare will always compare.)

    Usage:
      +stats
      +stats <creature>
      +compare <creature>
    """

    key = "+stats"
    aliases = ["+sheet", "+compare"]
    locks = "cmd:all()"
    help_category = "People"

    def func(self):

        caller = self.caller
        args = self.args.strip()
        if not args:
            target = caller
        else:
            target = caller.search(args) #, typeclass=Character)
            if not target:
                return
            if not target.is_typeclass(Character):
                # Because searching by typeclass isn't working fsr
                self.msg(f"{target.get_display_name()} isn't something that can have stats.")
                return
            
        if not target.access(self, "view"):
            self.msg(f"Could not view '{target.get_display_name(caller)}'.")
            return
            
        always_compare = True if self.cmdstring.lower() == '+compare' else False

        sheet = target.get_statblock(caller, always_compare=always_compare)

        self.msg(text=(sheet, {"type": "stats"}), options=None)


class CmdFinger(Command):
    """
    Get extra info about a player and their character. Unlike other examination commands, this one
    can target anyone anywhere.

    Usage:
      +finger <player character>
    """

    key = "+finger"
    locks = "cmd:all()"

    def func(self):

        caller = self.caller

        args = self.args.strip()

        if not args:
            self.msg("Usage: +finger <player character>")
            return
        
        if args in ('self', 'me'):
            target = caller
        else:
            search = PlayerCharacter.objects.search(args)
            if not search:
                self.msg(f"Couldn't find player character '{args}'.")
                return
            if len(search) != 1:
                self.msg(f"Got multiple hits for '{args}'. This shouldn't happen. Please notify staff.")
                return
            target = search[0]

        if not target.access(self, "view"):
            self.msg(f"Could not view '{target.get_display_name(caller)}'.")
            return

        finger = target.get_finger(caller)
        
        self.msg(text=(finger, {"type": "finger"}), options=None)


class CmdFullLook(Command):
    """
    Get all details about a creature in one go. 

    Usage:
      +fulllook [creature]
    """

    key = "+fulllook"
    aliases = "+flook"
    locks = "cmd:all()"
    help_category = "People"

    def func(self):

        caller = self.caller
        args = self.args.strip()
        if not args:
            target = caller
        else:
            target = caller.search(args) #, typeclass=Character)
            if not target:
                return
            if not target.is_typeclass(Character):
                # Because searching by typeclass isn't working fsr
                self.msg(f"{target.get_display_name()} isn't something that can have stats or finger data.")
                return
            
        if not target.access(self, "view"):
            self.msg(f"Could not view '{target.get_display_name(caller)}'.")
            return
   
        if target.is_typeclass(PlayerCharacter):
            target.msg(f"{caller.get_display_name(target)} just looked at {target.get_display_name(target)}.")


        finger = target.get_finger(caller, show_header=True)
        sheet = target.get_statblock(caller, show_header=False)
        desc = target.return_appearance(caller, show_header=False)

        self.msg(text=(''.join((finger,sheet,'\n',desc)), {"type": "stats"}), options=None)


class CmdTeleportOOC(Command):
    """
    Teleport yourself to the OOC nexus, marking where you were on the IC grid to return to with |b+ic|n later.

    Usage:
      +ooc
    """

    key = "+ooc"
    locks = "cmd:all()"
    # help_category = "People"

    def func(self):

        caller = self.caller

        oldloc = caller.location

        if not oldloc.is_ic_room:
            caller.msg(f"{caller.get_display_name(caller)} is already off the IC grid.")
            return

        oocnex = get_specialroom(_TAG_OOC_TARGET)
        oocnex = oocnex if oocnex else get_defaulthome()

        if caller.move_to(oocnex, move_type="ic-ooc"):
            caller.last_ic_room = oldloc
        else:
            caller.msg(f"|mSomething went wrong with moving {caller.get_display_name(caller)}")

        
class CmdTeleportIC(Command):
    """
    Teleport yourself back to the IC grid from where you used |b+ooc|n earlier.

    Usage:
      +ic
    """

    key = "+ic"
    locks = "cmd:all()"
    # help_category = "People"

    def func(self):

        caller = self.caller

        if caller.location.is_ic_room:
            caller.msg(f"{caller.get_display_name(caller)} is already on the IC grid.")
            return
        
        if not caller.last_ic_room:
            caller.msg(f"{caller.get_display_name(caller)} will have to walk.")
            return

        if caller.move_to(caller.last_ic_room, move_type="ic-ooc"):
            caller.last_ic_room = None
        else:
            caller.msg(f"|mSomething went wrong with moving {caller.get_display_name(caller)}")