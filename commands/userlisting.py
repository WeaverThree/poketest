
import time
import math
from collections import defaultdict

from django.conf import settings  # type: ignore

import evennia
from evennia.utils import utils, evtable, crop, display_len
from evennia.utils.ansi import ANSIString

from .command import Command, MuxCommand
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.utils import header_two_slot, is_staff_character
from world.monutils import get_display_mon_banner, get_inline_mon_banner_nodex

_WIDTH = settings.OUR_WIDTH


class CmdWho(MuxCommand):
    """
    list who is currently online

    Usage:
        who
        doing

    Shows who is currently online. Doing is an alias that limits info also for those with all
    permissions.
    """

    key = "who"
    aliases = "doing"
    locks = "cmd:all()"
    help_category = "People"

    def func(self):

        session_list = evennia.SESSION_HANDLER.get_sessions()
        session_list = sorted(session_list, key=lambda ses: ses.puppet.key if ses.puppet else "---"+ses.account.key)

        if self.cmdstring == "doing":
            show_session_data = False
        else:
            show_session_data = self.account.permissions.check("Admin")

        naccounts = evennia.SESSION_HANDLER.account_count()

        names = []
        durations = []
        idles = []
        icidles = []
        locations = []
        modes = []
        statuses = []
        cmds = []
        protocols = []
        hosts = []

        for session in session_list:
            if not session.logged_in:
                continue

            session_account = session.get_account()
            puppet = session.get_puppet()

            name = (
                session.get_puppet().get_display_name(self.caller) if session.get_puppet() 
                else f"|[R|X{session.account.name}|n"
            )
            
            names.append(utils.crop(name, width=25))
            durations.append(utils.time_format(time.time() - session.conn_time, 1))
            idles.append(utils.time_format(time.time() - session.cmd_last_visible, 0))
            icidles.append(utils.time_format(puppet.ic_idle_time, 0) if puppet.ic_idle_time else "Never")
            locations.append(puppet.location.key if puppet and puppet.location else "|[R|X---|n")
            modes.append(puppet.player_mode)
            statuses.append(utils.crop(puppet.whostatus,50,"…") if puppet else "")
            cmds.append(session.cmd_total)
            protocols.append(session.protocol_key)
            hosts.append(isinstance(session.address, tuple) and session.address[0] or session.address)


        if show_session_data:
            # privileged info
            header = (
                "|wName|n",
                "|wOn for|n",
                "|wIdle|n",
                "|wLastIC|n",
                "|wLocation|n",
                "|wMode|n",
                "|wStatus|n",
                "|wCmds|n",
                "|wProtocol|n",
                "|wHost|n",
            )

            table = evtable.EvTable(
                *header, table=(names,durations,idles,icidles, locations,modes,statuses,cmds,protocols,hosts),
                border_width=0,                              
            )

        else:
            header = (
                "|wName|n",
                "|wOn for|n",
                "|wIdle|n",
                "|wIcIdle|n",
                "|wLocation|n",
                "|wMode|n",
                "|wStatus|n",
            )

            table = evtable.EvTable(
                *header, table=(names,durations,idles, icidles, locations,modes,statuses),
                border_width=0,                                  
            )

        header = header_two_slot(_WIDTH, "|wWho's Online|n", headercolor="|M")

        self.msg(f"{header}\n{table}\n  {naccounts} online.\n")


class CmdWhat(MuxCommand):
    """
    list what everyone who is currently online is

    Usage:
        what
    """

    key = "what"
    locks = "cmd:perm(Admin)"
    help_category = "People"

    def func(self):

        session_list = evennia.SESSION_HANDLER.get_sessions()
        session_list = sorted(session_list, key=lambda ses: ses.puppet.key if ses.puppet else "---"+ses.account.key)

        naccounts = evennia.SESSION_HANDLER.account_count()

        names = []
        species = []
        shortdescs = []


        for session in session_list:
            if not session.logged_in:
                continue

            session_account = session.get_account()
            puppet = session.get_puppet()

            name = (
                puppet.get_display_name(self.caller) if puppet 
                else f"|[R|X{session.account.name}|n"
            )
            
            names.append(crop(name, 25,"…"))
            
            species.append(get_display_mon_banner(puppet))

            shortdescs.append(crop(puppet.short_desc if puppet else "", 100,'…'))

            header = (
                "|wName|n",
                "|wSpecies|n",
                "|wShort Description|n",
            )

        table = evtable.EvTable(
            *header, table=(names,species,shortdescs),
            border_width=0,                              
        )
        table.reformat_column(1,align='c')
        table.reformat_column(2,align="a")

        header = header_two_slot(_WIDTH, "|wWhat's Online|n", headercolor="|M")

        self.msg(f"{header}\n{table}\n  {naccounts} online.\n")


