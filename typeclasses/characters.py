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
from collections import deque

from django.db.models import Q 
from django.conf import settings
from django.utils.translation import gettext as _ # Not really using this but...


from evennia import AttributeProperty
from evennia.comms.models import ChannelDB
from evennia.objects.objects import DefaultCharacter
from evennia.utils import logger, display_len, time_format, crop
from evennia.utils.ansi import ANSI_PARSER

from .objects import ObjectParent

from world.utils import header_two_slot, anyone_notice, get_specialroom, get_defaulthome
from world.monutils import get_display_mon_banner, moves_table

_WIDTH = settings.OUR_WIDTH
_IV_TOKEN_BUDGET = settings.CHARACTER_IV_TOKEN_BUDGET
_RP_TRAP_MOVE_DELAY = settings.RP_TRAP_MOVE_DELAY
_RP_TRAP_IDLE_TIME = settings.RP_TRAP_IDLE_TIME
_GENERAL_IDLE_TIME = settings.GENERAL_IDLE_TIME
_TAG_OOC_TARGET = settings.TAG_OOC_TARGET

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

# There's an issue with the math here where being 40 points apart will show as 'stronger' to one side
# but 'slightly weaker' to the other. Not sure how to fix that.

_comparetable = [
    (-999, -80, "Incredibly Weaker",      "|g"),
    ( -80, -60, "Significantly Weaker",   "|g"),
    ( -60, -40, "Weaker",                 "|G"),
    ( -40, -20, "Slightly Weaker",        "|G"),
    ( -20,  20, "Comprable",              "|Y"),
    (  20,  40, "Slightly Stronger",      "|R"),
    (  40,  60, "Stronger",               "|R"),
    (  60,  80, "Significantly Stronger", "|r"),
    (  80, 999, "Incredibly Stronger",    "|r"),
]

def _comparestatline (statname, us, them):
    # We're going to assume that both sides have stats here
    ourstat = us.stats[statname]
    theirstat = them.stats[statname]
    diff = theirstat - ourstat # this + us = them

    desc = ""
    color = ""
    for low, high, d, c in _comparetable:
        if low <= diff < high:
            desc = d
            color = c
            break

    return f"|#{_statcolor[statname]}{_display_statname[statname]:>7}:{color}{desc:>23}|n"

def _comparecrossstats (stat1, stat2, us, them):
    # We're going to assume that both sides have stats here
    ourstat = us.stats[stat1]
    theirstat = them.stats[stat2]
    diff = theirstat - ourstat # this + us = them

    desc = ""
    color = ""
    for low, high, d, c in _comparetable:
        if low <= diff < high:
            desc = d
            color = c
            break

    return (
        f"|#{_statcolor[stat1]}{_display_statname[stat1]}"
        f"|w vs |#{_statcolor[stat2]}{_display_statname[stat2]}"
        f": {color}{desc}|n"
    )


