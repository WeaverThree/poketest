

import math

from .command import MuxCommand, Command
from evennia import GLOBAL_SCRIPTS
from evennia.utils import evtable

from world.monutils import type_vuln_table

class CmdMonTypes(Command):
    """
    Without arguments, prints the full type effectiveness table.
    Otherwise:
        montypes type1[/type2] -> analyze type (combination) vulnerabilities
    """

    key = "montypes"
    aliases = "Vulns"
    locks = "cmd:all()"
    help_category = "Mons"

    _usage = "Usage: montypes type1[/type2] - analyze pokemon type (combo)"

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
    