class CmdGlance(MuxCommand):
    """
    A more detailed list of who's in the current area.

    Usage:
        glance
    """

    key = "glance"
    locks = "cmd:all()"
    help_category = "People"

    def func(self):

        caller = self.caller

        # data = []
        # shortdescs = []
        # header = (
        #     "|wData|n",
        #     "|wShort Description|n",
        # )
        # table = evtable.EvTable(
        #     *header, table=(data, shortdescs),
        #     border_width=0, width=140,                              
        # )

        # maxline = 0

        # for character in sorted(caller.location.contents_get(content_type="character"), key = lambda x: x.name.lower()):
            
        #     line1 = f"{character.faction} {character.rank} {character.get_display_name(caller)}"
        #     line2 = f"{get_display_mon_banner(character)}"

        #     data = evtable.EvCell(f"{line1}\n{line2}\n")

        #     maxline = max(maxline, display_len(line1), display_len(line2))
            
        #     table.add_row(data, character.short_desc)

        # table.reformat_column(0, align='a', valign='t', width=45)
        # table.reformat_column(1, valign='t')
        
        # headercenter = "< In This Room >"
        # headerleft = ">-"
        # headerright = "--"
        # fill = _WIDTH - display_len(headercenter) - display_len(headerleft) - display_len(headerright)
        # fill1 = math.ceil(fill/2.0)
        # fill2 = math.floor(fill/2.0)
        # header = f"{headerleft}{'-' * fill1}{headercenter} ----

        out = [header_two_slot(
            _WIDTH, f"|wGlancing Around {caller.location.get_display_name(caller)}|n", headercolor="|M"
        )]

        for character in sorted(caller.location.contents_get(content_type="character"), key = lambda x: x.name.lower()):
            out.append(
                f"    {character.get_display_name(caller)}: "
                f"{get_inline_mon_banner_nodex(character, capstart=True)} "
                f"{character.faction} {character.rank} - "
                f"{character.short_desc}"
            )
        
        out.append('')

        self.msg('\n'.join(out))


class CmdRoster(MuxCommand):
    """
    How many of each mon type have been created in the game world.
    Excludes staff creatures.

    Switches:
        /bycount - Sort by count, then by dexno.
        /onecol - For narrow terminals
    
    Usage:
        +roster
        +roster/bycount
    """

    key = "+roster"
    locks = "cmd:all()"
    help_category = "People"

    def func(self):

        mondata = evennia.GLOBAL_SCRIPTS.mondata

        mons = defaultdict(int)

        for character in PlayerCharacter.objects.all_family():
            mon = {}
            if not character.species:
                continue
            if is_staff_character(character):
                continue
            
            key = (character.dexno, character.subtype, character.form)

            mons[key] += 1

        out = []

        if 'bycount' in self.switches:
            order = sorted(mons, key=lambda m:(mons[m],m))
        else:
            order = sorted(mons)

        for key in order:
            count = mons[key]
            dexno, subtype, form = key
            subtype = subtype if subtype else '-'
            form = form if form else '-'
            
            mon = mondata.search_mons(dexno, subtype, form)

            if len(mon) != 1:
                self.msg(f"Error looking up {dexno}, {subtype}, {form}.")

            mon = mon[0]

            count = "#" * count if count < 5 else count

            out.append(f" {count:>5} {get_display_mon_banner(mon)}")
        
        if not 'onecol' in self.switches:
            half = math.ceil(len(out) / 2.0)
            table = evtable.EvTable(table=(out[:half],out[half:]), border_width=0)
            table.reformat_column(0, align='a')
            table.reformat_column(1, align='a')
        else:
            table = evtable.EvTable(table=(out,), border_width=0)
            table.reformat_column(0, align='a')

        header = header_two_slot(_WIDTH, "|wServer Type Roster|n", headercolor="|M")
        
        self.caller.msg(f"{header}\n{table}\n")
            


