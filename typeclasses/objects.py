"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for *all* entities
with a location in the game world (like Characters, Rooms, Exits).

"""

import string
import time
import typing
from collections import defaultdict

import inflect 
from django.utils.translation import gettext as _

from evennia import AttributeProperty
from evennia.objects.objects import DefaultObject
from evennia.utils import evtable, ansi, group_objects_by_key_and_desc, make_iter, display_len, time_format

from world.utils import builder_notice, replace_mush_escapes, header_two_slot, get_wordcount, split_on_all_newlines

_INFLECT = inflect.engine()
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

    # This goes here so we don't have to worry about if we're contained in a room
    last_ic_talk_time_loc = AttributeProperty(0, category="talkmonitor")
    ic_wordcount_loc = AttributeProperty(0, category="talkmonitor")

    DESC_LENGTH_REQ = 0

    def register_post_command_message(self, message):
        """Register a message for display after the current command. Forwards to the object's account."""
        if self.has_account:
            self.account.register_post_command_message(message)


    def get_display_desc(self, looker=None, **kwargs):
        """Format our desc for display"""
        desc = self.db.desc or self.default_description
        return replace_mush_escapes(desc)
    

    def get_display_name(self, looker=None, **kwargs):
        """Takes display name and colors it"""
        return self.color_name(self.get_base_display_name(looker, **kwargs), looker, **kwargs)
    

    def get_base_display_name(self, looker=None, **kwargs):
        """Get the name without any color"""
        return self.name
    

    def color_name(self, name_to_decorate, looker=None, **kwargs):
        """Wrap the name in an appropriate color"""
        return name_to_decorate


    def get_numbered_name(self, count, looker, **kwargs):
        """
        Return the numbered (singular, plural) forms of this object's key. This is by default called
        by return_appearance and is used for grouping multiple same-named of this object. Note that
        this will be called on *every* member of a group even though the plural name will be only
        shown once. Also the singular display version, such as 'an apple', 'a tree' is determined
        from this method.

        Args:
            count (int): Number of objects of this type
            looker (DefaultObject): Onlooker. Not used by default.

        Keyword Args:
            key (str): Optional key to pluralize. If not given, the object's `.get_display_name()`
                method is used.
            return_string (bool): If `True`, return only the singular form if count is 0,1 or
                the plural form otherwise. If `False` (default), return both forms as a tuple.

        Returns:
            tuple: This is a tuple `(str, str)` with the singular and plural forms of the key
            including the count.

        Examples:
        ::

            obj.get_numbered_name(3, looker, key="foo")
                  -> ("a foo", "three foos")
            obj.get_numbered_name(1, looker, key="Foobert", return_string=True)
                  -> "a Foobert"
        """
        key = kwargs.get("key")
        using_arg = False
        if key:
            using_arg = True
        else:
            key = self.get_base_display_name(looker)
        key = ansi.ANSIString(key)  # this is needed to allow inflection of colored names
        try:
            plural = _INFLECT.plural(key, count)
            num = _INFLECT.number_to_words(count, threshold=1)
            # Null character as a workaround for a color problem when only one character is colored
            # Might be the table in inventory doing... evtable does the same v.v
            plural = f"|c{num}\000|n {self.color_name(plural, looker) if not using_arg else plural}"
        except IndexError:
            # this is raised by inflect if the input is not a proper noun
            plural = key
            if not using_arg: 
                plural = self.color_name(plural, looker)

        singular = self.color_name(key, looker)
        # if not self.aliases.get(plural, category=self.plural_category):
        #     # we need to wipe any old plurals/an/a in case key changed in the interrim
        #     self.aliases.clear(category=self.plural_category)
        #     self.aliases.add(plural, category=self.plural_category)

        if kwargs.get("return_string"):
            return singular if count == 1 else plural

        return singular, plural


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
        
        if display_len(desc) < self.DESC_LENGTH_REQ:
            builder_notice(looker, "This room should have a longer desc.")

        from .rooms import Room

        if self.is_typeclass(Room): # Only warn about zones if it's actually a room we're in
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
        other_things = []
        for obj in sorted(things, key=lambda x: x.name.lower()):
            name = obj.get_display_name(looker, **kwargs)
            if obj.is_typeclass(Feature):
                feature_names.append(name)
            elif obj.is_typeclass(Interactable):
                interactable_names.append(name)
            else:
                other_things.append(obj)

        thing_names = [name for name,_,_ in group_objects_by_key_and_desc(other_things, looker)]

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

        tmp_last_talk_time = "Last Talk: " + time_format(time.time() - self.last_ic_talk_time_loc)
        tmp_last_talk_time += f" Wordcount here: {self.ic_wordcount_loc}"

        return f"\n{header}\n{tmp_last_talk_time}\n{desc[0]}{feature_line}\n\n{looktable}\n"
    

    def at_say(
        self,
        message,
        msg_self=None,
        msg_location=None,
        receivers=None,
        msg_receivers=None,
        **kwargs,
    ):
        """
        Display the actual say (or whisper) of self.

        This hook should display the actual say/whisper of the object in its
        location.  It should both alert the object (self) and its
        location that some text is spoken.  The overriding of messages or
        `mapping` allows for simple customization of the hook without
        re-writing it completely.

        Args:
            message (str): The message to convey.
            msg_self (bool or str, optional): If boolean True, echo `message` to self. If a string,
                return that message. If False or unset, don't echo to self.
            msg_location (str, optional): The message to echo to self's location.
            receivers (DefaultObject or iterable, optional): An eventual receiver or receivers of the
                message (by default only used by whispers).
            msg_receivers(str): Specific message to pass to the receiver(s). This will parsed
                with the {receiver} placeholder replaced with the given receiver.
        Keyword Args:
            mapping (dict): Pass an additional mapping to the message.

        Notes:

            Messages can contain {} markers. These are substituted against the values
            passed in the `mapping` argument.
            ::

                msg_self = 'You say: "{speech}"'
                msg_location = '{object} says: "{speech}"'
                msg_receivers = '{object} whispers: "{speech}"'

            Supported markers by default:

            - {self}: text to self-reference with (default 'You')
            - {speech}: the text spoken/whispered by self.
            - {object}: the object speaking.
            - {receiver}: replaced with a single receiver only for strings meant for a specific
              receiver (otherwise 'None').
            - {all_receivers}: comma-separated list of all receivers,
              if more than one, otherwise same as receiver
            - {location}: the location where object is.

        """

        from .characters import PlayerCharacter

        msg_type = "say"
        msg_self = _('{self} says, "|n{speech}|n"') if msg_self is True else msg_self
        msg_location = msg_location or _('{object} says, "{speech}"')
        msg_receivers = msg_receivers or message

        custom_mapping = kwargs.get("mapping", {})
        receivers = make_iter(receivers) if receivers else None
        location = self.location

        # We don't allow newlines in SAY type messages because they're wrapped in " " and we don't
        # want anything silly to happen with the formatting or anything...
        message = ' '.join(split_on_all_newlines(message))

        if msg_self:
            self_mapping = {
                "self": self.get_display_name(self),
                "object": self.get_display_name(self),
                "location": location.get_display_name(self) if location else None,
                "receiver": None,
                "all_receivers": (
                    ", ".join(recv.get_display_name(self) for recv in receivers)
                    if receivers
                    else None
                ),
                "speech": message,
            }
            self_mapping.update(custom_mapping)
            self.msg(text=(msg_self.format_map(self_mapping), {"type": msg_type}), from_obj=self)

        if receivers and msg_receivers:
            receiver_mapping = {
                "self": self.get_display_name(self),
                "object": None,
                "location": None,
                "receiver": None,
                "all_receivers": None,
                "speech": message,
            }
            for receiver in make_iter(receivers):
                individual_mapping = {
                    "object": self.get_display_name(receiver),
                    "location": location.get_display_name(receiver),
                    "receiver": receiver.get_display_name(receiver),
                    "all_receivers": (
                        ", ".join(recv.get_display_name(recv) for recv in receivers)
                        if receivers
                        else None
                    ),
                }
                receiver_mapping.update(individual_mapping)
                receiver_mapping.update(custom_mapping)
                receiver.msg(
                    text=(msg_receivers.format_map(receiver_mapping), {"type": msg_type}),
                    from_obj=self,
                )

        if self.location and msg_location:
            location_mapping = {
                "self": self.get_display_name(self),
                "object": self,
                "location": location,
                "all_receivers": ", ".join(str(recv) for recv in receivers) if receivers else None,
                "receiver": None,
                "speech": message,
            }
            location_mapping.update(custom_mapping)
            exclude = []
            if msg_self:
                exclude.append(self)
            if receivers:
                exclude.extend(receivers)
            self.location.msg_contents(
                text=(msg_location, {"type": msg_type}),
                from_obj=self,
                exclude=exclude,
                mapping=location_mapping,
            )
            wordcount = get_wordcount(message)
            self.location.last_ic_talk_time_loc = time.time()
            self.location.ic_wordcount_loc += wordcount
            if self.is_typeclass(PlayerCharacter):
                self.last_ic_talk_time = time.time()
                self.ic_wordcount += wordcount  


class Object(ObjectParent, DefaultObject):
    """
    This is the root Object typeclass, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.
    """
    PLURALIZE = True
    
    def at_object_creation(self):

        # We want the name for the plural (e.g. boxes) to be a valid name for anything that can be
        # pluralized...
        if self.PLURALIZE:
            plural = _INFLECT.plural(self.name, 5)
            self.aliases.add(plural, category=self.plural_category)

        return super().at_object_creation()
    
    def at_rename(self, oldname, newname):

        super().at_rename(oldname, newname)
        if self.PLURALIZE:
            plural = _INFLECT.plural(self.name, 5)
            self.aliases.add(plural, category=self.plural_category)

class Interactable(Object):
    """
    Something you can do things with. How this is to be implemented is TBD.
    """

    PLURALIZE = False

    def get_display_name(self, looker, **kwargs):
        """Takes display name and colors it"""
        return f"|G{self.name}|n"

class Feature(Object):
    """
    Something that decorates a place. The idea is to make these invisible and key them off
    highlighted words in the room description so that they don't take up any description space.
    That's why they show up so prominently in the room view when not inivisible. 
    """
    
    PLURALIZE = False