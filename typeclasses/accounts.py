"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""



from evennia.accounts.accounts import DefaultAccount, DefaultGuest

from django.conf import settings
from django.utils.translation import gettext as _

from evennia import AttributeProperty
from evennia.comms.models import ChannelDB
from evennia.server.signals import (
    SIGNAL_ACCOUNT_POST_CREATE,
)
from evennia.server.throttle import Throttle
from evennia.utils import create, logger
from evennia.utils.utils import (
    variable_from_module,
)

__all__ = ("DefaultAccount", "DefaultGuest")

_AUTO_CREATE_CHARACTER_WITH_ACCOUNT = settings.AUTO_CREATE_CHARACTER_WITH_ACCOUNT

# Create throttles for too many account-creations and login attempts
CREATION_THROTTLE = Throttle(
    name="creation",
    limit=settings.CREATION_THROTTLE_LIMIT,
    timeout=settings.CREATION_THROTTLE_TIMEOUT,
)
LOGIN_THROTTLE = Throttle(
    name="login", limit=settings.LOGIN_THROTTLE_LIMIT, timeout=settings.LOGIN_THROTTLE_TIMEOUT
)




class Account(DefaultAccount):
    """
    An Account is the actual OOC player entity. It doesn't exist in the game,
    but puppets characters.

    This is the base Typeclass for all Accounts. Accounts represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. An Account
    can connect to a Character Object in order to "enter" the
    game.
    """
    
    bitching_betty_messages = AttributeProperty([])

    @classmethod
    def create(cls, *args, **kwargs):
        """
        Creates an Account (or Account/Character pair for MULTISESSION_MODE<2)
        with default (or overridden) permissions and having joined them to the
        appropriate default channels.

        Overriding this to remove channel creation --Weaver

        Keyword Args:
            username (str): Username of Account owner
            password (str): Password of Account owner
            email (str, optional): Email address of Account owner
            ip (str, optional): IP address of requesting connection
            guest (bool, optional): Whether or not this is to be a Guest account

            permissions (str, optional): Default permissions for the Account
            typeclass (str, optional): Typeclass to use for new Account
            character_typeclass (str, optional): Typeclass to use for new char
                when applicable.

        Returns:
            account (Account): Account if successfully created; None if not
            errors (list): List of error messages in string form

        """

        account = None
        errors = []

        username = kwargs.get("username", "")
        password = kwargs.get("password", "")
        email = kwargs.get("email", "").strip()
        guest = kwargs.get("guest", False)

        permissions = kwargs.get("permissions", settings.PERMISSION_ACCOUNT_DEFAULT)
        typeclass = kwargs.get("typeclass", cls)

        ip = kwargs.get("ip", "")
        if isinstance(ip, (tuple, list)):
            ip = ip[0]

        if ip and CREATION_THROTTLE.check(ip):
            errors.append(
                _("You are creating too many accounts. Please log into an existing account.")
            )
            return None, errors

        # Normalize username
        username = cls.normalize_username(username)

        # Validate username
        if not guest:
            valid, errs = cls.validate_username(username)
            if not valid:
                # this echoes the restrictions made by django's auth
                # module (except not allowing spaces, for convenience of
                # logging in).
                errors.extend(errs)
                return None, errors

        # Validate password
        # Have to create a dummy Account object to check username similarity
        valid, errs = cls.validate_password(password, account=cls(username=username))
        if not valid:
            errors.extend(errs)
            return None, errors

        # Check IP and/or name bans
        banned = cls.is_banned(username=username, ip=ip)
        if banned:
            # this is a banned IP or name!
            string = _(
                "|rYou have been banned and cannot continue from here."
                "\nIf you feel this ban is in error, please email an admin.|x"
            )
            errors.append(string)
            return None, errors

        # everything's ok. Create the new account.
        try:
            try:
                account = create.create_account(
                    username, email, password, permissions=permissions, typeclass=typeclass
                )
                logger.log_sec(f"Account Created: {account} (IP: {ip}).")

            except Exception:
                errors.append(
                    _(
                        "There was an error creating the Account. "
                        "If this problem persists, contact an admin."
                    )
                )
                logger.log_trace()
                return None, errors

            # This needs to be set so the engine knows this account is
            # logging in for the first time. (so it knows to call the right
            # hooks during login later)
            account.db.FIRST_LOGIN = True

            # Record IP address of creation, if available
            if ip:
                account.db.creator_ip = ip

            # join the new account to the public channels
            # for chan_info in settings.DEFAULT_CHANNELS:
            #     if chankey := chan_info.get("key"):
            #         channel = ChannelDB.objects.get_channel(chankey)
            #         if not channel or not (
            #             channel.access(account, "listen") and channel.connect(account)
            #         ):
            #             string = (
            #                 f"New account '{account.key}' could not connect to default channel"
            #                 f" '{chankey}'!"
            #             )
            #             logger.log_err(string)
            #     else:
            #         logger.log_err(f"Default channel '{chan_info}' is missing a 'key' field!")

            if account and _AUTO_CREATE_CHARACTER_WITH_ACCOUNT:
                # Auto-create a character to go with this account

                character, errs = account.create_character(
                    typeclass=kwargs.get("character_typeclass", account.default_character_typeclass)
                )
                if errs:
                    errors.extend(errs)

        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't,
            # we won't see any errors at all.
            errors.append(_("An error occurred. Please e-mail an admin if the problem persists."))
            logger.log_trace()

        # Update the throttle to indicate a new account was created from this IP
        if ip and not guest:
            CREATION_THROTTLE.update(ip, "Too many accounts being created.")
        SIGNAL_ACCOUNT_POST_CREATE.send(sender=account, ip=ip)
        return account, errors


    def register_post_command_message(self, message):
        """Register message to be sent at the end of the current command."""
        self.bitching_betty_messages.append(message)


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass
