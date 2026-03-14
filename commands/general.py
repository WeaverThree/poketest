
import time

from .command import Command
from world.utils import split_on_all_newlines, get_wordcount

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
        
        if not args:
            self.caller.msg(self._usage)
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

        self.caller.location.msg_contents(''.join(out), mapping={'sender': self.caller}, from_obj=self.caller)


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
        
        if not args:
            self.caller.msg(self._usage)
            return
        
        out = []
        paragraphs = split_on_all_newlines(args)

        for paragraph in paragraphs:
            if paragraph:
                paragraph += " ({sender})"

            out.append(paragraph)

        self.caller.location.msg_contents('\n'.join(out), mapping={'sender': self.caller}, from_obj=self.caller)

        wordcount = get_wordcount(args)

        self.caller.location.last_ic_talk_time_loc = time.time()
        self.caller.location.ic_wordcount_loc += wordcount
        if self.caller.location.is_ic_room:
            self.caller.last_ic_talk_time = time.time()
            self.caller.ic_wordcount += wordcount
