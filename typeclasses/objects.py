"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for *all* entities
with a location in the game world (like Characters, Rooms, Exits).

"""

import string

from evennia.objects.objects import DefaultObject

from evennia.utils import evtable

from world.utils import dev_notice, builder_notice, replace_mush_escapes, header_two_slot

_EXIT_NAME_ORDER = ["[N]", "[NE", "[E]", "[SE", "[S]", "[SW", "[W]", "[NW", "[U]", "[D]", "[I]", "[O]"]
def _exit_name_sort_key(exitname):
    """
    Key formatted exit name to sort cardinals clockwise and first.

    This assumes that every input will have a two-character color code prepended, and does some
    silly hijinks with the key to make the sorting order what we want, but it works. Somewhat
    fragile. Assumes that you're not going to use U/D/I/O or directional tags for any
    exits that aren't part of the main grid.
    """
    try: 
        return "[ZZZ{:02d}{}".format(_EXIT_NAME_ORDER.index(exitname[2:5])+1, exitname[2:]) 
    except ValueError:
        return exitname[2:]


class ObjectParent:
    """
    This is a mixin that can be used to override *all* entities inheriting at
    some distance from DefaultObject (Objects, Exits, Characters and Rooms).
    """

    def register_post_command_message(self, message):
        """Register a message for display after the current command. Forwards to the object's account."""
        if self.has_account:
            self.account.register_post_command_message(message)

    def get_display_desc(self, looker, **kwargs):
        """Format our desc for display"""
        desc = self.db.desc or self.default_description
        return replace_mush_escapes(desc)
    
    def get_display_name(self, looker, **kwargs):
        """Takes display name and colors it"""
        return self.name

    def return_appearance(self, looker, **kwargs):
        """
        Format our overall appearance for being looked at.
        
        Uses room-style appearance if you are inside this object, instead of switching on object type.
        """

        if not looker:
            return
        if looker in self.contents:
            return self.get_room_style_appearance(looker, **kwargs)
        else:
            return super().return_appearance(looker, **kwargs)

    def get_room_style_appearance(self, looker, **kwargs):
        """Return a big fancy room view with columns for stuff in the room."""
        if not looker:
            return
        
        roomname = self.get_display_name(looker, **kwargs),
        extra_name_info = self.get_extra_display_name_info(looker, **kwargs),
        desc = self.get_display_desc(looker, **kwargs),
        
        from .rooms import Room

        if isinstance(self, Room): # Only warn about zones if it's actually a room we're in
            zone = self.tags.get(category="Zone", return_list=True)
            if len(zone) == 0:
                builder_notice(looker, "You should zone this room.")
            elif len(zone) != 1:
                builder_notice(looker, "Room should only have one zone tag.")
            zone = string.capwords(zone[0]) if zone else ""
        else:
            zone = "Somewhere Strange"

        characters = sorted(self.contents_get(content_type="character"), key = lambda x: x.name.lower())
        char_names = []
        for char in characters:
            if not char.access(looker, "view"):
                continue
            if not char.access(looker, "search", default=True):
                continue
            char_names.append(char.get_display_name(looker))
            
        things = self.filter_visible(self.contents_get(content_type="object"), looker, **kwargs)
        
        feature_names = []
        interactable_names = []
        thing_names = []
        for thing in sorted(things, key=lambda x: x.name.lower()):
            name = thing.get_display_name(looker, **kwargs)
            if isinstance(thing, Feature):
                feature_names.append(name)
            elif isinstance(thing, Interactable):
                interactable_names.append(name)
            else:
                thing_names.append(name)

        feature_line = f"\n|X|[xFeatures:|n {', '.join(sorted(feature_names))}." if feature_names else ""

        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        exit_names = [exit.get_display_name(looker, **kwargs) for exit in exits]
        exit_names.sort(key=_exit_name_sort_key)
        
        header = header_two_slot(80, roomname[0] + extra_name_info[0], zone)
        
        looktable = evtable.EvTable("|c-People-|n","|c-Things-|n","|c-Exits-|n",
                table=(char_names, sorted(interactable_names) + sorted(thing_names), exit_names),
                border_width=0, pad_left=0
        )

        looktable.reformat_column(0,width=25)
        looktable.reformat_column(1,width=25)
        looktable.reformat_column(2,width=30)

        return f"\n{header}\n{desc[0]}{feature_line}\n\n{looktable}\n"




class Object(ObjectParent, DefaultObject):
    """
    This is the root Object typeclass, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.
    """
    pass

class Interactable(Object):
    """
    Something you can do things with. How this is to be implemented is TBD.
    """
    def get_display_name(self, looker, **kwargs):
        """Takes display name and colors it"""
        return f"|G{self.name}|n"

class Feature(Object):
    """
    Something that decorates a place. The idea is to make these invisible and key them off
    highlighted words in the room description so that they don't take up any description space.
    That's why they show up so prominently in the room view when not inivisible. 
    """
    pass