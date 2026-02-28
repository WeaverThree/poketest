"""
Room

Rooms are simple containers that has no location of their own.

"""

from collections import defaultdict
import string

from evennia.objects.objects import DefaultRoom

from .objects import ObjectParent

from evennia.utils.utils import (
    class_from_module,
    compress_whitespace,
    dbref,
    is_iter,
    iter_to_str,
    lazy_property,
    make_iter,
    to_str,
    variable_from_module,
)

from evennia.utils import evtable

def dev_notice(target, message):
    if target.permissions.check("Builder"):
        target.msg("|[r|XDev Notice|n|r {}|n".format(message))

class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    def return_appearance(self, looker, **kwargs):
        if not looker:
            return
        
        mainname = self.get_display_name(looker, **kwargs),
        extra_name_info = self.get_extra_display_name_info(looker, **kwargs),
        desc = self.get_display_desc(looker, **kwargs),
        
        zone = self.tags.get(category="Zone", return_list=True)
        if len(zone) == 0:
            dev_notice(looker, "You should zone this room.")
        elif len(zone) != 1:
            dev_notice(looker, "Room should only have one zone tag.")
        zone = string.capwords(zone[0]) if zone else ""

        def _sort_exit_names(names):
            exit_order = kwargs.get("exit_order")
            if not exit_order:
                return names
            sort_index = {name: key for key, name in enumerate(exit_order)}
            names = sorted(names)
            end_pos = len(sort_index)
            names.sort(key=lambda name: sort_index.get(name, end_pos))
            return names

        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        exit_names = []
        for exi in exits:
            name = exi.get_display_name(looker, **kwargs).strip()
            if name:
                aliases = exi.aliases.all()
                if aliases:
                    best_alias = min(aliases, key=len)
                    if len(best_alias) < len(name):
                        name = "|g[{}]|n {}".format(best_alias.capitalize(), name)
                exit_names.append(name)

        characters = sorted(self.contents_get(content_type="character"), key = lambda x: x.name)
        char_names = []
        for char in characters:
            if not char.access(looker, "view"):
                continue
            if not char.access(looker, "search", default=True):
                continue
            char_names.append(char.get_formatted_name(looker))
            
        # sort and handle same-named things
        things = self.filter_visible(self.contents_get(content_type="object"), looker, **kwargs)

        grouped_things = defaultdict(list)
        for thing in things:
            grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

        thing_names = []
        for thingname, thinglist in sorted(grouped_things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            thing_names.append(singular if nthings == 1 else plural)

        WIDTH = 80
        header_left = "|R--< |w{}{} |R>-".format(mainname[0], extra_name_info[0])
        header_right = "|R-< |w{} |R>--|n".format(zone)
        fill = WIDTH - len(header_left) - len(header_right) + 14
        header = "{}{}{}".format(header_left, "-" * fill, header_right)

        # char_col = evtable.EvColumn(*char_names)
        # thing_col = evtable.EvColumn(*thing_names)
        # exit_col = evtable.EvColumn(*exit_names)

        looktable = evtable.EvTable("|c-People-|n","|c-Things-|n","|c-Exits-|n",
                table=(char_names, thing_names, exit_names),
                border_width=0, pad_left=0
        )

        looktable.reformat_column(0,width=25)
        looktable.reformat_column(1,width=30)
        looktable.reformat_column(2,width=25)

        finaldesc = "\n{}\n{}\n\n{}".format(header, desc[0],looktable)
        return finaldesc
        