def _getpuppet(account):
    sessions = account.sessions.get()
    puppet = account.get_puppet(sessions[0]) if sessions else None
    if not puppet:
        puppet = account.db._last_puppet # Fragile but should work with our config.
    
    return puppet


class CmdStaff(Command):
    """
    List MU staff

    Usage:
      staff
    """

    key = "staff"
    aliases = ['stafflist']
    locks = "cmd:all()"
    help_category = "People"

    def func(self):
    
        # Get all staff with a valid character, sorted by puppet name

        staff = [
            (_getpuppet(account), account) for account in Account.objects.all() 
            if account.permissions.check("Builder")
        ]
        
        staff = sorted([pair for pair in staff if pair[0]], key=lambda x: x[0].name)
        
        names = []
        durations = []
        idles = []
        titles = []
        stafftags = []

        for character, account in staff:
            if account.is_superuser:
                continue

            names.append(utils.crop(character.get_display_name(self.caller), width=25))

            is_online = True if account.sessions.get() else False
            
            duration = utils.time_format(account.connection_time, 0) if is_online else "Offline"
            durations.append(duration)

            idle = utils.time_format(account.idle_time,1) if is_online else "--"
            idles.append(idle)

            if account.permissions.check("Developer"):
                titles.append("|mDev|n")
            elif account.permissions.check("Admin"):
                titles.append("|cAdmin|n")
            elif account.permissions.check("Builder"):
                titles.append("|yBuilder|n")
            else:
                titles.append("|[M|X???|n")

            stafftags.append(utils.crop(character.stafftag, 50, "…"))
            
        header = (
            "|wName",
            "|wOn for",
            "|wIdle",
            "|wTitle",
            "|wInfo",
        )

        table = evtable.EvTable(
            *header, table=(names,durations,idles,titles,stafftags),
            border_width=0,                              
        )
        title = header_two_slot(_WIDTH, f"|w{settings.SERVERNAME} Staff|n", headercolor="|M")
        self.caller.msg(f"{title}\n{table}\n")


class CmdStatus(Command):
    """
    Set your status message 

    Usage:
        status <my status message>
    """

    key = "status"
    aliases = ['setstatus']
    locks = "cmd:all()"
    help_category = "People"

    def func(self):

        status = self.args.strip()
        status = status.split("\n")[0]
        status = status.split("|/")[0]

        if not status:
            self.msg(f"Current status is: {self.caller.whostatus if self.caller.whostatus else '<NOT SET>'}")
            return

        self.caller.whostatus = status
        self.caller.msg(f"Status set to '{status}'")


class CmdStaffInfo(Command):
    """
    Set your staff info 

    Usage:
        staffinfo <my staff info>
    """

    key = "staffinfo"
    aliases = []
    locks = "cmd:perm(Builder)"
    help_category = "People"

    def func(self):

        status = self.args.strip()
        status = status.split("\n")[0]
        status = status.split("|/")[0]

        if not status:
            self.msg(f"Current staff tag is: {self.caller.stafftag if self.caller.stafftag else '<NOT SET>'}")
            return

        self.caller.stafftag = status
        self.msg(f"Staff Info set to '{status}'")


class CmdTalkers(Command):
    """
    Show recent (ic) talkers in the current location

    Usage:
        +talkers
    """
    key = "+talkers"
    locks = "cmd:all()"
    help_category = "People"
    
    def func(self):
        
        # Dang we don't even care about args

        if not self.caller.location:
            self.msg(f"{self.caller.get_display_name()} |mdoesn't have a location!|n")

        self.msg(self.caller.location.get_display_talker_list(self.caller))