

import math

from .command import MuxCommand, Command
from evennia import GLOBAL_SCRIPTS
from evennia.utils import evtable


class CmdMonTypes(Command):
    """
    Prints the type effectiveness table.
    """

    key = "MonTypes"
    aliases = "Vulns"
    locks = "cmd:all()"
    help_category = "Mons"

    _usage = "Usage: MonTypes type1[,type2] - analyze pokemon type (combo)"

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
        types = mondata.types
        typenames = mondata.typenames
        typelookup = mondata.typelookup

        if not type1 in typelookup:
            self.caller.msg(f"{type1} not a valid type. {self._usage}")
            return

        if type2 and not type2 in typelookup:
            self.caller.msg(f"{type2} not a valid type. {self._usage}")
            return
        
        type1 = typelookup[type1]
        type2 = typelookup[type2] if type2 else type2

        if type1 == type2:
            self.caller.msg("Double of same type not allowed, sorry.")
            return
        
        typevulns = [1.0 for type in typenames]
        
        for i, type in enumerate(typenames):
            typevulns[i] = typevulns[i] * types[type]['vs'][type1]
        
        if type2:
            for i, type in enumerate(typenames):
                typevulns[i] = typevulns[i] * types[type]['vs'][type2]

        invuln = []
        quarter = []
        half = []
        one = []
        two = []
        four = []
        huh = []

        def _appendwrap(list,data):
            if len(list) > 1 and len(list) % 8 == 0:
                list.append('\n          ')
            list.append(data)

        for type, vuln in zip(typenames, typevulns):
            if vuln == 0.0:
                _appendwrap(invuln,types[type]['colortoken'])
            elif vuln == 0.25:
                _appendwrap(quarter,types[type]['colortoken'])
            elif vuln == 0.5:
                _appendwrap(half,types[type]['colortoken'])
            elif vuln == 1.0:
                _appendwrap(one,types[type]['colortoken'])
            elif vuln == 2.0:
                _appendwrap(two,types[type]['colortoken'])
            elif vuln == 4.0:
                _appendwrap(four,types[type]['colortoken'])
            else:
                _appendwrap(huh,types[type]['colortoken'])
            

        out = []
        out.append(f"\n|wVulnerabilities for >|n{types[type1]['colortoken']}{types[type2]['colortoken'] if type2 else ''}|w<|n")
        if one: 
            out.append(f"NO CHANGE:{''.join(one)}")
        if invuln:
            out.append(f"   |wINVULN|n:{''.join(invuln)}")
        if quarter:
            out.append(f"  |bQUARTER|n:{''.join(quarter)}")
        if half:
            out.append(f"     |gHALF|n:{''.join(half)}")
        if two:
            out.append(f"   |yDOUBLE|n:{''.join(two)}")
        if four:
            out.append(f"     |rQUAD|n:{''.join(four)}")
        if huh:
            out.append(f"    |[r|XERROR|n:{''.join(huh)}")


        self.caller.msg('\n'.join(out))

            







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
    



