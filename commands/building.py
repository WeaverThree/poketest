
from collections import defaultdict

import evennia

from .command import MuxCommand, Command

from typeclasses.rooms import Room

_VALID_ROOM_TAGS = [
    "defaulthome",
    "jail",
    "ooctarget",
    "sleeperhome",
    "spawn",
]

class CmdZone(Command):
    """
    Sets the zone for the current area. Equivilant to @tag here=zonename:Zone, but ensures that any
    prior zone tagging is also removed. Does not let you clear zones because no room should be
    unzoned.

    Usage:
        @zone <zone name>
    """
    key = "@zone"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    _usage = "Usage: @zone <zone name>"

    def func(self):
        
        newzone = self.args.strip().lower()

        if not newzone:
            self.caller.msg(self._usage)
            return

        target = self.caller.location

        if not target:
            self.caller.msg(
                "You don't seem to have a location. " 
                "This is probably a serious problem, but get one before using this command."
            )
            return
        
        if not isinstance(target, Room):
            self.caller.msg("You're not in any kind of room. This command only works on rooms. Please come again.")
            return

        oldzones = target.tags.get(category="Zone", return_list=True)
        if not oldzones:
            oldzones = "<nothing>"
        elif len(oldzones) == 1:
            oldzones = oldzones[0]
        else:
            self.caller.msg("|RFound more than one zone to replace. Fixing that.|n")
            oldzones = ', '.join(oldzones)
        
        target.tags.clear(category="Zone")
        target.tags.add(newzone, category="Zone")

        self.caller.msg(f"Updated zone of {target.get_display_name(self.caller)} from {oldzones} to {newzone}")
        

class CmdSetSpecialRoom(Command):
    """
    Sets the special room flag for the current location. Equivilant to @tag here=flag:SpecialRoom,
    but ensures that only one room in the system has any given special flag.

    Lists special rooms if no input given.

    Usage:
        @setspecialroom [flag]
    """
    key = "@setspecialroom"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    _usage = "Usage: @setspecialroom [flag]"

    def func(self):

        caller = self.caller
        
        # Going to need this data no matter what happenes

        all_special_rooms = defaultdict(set)
        objs = evennia.search_tag(category="SpecialRoom")
        for obj in objs:
            tags = obj.tags.get(category="SpecialRoom", return_list=True)
            if not isinstance(obj, Room):
                caller.msg(
                    f"Found non-room object {obj.get_display_name()} with SpecialRoom tags "
                    f"{', '.join(tags)}, removing them."
                )
                obj.tags.clear(category="SpecialRoom")
                continue

            for tag in tags:
                all_special_rooms[tag].add(obj)

        newspecial = self.args.strip().lower()

        if not newspecial:
            if not any(all_special_rooms.values()):
                caller.msg("No special room tags have been set. That's probably not great.")
            out = ['']
            for tag in sorted(all_special_rooms):
                objs = []
                for obj in all_special_rooms[tag]:
                    objs.append(f"{obj.get_display_name(caller)}{obj.get_extra_display_name_info(caller)}")
                out.append(f"|b{tag}|n: {', '.join(objs)}")
                if len(objs) > 1:
                    out.append(" |RMore than one of this tag exists. You should fix this by tagging the correct room.|n")
            caller.msg('\n'.join(out))
            return
        
        if newspecial not in _VALID_ROOM_TAGS:
            caller.msg(
                f"Valid special tags are {', '.join(f"|b{tag}|n" for tag in _VALID_ROOM_TAGS)}. "
                "Please pick one of these."
            )
            return

        target = caller.location

        if not target:
            caller.msg(
                "You don't seem to have a location. " 
                "This is probably a serious problem, but get one before using this command."
            )
            return
        
        if not target.is_typeclass(Room):
            caller.msg("You're not in any kind of room. This command only works on rooms. Please come again.")
            return
        
        previousrooms = all_special_rooms.get(newspecial, set())

        if len(previousrooms) == 1 and target in previousrooms:
            caller.msg(
                f"{target.get_display_name(caller)}{target.get_extra_display_name_info(caller)} "
                f"is already |b{newspecial}|n."
            )


        for room in previousrooms:
            room.tags.remove(newspecial, category="SpecialRoom")

        target.tags.add(newspecial, category="SpecialRoom")

        if not previousrooms:
            caller.msg(
                f"Set {target.get_display_name(caller)}{target.get_extra_display_name_info(caller)} "
                f"as |b{newspecial}|n."
                )
        else:
            previousroomdescs = [
                f"{room.get_display_name(caller)}{room.get_extra_display_name_info(caller)}"
                for room in previousrooms
            ]

            caller.msg(
                f"Moved |b{newspecial}|n from {', '.join(previousroomdescs)} to "
                f"{target.get_display_name(caller)}{target.get_extra_display_name_info(caller)}"
            )
        


        

        


