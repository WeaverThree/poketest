

import datetime
import re
from codecs import lookup as codecs_lookup

from django.conf import settings

import evennia
from evennia.comms.models import ChannelDB
from evennia.utils import class_from_module, create, gametime, logger, utils

from .command import MuxCommand

class CmdUnconnectedCreate(MuxCommand):
    """
    create a new account account

    Usage (at login screen):
      create <accountname> <password> [registration passtoken]

    This creates a new account and attached character of the same name.
    """

    key = "create"
    aliases = ["cre", "cr"]
    locks = "cmd:all()"
    arg_regex = r"\s.*?|$"

    def at_pre_cmd(self):
        """Verify that account creation is enabled."""
        if not settings.NEW_ACCOUNT_REGISTRATION_ENABLED and not settings.REGISTRATION_PASSTOKEN:
            # truthy return cancels the command
            self.msg("Registration is currently disabled.")
            return True

        return super().at_pre_cmd()

    def func(self):
        """Do checks and create account"""

        session = self.caller
        args = self.args.strip()

        address = session.address

        # Get account class
        Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        # We're just not allowing spaces in passwords either.
        parts = [arg.strip() for arg in args.split()]

        if not settings.NEW_ACCOUNT_REGISTRATION_ENABLED:
            if len(parts) != 3:
                session.msg(
                    "\nOpen account registration is disabled.\n"
                    "You must provide the correct registration token to make an account.\n"
                    "Usage: create <name> <password> <registration-token>"
                )
                return
            
            username, password, regtoken = parts

            if regtoken != settings.REGISTRATION_PASSTOKEN:
                session.msg(
                    "\nOpen account registration is disabled.\n"
                    "|rIncorrect registartion token.|n\n"
                    "Usage: create <name> <password> <registration-token>"
                )
                return
            
        else:
            if 2 > len(parts) > 3:
                session.msg("\n Usage (without <>): create <name> <password>")
                return
            username, password, _ = parts

        if username[0].islower():
            session.msg(
                "Please start your name with a capital letter. " 
                "This is going to be your character name, afterall."
            )
            return

        # pre-normalize username so the user know what they get
        non_normalized_username = username
        username = Account.normalize_username(username)
        if non_normalized_username != username:
            session.msg(
                "Note: your username was normalized to strip spaces and remove characters "
                "that could be visually confusing."
            )

        # have the user verify their new account was what they intended
        answer = yield (
            f"You want to create an account '{username}' with password '{'*' * len(password)}'."
            "\nIs this what you intended? [Y]/N?"
        )
        if answer.lower() in ("n", "no"):
            session.msg("|xAborted.|n")
            return

        # everything's ok. Create the new player account.
        account, errors = Account.create(
            username=username, password=password, ip=address, session=session
        )
        if account:
            # tell the caller everything went well.
            string = "A new account '%s' was created. Welcome!"
            string += "\n\nYou can now log with the command 'connect %s <your password>'."
            session.msg(string % (username, username))
        else:
            session.msg("|R%s|n" % "\n".join(errors))