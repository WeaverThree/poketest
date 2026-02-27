"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""

import time

from django.db.models import Q 

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent

MOVE_DELAY = 20

class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    def at_pre_move(self, dest, move_type=None, **kwargs):
        if move_type == "traverse":
            now = time.time()
            if self.ndb.movelock and self.ndb.movelock > now:
                self.msg("Can't move for another {:.0f} seconds".format(self.ndb.movelock - now))
                return False
            else:
                return super().at_pre_move(dest, move_type, **kwargs)
        else:
            return super().at_pre_move(dest, move_type, **kwargs)

    def at_post_move(self, src, **kwargs):
        active_players_in_room = [char 
                for char in Character.objects.filter(Q(db_location=self.location) & ~ Q(db_key=self)) 
                if char.idle_time < 5]
        if active_players_in_room:
            self.ndb.movelock = time.time() + MOVE_DELAY
            self.msg("|MPlayer activity detected|n, locking movement for {} seconds.".format(MOVE_DELAY))
        else:
            self.ndb.movelock = None;
        super().at_post_move(src, **kwargs)
