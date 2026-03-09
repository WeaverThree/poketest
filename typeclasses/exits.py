"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.
    """

    def get_display_name(self, looker, **kwargs):
        """
        Returns a fancy name based on who's looking at this object. In particular, will grey out and
        cross out destinations that the user does not meet lock on. This doesn't guarentee they're
        allowed to go that way, of course, but it should usually be the way we block access I think.
        """
        name = self.name
        aliases = self.aliases.all()
        if aliases:
            best_alias = min(aliases, key=len)
            if len(best_alias) < len(name):
                name = f"|g[{best_alias.upper()}]|n {name}"
        return name
            
