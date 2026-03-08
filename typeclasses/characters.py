"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

import time
import random
import math

from django.db.models import Q  # type: ignore
from django.conf import settings # type: ignore

from evennia import AttributeProperty
from evennia.comms.models import ChannelDB
from evennia.objects.objects import DefaultCharacter
from evennia.utils import logger
from evennia.utils.ansi import ANSI_PARSER

from .objects import ObjectParent

from world.utils import header_two_slot
from world.monutils import get_display_mon_banner

_IV_TOKEN_BUDGET = math.ceil((6 * 16) / 3)
_MOVE_DELAY = 15
_IDLE_TIME = 60*5

_display_statname = {
    'health': 'Health',
    'physical attack': 'PhysAtk',
    'special attack': 'SpecAtk',
    'physical defense': 'PhysDef',
    'special defense': 'SpecDef',
    'speed': 'Speed',
}

_statcolor = {
    'health': '69DC12',
    'physical attack': 'EFCC18',
    'special attack': '14C3F1',
    'physical defense': 'E86412',
    'special defense': '4A6ADF',
    'speed': 'D51DAD',
}


def _statline(statname, char):
    stat = char.stats[statname] if char.stats else 0
    iv = char.ivs[statname] if char.stats else 0
    ev = char.evs[statname] if char.stats else 0
    sep = ':'
    if char.favored_stat.lower() == statname:
        sep = '+'
    elif char.neglected_stat.lower() == statname:
        sep = '-'
    return f"|#{_statcolor[statname]}{_display_statname[statname]:>7}{sep}|w{stat:3d}|x[{iv:2d}||{ev:3d}]|n"



class Character(ObjectParent, DefaultCharacter):
    """
    A general character. Contains functionality that's important for NPCs and PCs alike.
    """
    
    species = AttributeProperty("")
    subtype = AttributeProperty("")
    form = AttributeProperty("")
    dexno = AttributeProperty(0)
    type1 = AttributeProperty("")
    type2 = AttributeProperty("")
    ability = AttributeProperty("")
    base_stats = AttributeProperty({})
    nature = AttributeProperty("")
    moves = AttributeProperty("")

    favored_stat = AttributeProperty("")
    neglected_stat = AttributeProperty("")
    stats = AttributeProperty({})
    ivs = AttributeProperty({})
    evs = AttributeProperty({})
    
    level = AttributeProperty(50)
    
    ivtokens = AttributeProperty(0)
    ivtokens_spent = AttributeProperty(0)
    evtokens = AttributeProperty(0)
    evtokens_spent = AttributeProperty(0)


    def return_appearance(self, looker=None, **kwargs):
        
        header = header_two_slot(80,
            f"{self.get_display_name()}{self.get_extra_display_name_info(looker, **kwargs)}",
            f"{get_display_mon_banner(self)}",
            headercolor="|b"
        )

        statblock = self.get_statblock(looker, **kwargs)

        return f"\n{header}\n{statblock}\n{self.get_display_desc(looker, **kwargs)}"
    

    def get_statblock(self, looker=None, **kwargs):

        stat1 = f"{_statline('health',self)}{_statline('physical attack',self)}{_statline('special attack',self)}"
        stat2 = f"{_statline('speed',self)}{_statline('physical defense',self)}{_statline('special defense',self)}"

        stat1 += f"|b  Level:|n {self.level}"
        stat2 += f"|b Nature:|n {self.nature}"

        ivtokens_left = self.ivtokens - self.ivtokens_spent
        evtokens_left = self.evtokens - self.evtokens_spent
        
        ivcolor = '|r' if ivtokens_left else '|n'
        evcolor = '|r' if evtokens_left else '|n'

        stat3 = f"|b{'IV Tokens:':>15}{ivcolor} {self.ivtokens - self.ivtokens_spent:2n} "
        stat3 += f"|b{'EV Tokens:':>15}{evcolor} {self.evtokens - self.evtokens_spent:2n} "
        stat3 += f"|b{"Ability:":>15}|n {self.ability}"

        return '\n'.join((stat1, stat2, stat3))
    

    def reset_ivs(self):

        ivs = {}
        for key in self.base_stats.keys():
            ivs[key] = 0
        self.ivs = ivs
        self.ivtokens = _IV_TOKEN_BUDGET
        self.ivtokens_spent = 0
    
    def reset_evs(self):

        evs = {}
        for key in self.base_stats.keys():
            evs[key] = 0
        self.evs = evs
        # Evtokens can only be removed or added by staff
        self.evtokens_spent = 0


    def init_stats (self):

        self.reset_ivs()
        self.reset_evs()
        self.update_stats()
    

    def update_stats(self):

        stats = {}
        for stat in self.base_stats.keys():
            if stat == "health":
                topline = (2 * self.base_stats[stat] + self.ivs[stat] + math.floor(self.evs[stat] / 4)) * self.level
                value = math.floor(topline / 100) + self.level + 10
            else:
                topline = (2 * self.base_stats[stat] + self.ivs[stat] + math.floor(self.evs[stat] / 4)) * self.level
                value = math.floor(topline / 100) + 5

            if stat == self.favored_stat:
                value = math.floor(stat * 1.10)
            elif stat == self.neglected_stat:
                value = math.floor(stat * 0.90)
            
            stats[stat] = value
        self.stats = stats


    def set_species(self, caller, mon, ability):

        self.species = mon['name']
        self.subtype = mon['subtype']
        self.form = mon['form']
        self.dexno = mon['dexno']
        self.type1 = mon['type1']
        self.type2 = mon['type2']
        self.base_stats = mon['base_stats']
        self.ability = ability

        self.init_stats()

        
    def set_nature(self, caller, nature):

        favored = nature['favored_stat']
        neglected = nature['neglected_stat']
        if favored == neglected:
            favored = ""
            neglected = ""

        self.nature = nature['name']
        self.favored_stat = favored
        self.neglected_stat = neglected
        self.update_stats()
        
        
    def spend_iv_tokens(self, caller, stat, amount):
        
        self.ivs[stat] += amount * 3
        self.ivtokens_spent += amount
        self.update_stats()

    @property
    def is_idle(self):
        """
        Has the character been idle for longer than the set time?
        """
        if not self.has_account:
            return True
        return self.idle_time > _IDLE_TIME
    
    @property
    def is_comms_idle(self):
        """
        Has the character emitted text that others can see for longer than the set time?
        """
        # TODO: Implement comms idle system
        return self.is_idle
    
    @property
    def is_player_character(self):
        """Is this a player character. Better than using instanceof."""
        return False
    
    def get_display_name(self, looker=None):
        """
        Color this character name based on what their account's permissions are,
        or otherwise what type of character it is. Staff is always staff. Quelling
        doesn't change that.

        TODO: Move colors into a config somewhere?
        """

        color = ""
        if not self.is_player_character:
            color = "|x"
        elif looker == self or looker == self.account:
            color="|420"
        elif not self.has_account:
            color = ""
        elif self.account.is_superuser:
            color = "|[M|X" if self.is_comms_idle else "|[m|X"
        elif self.account.permissions.check("Developer"):
            color = "|M" if self.is_comms_idle else "|m"
        elif self.account.permissions.check("Admin"):
            color = "|C" if self.is_comms_idle else "|c"
        elif self.account.permissions.check("Builder"):
            color = "|Y" if self.is_comms_idle else "|y"
        elif self.account.permissions.check("Helper"):
            color = "|B" if self.is_comms_idle else "|b"
        elif not self.is_comms_idle:
            color = "|g"
        else:
            color = "|G"

        return "{}{}{}".format(color, self.name, "|n" if color else "")
        

