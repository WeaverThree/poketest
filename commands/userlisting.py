
import time

from django.conf import settings  # type: ignore

import evennia
from evennia.utils import utils, evtable, crop
from evennia.utils.ansi import ANSIString

from .command import Command, MuxCommand
from typeclasses.accounts import Account
from world.monutils import get_display_mon_name, get_display_mon_type, get_display_mon_banner

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
        """
        Get all connected accounts by polling session.
        """
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

        self.msg(f"{table}\n  {naccounts} online.\n")



_colorsex = {
    "A": "|gA|n",
    "F": "|rF|n",
    "M": "|bM|n",
    "N": "|yN|n",
    "": "|[r|X?|n",
}


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
        """
        Get all connected accounts by polling session.
        """
        session_list = evennia.SESSION_HANDLER.get_sessions()
        session_list = sorted(session_list, key=lambda ses: ses.puppet.key if ses.puppet else "---"+ses.account.key)

        naccounts = evennia.SESSION_HANDLER.account_count()

        names = []
        sexes = []
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
            
            sexes.append(_colorsex[puppet.sex[0] if puppet and puppet.sex else ''])

            species.append(get_display_mon_banner(puppet))

            shortdescs.append(crop(puppet.short_desc if puppet else "", 100,'…'))

            header = (
                "|wName|n",
                "|wSex|n",
                "|wSpecies|n",
                "|wShort Description|n",
            )

        table = evtable.EvTable(
            *header, table=(names,sexes,species,shortdescs),
            border_width=0,                              
        )
        table.reformat_column(1,align='c')
        table.reformat_column(2,align="a")

        self.msg(f"{table}\n  {naccounts} online.\n")


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
        """
        Get all connected accounts by polling session.
        """

        caller = self.caller

        names = []
        sexes = []
        species = []
        shortdescs = []
        
        affiliations = []
        ranks = []


        for character in sorted(caller.location.contents_get(content_type="character"), key = lambda x: x.name.lower()):
            
            names.append(character.get_display_name(caller))
            
            sexes.append(_colorsex[character.sex[0] if character.sex else ''])

            species.append(get_display_mon_banner(character))

            shortdescs.append(character.short_desc)

            affiliations.append(character.faction)
            ranks.append(character.rank)

            header = (
                "|wName|n",
                "|wSex|n",
                "|wSpecies|n",
                "|wAffiliation|n",
                "|wRank|n",
            )

        table = evtable.EvTable(
            *header, table=(names,sexes,species, affiliations, ranks),
            border_width=0,                              
        )
        table.reformat_column(1,align='c')
        table.reformat_column(2,align="a")
        
        lines = table.get()

        out = [str(str(ANSIString(lines[0])))]
        
        for tableline, sdesc in zip(lines[1:], shortdescs):
            out.append(str(str(ANSIString(tableline))))
            out.append(f"    {sdesc}")
        
        out.append('')

        self.msg('\n'.join(out))






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
        title = f' - - - {settings.SERVERNAME} Staff List - - - '
        self.caller.msg(f"\n|w{title:^{_WIDTH}}|n\n{table}")


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