
import time

from django.conf import settings  # type: ignore

import evennia
from evennia.utils import utils, evtable
from typeclasses.accounts import Account


from .command import Command, MuxCommand

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
        locations = []
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
            locations.append(puppet.location.key if puppet and puppet.location else "|[R|X---|n")
            statuses.append(utils.crop(puppet.whostatus,50,"…") if puppet else "")
            cmds.append(session.cmd_total)
            protocols.append(session.protocol_key)
            hosts.append(isinstance(session.address, tuple) and session.address[0] or session.address)


        if show_session_data:
            # privileged info
            header = (
                "|wName",
                "|wOn for",
                "|wIdle",
                "|wLocation",
                "|wStatus",
                "|wCmds",
                "|wProtocol",
                "|wHost",
            )

            table = evtable.EvTable(
                *header, table=(names,durations,idles,locations,statuses,cmds,protocols,hosts),
                border_width=0,                              
            )

        else:
            header = (
                "|wName",
                "|wOn for",
                "|wIdle",
                "|wLocation",
                "|wStatus",
            )

            table = evtable.EvTable(
                *header, table=(names,durations,idles,locations,statuses),
                border_width=0,                                  
            )

        is_one = naccounts == 1
        self.msg(f"\n{table}\n  {"One" if is_one else naccounts} unique account{"" if is_one else "s"} logged in.")


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
        self.caller.msg(f"\n|w{title:^80}|n\n{table}")


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

        self.caller.stafftag = status
        self.caller.msg(f"Staff Info set to '{status}'")
