
import time
import itertools

from django.conf import settings

import evennia
from evennia.utils.evtable import EvTable

from .command import Command, MuxCommand
from world.utils import split_on_all_newlines, get_wordcount, get_defaulthome, get_specialroom
from typeclasses.characters import Character, PlayerCharacter
from typeclasses.rooms import Room

_PRIORITY_EXITS = ["[N]", "[NE", "[E]", "[SE", "[S]", "[SW", "[W]", "[NW"]
_HIGH_PRIORITY_EXITS = ["[O]"]

_DEFAULT_WEIGHT = 4
_PRIORITY_WEIGHT = 2
_HIGH_PRIORITY_WEIGHT = 1


class CmdPathfind(Command):
    """
    Show the path of exits to get from where you are to where the chosen target is.

    Usage:
      find <player character>
    """
    aliases = "path"
    key = "find"
    locks = "cmd:all()"

    def func(self):
        
        try:
            import networkx
            import networkx.exception
        except ImportError:
            self.msg("|mFunctionality not available. Needs python package 'networx'.|n")

        caller = self.caller

        args = self.args.strip()

        if not args:
            self.msg("Usage: find <player character>")
            return
        
        if args in ('self', 'me'):
            self.msg(f"{caller.get_display_name(caller)} is right here!")
            return
    
        search = PlayerCharacter.objects.search(args)
        if not search:
            self.msg(f"Couldn't find player character '{args}'.")
            return
        if len(search) != 1:
            self.msg(f"Got multiple hits for '{args}'. This shouldn't happen. Please notify staff.")
            return
        target = search[0]

        if target.location == caller.location:
            self.msg(f"{target.get_display_name(caller)} is right here!")
            return
        
        our_dbref = caller.location.dbref
        target_dbref = target.location.dbref
        
        debug_time_start = time.time()

        graph = networkx.DiGraph()

        for room in Room.objects.all_family():
            dbref = room.dbref
            for exit in room.contents_get(content_type="exit"):
                exit_to_dbref = exit.destination.dbref               
                exit_name = exit.get_display_name(caller)
                
                # TODO This is kinda dumb and fragile but it'll work for now...
                tag_start = exit_name[2:5]
                if tag_start in _HIGH_PRIORITY_EXITS:
                    weight = _HIGH_PRIORITY_WEIGHT
                elif tag_start in _PRIORITY_EXITS:
                    weight = _PRIORITY_WEIGHT
                else:
                    weight = _DEFAULT_WEIGHT

                # This also kinda assumes that there are no parallel exits on the grid, results will
                # be undefined if they are...

                graph.add_edge(dbref, exit_to_dbref, name=exit_name, weight=weight)

        debug_time_graph = time.time()

        try:
            path = networkx.shortest_path(graph, source=our_dbref, target=target_dbref, weight='weight')
        except networkx.exception.NetworkXNoPath:
            self.msg(f"No path between {caller.get_display_name(caller)} and {target.get_display_name(caller)}.")
            return
        
        debug_time_path = time.time()

        path_table = EvTable("|wFrom|n", "|wTake|n", border_width=0)

        for src_dbref, dst_dbref in itertools.pairwise(path):
            exitname = graph.get_edge_data(src_dbref, dst_dbref)['name']
            src = evennia.search_object(src_dbref)[0]

            path_table.add_row(src.get_display_name(), exitname)
        
        final = evennia.search_object(path[-1])[0]
        path_table.add_row(final.get_display_name(), "")

        header = (
            f"|wFrom|n {caller.get_display_name(caller)} |wto|n {target.get_display_name(caller)} "
            f"|win {len(path) - 1} steps.|n"
        )

        self.msg(f"{header}\n{path_table}")
        self.msg(
            f"|x(Debug: graph construction: {(debug_time_graph - debug_time_start)*1000.0:0.2f}ms, "
            f"pathfinding: {(debug_time_path - debug_time_graph)*1000.0:0.2f}ms)"
        )

