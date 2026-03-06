

import math
import random

from .command import MuxCommand, Command
from evennia import GLOBAL_SCRIPTS
from evennia.utils import evtable, string_suggestions

from world.monutils import type_vuln_table, get_display_mon_name, get_display_mon_type, get_display_mon_banner

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
    aliases = ['setmon']
    locks = "cmd:all()"
    help_category = "Mons"
    
    _usage = "Usage: setspecies <target> = (subtype,||subtype,form,)<species name or dex number>"

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

            dexno = None
            try:
                dexno = int(monname)
            except ValueError:
                pass

            if dexno is not None:
                self.caller.msg(f"No mons found by the dex number '{dexno}'{subtypemsg}{formmsg}")
            else:
                self.caller.msg(f"No mons found by the species name '{monname}'{subtypemsg}{formmsg}")
                suggestions = string_suggestions(monname, mondata.monnames)
                self.caller.msg(f"Did you mean any of: {', '.join(suggestions)}")
            return

        if len(mons) == 1:
            mon = mons[0]
        else:
            out = ["Found multiple matches, please chose from:"]
            for idx, mon in enumerate(mons):
                out.append(f" - {idx+1} - {get_display_mon_banner(mon)}")
            out.append(f"Select [1-{len(mons)}]:")

            answer = yield('\n'.join(out))

            try:
                answer = int(answer.strip())
            except ValueError:
                self.caller.msg("|xAborted.|n")
                return
    
            if answer-1 >= 0 and answer-1 < len(mons):
                mon = mons[answer-1]
            else:
                self.caller.msg("|xAborted.|n")
                return
            

        self.caller.msg(f"Selected {get_display_mon_banner(mon)}")

        all_abilities = [abi for abi in mon['abilities'] if abi]
        all_abilities.extend([abi for abi in mon['hidden_abilities'] if abi])

        if not all_abilities:
            ability = ""
            self.caller.msg(f"{get_display_mon_banner(mon)} has no abilities.")
        elif len(all_abilities) == 1:
            ability = all_abilities[0]
            self.caller.msg(f"{get_display_mon_banner(mon)} only has ability '{ability}', selecting it.")
        else:
            idx = 1
            choices = []
            out = [f"{get_display_mon_banner(mon)} has these abilities available:"]
            for abi in mon['abilities']: 
                if abi:
                    out.append(f" - {idx} - Ability: {abi}")
                    choices.append(abi)
                    idx += 1
            for abi in mon['hidden_abilities']: 
                if abi:
                    out.append(f" - {idx} - |bHidden|n ability: {abi}")
                    choices.append(abi)
                    idx += 1

            out.append(f"Select [1-{len(choices)}]:")

            answer = yield('\n'.join(out))

            try:
                answer = int(answer.strip())
            except ValueError:
                self.caller.msg("|xAborted.|n")
                return
    
            if answer-1 >= 0 and answer-1 < len(choices):
                ability = choices[answer-1]
            else:
                self.caller.msg("|xAborted.|n")
                return
            
            self.caller.msg(f"{ability} selected.")
    

        target.species = mon['name']
        target.subtype = mon['subtype']
        target.form = mon['form']
        target.dexno = mon['dexno']
        target.type1 = mon['type1']
        target.type2 = mon['type2']
        target.base_stats = mon['base_stats']
        target.ability = ability

        target.level = 100
        target.init_stats()

        self.caller.msg(f"{target.name} updated.")


class CmdSetNature(MuxCommand):
    """
    Usage: 
        setnature <target> [= <nature>]
    """
    key = 'setnature'
    locks = "cmd:all()"
    help_category = "Mons"

    _usage = "Usage: setnature <target> [= <nature>]"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        target = self.caller.search(self.lhs)
    
        if not target:
            self.caller.msg(self._usage)
            return
    
        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            self.msg(f"You don't have permission to work on {target.name}.")
            return
        
        rhs = self.rhs.strip() if self.rhs else ""
        
        if rhs:
            if rhs in mondata.natures:
                nature = mondata.natures[rhs]
            else:
                self.caller.msg(f"Nature '{rhs}' does not exist.")
        else:
            choices = sorted(mondata.natures.keys())

            out = [f"|w -    - {'Nature':>8} - {'Favored Stat':<20} - {'Neglected Stat':<20}|n"]

            for idx, choice in enumerate(choices):
                favored = mondata.natures[choice]['favored_stat']
                neglected = mondata.natures[choice]['neglected_stat']
                if favored == neglected:
                    favored = ""
                    neglected = ""
                out.append(f" - {idx+1:2d} - {choice:>8} - |G{favored:<20}|n - |R{neglected:<20}|n")
                        
            out.append(f"Select [1-{len(choices)}]:")

            answer = yield('\n'.join(out))

            try:
                answer = int(answer.strip())
            except ValueError:
                self.caller.msg("|xAborted.|n")
                return
    
            if answer-1 >= 0 and answer-1 < len(choices):
                nature = choices[answer-1]
            else:
                self.caller.msg("|xAborted.|n")
                return
            
        self.caller.msg(f"{nature} selected.")

        naturedata = mondata.natures[nature]

        favored = naturedata['favored_stat']
        neglected = naturedata['neglected_stat']
        if favored == neglected:
            favored = ""
            neglected = ""

        target.nature = nature
        target.favored_stat = favored
        target.neglected_stat = neglected
        target.update_stats()

        self.caller.msg(f"{target.name} updated.")


class CmdRandMons(Command):
    """
    Usage:
        randmons [count]
    """
    key = 'randmons'
    locks = "cmd:all()"
    help_category = "Mons"
    
    _usage = "Usage: randmons [count]"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        if self.args:
            try:
                count = int(self.args.strip())
            except ValueError:
                self.caller.msg(self._usage)
                return
        else:
            count = 5
        
        count = min(count,50)

        mons = random.sample(mondata.mons, count)

        for idx, mon in enumerate(mons):

            num = f"{idx+1}" if count < 10 else f"{idx+1:2d}"
                
            self.caller.msg(f" - {num} - {get_display_type(mon)} #{mon['dexno']:<4d} {display_full_mon_name(mon)}")
            


