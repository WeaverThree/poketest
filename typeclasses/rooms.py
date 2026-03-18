"""
Room

Rooms are simple containers that has no location of their own.

"""

from django.conf import settings
import evennia
from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent
from .characters import PlayerCharacter

from commands import (
    chargen, 
    admin_overrides, 
    general, 
    general_overrides, 
    comms_overrides, 
    system_overrides,
    building_overrides,
    userlisting,
    help_overrides,
    building,
)

from evennia.commands.default import building as default_building

class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    DESC_LENGTH_REQ = settings.DESIRED_MIN_DESC

    @property
    def is_ic_room(self):
        return not 'ooc' in self.tags.get(category="Zone", return_list=True)
    

    def at_pre_object_receive(self, arriving_object, source_location, **kwargs):

        if arriving_object.is_typeclass(PlayerCharacter):
            if not arriving_object.approved and not arriving_object.account.permissions.check('Builder'):
                zone = self.tags.get(category="Zone", return_list=True)
                if zone and zone[0] != 'ooc':
                    arriving_object.msg(
                        "|mYou're not approved for IC access yet. |n"
                        "Please complete chargen and then ask staff for assistance."
                    )
                    return False
        
        return True

    
    def at_object_receive(self, moved_obj, source_location, move_type="move", **kwargs):

        if moved_obj.is_typeclass(PlayerCharacter):
            if moved_obj.player_mode not in ("DOWN", "JAIL", "AUP"):
                zone = self.tags.get(category="Zone", return_list=True)
                if zone and zone[0] != 'ooc' and not moved_obj.account.permissions.check('Builder'):
                    if moved_obj.player_mode != "IC":
                        moved_obj.msg("|mMoving to IC grid, enetring IC mode.|n")
                        moved_obj.player_mode = "IC"
                else:
                    if moved_obj.player_mode != "OOC":
                        moved_obj.msg("|mLeaving IC grid, enetring OOC mode.|n")
                        moved_obj.player_mode = "OOC"

    # def at_object_leave(self, moved_obj, target_location, move_type="move", **kwargs):

    #     if moved_obj.is_typeclass(PlayerCharacter):
    #         moved_obj.recheck_movelock()

    #     return super().at_object_leave(moved_obj, target_location, move_type, **kwargs)


class SuperDarkRoom(Room):
    """
    This is a room in which you can't see anything, hear anything, receive any messages from inside
    the room, etc. It's goign to be used for the chargen room and the AUP room. It should be just
    like you're in a room by yourself when you're in here.
    """

    @property
    def can_talk(self):
        return False

    def get_room_inventory(self, looker, kwargs):
        """Only admin can see what's in here"""
        if looker.permissions.check("Builder"):
            table = super().get_room_inventory(looker, kwargs)
            return f"|[y|X Notice |n|y Only BUILDER+ can see the contents of this room:|n\n{table}"
        else:
            return ""
        
    def at_pre_object_receive(self, arriving_object, source_location, move_type="", **kwargs):
        """Can't drop anything in a super dark room."""
        if move_type == "drop":
            return False
        return super().at_pre_object_receive(arriving_object, source_location, move_type=move_type, **kwargs)
    
    def msg_contents(
            self, text=None, exclude=None, from_obj=None, mapping=None,
            raise_funcparse_errors=False, **kwargs
            ):
        """Nothing gets emitted here..."""
        return


class AUPRoomCmdSet(evennia.CmdSet):
    """The 'accept' command for policy and also a few minimal others and a few admin commands"""
    mergetype = "Replace"
    priority = 100
    
    def at_cmdset_creation(self):
        
        self.add(chargen.CmdAcceptPolicy())

        self.add(building_overrides.CmdDesc())
        self.add(system_overrides.CmdAbout())
        self.add(comms_overrides.CmdChannel())
        self.add(general_overrides.CmdLook())
        self.add(userlisting.CmdStaff())
        self.add(default_building.CmdTeleport())
        self.add(default_building.CmdSetAttribute())
        self.add(default_building.CmdExamine())
        self.add(help_overrides.CmdHelp())
        self.add(default_building.CmdTag())
        self.add(building.CmdZone())
        self.add(building.CmdSetSpecialRoom())




class AUPRoom(SuperDarkRoom):
    """A room in which the policy is laid out. Policy not included."""
    DESC_LENGTH_REQ = 0

    def at_object_creation(self):

        super().at_object_creation()

        self.cmdset.add(AUPRoomCmdSet(), persistent=True)
