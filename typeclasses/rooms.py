"""
Room

Rooms are simple containers that has no location of their own.

"""

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent
from .characters import PlayerCharacter

class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    DESC_LENGTH_REQ = 500

    def at_pre_object_receive(self, arriving_object, source_location, **kwargs):

        if arriving_object.is_typeclass(PlayerCharacter):
            if not arriving_object.approved and not arriving_object.account.permissions.check('Builder'):
                zone = self.tags.get(category="Zone", return_list=True)
                if zone and zone[0] != 'ooc':
                    arriving_object.msg(
                        "You're not approved for IC access yet. "
                        "Please complete chargen and then ask staff for assistance."
                    )
                    return False
        
        return True

    
    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):

        if moved_obj.is_typeclass(PlayerCharacter):
            if moved_obj.player_mode not in ("DOWN", "JAIL"):
                zone = self.tags.get(category="Zone", return_list=True)
                if zone and zone[0] != 'ooc' and not moved_obj.account.permissions.check('Builder'):
                    moved_obj.player_mode = "IC"
                else:
                    moved_obj.player_mode = "OOC"
            