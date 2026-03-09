import datetime
import os
import sys

import django # type: ignore
import twisted # type: ignore
from django.conf import settings # type: ignore

import evennia
from evennia.utils import gametime, logger, search, utils

from .command import MuxCommand

class CmdTime(MuxCommand):
    """
    show server time statistics

    Usage:
      time

    List Server time statistics such as uptime
    and the current time stamp.
    """

    key = "time"
    aliases = "uptime"
    locks = "cmd:perm(time) or perm(Player)"
    help_category = "System"

    def func(self):
        """Show server time data in a table."""
        table1 = self.styled_table("|wServer time", "", align="l", width=78)
        table1.add_row("Current uptime", utils.time_format(gametime.uptime(), 3))
        table1.add_row("Portal uptime", utils.time_format(gametime.portal_uptime(), 3))
        table1.add_row("Total runtime", utils.time_format(gametime.runtime(), 2))
        table1.add_row("First start", datetime.datetime.fromtimestamp(gametime.server_epoch()))
        table1.add_row("Current time", datetime.datetime.now())
        table1.reformat_column(0, width=30)
        table2 = self.styled_table(
            "|wIn-Game time",
            "|wReal time x %g" % gametime.TIMEFACTOR,
            align="l",
            width=78,
            border_top=0,
        )
        epochtxt = "Epoch (%s)" % ("from settings" if settings.TIME_GAME_EPOCH else "server start")
        table2.add_row(epochtxt, datetime.datetime.fromtimestamp(gametime.game_epoch()))
        table2.add_row("Total time passed:", utils.time_format(gametime.gametime(), 2))
        table2.add_row(
            "Current time ", datetime.datetime.fromtimestamp(gametime.gametime(absolute=True))
        )
        table2.reformat_column(0, width=30)
        self.msg(str(table1) + "\n" + str(table2))

class CmdAbout(MuxCommand):
    """
    show Evennia info

    Usage:
      about

    Display info about the game engine.
    """

    key = "about"
    aliases = "version"
    locks = "cmd:all()"
    help_category = "System"

    def func(self):
        """Display information about server or target"""

        string = """
         |cEvennia|n MU* development system

         |wEvennia version|n: {version}
         |wOS|n: {os}
         |wPython|n: {python}
         |wTwisted|n: {twisted}
         |wDjango|n: {django}

         |wHomepage|n https://evennia.com
         |wCode|n https://github.com/evennia/evennia
         |wGame listing|n http://games.evennia.com
         |wChat|n https://discord.gg/AJJpcRUhtF
         |wForum|n https://github.com/evennia/evennia/discussions
         |wLicence|n https://opensource.org/licenses/BSD-3-Clause
         |wMaintainer|n (2010-)   Griatch (griatch AT gmail DOT com)
         |wMaintainer|n (2006-10) Greg Taylor

        """.format(
            version=utils.get_evennia_version(),
            os=os.name,
            python=sys.version.split()[0],
            twisted=twisted.version.short(),
            django=django.get_version(),
        )
        self.msg(string)

