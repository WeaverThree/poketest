import math
import random

from django.conf import settings

from .command import MuxCommand, Command
from evennia import GLOBAL_SCRIPTS
from evennia.comms.models import ChannelDB
from evennia.utils import evtable, string_suggestions, logger

from world.utils import get_defaulthome, get_specialroom
from world.monutils import type_vuln_table, get_display_mon_name, get_display_mon_type, get_display_mon_banner

_MAX_EQUIPPED_MOVES = 6

class CmdAcceptPolicy(Command):
    """
    Accept the rules of this server to join.
    
    Usage:
        accept
    """
    key = 'accept'
    locks = "cmd:all()"
    help_category = "Special"

    def func(self):

        caller = self.caller

        message = (
            "|MDo you agree to abide by the rules of the server and the acceptable use policy outlined above, "
            "and also available at any time via the commands 'help aup' or 'help rules'?\n"
            "|m[Please type 'i accept' to continue.]|n"
        )

        answer = yield message

        if answer.strip().lower() != "i accept":
            self.msg("|xAborted.|n")
            return
        
        # AUP acceptance stuff

        caller.accepted_rules = True

        for chankey in settings.REMOVE_ON_ACCEPT_CHANNELS:
            channel = ChannelDB.objects.get_channel(chankey)
            if channel:
                if not channel.disconnect(caller):
                    self.msg(f"|rCould not remove you from channel '{chankey}'!|n")

        for chankey in settings.ADD_ON_ACCEPT_CHANNELS:
            channel = ChannelDB.objects.get_channel(chankey)
            if not channel or not (channel.access(caller, "listen") and channel.connect(caller)):
                self.msg(f"|rCould not add you to channel '{chankey}'!|n")

        destination = get_specialroom(settings.TAG_OOC_TARGET)
        if not destination:
            destination = get_defaulthome()

        if not caller.move_to(destination, move_type="teleport"):
            self.msg("|mCould not move you out of here, please contact staff.|n")
            


class CmdChargenSetSpecies(Command):
    """
    Usage:
        setspecies (subtype,||subtype,form,)<species name or dex number>
    """
    key = 'setspecies'
    aliases = ['setmon']
    locks = "cmd:all()"
    help_category = "Chargen"
    
    _usage = "Usage: setspecies (subtype,||subtype,form,)<species name or dex number>"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata
    
        target = self.caller

        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            # Should never happen, but
            self.msg(f"You don't have permission to work on {target.name}.")
            return

        arglist = [arg.strip() for arg in self.args.split(',')]

        if len(arglist) == 3:
            subtype, form, monname = arglist
        elif len(arglist) == 2:
            subtype, monname = arglist
            form = ""
        elif len(arglist) == 1:
            monname = arglist[0]
            form, subtype = "",""
        else:
            self.msg(self._usage)
            return

        if not monname:
            self.msg(self._usage)

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
                self.msg(f"No mons found by the dex number '{dexno}'{subtypemsg}{formmsg}")
            else:
                self.msg(f"No mons found by the species name '{monname}'{subtypemsg}{formmsg}")
                suggestions = string_suggestions(monname, mondata.monnames)
                self.msg(f"Did you mean any of: {', '.join(suggestions)}")
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
                self.msg("|xAborted.|n")
                return
    
            if answer-1 >= 0 and answer-1 < len(mons):
                mon = mons[answer-1]
            else:
                self.msg("|xAborted.|n")
                return
            

        self.msg(f"Selected {get_display_mon_banner(mon)}")

        all_abilities = [abi for abi in mon['abilities'] if abi]
        all_abilities.extend([abi for abi in mon['hidden_abilities'] if abi])

        if not all_abilities:
            ability = ""
            self.msg(f"{get_display_mon_banner(mon)} has no abilities.")
        elif len(all_abilities) == 1:
            ability = all_abilities[0]
            self.msg(f"{get_display_mon_banner(mon)} only has ability '{ability}', selecting it.")
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
                self.msg("|xAborted.|n")
                return
    
            if answer-1 >= 0 and answer-1 < len(choices):
                ability = choices[answer-1]
            else:
                self.msg("|xAborted.|n")
                return
            
            self.msg(f"{ability} selected.")
    
        target.set_species(self.caller, mon, ability)

        self.msg(f"{target.get_display_name(looker=self.caller)} updated.")


