
import time

from .command import MuxCommand, Command
from evennia import GLOBAL_SCRIPTS
from evennia.utils import string_suggestions

from typeclasses.characters import Character, PlayerCharacter

from world.monutils import get_display_mon_banner

from .chargen import _MAX_EQUIPPED_MOVES

class CmdAdminSetSpecies(MuxCommand):
    """
    Usage:
        @setspecies <target> = (subtype,||subtype,form,)<species name or dex number>
    """
    key = '@setspecies'
    aliases = ['@setmon']
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"
    
    _usage = "Usage: @setspecies <target> = (subtype,||subtype,form,)<species name or dex number>"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        if not self.lhs:
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.lhs, exact=True, typeclass=[Character, PlayerCharacter])

        if not target:
            return

        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            self.caller.msg(f"You don't have permission to work on {target.name}.")
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
    
        if target.is_typeclass(PlayerCharacter) and target.species:
            out = (
                f"{target.get_display_name(looker=self.caller)} is a player character that already has a species "
                f"set.\n|RProceeding will reset their IV and EV expendatures to zero. |rAre you sure?|n [y/N]")
            answer = yield out
            if not answer.strip().lower().startswith('y'):
                self.caller.msg("|xAborted.|n")
                return

        target.set_species(self.caller, mon, ability)

        self.caller.msg(f"{target.get_display_name(looker=self.caller)} updated.")


class CmdAdminSetNature(MuxCommand):
    """
    Usage: 
        @setnature <target> [= nature]
    """
    key = '@setnature'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"

    _usage = "Usage: @setnature <target> [= nature]"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        if not self.lhs:
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.lhs, exact=True, typeclass=[Character, PlayerCharacter])

        if not target:
            return
        
        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            self.caller.msg(f"You don't have permission to work on {target.name}.")
            return

        rhs = self.rhs.strip() if self.rhs else ""
        
        if rhs:
            if rhs in mondata.natures:
                nature = rhs
            else:
                self.caller.msg(f"Nature '{rhs}' does not exist.")
                return
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

        target.set_nature(self.caller, mondata.natures[nature])

        self.caller.msg(f"{target.get_display_name(looker=self.caller)} updated.")


class CmdAdminBuyIVs(MuxCommand):
    """
    Usage:
        @buyivs <target> = <stat>, <tokens to spend>
    """
    key = '@buyivs'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"

    _usage = "Usage: buyivs [<target> =] stat,tokens to spend"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata
    
        if not self.lhs:
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.lhs, exact=True, typeclass=[Character, PlayerCharacter])

        if not target:
            return
    
        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            self.caller.msg(f"You don't have permission to work on {target.name}.")
            return
        
        remaining = target.ivtokens - target.ivtokens_spent
        if not remaining:
            self.caller.msg(f"{target.name} has no IV tokens to spend.")
        
        if len(self.rhslist) != 2:
            self.caller.msg(self._usage)
            return
        
        stat, amount = self.rhslist

        if stat not in mondata.lookup_statlist:
            self.msg(f"'{stat}' is not a valid stat.")
            return
        
        stat = mondata.lookup_statlist[stat]
        
        try:
            amount = int(amount)
        except ValueError:
            self.caller.msg(f"Tokens to spend must be a positive integer")
            return
        
        if not 0 <= amount:
            self.caller.msg(f"Tokens to spend must be a positive integer")
            return
        
        amount = min(amount,remaining)
        while amount and amount * 3 + target.ivs[stat] > 30:
            amount -= 1
        
        if not amount:
            self.caller.msg(f"{target}'s {stat} is already maxed out!")
            return
        
        question = (
            f"Spend {amount} of {target.get_display_name(looker=self.caller)}'s {remaining} " 
            f"remaining IV tokens to raise "
            f"{stat}'s IVs from {target.ivs[stat]} to {target.ivs[stat] + amount * 3}? [y/N]"
        )

        answer = yield question

        if not answer.strip().lower().startswith('y'):
            self.caller.msg("|xAborted.|n")
            return
        
        target.spend_iv_tokens(self.caller, stat, amount)

        self.caller.msg(f"{target.get_display_name(looker=self.caller)} updated.")


