
import time

from .command import Command, MuxCommand
from world.utils import split_on_all_newlines, get_wordcount
from typeclasses.characters import Character

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

        out = ["|Y<OOC>|n {sender}"]
        if args[0] == ":":
            if args[1] == "'":
                out.append(args[1:])
            else:
                out.append(f" {args[1:]}")
        elif args[0] == ";":
            out.append(args[1:])
        else:
            out.append(f' says, "{args}"')

        location.msg_contents(''.join(out), mapping={'sender': self.caller}, from_obj=self.caller)


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

        location.last_ic_talk_time_loc = time.time()
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
            
        always_compare = True if self.cmdstring.lower() == 'compare' else False

        sheet = target.get_statblock(caller, always_compare=always_compare)

        self.msg(text=(sheet, {"type": "stats"}), options=None)