class CmdChargenSetNature(Command):
    """
    Usage: 
        setnature [nature]
    """
    key = 'setnature'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: setnature [nature]"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata

        target = self.caller

        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            # Should never happen, but
            self.msg(f"You don't have permission to work on {target.name}.")
            return

        args = self.args.strip() if self.args else ""
        
        if args:
            if args in mondata.natures:
                nature = args
            else:
                self.msg(f"Nature '{args}' does not exist.")
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
                self.msg("|xAborted.|n")
                return
    
            if answer-1 >= 0 and answer-1 < len(choices):
                nature = choices[answer-1]
            else:
                self.msg("|xAborted.|n")
                return
            
        self.msg(f"{nature} selected.")

        target.set_nature(self.caller, mondata.natures[nature])

        self.msg(f"{target.get_display_name(looker=self.caller)} updated.")


class CmdChargenBuyIVs(MuxCommand):
    """
    Usage:
        buyivs <stat> = <tokens to spend>
    """
    key = 'buyivs'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: buyivs <stat> = <tokens to spend>"

    def func(self):
        mondata = GLOBAL_SCRIPTS.mondata
    
        target = self.caller

        if not (target.access(self.caller, "control") or target.access(self.caller, "edit")):
            # Should never happen, but
            self.msg(f"You don't have permission to work on {target.name}.")
            return
        
        remaining = target.ivtokens - target.ivtokens_spent
        if not remaining:
            self.msg(f"{target.get_display_name(looker=self.caller)} has no IV tokens to spend.")
        
        stat = self.lhs
        amount = self.rhs

        if not (stat and amount):
            self.msg(self._usage)
            return

        if stat not in mondata.lookup_statlist:
            self.msg(f"'{stat}' is not a valid stat.")
            return

        stat = mondata.lookup_statlist[stat]
        
        try:
            amount = int(amount)
        except ValueError:
            self.msg(f"Tokens to spend must be a positive integer")
            return
        
        if not 0 <= amount:
            self.msg(f"Tokens to spend must be a positive integer")
            return
        
        amount = min(amount,remaining)
        while amount and amount * 3 + target.ivs[stat] > 30:
            amount -= 1
        
        if not amount:
            self.msg(f"{target}'s {stat} is already maxed out!")
            return
        
        question = (
            f"Spend {amount} of {target.get_display_name(looker=self.caller)}'s {remaining} " 
            f"remaining IV tokens to raise "
            f"{stat}'s IVs from {target.ivs[stat]} to {target.ivs[stat] + amount * 3}? [y/N]"
        )

        answer = yield question

        if not answer.strip().lower().startswith('y'):
            self.msg("|xAborted.|n")
            return
        
        target.spend_iv_tokens(self.caller, stat, amount)

        self.msg(f"{target.get_display_name(looker=self.caller)} updated.")


class CmdChargenResetIVs(MuxCommand):
    """
    Usage:
        resetivs
    """
    key = 'resetivs'
    locks = "cmd:all()"
    help_category = "Chargen"

    def func(self):

        target = self.caller

        if not any(target.ivs.values()):
            self.msg(f"{target.get_display_name(self.caller)} has no ivs bought, no need to reset.")
            return

        target.reset_ivs(self.caller)

        self.msg(f"{target.get_display_name(self.caller)} updated.")


