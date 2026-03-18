"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command can be part of any number of
cmdsets and cmdsets can be added/removed and merged onto entities at runtime.

To create new commands to populate the cmdset, see `commands/command.py`.

This module wraps the default command sets of Evennia; overloads them to add/remove commands from
the default lineup. You can create your own cmdsets by inheriting from them or directly from
`evennia.CmdSet`.

"""

from evennia import default_cmds

from . import admin_overrides
from . import batchprocess_overrides
from . import building_overrides
from . import comms_overrides
from . import general_overrides
from . import help_overrides
from . import system_overrides
from . import unloggedin_overrides
from . import mons
from . import chargen
from . import chargen_admin
from . import userlisting
from . import general
from . import building
from . import dice

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`, `get`, etc available on
    in-game Character objects. It is merged with the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.remove("whisper")
        self.remove("ban")
        self.remove("boot")
        self.remove("emit")
        self.remove("force")
        self.remove("perm")
        self.remove("unban")
        self.remove("wall")
        self.remove("@time")
        self.remove("@about")
        self.remove("sethelp")
        self.remove("batchcommands")
        self.remove("batchcode")
        self.remove("unlink")
        
        self.add(admin_overrides.CmdBan())
        self.add(admin_overrides.CmdBoot())
        self.add(admin_overrides.CmdEmit())
        self.add(admin_overrides.CmdForce())
        self.add(admin_overrides.CmdNewPassword())
        self.add(admin_overrides.CmdPerm())
        self.add(admin_overrides.CmdUnban())
        self.add(admin_overrides.CmdWall())
        self.add(batchprocess_overrides.CmdBatchCode())
        self.add(batchprocess_overrides.CmdBatchCommands())
        self.add(building_overrides.CmdDesc())
        self.add(building_overrides.CmdDestroy())
        self.add(building_overrides.CmdUnLink())
        self.add(building_overrides.CmdWipe())
        self.add(comms_overrides.CmdChannel())
        self.add(comms_overrides.CmdPage())
        self.add(comms_overrides.CmdDiscord2Chan())
        self.add(comms_overrides.CmdGrapevine2Chan())
        self.add(comms_overrides.CmdIRC2Chan())
        self.add(comms_overrides.CmdIRCStatus())
        self.add(comms_overrides.CmdRSS2Chan())
        self.add(general_overrides.CmdSay())
        self.add(general_overrides.CmdPose())
        self.add(general_overrides.CmdHome())
        self.add(general_overrides.CmdLook())
        self.add(general_overrides.CmdInventory())
        self.add(general_overrides.CmdGet())
        self.add(general_overrides.CmdDrop())
        self.add(general_overrides.CmdGive())
        self.add(help_overrides.CmdHelp())
        self.add(help_overrides.CmdSetHelp())
        self.add(system_overrides.CmdAbout())
        self.add(system_overrides.CmdTime())

        self.add(building.CmdZone())
        self.add(building.CmdSetSpecialRoom())
        self.add(chargen.CmdChargenSetInfo())
        self.add(chargen.CmdChargenSetSex())
        self.add(chargen_admin.CmdAdminSetSpecies())
        self.add(chargen_admin.CmdAdminSetNature())
        self.add(chargen_admin.CmdAdminBuyIVs())
        self.add(chargen_admin.CmdAuditLog())
        self.add(chargen_admin.CmdAdminResetIVs())
        self.add(chargen_admin.CmdAdminEquipMove())
        self.add(chargen_admin.CmdAdminUnequipMove())
        self.add(chargen_admin.CmdAdminLearnMove())
        self.add(chargen_admin.CmdAdminForgetMove())
        self.add(dice.CmdDice())
        self.add(general.CmdOOC())
        self.add(general.CmdSpoof())
        self.add(general.CmdStats())
        self.add(mons.CmdMonTypes()) 
        self.add(mons.CmdRandMons())
        self.add(mons.CmdMoveLookup())
        self.add(mons.CmdRandMoves())
        self.add(userlisting.CmdWho())
        self.add(userlisting.CmdStatus())
        self.add(userlisting.CmdStaffInfo())





class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.remove("@channel")
        self.remove("page")
        self.remove("ic")
        self.remove("ooc")
        self.remove("charcreate")
        self.remove("chardelete")
        self.remove("who")
        self.remove("userpassword")
        self.remove("irc2chan")
        self.remove("ircstatus")
        self.remove("rss2chan")
        self.remove("grapevine2chan")
        self.remove("discord2chan")



class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(unloggedin_overrides.CmdUnconnectedCreate())



class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
