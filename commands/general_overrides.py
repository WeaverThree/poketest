from .command import MuxCommand

from evennia.utils import utils


class CmdPose(MuxCommand):
    """
    strike a pose

    Usage:
      pose <pose text> pose's <pose text>

    Example:
      pose is standing by the wall, smiling.
       -> others will see:
      Tom is standing by the wall, smiling.

    Describe an action being taken. The pose text will automatically begin with your name.

    All commands strip leading space if followed by [',:] ; always does.
    """

    key = "pose"
    aliases = [":", "emote", ";"]
    locks = "cmd:all()"
    arg_regex = ""

    # we want to be able to pose without whitespace between
    # the command/alias and the pose (e.g. :pose)
    arg_regex = None

    def parse(self):
        """
        Custom parse the cases where the emote starts with some special letter, such as 's, at which
        we don't want to separate the caller's name and the emote with a space.

        Include a semicolon command fallback for compatability.
        """
        args = self.args
        if args and not args[0] in ["'", ",", ":"] and not self.cmdstring == ';':
            args = " %s" % args.strip()
        self.args = args

    def func(self):
        """Hook function"""
        if not self.args:
            msg = "Do something, not nothing."
            self.msg(msg)
        else:
            msg = "{sender}" + self.args
            self.caller.location.msg_contents(
                text=(msg, self.args, {"type": "pose"}),
                 mapping={'sender':self.caller}, from_obj=self.caller)
            

class CmdHome(MuxCommand):
    """
    move to your character's home location

    Usage:
      home

    Teleports you to your home location.
    """

    key = "home"
    locks = "cmd:perm(home) or perm(Builder)"
    arg_regex = r"$"

    def func(self):
        """Implement the command"""
        caller = self.caller
        home = caller.home
        if not home:
            caller.msg("No home set. Probably contact staff.")
        elif home == caller.location:
            caller.msg("Already home.")
        else:
            caller.msg("Returning...")
            caller.move_to(home, move_type="teleport")


class CmdLook(MuxCommand):
    """
    look at location or object

    Usage:
      look
      look <obj>
      look *<account>

    Observes your location or objects in your vicinity.
    """

    key = "look"
    aliases = ["l", "ls"]
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """
        Handle the looking.
        """
        caller = self.caller
        if not self.args:
            target = caller.location
            if not target:
                caller.msg("No location to look at. This is an error. Contact staff.")
                return
        else:
            target = caller.search(self.args)
            if not target:
                return
        desc = caller.at_look(target)
        # add the type=look to the outputfunc to make it
        # easy to separate this output in client.
        self.msg(text=(desc, {"type": "look"}), options=None)


class CmdInventory(MuxCommand):
    """
    view inventory

    Usage:
      inventory
      inv

    Shows your inventory.
    """

    key = "inventory"
    aliases = ["inv", "i"]
    locks = "cmd:all()"
    arg_regex = r"$"

    def func(self):

        items = self.caller.contents
        if not items:
            string = f"{self.caller.get_display_name(self.caller)} isn't carrying anything."
        else:
            from evennia.utils.ansi import raw as raw_ansi

            # Might be some kind of bug with this table and single character colors at the beginning
            # of the first item...
            table = self.styled_table(border="header")
            for key, desc, _ in utils.group_objects_by_key_and_desc(items, caller=self.caller):
                desc = desc if desc else "" # In case we get a None somehow?
                desc = desc.split('\n')[0] # Only take first line
                desc = desc.split('|/')[0]
                table.add_row(f"{key}|n", f"{utils.crop(raw_ansi(desc), width=50)}|n")
            string = f"{self.caller.get_display_name(self.caller)} |wis carrying:\n{table}"

        self.msg(text=(string, {"type": "inventory"}))



class NumberedTargetCommand(MuxCommand):
    """
    A class that parses out an optional number component from the input string. This
    class is intended to be inherited from to provide additional functionality, rather
    than used on its own.
    """

    def parse(self):
        """
        Parser that extracts a `.number` property from the beginning of the input string.

        For example, if the input string is "3 apples", this parser will set `self.number = 3` and
        `self.args = "apples"`. If the input string is "apples", this parser will set
        `self.number = 0` and `self.args = "apples"`.

        """
        super().parse()
        self.number = 0
        if getattr(self, "lhs", None):
            # handle self.lhs but don't require it
            count, *args = self.lhs.split(maxsplit=1)
            # we only use the first word as a count if it's a number and
            # there is more text afterwards
            if args and count.isdecimal():
                self.number = int(count)
                self.lhs = args[0]
        if self.args:
            # check for numbering
            count, *args = self.args.split(maxsplit=1)
            # we only use the first word as a count if it's a number and
            # there is more text afterwards
            if args and count.isdecimal():
                self.args = args[0]
                # we only re-assign self.number if it wasn't already taken from self.lhs
                if not self.number:
                    self.number = int(count)