class CmdChargenEquipMove(MuxCommand):
    """
    Usage:
        equipmove <move name>
    """
    key = 'equipmove'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: equipmove <move name>"

    def func(self):

        mondata = GLOBAL_SCRIPTS.mondata

        target = self.caller

        if len(target.moves_equipped) >= _MAX_EQUIPPED_MOVES:
            self.msg(
                f"{target.get_display_name(self.caller)} already has "
                f"{len(target.moves_equipped)} out of {_MAX_EQUIPPED_MOVES} moves equipped."
            )
            return

        movename = self.args.strip()

        if not movename:
            self.msg(self._usage)
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            suggestions = string_suggestions(movename, mondata.movenames)
            self.msg(f"Could not find a move named '{movename}', did you mean one of {suggestions}?")
            return
        
        if actual_movename in target.moves_equipped:
            self.msg(f"{target.get_display_name(self.caller)} already has {actual_movename} equipped.")
            return

        if not actual_movename in target.moves_known:
            if target.player_mode == "CG":
                target.learn_move(self.caller, actual_movename)
                self.msg(
                    f"This is chargen, so {target.get_display_name(self.caller)} is "
                    f"also learning {actual_movename}."
                )
            else:
                self.msg(f"{target.get_display_name(self.caller)} doesn't know the move {actual_movename}.")
                return
        
        target.equip_move(self.caller, actual_movename)
        self.msg(f"{target.get_display_name(self.caller)} equipped {actual_movename}.")


class CmdChargenUnequipMove(MuxCommand):
    """
    Unequip move or show equipped moves if move name not given.

    Usage:
        unequipmove [move name]
    """
    key = 'unequipmove'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: unequipmove [move name]"

    def func(self):

        mondata = GLOBAL_SCRIPTS.mondata

        target = self.caller

        if not target.moves_equipped:
            self.msg(f"No moves equipped by {target.get_display_name(self.caller)}.")
            return

        movename = self.args.strip()

        if not movename:
            self.msg(
                f"{target.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(target.moves_equipped.keys()))}."
            )
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            suggestions = string_suggestions(movename, mondata.movenames)
            self.msg(
                f"Could not find a move named '{movename}'. "
                f"{target.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(target.moves_equipped.keys()))}."
            )
            return
        
        if actual_movename not in target.moves_equipped:
            
            self.msg(
                f"{target.get_display_name(self.caller)} doesn't have {actual_movename} equipped. "
                f"{target.get_display_name(self.caller)} has these moves equipped: "
                f"{', '.join(sorted(target.moves_equipped.keys()))}."
            )
            return

        target.unequip_move(self.caller, actual_movename)
        self.msg(f"{target.get_display_name(self.caller)} unequipped {actual_movename}.")


class CmdChargenLearnMove(MuxCommand):
    """
    Usage:
        learnmove <move name>
    """
    key = 'learnmove'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: learnmove <move name>"

    def func(self):
        
        mondata = GLOBAL_SCRIPTS.mondata

        target = self.caller

        movename = self.args.strip()

        if not movename:
            self.msg(self._usage)
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            suggestions = string_suggestions(movename, mondata.movenames)
            self.msg(f"Could not find a move named '{movename}', did you mean one of {suggestions}?")
            return
        
        if actual_movename in target.moves_known:
            self.msg(f"{target.get_display.name(self.caller)} doesn't know {actual_movename}")
            return

        target.learn_move(self.caller, actual_movename)
        self.msg(f"{target.get_display_name(self.caller)} learned {actual_movename}.")


