from evennia.commands.default.account import CmdIC, CmdOOC

class CmdPlusIC(CmdIC):
    """
    control an object you have permission to puppet

    Usage:
      +ic <character>

    Go in-character (IC) as a given Character.

    This will attempt to "become" a different object assuming you have
    the right to do so. Note that it's the ACCOUNT character that puppets
    characters/objects and which needs to have the correct permission!

    You cannot become an object that is already controlled by another
    account. In principle <character> can be any in-game object as long
    as you the account have access right to puppet it.
    """

    key = "+ic"


class CmdPlusOOC(CmdOOC):
    """
    stop puppeting and go ooc

    Usage:
      +ooc

    Go out-of-character (OOC).

    This will leave your current character and put you in a incorporeal OOC state.
    """

    key = "+ooc"