class PlayerCharacter(Character):
    """
    This Character is for accounts to connect to. It adds functionality that only matters for
    characters that are controlled by people. 
    """

    approved = AttributeProperty(False)
    auditlog = AttributeProperty([])
    whostatus = AttributeProperty("")
    stafftag = AttributeProperty("")

    
    def logaudit(self, msg):
        self.auditlog.append((time.time(),msg))

        msg = ANSI_PARSER.strip_mxp(msg)
        msg = ANSI_PARSER.parse_ansi(msg, strip_ansi=True)
        logger.log_file(msg, "audit.log")
        logger.log_info("Audit: " + msg)


    def init_stats(self):
        self.level = 50
        super().init_stats()

    def set_species(self, caller, mon, ability):
        super().set_species(caller, mon, ability)

        msg = (
            f"{caller.get_display_name(looker=self)} updated {self.get_display_name(looker=self)}'s "
            f"species to {get_display_mon_banner(mon)} with an ability of {ability}."
        )
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)
            
    
    def set_nature(self, caller, nature):
        super().set_nature(caller, nature)

        msg = (
            f"{caller.get_display_name(looker=self)} updated {self.get_display_name(looker=self)}'s "
            f"nature to {nature['name']}."
        )
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)

    def spend_iv_tokens(self, caller, stat, amount):
        super().spend_iv_tokens(caller, stat, amount)

        msg = (
            f"{caller.get_display_name(looker=self)} spent {amount} of {self.get_display_name(looker=self)}'s "
            f"IV tokens to raise {stat} IVs from {self.ivs[stat] - amount * 3} to {self.ivs[stat]}. "
            f"{self.ivtokens - self.ivtokens_spent} IV tokens remain."
        )
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)




    @property
    def is_player_character(self):
        """Is this a player character. Better than using instanceof."""
        return True

    def at_object_creation(self):
        """
        Setup default channels and messaging permissions that now live on characters instead of
        accounts.
        """
        
        self.logaudit(f"{self.name} created.")

        # For the character-focused channel system
        self.locks.add("msg:all()")

        # Transplanted from default account.

        channel = ChannelDB.objects.get_channel("ConnectInfo")
        if not channel or not (channel.access(self, "listen") and channel.connect(self)):
            logger.log_err("New character '{self.key}' could not connect to ConnectInfo")
            
        for chan_info in settings.DEFAULT_CHANNELS:
            if chankey := chan_info.get("key"):
                channel = ChannelDB.objects.get_channel(chankey)
                if not channel or not (channel.access(self, "listen") and channel.connect(self)):
                    logger.log_err(f"New character '{self.key}' could not connect to default channel '{chankey}'!")
            else:
                logger.log_err(f"Default channel '{chan_info}' is missing a 'key' field!")



        return super().at_object_creation() # Not sure if return part is needed but


    def at_pre_move(self, dest, move_type=None, **kwargs):
        if move_type == "traverse":
            now = time.time()
            if self.ndb.movelock and self.ndb.movelock > now:
                self.msg("Can't move for another {:.0f} seconds".format(self.ndb.movelock - now))
                return False
            else:
                return super().at_pre_move(dest, move_type, **kwargs)
        else:
            return super().at_pre_move(dest, move_type, **kwargs)

    def at_post_move(self, src, **kwargs):
        active_players_in_room = [char 
                for char in PlayerCharacter.objects.filter(Q(db_location=self.location) & ~ Q(db_key=self)) 
                if char.idle_time and char.idle_time < _IDLE_TIME]
        if active_players_in_room:
            self.ndb.movelock = time.time() + _MOVE_DELAY
            self.register_post_command_message(
                "|MPlayer activity detected|n, locking movement for {} seconds.".format(_MOVE_DELAY)
            )
        else:
            self.ndb.movelock = None;
        super().at_post_move(src, **kwargs)


    def at_pre_channel_msg(self, message, channel, senders=None, **kwargs):
        """
        Called by the Channel just before passing a message into `channel_msg`.
        This allows for tweak messages per-user and also to abort the
        receive on the receiver-level. (Copied from Account)

        Args:
            message (str): The message sent to the channel.
            channel (Channel): The sending channel.
            senders (list, optional): Accounts or Objects acting as senders.
                For most normal messages, there is only a single sender. If
                there are no senders, this may be a broadcasting message.
            **kwargs: These are additional keywords passed into `channel_msg`.
                If `no_prefix=True` or `emit=True` are passed, the channel
                prefix will not be added (`[channelname]: ` by default)

        Returns:
            str or None: Allows for customizing the message for this recipient.
                If returning `None` (or `False`) message-receiving is aborted.
                The returning string will be passed into `self.channel_msg`.

        Notes:
            This support posing/emotes by starting channel-send with : or ;.

        """
        if senders:
            sender_string = ", ".join(sender.get_display_name(self) for sender in senders)
            message_lstrip = message.lstrip()
            if message_lstrip.startswith((":", ";")):
                # this is a pose, should show as e.g. "User1 smiles to channel"
                spacing = "" if message_lstrip[1:].startswith((":", "'", ",")) else " "
                message = f"{sender_string}{spacing}{message_lstrip[1:]}"
            else:
                # normal message
                message = f"{sender_string}: {message}"

        if not kwargs.get("no_prefix") and not kwargs.get("emit"):
            message = channel.channel_prefix() + message

        return message

    def channel_msg(self, message, channel, senders=None, **kwargs):
        """
        This performs the actions of receiving a message to an un-muted
        channel. (Copied from Account)

        Args:
            message (str): The message sent to the channel.
            channel (Channel): The sending channel.
            senders (list, optional): Accounts or Objects acting as senders.
                For most normal messages, there is only a single sender. If
                there are no senders, this may be a broadcasting message or
                similar.
            **kwargs: These are additional keywords originally passed into
                `Channel.msg`.

        Notes:
            Before this, `Channel.at_pre_channel_msg` will fire, which offers a way
            to customize the message for the receiver on the channel-level.

        """
        self.msg(
            text=(message, {"from_channel": channel.id}),
            from_obj=senders,
            options={"from_channel": channel.id},
        )

    def at_post_channel_msg(self, message, channel, senders=None, **kwargs):
        """
        Called by `self.channel_msg` after message was received. (Copied from Account)

        Args:
            message (str): The message sent to the channel.
            channel (Channel): The sending channel.
            senders (list, optional): Accounts or Objects acting as senders.
                For most normal messages, there is only a single sender. If
                there are no senders, this may be a broadcasting message.
            **kwargs: These are additional keywords passed into `channel_msg`.

        """
        pass
