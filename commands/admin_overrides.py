from .command import MuxCommand
from typeclasses.characters import PlayerCharacter

class CmdForce(MuxCommand):
    """
    forces an object to execute a command

    Usage:
        force <object>=<command string>

    Example:
        force bob=get stick
    """

    key = "force"
    locks = "cmd:perm(spawn) or perm(Builder)"
    help_category = "Building"
    perm_used = "edit"

    def func(self):
        """Implements the force command"""
        if not self.lhs or not self.rhs:
            self.msg("You must provide a target and a command string to execute.")
            return
        targ = self.caller.search(self.lhs)
        if not targ:
            return
        if isinstance(targ, PlayerCharacter):
            self.msg("Forcing player characters to execute commands is disabled as it's rude.")
            return
        if not targ.access(self.caller, self.perm_used):
            self.msg(f"You don't have permission to force {targ} to execute commands.")
            return
        targ.execute_cmd(self.rhs)
        self.msg(f"You have forced {targ} to: {self.rhs}")
