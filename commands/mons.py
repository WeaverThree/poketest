

import math
import random

from django.conf import settings

from evennia import GLOBAL_SCRIPTS
from evennia.utils import evtable, string_suggestions

from .command import MuxCommand, Command
from typeclasses.characters import Character, PlayerCharacter
from typeclasses.rooms import Room
from world.monutils import type_vuln_table, get_display_mon_banner, moves_table, single_move, color_uses_text

_ROOM_TAG_TELTARGET = settings.ROOM_TAG_TELTARGET
_ROOM_TAG_NOTEL = settings.ROOM_TAG_NOTEL

class CmdMonTypes(Command):
    """
    Without arguments, prints the full type effectiveness table.
    Otherwise:
        +montypes type1[/type2] -> analyze type (combination) vulnerabilities
    """

    key = "+montypes"
    aliases = "Vulns"
    locks = "cmd:all()"
    help_category = "Mons"

    _usage = "Usage: +montypes type1[/type2] - analyze pokemon type (combo)"

    def func(self):
        self.args = self.args.strip()
        if not self.args:
            self.print_table()
        else:
            self.args = self.args.replace('/',',')
            types = self.args.split(',')
            if 1 <= len(types) <= 2:
                self.type_analysis(*types)
            else:
                self.caller.msg(self._usage)
            

    def type_analysis(self, type1,type2=""):    
        mondata = GLOBAL_SCRIPTS.mondata
        typelookup = mondata.typelookup

        if not type1 in typelookup:
            self.caller.msg(f"{type1} not a valid type. {self._usage}")
            return

        if type2 and not type2 in typelookup:
            self.caller.msg(f"{type2} not a valid type. {self._usage}")
            return
        
        type1 = typelookup[type1]
        type2 = typelookup[type2] if type2 else ""

        if type1 == type2:
            self.caller.msg("Double of same type not allowed, sorry.")
            return

        self.caller.msg(type_vuln_table(type1, type2))


    def print_table(self):
        mondata = GLOBAL_SCRIPTS.mondata
        types = mondata.types

        out = []

        line = ["      "]
        for type0 in mondata.typenames:
            line.append(f"{types[type0]['color']}{types[type0]['short']:<3}|n ")
        out.append(''.join(line))

        for type1 in mondata.typenames:
            line = []
            line.append(types[type1]['colortoken'])
            for type2 in mondata.typenames:
                mult = types[type1]['vs'][type2]
                if mult == 0.0:
                    line.append(" |r×|n |x|||n")
                elif mult == 0.5:
                    line.append(" |y~|n |x|||n")
                elif mult == 1.0:
                    line.append("   |x|||n")
                elif mult == 2.0:
                    line.append(" |g#|n |x|||n")
                else:
                    line.append(" |b?|n |x|||n")

            out.append("".join(line))
        
        title = " Left: Attacker, Top: Defender "
        fill = ((6 + len(types) * 4) - len(title)) / 2.0
        leftfill = "-" * math.floor(fill)
        rightfill = "-" * math.ceil(fill)

        self.caller.msg(f"|x{leftfill}|w{title}|x{rightfill}|n")
        self.caller.msg("\n".join(out))
    

class CmdRandMons(Command):
    """
    For inspiration.

    Usage:
        +randmons [count]
    """
    key = '+randmons'
    locks = "cmd:all()"
    help_category = "Mons"
    
    _usage = "Usage: +randmons [count]"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        if self.args:
            try:
                count = int(self.args.strip())
            except ValueError:
                self.caller.msg(self._usage)
                return
            if count <= 0:
                self.caller.msg(self._usage)
                return
        else:
            count = 5
        
        count = min(count,50)

        count = min(count, len(mondata.mons))

        mons = random.sample(mondata.mons, count)

        for idx, mon in enumerate(mons):

            num = f"{idx+1}" if count < 10 else f"{idx+1:2d}"
                
            self.caller.msg(f" - {num} - {get_display_mon_banner(mon)}")


            
class CmdMoveLookup(Command):
    """
    For checking the data available.

    Usage:
        +movelookup <name>
    """
    key = '+movelookup'
    locks = "cmd:all()"
    help_category = "Mons"
    
    _usage = "Usage: +movelookup <name>"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        movename = self.args.strip()

        if not movename:
            self.caller.msg(self._usage)
            return
        
        if movename in mondata.moves:
            moves = [mondata.moves[movename]]
            errorstring = ""
        else:
            movenames = string_suggestions(movename, mondata.movenames, maxnum=5)
            moves = [mondata.moves[movename] for movename in movenames]
            errorstring = f"Could not find move '{movename}', is it any of these?\n"
        
        table = moves_table(moves)

        self.caller.msg(f"\n{errorstring}{table}")