class CmdGet(NumberedTargetCommand):
    """
    pick up something

    Usage:
      get <obj>

    Picks up an object from your location and puts it in your inventory.
    """

    key = "get"
    aliases = "grab"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):

        caller = self.caller

        if not self.args:
            self.msg("Get what?")
            return
        objs = caller.search(self.args, location=caller.location, stacked=self.number)
        if not objs:
            return
        # the 'stacked' search sometimes returns a list, sometimes not, so we make it always a list
        # NOTE: this behavior may be a bug, see issue #3432
        objs = utils.make_iter(objs)

        if len(objs) == 1 and caller == objs[0]:
            self.msg("Self-referential containment denied.")
            return

        # if we aren't allowed to get any of the objects, cancel the get
        for obj in objs:
            # check the locks
            if not obj.access(caller, "get"):
                if obj.db.get_err_msg:
                    self.msg(obj.db.get_err_msg)
                else:
                    self.msg("Can't get that.")
                return
            # calling at_pre_get hook method
            if not obj.at_pre_get(caller):
                return

        moved = []
        # attempt to move all of the objects
        for obj in objs:
            if obj.move_to(caller, quiet=True, move_type="get"):
                moved.append(obj)
                # calling at_get hook method
                obj.at_get(caller)

        if moved:
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.location.msg_contents(
                "{picker} picked up {obj_name}.", 
                mapping={'picker':caller, 'obj_name':obj_name}, from_obj=caller
            )
        else:
            self.msg(f"{obj[0].get_display_name(caller)} can't be picked up.")



class CmdDrop(NumberedTargetCommand):
    """
    drop something

    Usage:
      drop <obj>

    Lets you drop an object from your inventory into the location you are currently in.
    """

    key = "drop"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):

        caller = self.caller
        if not self.args:
            caller.msg("Drop what?")
            return

        # Because the DROP command by definition looks for items
        # in inventory, call the search function using location = caller
        objs = caller.search(
            self.args,
            location=caller,
            nofound_string=f"Not carrying {self.args}.",
            multimatch_string=f"Carrying more than one {self.args}:",
            stacked=self.number,
        )
        if not objs:
            return
        # the 'stacked' search sometimes returns a list, sometimes not, so we make it always a list
        # NOTE: this behavior may be a bug, see issue #3432
        objs = utils.make_iter(objs)

        # if any objects fail the drop permission check, cancel the drop
        for obj in objs:
            # Call the object's at_pre_drop() method.
            if not obj.at_pre_drop(caller):
                return

        # do the actual dropping
        moved = []
        for obj in objs:
            if obj.move_to(caller.location, quiet=True, move_type="drop"):
                moved.append(obj)
                # Call the object's at_drop() method.
                obj.at_drop(caller)

        if moved:
            # none of the objects were successfully moved
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.location.msg_contents(
                "{dropper} dropped {obj_name}.", 
                mapping={'dropper':caller, 'obj_name':obj_name}, from_obj=caller
            )
        else:
            self.msg(f"{obj.get_display_name(caller)} can't be dropped.")


class CmdGive(NumberedTargetCommand):
    """
    give away something to someone

    Usage:
      give <inventory obj> <to||=> <target>

    Gives an item from your inventory to another person, placing it in their inventory.
    """

    key = "give"
    rhs_split = ("=", " to ")  # Prefer = delimiter, but allow " to " usage.
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):

        caller = self.caller
        if not self.args or not self.rhs:
            caller.msg("Usage: give <inventory object> = <target>")
            return
        # find the thing(s) to give away
        to_give = caller.search(
            self.lhs,
            location=caller,
            nofound_string=f"Not carrying {self.lhs}.",
            multimatch_string=f"Carrying more than one {self.lhs}:",
            stacked=self.number,
        )
        if not to_give:
            return
        # find the target to give to
        target = caller.search(self.rhs)
        if not target:
            return

        # the 'stacked' search sometimes returns a list, sometimes not, so we make it always a list
        # NOTE: this behavior may be a bug, see issue #3432
        to_give = utils.make_iter(to_give)

        singular, plural = to_give[0].get_numbered_name(len(to_give), caller)
        if target == caller:
            caller.msg(
                f"The {plural if len(to_give) > 1 else singular} {'are' if len(to_give) > 1 else 'is'} already there."
            )
            return

        # if any of the objects aren't allowed to be given, cancel the give
        for obj in to_give:
            # calling at_pre_give hook method
            if not obj.at_pre_give(caller, target):
                return

        # do the actual moving
        moved = []
        for obj in to_give:
            if obj.move_to(target, quiet=True, move_type="give"):
                moved.append(obj)
                # Call the object's at_give() method.
                obj.at_give(caller, target)

        if not moved:
            caller.msg(f"Could not give that to {target.get_display_name(caller)}.")
        else:
            obj_name = to_give[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.msg(f"{caller.get_display_name(caller)} gives {obj_name} to {target.get_display_name(caller)}.")
            target.msg(f"{caller.get_display_name(target)} gives you {obj_name}.")


class CmdSetDesc(MuxCommand):
    """
    describe yourself

    Usage:
      setdesc <description>

    Add a description to yourself. This will be visible to people when they look at you.
    """

    key = "setdesc"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        """add the description"""

        if not self.args:
            self.msg("You must add a description.")
            return

        self.caller.db.desc = self.args.strip()
        self.msg("You set your description.")