class CmdChargenForgetMove(MuxCommand):
    """
    Forget move or show known moves if move name not given.
    Usage:
        forgetmove [move name]
    """
    key = 'forgetmove'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: forgetmove [move name]"

    def func(self):

        mondata = GLOBAL_SCRIPTS.mondata

        target = self.caller

        if not target.moves_known:
            self.msg(f"No moves known by {target.get_display_name(self.caller)}.")
            return

        movename = self.args.strip()

        if not movename:
            self.msg(
                f"Moves {target.get_display_name(self.caller)} knows are: "
                f"{', '.join(sorted(target.moves_known))}."
            )
            return
        
        movename = movename.lower()

        if movename in mondata.movelookup:
            actual_movename = mondata.movelookup[movename]
        else:
            self.msg(
                f"Could not find a move named '{movename}'. "
                f"Moves {target.get_display_name(self.caller)} knows are: {', '.join(sorted(target.moves_known))}."
            )
            return
        
        if actual_movename not in target.moves_known:
            self.msg(
                f"{target.get_display_name(self.caller)} doesn't know {actual_movename}. "
                f"Moves {target.get_display_name(self.caller)} knows are: {', '.join(sorted(target.moves_known))}."
            )
            return
        
        if actual_movename in target.moves_equipped:
            target.unequip_move(self.caller, actual_movename)
            self.msg(f"{target.get_display_name(self.caller)} unequips {actual_movename} to forget it.")

        target.forget_move(self.caller, actual_movename)
        self.msg(f"{target.get_display_name(self.caller)} forgot {actual_movename}.")


_valid_fields = {
    "full name": "full name", 
    "fullname": "full name", 
    "fname": "full name",
    "short desc": "short desc", 
    "shortdesc": "short desc", 
    "sdesc": "short desc",
    "player name": "player name", 
    "playername": "player name",
    "pname": "player name",
    "player contact": "player contact",
    "playercontact": "player contact",
    "pcontact": "player contact",
}

class CmdChargenSetInfo(MuxCommand):
    """
    Set a piece of extended info on your character

    For valid fields and current settings run with no parameters.

    Usage:
        +setinfo [field = text]
    """
    key = '+setinfo'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: +setinfo [field = text]"

    def func(self):
        
        target = self.caller
        field = self.lhs
        text = self.rhs

        if not (field and text):
            short_desc = target.short_desc
            full_name = target.full_name
            player_name = target.player_name
            player_contact = target.player_contact

            self.msg(
                f"Fields settable by this command as seen on {target.get_display_name()}:\n"
                f" |wShort Description/sdesc|n: |b{short_desc if short_desc else "<NOT SET>"}|n\n"
                f" |wFull Name/fname        |n: |b{full_name if full_name else "<NOT SET>"}|n\n"
                f" |wPlayer Name/pname      |n: |b{player_name if player_name else "<NOT SET>"}|n\n"
                f" |wPlayer Contact/pcontact|n: |b{player_contact if player_contact else "<NOT SET>"}|n"
            )
            return      
            
        field = field.lower()
        if not field in _valid_fields:
            self.msg(f"'{field}' is not a valad field")
            return
        
        field = _valid_fields[field]
        if field == 'full name':
            target.full_name = text
        elif field == 'short desc':
            target.short_desc = text
        elif field == 'player name':
            target.player_name = text
        elif field == 'player contact':
            target.player_contact = text

        self.msg(f"{target.get_display_name(self.caller)} updated.")
        

class CmdChargenSetSex(MuxCommand):
    """
    Set your character's apparent sex.

    Do you appear |wM|nale, |wF|nemale, |wA|nndrogynous, |wN|neuter.

    Usage:
        +setsex <sex>
    """
    key = '+setsex'
    locks = "cmd:all()"
    help_category = "Chargen"

    _usage = "Usage: +setsex [sex]"

    def func(self):
        
        target = self.caller
        field = self.args
        
        if not field:
            sex = target.sex
            self.msg(f"{target.get_display_name()}'s apparent sex is |b{sex if sex else '<NOT SET>'}|n.")

        field = field.lower()
        if field.startswith('a'):
            target.sex = 'Androgynous'
        elif field.startswith('f'):
            target.sex = 'Female'
        elif field.startswith('m'):
            target.sex = 'Male'
        elif field.startswith('n'):
            target.sex = 'Neuter'
        else:
            self.msg("Please pick from |bandrogynous|n, |bfemale|n, |bmale|n, |bneuter|n.")
            return

        self.msg(f"{target.get_display_name(self.caller)} is now {target.sex}.")
        
