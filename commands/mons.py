

import math

from .command import MuxCommand, Command
from evennia import GLOBAL_SCRIPTS
from evennia.utils import evtable

from world.monutils import type_vuln_table, display_full_mon_name, get_display_type

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
    
class CmdSetSpecies(MuxCommand):
    """
    Usage:
        setspecies <target> = (subtype,||subtype,form,)<species name or dex number>
    """
    key = 'setspecies'
    locks = "cmd:all()"
    help_category = "Mons"
    
    _usage = "setspecies <target> = (subtype,||subtype,form,)<species name or dex number>"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        target = self.caller.search(self.lhs)
    
        if not target:
            self.caller.msg(self._usage)
            return
    
        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            self.msg(f"You don't have permission to work on {target.name}.")
            return

        if len(self.rhslist) == 3:
            subtype, form, monname = self.rhslist
        elif len(self.rhslist) == 2:
            subtype, monname = self.rhslist
            form = ""
        elif len(self.rhslist) == 1:
            monname = self.rhslist[0]
            form, subtype = "",""
        else:
            self.caller.msg(self._usage)
            return

        if not monname:
            self.caller.msg(self._usage)

        mons = mondata.search_mons(monname,subtype,form)

        if not mons:
            subtypemsg = f" with subtype '{subtype}'" if subtype else ""
            formmsg = f" {'and' if subtypemsg else 'with'} form '{form}'" if form else ""
            self.caller.msg(f"No mons found by the species name '{monname}'{subtypemsg}{formmsg}")
            return

        if len(mons) == 1:
            mon = mons[0]
        else:
            out = ["Found multiple matches, please chose from:"]
            for mon in mons:
                out.append(f" - {get_display_type(mon)} #{mon['dexno']} {display_full_mon_name(mon)}")
            out.append(f"Use setspecies {target} = (subtype,||subtype,form,){monname} to select. Use '-' for blank.")
            self.caller.msg('\n'.join(out))
            return

        self.caller.msg(f"Selected {get_display_type(mon)} #{mon['dexno']} {display_full_mon_name(mon)}")

        target.species = mon['name']
        target.subtype = mon['subtype']
        target.form = mon['form']
        target.dexno = mon['dexno']
        target.type1 = mon['type1']
        target.type2 = mon['type2']
        target.base_stats = mon['base_stats']
        self.caller.msg(f"{target.name} updated.")