class CmdRandMoves(Command):
    """
    For inspiration.

    Usage:
        +randmoves [count]
    """
    key = '+randmoves'
    locks = "cmd:all()"
    help_category = "Mons"
    
    _usage = "Usage: +randmoves [count]"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        if self.args:
            try:
                count = int(self.args.strip())
            except ValueError:
                self.caller.msg(self._usage)
                return
            if count <= 0:
                self.caller.msg(self._usage)
                return
        else:
            count = 5
        
        count = min(count,50)

        count = min(count, len(mondata.movenames))

        movenames = random.sample(sorted(mondata.movenames), count)
        moves = [mondata.moves[movename] for movename in movenames]

        table = moves_table(moves)

        self.caller.msg(f"\n|w - - - {count} Random Moves - - -|n\n{table}")


class CmdUseMove(Command):
    """
    Use a move, reducing it's PP until the next refresh.

    Usage:
        +use <move>
    """
    key = '+use'
    locks = "cmd:all()"
    help_category = "Mons"
    
    _usage = "Usage: +use <move>"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        caller = self.caller

        movename = self.args.strip()

        if not movename:
            self.msg(
                f"{caller.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(caller.moves_equipped.keys()))}."
            )
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            self.msg(
                f"Could not find a move named '{movename}'. "
                f"{caller.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(caller.moves_equipped.keys()))}."
            )
            return
        
        if actual_movename not in caller.moves_equipped:
            
            self.msg(
                f"{caller.get_display_name(self.caller)} doesn't have {actual_movename} equipped. "
                f"{caller.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(caller.moves_equipped.keys()))}."
            )
            return
        
        move = mondata.moves[actual_movename]
        used = caller.moves_equipped[actual_movename]
        if used + 1 > move['uses']:
            self.msg(f"{caller.get_display_name(caller)} doesn't have the PP left to use {actual_movename} right now.")
            return
        
        caller.moves_equipped[actual_movename] += 1

        used += 1

        movetext = "{sender} used " + single_move(actual_movename)
        caller.location.msg_contents(movetext, mapping={'sender': caller})
        caller.msg(f"    |x(PP Remaining: {color_uses_text(move['uses'],used,"|x")})|n")