class CmdAuditLog(MuxCommand):
    """
    Usage:
        auditlog <target> [= maxmessages]
        auditlog/full target
        auditlog/top target [= maxmessages]
    """

    key = '@auditlog'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"
    
    def func(self):

        if not self.lhs:
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.lhs, exact=True, typeclass=[PlayerCharacter])

        if not target:
            return
        
        if 'full' in self.switches:
            slice = target.auditlog
            first = 1
            last = len(target.auditlog)
        else:
            try:
                count = int(self.rhs) if self.rhs else 25
            except ValueError:
                count = 25
            
            if 'top' in self.switches:
                slice = target.auditlog[:count]
                first = 1
                last = min(count, len(target.auditlog))
            else:
                slice = target.auditlog[-count:]
                first = max(1, len(target.auditlog) - len(slice) + 1)
                last = max(len(slice), len(target.auditlog))
        
        self.caller.msg(f" - Audit log for {target.get_display_name()}, lines {first}-{last} of {len(target.auditlog)}")

        for timestamp, msg in slice:
            timestamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
            self.caller.msg(f" |B{timestamp}|n - {msg}")


class CmdAdminResetIVs(MuxCommand):
    """
    Usage:
        @resetivs <target>
    """
    key = '@resetivs'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"

    _usage = "Usage: @resetivs <target>"

    def func(self):

        if not self.args.strip():
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.args.strip(), exact=True, typeclass=[Character, PlayerCharacter])

        if not target:
            return

        if not any(target.ivs.values()):
            self.caller.msg(f"{target.get_display_name(self.caller)} has no ivs bought, no need to reset.")
            return

        target.reset_ivs(self.caller)

        self.caller.msg(f"{target.get_display_name(self.caller)} updated.")


class CmdAdminEquipMove(MuxCommand):
    """
    Usage:
        @equipmove <target> = <move name>
    """
    key = '@equipmove'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"

    _usage = "Usage: @equipmove <target> = <move name>"

    def func(self):

        mondata = GLOBAL_SCRIPTS.mondata

        if not self.lhs:
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.lhs, exact=True, typeclass=[Character, PlayerCharacter])

        if len(target.moves_equipped) >= _MAX_EQUIPPED_MOVES:
            self.caller.msg(
                f"{target.get_display_name(self.caller)} already has "
                f"{len(target.moves_equipped)} out of {_MAX_EQUIPPED_MOVES} moves equipped."
            )
            return

        if not target:
            return

        movename = self.rhs

        if not movename:
            self.caller.msg(self._usage)
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            suggestions = string_suggestions(movename, mondata.movenames)
            self.caller.msg(f"Could not find a move named '{movename}', did you mean one of {suggestions}?")
            return
        
        if actual_movename in target.moves_equipped:
            self.caller.msg(f"{target.get_display_name(self.caller)} already has {actual_movename} equipped.")
            return

        if not actual_movename in target.moves_known:
            if not target.approved:
                target.learn_move(self.caller, actual_movename)
                self.caller.msg(
                    f"This is chargen, so {target.get_display_name(self.caller)} is "
                    f"also learning {actual_movename}."
                )
            else:
                self.caller.msg(f"{target.get_display_name(self.caller)} doesn't know the move {actual_movename}.")
                return
        
        target.equip_move(self.caller, actual_movename)
        self.caller.msg(f"{target.get_display_name(self.caller)} equipped {actual_movename}.")


