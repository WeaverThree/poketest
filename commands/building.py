
from collections import defaultdict

from django.conf import settings
import evennia
from evennia.utils import evtable, crop, display_len

from .command import MuxCommand, Command
from typeclasses.rooms import Room
from world.utils import header_two_slot, wrapif


_VALID_ROOM_TAGS = settings.VALID_ROOM_TAGS 
_WIDTH = settings.OUR_WIDTH

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
            self.msg(self._usage)
            return

        target = self.caller.location

        if not target:
            self.msg(
                "You don't seem to have a location. " 
                "This is probably a serious problem, but get one before using this command."
            )
            return
        
        if not target.is_typeclass(Room):
            self.msg("You're not in any kind of room. This command only works on rooms. Please come again.")
            return

        oldzones = target.tags.get(category="Zone", return_list=True)
        if not oldzones:
            oldzones = "<nothing>"
        elif len(oldzones) == 1:
            oldzones = oldzones[0]
        else:
            self.msg("|RFound more than one zone to replace. Fixing that.|n")
            oldzones = ', '.join(oldzones)
        
        target.tags.clear(category="Zone")
        target.tags.add(newzone, category="Zone")

        self.msg(f"Updated zone of {target.get_display_name(self.caller)} from {oldzones} to {newzone}")
        

class CmdZoneInfo(MuxCommand):
    """
    Sets info about a zone.
    
    Usage:
        @zoneinfo -> returns information about zones that exist
        @zoneinfo zone -> returns full info about one zone
        @zoneinfo zone/desc=zone desc goes here
        @zoneinfo zone/name=Zone Fullname
    """

    _usage = "USAGE: @zoneinfo [zone][/desc||/name=<data>]"

    key = "@zoneinfo"
    locks = "cmd:perm(Builder)"
    help_category = "Building"

    def func(self):

        # General setup section -

        zonedb = evennia.GLOBAL_SCRIPTS.zonedb

        caller = self.caller

        zoneuses = defaultdict(int)
        unzoned = 0

        for room in Room.objects.all_family():

            zone = room.tags.get(category="Zone", return_list=True)
            if not zone:
                unzoned += 1
                continue
            elif len(zone) == 1:
                zone = zone[0]
            else:
                self.msg(
                    f"|RFound more than one zone on |n{room.get_display_name(caller)}|R. "
                    "You should fix that. Results may be wrong until then|n"
                )
                zone = zone[0]

            if zone not in zonedb.zones:
                zonedb.zones[zone] = {'name': '', 'desc': ''}
            zoneuses[zone] += 1
        
        # Get orphans
        for zone in zonedb.zones:
            if zone not in zoneuses:
                zoneuses[zone] = 0

        if not self.args:
            # Report section -
       
            table = evtable.EvTable("|wRooms|n", "|wZone Tag|n", "|wZone Name|n", "|wZone Desc|n", border_width=0)
            table.reformat_column(0, align='r')

            for count, zone in reversed(sorted([(count, zone) for (zone, count) in zoneuses.items()])):
                name = zonedb.zones[zone]['name']
                desc = zonedb.zones[zone]['desc']
                table.add_row(
                    wrapif("|Y", f"{count:2d}", "|n", not count),
                    wrapif("|Y", zone, "|n", not count),
                    name if name else "|B<NOT SET>|n",
                    f"{crop(desc, 50, '…')} |B[{display_len(desc)} chars]|n",
                )
            
            header = header_two_slot(_WIDTH, "|wRoom Zones Report|n", headercolor="|Y")
            unzonedline = f" |R{unzoned:5d} unzoned rooms.|n" if unzoned else ''
            
            self.msg(f"{header}\n{table}\n{unzonedline}\n")
            return
        
        # More setup

        rhs = self.rhs
        lhs = self.lhs

        split = [part.strip() for part in lhs.split('/',1)]
        
        targetzone = split[0]
        action = split[1] if len(split) == 2 else None
    
        if not targetzone:
            self.msg(self._usage)
            return
        
        if targetzone not in zonedb.zones:
            self.msg(f"Could not find zone '{targetzone}'.")
            return
        
        # Single zone report:

        if not rhs:
            if action:
                self.msg(self._usage)
                return
            
            zone = zonedb.zones[targetzone]
            name = zone['name']
            desc = zone['desc']
            count = zoneuses[targetzone]
            
            self.msg(
                f" |YZone Tag:|n {targetzone:10} |YZone Name:|n {name:20} |YUsed on |b{count}|Y rooms.|n\n" 
                f"{desc}\n"
            )
            return
        
        if rhs:
            if action == 'name':
                zonedb.zones[targetzone]['name'] = rhs
                self.msg(f"Zone {targetzone} name updated.")
            elif action == 'desc':
                zonedb.zones[targetzone]['desc'] = rhs
                self.msg(f"Zone {targetzone} desc updated.")
            else:
                self.msg(self._usage)
                return


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
            if not obj.is_typeclass(Room):
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
        

class CmdFeature(MuxCommand):
    """
    Sets info about a zone.
    
    Usage:
        @feature <target> -> show all features on target
        @feature <target>/<featurename> -> show text of just feature
        @feature <target>/<featurename> = <text> -> Set text of feature
        @feature/del <target>/<featurename> -> remove feature
    """

    _usage = "USAGE: <target>[/featurename [= text]]"

    key = "@feature"
    locks = "cmd:all()"
    help_category = "Building"

    def func(self):

        # General setup section -

        zonedb = evennia.GLOBAL_SCRIPTS.zonedb

        caller = self.caller

        rhs = self.rhs
        lhs = self.lhs

        split = [part.strip() for part in lhs.split('/',1)]
        
        targetname = split[0]
        featurename = split[1] if len(split) == 2 else ''
        featuresearch = featurename.lower()
    
        if not targetname:
            self.msg(self._usage)
            return

        target = caller.search(targetname)
        if not target:
            return

        if not rhs and 'del' not in self.switches:
            if not featuresearch:
                if not target.features:
                    self.msg(f"{target.get_display_name(caller)} has no features.")
                    return
                header = header_two_slot(_WIDTH, f"{target.get_display_name(caller)}|w's Features|n", headercolor='|Y')
                table = evtable.EvTable("|wFeature|n", "|wDesc|n", border_width=0)
                for fsearch in target.features:
                    feat = target.features[fsearch]
                    desc = feat['desc']
                    name = feat['name']
                    desc = f"{crop(desc, 50, '…')} |B[{display_len(desc)} chars]|n"
                    table.add_row(name, desc)

                self.msg(f"{header}\n{table}\n")

            elif featuresearch in target.features: 
                feat = target.features[featuresearch]
                name = feat['name']
                desc = feat['desc']
                self.msg(
                    f"|Y - |n{target.get_display_name(caller)}|Y's {name} -> |n{desc}\n"
                )
            else:
                self.msg(f"{target.get_display_name(caller)} has no feature '{featuresearch}'")
            return

        # At this point we have an = so permissions come into play

        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            self.msg(
                f"{caller.get_display_name(caller)} doesn't have permission to edit "
                f"the features of {target.get_display_name(caller)}."
            )
            return

        if not featurename:
            self.msg(self._usage)
            return
        
        if not rhs and 'del' in self.switches:
            if featuresearch in target.features:
                del target.features[featuresearch]
                self.msg(f"{target.get_display_name(caller)} updated.")
                return
            else:
                self.msg(f"{target.get_display_name(caller)} has no feature '{featuresearch}'")
                return

        target.features[featuresearch] = {'name':featurename, 'desc':rhs}
        self.msg(f"{target.get_display_name(caller)} updated.")
        