class CmdMoveTeleport(MuxCommand):
    """
    Use the move Teleport to teleport yourself to another location or person. Call with no arguments
    for destination list.

    Usage:
        +teleport -> show known teleport destinations
        +teleport <destination> -> teleport to destination
        +teleport <creature> -> teleport to creature if they allow it
    """
    key = '+teleport'
    aliases = '+tel'
    locks = "cmd:all()"
    help_category = "Mons"
    
    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        caller = self.caller
        location = caller.location
        args = self.args

        if caller.teleport_waiting:
            target = caller.teleport_waiting
            if args.strip().lower().startswith('y'):
                self.msg("Teleport accepted.")
                target.teleport_response = 'y'
            elif args.strip().lower().startswith('n'):
                self.msg("Teleport declined.")
                target.teleport_response = 'n'
            else:
                self.msg(
                    f"{target.get_display_name(caller)} is waiting for {caller.get_display_name(caller)}'s "
                    "response about teleporting to you.\n"
                    "Use |b+teleport yes|n or |b+teleport no|n to respond. Thanks!"
                )
            return

        teleport_move = "Teleport"

        if teleport_move not in caller.moves_equipped:
            if teleport_move not in caller.moves_known:
                self.msg(
                    f"{caller.get_display_name(caller)} doesn't know how to teleport."
                )
            else:
                self.msg(
                    f"{caller.get_display_name(caller)} doesn't have teleport equipped."
                )
            return
        
        if not args:
            if not caller.teleport_known:
                self.msg(f"{caller.get_display_name(caller)} doesn't know any destinations to teleport to.")
                return

            out = [f"Places {caller.get_display_name(caller)} knows how to teleport to:"]
            for room in sorted(caller.teleport_known, key=lambda x: x.name):
                if room.tags.get(_ROOM_TAG_TELTARGET): # Filter out rooms with tag removed...
                    out.append(f" - {room.get_display_name(caller)}")
            out.append('')

            self.msg('\n'.join(out))
            return

        used = caller.moves_equipped[teleport_move]
        move = mondata.moves[teleport_move]
        if used + 1 > move['uses']:
            self.msg(f"{caller.get_display_name(caller)} doesn't have the PP left to use {teleport_move} right now.")
            return

        if location.tags.get(_ROOM_TAG_NOTEL):
            self.msg(
                "Something is interfering with the psychic field here. "
                f"{caller.get_display_name(caller)} can't teleport from here."
            )
            return
        elif not location.is_ic_room:
            self.msg(
                "Please enter the IC grid before teleporting."
            )
            return

        if args in ('self', 'me'):
            self.msg("Teleportation to self denied~")
            return
    
        search = PlayerCharacter.objects.search(args)
        chartarget = None
        if len(search) > 2:
            self.msg(f"Got multiple hits for '{args}'. This shouldn't happen. Please notify staff.")
            return
        if search:
            chartarget = search[0]

        movetext = "{sender} used " + single_move(teleport_move)
        starttext = "{sender} begins to glow in rainbow hues."
        failtext = "{sender}'s rainbow colors flicker and fade."

        if chartarget:
            if chartarget == caller:
                self.msg("Teleportation to self denied~")
                return

            target = chartarget.location

            if target == caller.location:
                self.msg(f"{chartarget.get_display_name(caller)} is right here!")
                return
            
            if chartarget.is_idle:
                self.msg(
                    f"{chartarget.get_display_name(caller)} is idle. "
                    f"Don't want to waste {caller.get_display_name(caller)}'s PP, try again when "
                    f"{chartarget.get_display_name(caller)} is active."
                )
                return

            if chartarget.teleport_waiting:
                self.msg(
                    f"The psychic line to {chartarget.get_display_name(caller)} is congested. "
                    "Wait a little and try again."
                )
                return

            if target.tags.get(_ROOM_TAG_NOTEL) or not target.is_ic_room:
                self.msg(
                    f"{caller.get_display_name(caller)} can't get a lock on {chartarget.get_display_name(caller)}, "
                    "something is interfering with the psychic field around them."
                )
                return
            
            # Ok we're doing it (character)
            
            caller.moves_equipped[teleport_move] += 1
            used += 1
            location.msg_contents(movetext, mapping={'sender': caller})
            caller.msg(f"    |x(PP Remaining: {color_uses_text(move['uses'],used,"|x")})|n")
            location.msg_contents(starttext, mapping={'sender': caller})

            caller.msg(
                f"Asking {chartarget.get_display_name(caller)} if {caller.get_display_name(caller)} "
                "can teleport to their location. Please hold. (Up to 30 seconds.)"
            )
            chartarget.msg(
                f"{caller.get_display_name(chartarget)} |Mis asking to teleport to |n"
                f"{chartarget.get_display_name(chartarget)}|M's "
                "location. Respond with |b+teleport yes|M or |b+teleport no|M. The request will time out in "
                "30 seconds.|n" 
            )

            caller.teleport_response = ""
            chartarget.teleport_waiting = caller

            for tick in range(10):
                yield 3
                if caller.teleport_response:
                    if caller.teleport_response.strip().lower().startswith('y'):
                        chartarget.teleport_waiting = None
                        caller.teleport_response = ""
                        caller.move_to(target, move_type="teleportmove")
                        return
                    else:
                        break
            
            chartarget.teleport_waiting = None
            caller.teleport_response = ""
            caller.msg("Teleport declined.")
            location.msg_contents(failtext, mapping={'sender': caller})
            return
        
        # If we get here, we're teleporting to a location
        search = Room.objects.search(args)
        target = None
        if len(search) > 2:
            self.msg(f"Got multiple hits for '{args}'. This shouldn't happen. Please notify staff.")
            return
        if search:
            target = search[0]

        if (not target) or (not target.tags.get(_ROOM_TAG_TELTARGET)):
            self.msg(f"Could not find a location or creature named '{args}'")
            return

        if target == caller.location:
            self.msg(f"{caller.get_display_name(caller)} is already here!")
            return

        if not target in caller.teleport_known:
            self.msg(
                f"{caller.get_display_name(caller)} hasn't learned how to teleport to "
                f"{target.get_display_name(caller)}."
            )
            return
        
        # At this point, we're good...
            
        caller.moves_equipped[teleport_move] += 1
        used += 1
        location.msg_contents(movetext, mapping={'sender': caller})
        caller.msg(f"    |x(PP Remaining: {color_uses_text(move['uses'],used,"|x")})|n")
        location.msg_contents(starttext, mapping={'sender': caller})

        yield 3 # do a little pause for effect

        caller.move_to(target, move_type="teleportmove")

        




                        






            


        



