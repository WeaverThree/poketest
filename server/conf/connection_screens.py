# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

from django.conf import settings # type: ignore

from evennia import utils

CONNECTION_SCREEN = f"""
|R--------------------------------------------------------------|n
 Welcome to |g{settings.SERVERNAME}|n. |rThis is an 18+ server|n.

 If you have an existing account, connect to it by typing:
      |wconnect <username> <password>|n
 If you need to create an account, type (without the <>'s):
      |wcreate <username> <password> [registration passtoken]|n

 Your account name is also your character name.
 One character per account. Multiple accounts per player.

 No spaces allowed in username or in password.
 Enter |whelp|n for more info. |wlook|n will re-show this screen.
|R--------------------------------------------------------------|n"""