class Character(ObjectParent, DefaultCharacter):
    """
    A monmorph character. Contains functionality that's important for NPCs and PCs alike.
    """
    
    # Game system properties

    species = AttributeProperty("")
    subtype = AttributeProperty("")
    form = AttributeProperty("")
    dexno = AttributeProperty(0)
    type1 = AttributeProperty("")
    type2 = AttributeProperty("")
    base_stats = AttributeProperty({})

    ability = AttributeProperty("")
    
    nature = AttributeProperty("")
    favored_stat = AttributeProperty("")
    neglected_stat = AttributeProperty("")

    level = AttributeProperty(50)
    stats = AttributeProperty({})
    
    ivs = AttributeProperty({})
    ivtokens = AttributeProperty(0)
    ivtokens_spent = AttributeProperty(0)

    evs = AttributeProperty({})
    evtokens = AttributeProperty(0)
    evtokens_spent = AttributeProperty(0)
    
    moves_known = AttributeProperty(set())
    moves_equipped = AttributeProperty({})

    health_lost = AttributeProperty(0)

    # Profile Properties

    sex = AttributeProperty("")

    short_desc = AttributeProperty("")
    full_name = AttributeProperty("")
    player_name = AttributeProperty("")
    player_contact = AttributeProperty("")
    
    faction = AttributeProperty("Unaffiliated")
    subfaction = AttributeProperty("")
    rank = AttributeProperty("Nobody")

    last_puppeted = AttributeProperty(0)
    last_puppeted_by = AttributeProperty(None)

    last_ic_room = AttributeProperty(None)

    following = AttributeProperty(None, category='follow')
    followers = AttributeProperty(set(), category='follow')



    def get_display_header(self, looker=None, **kwargs):
        return header_two_slot(_WIDTH,
            f"{self.get_display_name(looker, **kwargs)}{self.get_extra_display_name_info(looker, **kwargs)}",
            f"{get_display_mon_banner(self)}",
            headercolor="|b"
        )


    def return_appearance(self, looker=None, show_header=True, **kwargs):
        desc = self.get_display_desc(looker, **kwargs)

        if looker == self:
            if display_len(desc) < self.DESC_LENGTH_REQ:
                anyone_notice(looker, "Your description should be longer.")

        return f"{self.get_display_header() + '\n' if show_header else ''}{desc}\n"
    

    def get_statblock(self, looker, always_compare=False, show_header=True, **kwargs):

        if not self.species:
            return (
                f"{self.get_display_name(looker)} does not have a species selected, "
                "thus there are no stats to see or compare to.\n"
            )

        out = [self.get_display_header(looker)] if show_header else []

        if self == looker or (looker.permissions.check("Admin") and not always_compare):

            # Return the real full stat block
            stat1 = (
                f"{_statline('health',self)}{_statline('physical attack',self)}{_statline('special attack',self)}"
                f"|b  Level:|n {self.level}"
            )

            stat2 = (
                f"{_statline('speed',self)}{_statline('physical defense',self)}{_statline('special defense',self)}"
                f"|b Nature:|n {self.nature}"
            )

            ivtokens_left = self.ivtokens - self.ivtokens_spent
            evtokens_left = self.evtokens - self.evtokens_spent
            
            ivcolor = '|r' if ivtokens_left else '|n'
            evcolor = '|r' if evtokens_left else '|n'

            stat3 = (
                f"|b{'EV Tokens:':>15}{evcolor} {evtokens_left:2n} "
                f"|b{'Ability:':>15}|n {self.ability}"
            )

            stat4 = f"|b{'IV Tokens:':>15}{ivcolor} {ivtokens_left:2n}|n" if ivtokens_left else ""

            out += [stat1, stat2, stat3]

            if stat4:
                out.append(stat4)

            if self.moves_equipped:
                out.append(f"|w{'- - - Moves Equipped - - -':^{_WIDTH}}|n")
                out.append(str(moves_table(self.moves_equipped)))

            moves_known_filtered = self.moves_known.copy()
            for move in self.moves_equipped:
                moves_known_filtered.remove(move)
            
            if moves_known_filtered:
                out.append(f"|w{'- - - Moves Known - - -':^{_WIDTH}}|n")
                out.append(str(moves_table(moves_known_filtered, useheader=(not self.moves_equipped))))
            
            out.append('')
        
        else:
            stat0 = (
                f" Compared to |bLv{looker.level}|n {looker.get_display_name(looker)}, "
                f"|bLv{self.level}|n {self.get_display_name(looker)} is:"
            )
            stat1 = (
                f" {_comparestatline("health", looker, self)}  "
                f" {_comparestatline("speed", looker, self)}"
            )
            stat2 = (
                f" {_comparestatline("physical attack", looker, self)}  "
                f" {_comparestatline("physical defense", looker, self)}"
            )
            stat3 = (
                f" {_comparestatline("special attack", looker, self)}  "
                f" {_comparestatline("special defense", looker, self)}"
            )
            # stat4 = f" {_comparecrossstats('physical attack', 'physical defense', looker, self)}"
            # stat5 = f" {_comparecrossstats('special attack', 'special defense', looker, self)}"

            out += [stat0, stat1, stat2, stat3, '']

        return '\n'.join(out)
    

    def get_finger(self, looker=None, show_header=True, **kwargs):

        out = [self.get_display_header(looker)] if show_header else []

        # subfaction = f"|w/|n{self.subfaction}" if self.subfaction else ""
        # fullfaction = f"{self.faction}{subfaction}"
        lastic = time_format(self.ic_idle_time) if self.ic_idle_time else "Never"

        if self.is_typeclass(PlayerCharacter):
            if self.has_account:
                session = self.account.sessions.get()[0]
                on_line = f" |bOn for:|n {time_format(time.time() - session.conn_time)}"
            else:
                on_line = (
                    " |bLast on:|n " + time_format(time.time() - self.last_puppeted) if self.last_puppeted else "Never"
                )
            playertype = "Player"
        else:
            playertype = "Owner"
            on_line = "|b<NOT PLAYER CHARACTER>|n"
        

        out.append(f" |w{self.short_desc}|n")
        out.append(f" |bFull Name:|n {self.full_name}")
        out.append(
            f" |bSex:|n {self.sex:12}"
            f" |bAffiliation:|n {self.faction:20}"
            f" |bRank:|n {self.rank}"
        )
        out.append(
            f" |b{playertype:6}:|n {crop(self.player_name,22,"…"):22}"
            f" |bLastIC:|n {lastic:12}"
            f"{on_line}"
        )
        out.append('')

        return '\n'.join(out)


    def reset_ivs(self, caller=None):

        ivs = {}
        for key in self.base_stats.keys():
            ivs[key] = 0
        self.ivs = ivs
        self.ivtokens = _IV_TOKEN_BUDGET
        self.ivtokens_spent = 0
    
    def reset_evs(self, caller=None):

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

    
    def equip_move(self, caller, movename):
        """ Assumes caller is doing all the vetting """
        
        self.moves_equipped[movename] = 0


    def unequip_move(self, caller, movename):
        """ Assumes caller is doing all the vetting """

        # But still don't remove something that's not there
        if movename in self.moves_equipped:
            del self.moves_equipped[movename]


    def learn_move(self, caller, movename):
        """ Assumes caller is doing all the vetting """
        
        self.moves_known.add(movename)


    def forget_move(self, caller, movename):
        """ Assumes caller is doing all the vetting """

        # But still don't remove something that's not there
        if movename in self.moves_known:
            self.moves_known.remove(movename)


    def refresh_one(self, movename):
        """Refreshes a move. Returns true if a refresh actually happened, false if uses were already at 0"""
        
        if movename in self.moves_equipped:
            if self.moves_equipped[movename]:
                self.moves_equipped[movename] = 0
                return True
        # Not sure what we should do if move not equipped here but it shouldn't come up much...
        return False
            

    def refresh_all(self):
        """Refreshes all moves. Returns true if any rereshes happened, false if all uses were at 0"""

        return any([self.refresh_one(movename) for movename in self.moves_equipped])


    def start_following(self, target):
        
        if self.following:
            if self.following == target:
                target.followers.add(self) # just in case >.>
                self.msg(f"{self.get_display_name(self)} was already following {target.get_display_name(self)}.")
                target.msg(f"{self.get_display_name(target)} was already following {target.get_display_name(target)}.")
                return
            else:
                self.stop_following(self.following)
        
        if self.location != target.location:
            self.msg("Can't follow someone who isn't here.")

        # make sure we don't go cyclic
        checked_targets = set()
        unchecked_targets = deque()

        unchecked_targets.append(target.following)
        while unchecked_targets:
            subfollower = unchecked_targets.pop()
            if subfollower not in checked_targets:
                if subfollower == self:
                    self.msg(
                        f"{self.get_display_name(self)} following {target.get_display_name(self)} "
                        "would make a cycle, sorry!"
                    )
                    target.msg(
                        f"{self.get_display_name(target)} following {target.get_display_name(target)} "
                        "would make a cycle, sorry!"
                    )
                    return

                checked_targets.add(subfollower)
                if subfollower:
                    unchecked_targets.append(subfollower.following)
        



        self.following = target
        target.followers.add(self)
        self.msg(f"{self.get_display_name(self)} is now following {target.get_display_name(self)}.")
        target.msg(f"{self.get_display_name(target)} is now following {target.get_display_name(target)}.")


    def stop_following(self, target=None):
        
        if not self.following:
            return
        
        if target and self.following != target:
            self.msg(f"{self.get_display_name(self)} was never following {target.get_display_name(self)}.")
            target.msg(f"{self.get_display_name(target)} was never following {target.get_display_name(target)}.")
        
        self.msg(f"{self.get_display_name(self)} stops following {self.following.get_display_name(self)}.")
        self.following.msg(
            f"{self.get_display_name(self.following)} stops following {self.following.get_display_name(self.following)}."
        )

        if self in self.following.followers:
            self.following.followers.remove(self)
        self.following = None
        




    @property
    def is_dead(self):
        """Is remaing hp <= 0?"""
        if not self.stats:
            return False
        else:
            return self.health_lost >= self.stats['health']
        

    @property
    def is_idle(self):
        """
        Has the character been idle for longer than the set time?
        """
        if not self.has_account:
            return True
        return self.idle_time > _GENERAL_IDLE_TIME
    
    @property
    def is_comms_idle(self):
        """
        Has the character emitted text that others can see for longer than the set time?
        """
        # TODO: Implement comms idle system
        return self.is_idle
    
    def color_name(self, name, looker=None):
        """
        Color this character name based on what their account's permissions are,
        or otherwise what type of character it is. Staff is always staff. Quelling
        doesn't change that.

        TODO: Move colors into a config somewhere?
        """

        color = ""
        if not self.is_typeclass(PlayerCharacter):
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

        return f"{color}{name}{"|n" if color else ""}"
    

    def at_pre_puppet(self, account, session=None, **kwargs):
        """
        Reactivate the character. We aren't storing characters in none when they're offline anymore
        so this doesn't actually need to do anything here.

        Args:
            account (DefaultAccount): This is the connecting account.
            session (Session): Session controlling the connection.

        """
        return

    def at_post_puppet(self, **kwargs):
        """
        Called just after puppeting has been completed and all Account<->Object links have been
        established.

        Args:
            **kwargs (dict): Arbitrary, optional arguments for users overriding the call (unused by
            default).
        Notes:

            You can use `self.account` and `self.sessions.get()` to get account and sessions at this
            point; the last entry in the list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        if not self.location:
            if self.db.prelogout_location:
                newloc = self.db.prelogout_location
            elif self.home:
                newloc = self.home
            else:
                newloc = get_defaulthome()
                
            self.location = newloc
            self.location.at_object_receive(self, None)


        self.msg((self.at_look(self.location), {"type": "look"}), options=None)

        self.location.msg_contents(
            "|Y<Connection>|n {sender} has connected.",
            exclude=[self], from_obj=self, mapping={'sender':self}
        )

    def at_post_unpuppet(self, account=None, session=None, **kwargs):
        """
        We're not storing characters in None anymore. We need to store the time that they're last
        active though.

        Args:
            account (DefaultAccount): The account object that just disconnected
                from this object.
            session (Session): Session controlling the connection that
                just disconnected.
        Keyword Args:
            reason (str): If given, adds a reason for the unpuppet. This
                is set when the user is auto-unpuppeted due to being link-dead.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        if not self.sessions.count():
            self.location.msg_contents(
                "|Y<Connection>|n {sender} has left the game." + kwargs.get("reason", ""),
                exclude=[self], from_obj=self, mapping={'sender':self}
            )
            self.db.prelogout_location = self.location # Just in case
            self.last_puppeted = time.time()
            self.last_puppeted_by = account


    def at_pre_move(self, destination, move_type="move", **kwargs):
        if move_type != "traverse":
            # follow code won't work so drop followers
            for follower in self.followers:
                follower.stop_following(self)

        
        return super().at_pre_move(destination, move_type, **kwargs)

    def at_post_move(self, source_location, move_type="move", **kwargs):
        
        if self.following:
            if self.following.location != self.location:
                # We wanderd off or got separated.
                self.stop_following(self.following)
   
        super().at_post_move(source_location, move_type, **kwargs)




    def announce_move_from(self, destination, msg=None, mapping=None, move_type="move", **kwargs):
        """
        Called if the move is to be announced. This is
        called while we are still standing in the old
        location.

        Args:
            destination (DefaultObject): The place we are going to.
            msg (str, optional): a replacement message.
            mapping (dict, optional): additional mapping objects.
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:

            You can override this method and call its parent with a
            message to simply change the default message.  In the string,
            you can use the following as mappings:

            - `{object}`: the object which is moving.
            - `{exit}`: the exit from which the object is moving (if found).
            - `{origin}`: the location of the object before the move.
            - `{destination}`: the location of the object after moving.

        """
        if not self.location:
            return
        if msg:
            string = msg
        else:
            if move_type == "ic-ooc":
                string = "{object} disappears in a digital flash from {origin}, heading for {destination}."
            elif move_type == 'teleport':
                string = "{object} disappears in an unexpected way from {origin}, heading for {destination}."
            elif move_type == 'sweep':
                string = "{object} is gently swept away from {origin} to their home at {destination}."
            else:
                string = "{object} is leaving {origin}, heading for {destination}."


        location = self.location
        exits = [
            o for o in location.contents if o.location is location and o.destination is destination
        ]
        if not mapping:
            mapping = {}

        mapping.update(
            {
                "object": self,
                "exit": exits[0] if exits else _("somewhere"),
                "origin": location or _("nowhere"),
                "destination": destination or _("nowhere"),
            }
        )

        location.msg_contents(
            (string, {"type": move_type}), exclude=(self,), from_obj=self, mapping=mapping
        )

    def announce_move_to(self, source_location, msg=None, mapping=None, move_type="move", **kwargs):
        """
        Called after the move if the move was not quiet. At this point
        we are standing in the new location.

        Args:
            source_location (DefaultObject): The place we came from
            msg (str, optional): the replacement message if location.
            mapping (dict, optional): additional mapping objects.
            move_type (str): The type of move. "give", "traverse", etc.
                This is an arbitrary string provided to obj.move_to().
                Useful for altering messages or altering logic depending
                on the kind of movement.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Notes:

            You can override this method and call its parent with a
            message to simply change the default message.  In the string,
            you can use the following as mappings (between braces):


            - `{object}`: the object which is moving.
            - `{exit}`: the exit from which the object is moving (if found).
            - `{origin}`: the location of the object before the move.
            - `{destination}`: the location of the object after moving.

        """

        if not source_location and self.location.has_account:
            # This was created from nowhere and added to an account's
            # inventory; it's probably the result of a create command.
            string = _("You now have {name} in your possession.").format(
                name=self.get_display_name(self.location)
            )
            self.location.msg(string)
            return

        if source_location:
            if msg:
                string = msg
            else:
                if move_type == "ic-ooc":
                    string = "{object} appears in a digital flash at {destination}, from {origin}."
                elif move_type == "teleport":
                    string = "{object} appears in an unexpected way at {destination}, from {origin}."
                elif move_type == "sweep":
                    string = "{object} is gently deposited by the sweeper at {destination}, from {origin}."
                else:
                    string = "{object} arrives in {destination} from {origin}."
        else:
            string = "{object} arrives in {destination}."

        origin = source_location
        destination = self.location
        exits = []
        if origin:
            exits = [
                o
                for o in destination.contents
                if o.location is destination and o.destination is origin
            ]

        if not mapping:
            mapping = {}

        mapping.update(
            {
                "object": self,
                "exit": exits[0] if exits else _("somewhere"),
                "origin": origin or _("nowhere"),
                "destination": destination or _("nowhere"),
            }
        )

        destination.msg_contents(
            (string, {"type": move_type}), exclude=(self,), from_obj=self, mapping=mapping
        )