class CmdAdminUnequipMove(MuxCommand):
    """
    Unequips move or shows equipped moves if called without move name.

    Usage:
        @unequipmove <target> [= move name]
    """
    key = '@unequipmove'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"

    _usage = "Usage: @unequipmove <target> [= move name]"

    def func(self):

        mondata = GLOBAL_SCRIPTS.mondata

        if not self.lhs:
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.lhs, exact=True, typeclass=[Character, PlayerCharacter])

        if not target:
            return

        if not target.moves_equipped:
            self.caller.msg(f"No moves equipped by {target.get_display_name(self.caller)}.")
            return

        movename = self.rhs

        if not movename:
            self.caller.msg(
                f"{target.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(target.moves_equipped.keys()))}."
            )
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            suggestions = string_suggestions(movename, mondata.movenames)
            self.caller.msg(
                f"Could not find a move named '{movename}'. "
                f"{target.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(target.moves_equipped.keys()))}."
            )
            return
        
        if actual_movename not in target.moves_equipped:
            
            self.caller.msg(
                f"{target.get_display_name(self.caller)} doesn't have {actual_movename} equipped. "
                f"{target.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(target.moves_equipped.keys()))}."
            )
            return
        
        if not target.approved:
            target.forget_move(self.caller, actual_movename)
            self.msg(
                f"This is chargen, so {target.get_display_name(self.caller)} is "
                f"also forgetting {actual_movename}."
            )

        target.unequip_move(self.caller, actual_movename)
        self.caller.msg(f"{target.get_display_name(self.caller)} unequipped {actual_movename}.")


class CmdAdminLearnMove(MuxCommand):
    """
    Usage:
        @learnmove <target> = <move name>
    """
    key = '@learnmove'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"

    _usage = "Usage: @learnmove <target> = <move name>"

    def func(self):
    
        mondata = GLOBAL_SCRIPTS.mondata

        if not self.lhs:
            self.caller.msg(self._usage)
            return

        target = self.caller.search(self.lhs, exact=True, typeclass=[Character, PlayerCharacter])

        if not target:
            return
        
        movename = self.rhs

        if not movename:
            self.caller.msg(self._usage)
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            suggestions = string_suggestions(movename, mondata.movenames)
            self.caller.msg(f"Could not find a move named '{movename}', did you mean one of {suggestions}?")
            return
        
        if actual_movename in target.moves_known:
            self.caller.msg(f"{target.get_display.name(self.caller)} doesn't know {actual_movename}")
            return

        target.learn_move(self.caller, actual_movename)
        self.caller.msg(f"{target.get_display_name(self.caller)} learned {actual_movename}.")


class CmdAdminForgetMove(MuxCommand):
    """
    Forget move or show known moves if called without move name.
    
    Usage:
        @forgetmove <target> [= move name]
    """
    key = '@forgetmove'
    locks = "cmd:perm(Admin)"
    help_category = "Chargen"

    _usage = "Usage: @forgetmove <target> [= move name]"

    def func(self):

        mondata = GLOBAL_SCRIPTS.mondata

        if not self.lhs:
            self.caller.msg(self._usage)
            return
        
        target = self.caller.search(self.lhs, exact=True, typeclass=[Character, PlayerCharacter])

        if not target:
            return
        
        if not target.moves_known:
            self.caller.msg(f"No moves known by {target.get_display_name(self.caller)}.")
            return

        movename = self.rhs

        if not movename:
            self.caller.msg(
                f"Moves {target.get_display_name(self.caller)} knows are: "
                f"{', '.join(sorted(target.moves_known))}."
            )
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            self.caller.msg(
                f"Could not find a move named '{movename}'. "
                f"Moves {target.get_display_name(self.caller)} knows are: {', '.join(sorted(target.moves_known))}."
            )
            return
        
        if actual_movename not in target.moves_known:
            self.caller.msg(
                f"{target.get_display_name(self.caller)} doesn't know {actual_movename}. "
                f"Moves {target.get_display_name(self.caller)} knows are: {', '.join(sorted(target.moves_known))}."
            )
            return
        
        if actual_movename in target.moves_equipped:
            target.unequip_move(self.caller, actual_movename)
            self.caller.msg(f"{target.get_display_name(self.caller)} unequips {actual_movename} to forget it.")

        target.forget_move(self.caller, actual_movename)
        self.caller.msg(f"{target.get_display_name(self.caller)} forgot {actual_movename}.")