class PlayerCharacter(Character):
    """
    This Character is for accounts to connect to. It adds functionality that only matters for
    characters that are controlled by people. 

    Player_mode should be one of AUP (not accepted rules yet), OOC, IC, CG (chargen), DOWN, or JAIL
    """

    auditlog = AttributeProperty([])
    
    accepted_rules = AttributeProperty(False)
    approved = AttributeProperty(False)
    approvelocked = AttributeProperty(False)

    player_mode = AttributeProperty("OOC")
    
    whostatus = AttributeProperty("")
    stafftag = AttributeProperty("")

    last_ic_talk_time = AttributeProperty(0, category="talkmonitor")
    move_lock_end_time = AttributeProperty(0, category="talkmonitor")
    ic_wordcount = AttributeProperty(0, category="talkmonitor")

    DESC_LENGTH_REQ = settings.DESIRED_MIN_DESC
    
    def logaudit(self, msg):
        self.auditlog.append((time.time(),msg))

        msg = ANSI_PARSER.strip_mxp(msg)
        msg = ANSI_PARSER.parse_ansi(msg, strip_ansi=True)
        logger.log_file(msg, "audit.log")
        logger.log_info("Audit: " + msg)


    def reset_ivs(self, caller=None):
        super().reset_ivs(caller)
        if caller:
            msg = f"{caller.get_display_name(self)} reset IVs on {self.get_display_name(self)}."
        
            self.logaudit(msg)
            if caller != self:
                self.msg(msg)

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


    def equip_move(self, caller, movename):
        super().equip_move(caller, movename)

        msg = f"{caller.get_display_name(self)} made {self.get_display_name(self)} equip move {movename}."
        
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)


    def unequip_move(self, caller, movename):
        super().unequip_move(caller, movename)

        msg = f"{caller.get_display_name(self)} made {self.get_display_name(self)} unequip move {movename}."
        
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)

    
    def learn_move(self, caller, movename):
        super().learn_move(caller, movename)
                
        msg = f"{caller.get_display_name(self)} made {self.get_display_name(self)} learn move {movename}."
        
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)

    
    def forget_move(self, caller, movename):
        super().forget_move(caller, movename)
        
        msg = f"{caller.get_display_name(self)} made {self.get_display_name(self)} forget move {movename}."
        
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)


    def approvelock(self, caller):
        """Temporarially lock the player and mark approved to lock some commands."""
        self.approved = True
        self.approvelocked = True


    def drop_approvelock(self, caller):
        """Undo the approvelock without approving"""
        self.approved = False
        self.approvelocked = False


    def approve(self, caller):
        """Approve character with logging"""
        self.approved = True
        self.approvelocked = False

        msg = f"{caller.get_display_name(self)} approved {self.get_display_name(self)}."
        
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)


    def unapprove(self, caller):
        """Unapprove character with logging. Caller responsible for removing us from IC grid if needed."""
        self.approved = False

        msg = f"{caller.get_display_name(self)} unapproved {self.get_display_name(self)}."
        
        self.logaudit(msg)
        if caller != self:
            self.msg(msg)


    @property 
    def ic_idle_time(self):
        """How long since this character said something in character."""
        return time.time() - self.last_ic_talk_time if self.last_ic_talk_time else 0


    @property
    def is_ic(self):
        """Are we in (an) IC mode?"""
        return self.player_mode in ("IC", "DOWN") # all other modes are OOC modes
    
    @property
    def is_movelocked(self):
        """Are we currently under the movelock timer?"""
        # return time.time() < self.move_lock_end_time
        return False


    def at_object_creation(self):
        """
        Setup default channels and messaging permissions that now live on characters instead of
        accounts.
        """
        super().at_object_creation() 
        
        self.logaudit(f"{self.name} created.")

        home = get_specialroom(settings.TAG_START_LOCATION)
        home = home if home else get_defaulthome()

        # Have to do this some obscure-ass way because of how the function that calls us works.

        if hasattr(self, '_createdict'):
            self._createdict['home'] = home
        else:
            self._createdict = {'home': home}

        # For the character-focused channel system
        self.locks.add("msg:all()")

        # Transplanted from default account.

        channel = ChannelDB.objects.get_channel("ConnectInfo")
        if not channel or not (channel.access(self, "listen") and channel.connect(self)):
            logger.log_err("New character '{self.key}' could not connect to ConnectInfo")
            
        for chankey in settings.STARTING_CHANNELS:
            channel = ChannelDB.objects.get_channel(chankey)
            if not channel or not (channel.access(self, "listen") and channel.connect(self)):
                logger.log_err(f"New character '{self.key}' could not connect to default channel '{chankey}'!")


    

    def at_pre_move(self, dest, move_type=None, **kwargs):

        if not self.accepted_rules and not self.permissions.check("Builder"):
            self.msg("|mYou can't be moved until you |baccept|n.")
            return False

        if self.approvelocked:
            self.msg(f"{self.get_display_name(self)} |mis being examined by staff, please wait.|n")
            return False

        if not dest.is_typeclass("typeclasses.rooms.Room"):
            self.msg("Can't enter an object that is not a room (for now).")
            return False

        return super().at_pre_move(dest, move_type, **kwargs)

        # if move_type == "traverse":
        #     if self.is_movelocked:
        #         self.msg(f"|MCan't move for another {self.move_lock_end_time - time.time():.0f} seconds|n")
        #         return False
        #     else:
        #         return super().at_pre_move(dest, move_type, **kwargs)
        # else:
        #     return super().at_pre_move(dest, move_type, **kwargs)


    def at_post_move(self, src, **kwargs):

        # # If we move anyway, cancel movelock
        # self.move_lock_end_time = 0

        # if self.location.is_ic_room and self.location.ic_idle_time_loc < 2 * _RP_TRAP_IDLE_TIME:
        #     active_players_in_room = [
        #         char for char in PlayerCharacter.objects.filter(Q(db_location=self.location) & ~ Q(db_key=self)) 
        #         if char.is_ic and char.ic_idle_time < _RP_TRAP_IDLE_TIME
        #     ]
        #     if active_players_in_room:
        #         self.move_lock_end_time = time.time() + _RP_TRAP_MOVE_DELAY
        #         self.register_post_command_message(
        #             f"|MIC activity detected|n, locking movement for {_RP_TRAP_MOVE_DELAY} seconds."
        #         )
        super().at_post_move(src, **kwargs)


    def recheck_movelock(self):
        pass
        # # Does not presently work, not sure why. Removing this system for now.
        # if not self.is_movelocked:
        #     return
        # if self.location.is_ic_room and self.location.ic_idle_time_loc < 2 * _RP_TRAP_IDLE_TIME:
        #     active_players_in_room = [
        #         char for char in PlayerCharacter.objects.filter(Q(db_location=self.location) & ~ Q(db_key=self)) 
        #         if char.is_ic and char.ic_idle_time < _RP_TRAP_IDLE_TIME
        #     ]
        #     if not active_players_in_room:
        #         # Everyone moved out, so
        #         self.register_post_command_message(
        #             f"|MRoom empty, ending lock.|n"
        #         )
        #         self.move_lock_end_time = 0


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

    def at_look(self, target, **kwargs):
        """
        Called when this object performs a look. It allows to
        customize just what this means. It will not itself
        send any data. -- Actually it will, we need to send the person looked at you here.

        Args:
            target (DefaultObject): The target being looked at. This is
                commonly an object or the current location. It will
                be checked for the "view" type access.
            **kwargs: Arbitrary, optional arguments for users
                overriding the call. This will be passed into
                return_appearance, get_display_name and at_desc but is not used
                by default.

        Returns:
            str: A ready-processed look string potentially ready to return to the looker.

        """
        if not target.access(self, "view"):
            try:
                return _("Could not view '{target_name}'.").format(
                    target_name=target.get_display_name(self, **kwargs)
                )
            except AttributeError:
                return _("Could not view '{target_name}'.").format(target_name=target.key)

        description = target.return_appearance(self, **kwargs)
        
        if target.is_typeclass(PlayerCharacter):
            target.msg(f"{self.get_display_name(target)} just looked at {target.get_display_name(target)}.")

        # the target's at_desc() method.
        # this must be the last reference to target so it may delete itself when acted on.
        target.at_desc(looker=self, **kwargs)

        return description
