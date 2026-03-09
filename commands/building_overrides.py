
from django.conf import settings # type: ignore

from evennia.commands.default.building import ObjManipCommand, CmdLink
from evennia.utils import utils
from evennia.utils.eveditor import EvEditor
from evennia.utils.utils import (
    class_from_module,
)

from typeclasses.characters import PlayerCharacter

COMMAND_DEFAULT_CLASS = class_from_module(settings.COMMAND_DEFAULT_CLASS)

# destroy and wipe will not target player characters. desc doesn't autotarget here. unlink gains @

def _desc_load(caller):
    return caller.db.evmenu_target.db.desc or ""


def _desc_save(caller, buf):
    """
    Save line buffer to the desc prop. This should
    return True if successful and also report its status to the user.
    """
    caller.db.evmenu_target.db.desc = buf
    caller.msg("Saved.")
    return True


def _desc_quit(caller):
    caller.attributes.remove("evmenu_target")
    caller.msg("Exited editor.")



class CmdDesc(COMMAND_DEFAULT_CLASS):
    """
    describe an object or the current room.

    Usage:
      desc <obj> = <description>

    Switches:
      edit - Open up a line editor for more advanced editing.

    Sets the "desc" attribute on an object.
    """

    key = "@desc"
    switch_options = ("edit",)
    locks = "cmd:perm(desc) or perm(Builder)"
    help_category = "Building"

    def edit_handler(self):
        if self.rhs:
            self.msg("|rYou may specify a value, or use the edit switch, but not both.|n")
            return
        if self.args:
            obj = self.caller.search(self.args)
        if not obj:
            self.msg("Please spcify a target to edit.")
            return

        if not (obj.access(self.caller, "control") or obj.access(self.caller, "edit")):
            self.msg(f"You don't have permission to edit the description of {obj.key}.")
            return

        self.caller.db.evmenu_target = obj
        # launch the editor
        EvEditor(
            self.caller,
            loadfunc=_desc_load,
            savefunc=_desc_save,
            quitfunc=_desc_quit,
            key="desc",
            persistent=True,
        )
        return

    def func(self):
        """Define command"""

        caller = self.caller
        if not self.args and "edit" not in self.switches:
            caller.msg("Usage: desc <obj> = <description>")
            return

        if "edit" in self.switches:
            self.edit_handler()
            return

        if "=" in self.args:
            # We have an =
            obj = caller.search(self.lhs)
            if not obj:
                return
            desc = self.rhs or ""
        else:
            caller.msg("Usage: desc <obj> = <description>")
            return
        
        if obj.access(self.caller, "control") or obj.access(self.caller, "edit"):
            obj.db.desc = desc
            caller.msg(f"The description was set on {obj.get_display_name(caller)}.")
        else:
            caller.msg(f"You don't have permission to edit the description of {obj.key}.")


class CmdDestroy(COMMAND_DEFAULT_CLASS):
    """
    permanently delete objects

    Usage:
       destroy[/switches] [obj, obj2, obj3, [dbref-dbref], ...]

    Switches:
       override - The destroy command will usually avoid accidentally
                  destroying account objects. This switch overrides this safety.
       force - destroy without confirmation.
    Examples:
       destroy house, roof, door, 44-78
       destroy 5-10, flower, 45
       destroy/force north

    Destroys one or many objects. If dbrefs are used, a range to delete can be
    given, e.g. 4-10. Also the end points will be deleted. This command
    displays a confirmation before destroying, to make sure of your choice.
    You can specify the /force switch to bypass this confirmation.
    """

    key = "@destroy"
    aliases = ["@delete", "@del"]
    switch_options = ("override", "force")
    locks = "cmd:perm(destroy) or perm(Builder)"
    help_category = "Building"

    confirm = True  # set to False to always bypass confirmation
    default_confirm = "no"  # what to assume if just pressing enter (yes/no)

    def func(self):
        """Implements the command."""

        caller = self.caller
        delete = True

        if not self.args or not self.lhslist:
            caller.msg("Usage: destroy[/switches] [obj, obj2, obj3, [dbref-dbref],...]")
            delete = False

        def delobj(obj):
            # helper function for deleting a single object
            string = ""
            if not obj.pk:
                string = f"\nObject {obj.db_key} was already deleted."
            else:
                objname = obj.name
                if isinstance(obj,PlayerCharacter): # TODO: Probably not a good way... -WVR
                    return(f"\n{objname}: |rCannot delete player characters.|n "
                           "This would break the account the character is attached to. "
                           "Please contact a developer if this deletion is required."
                    )

                if not (obj.access(caller, "control") or obj.access(caller, "delete")):
                    return f"\nYou don't have permission to delete {objname}."
                if obj.account and "override" not in self.switches:
                    return (
                        f"\nObject {objname} is controlled by an active account. Use /override to"
                        " delete anyway."
                    )
                if obj.dbid == int(settings.DEFAULT_HOME.lstrip("#")):
                    return (
                        f"\nYou are trying to delete |c{objname}|n, which is set as DEFAULT_HOME. "
                        "Re-point settings.DEFAULT_HOME to another "
                        "object before continuing."
                    )

                # check if object to delete had exits or objects inside it
                obj_exits = obj.exits if hasattr(obj, "exits") else ()
                obj_contents = obj.contents if hasattr(obj, "contents") else ()
                had_exits = bool(obj_exits)
                had_objs = any(entity for entity in obj_contents if entity not in obj_exits)

                # do the deletion
                okay = obj.delete()
                if not okay:
                    string += (
                        f"\nERROR: {objname} not deleted, probably because delete() returned False."
                    )
                else:
                    string += f"\n{objname} was destroyed."
                    if had_exits:
                        string += f" Exits to and from {objname} were destroyed as well."
                    if had_objs:
                        string += f" Objects inside {objname} were moved to their homes."
            return string

        objs = []
        for objname in self.lhslist:
            if not delete:
                continue

            if "-" in objname:
                # might be a range of dbrefs
                dmin, dmax = [utils.dbref(part, reqhash=False) for part in objname.split("-", 1)]
                if dmin and dmax:
                    for dbref in range(int(dmin), int(dmax + 1)):
                        obj = caller.search("#" + str(dbref))
                        if obj:
                            objs.append(obj)
                    continue
                else:
                    obj = caller.search(objname)
            else:
                obj = caller.search(objname)

            if obj is None:
                self.msg(
                    " (Objects to destroy must either be local or specified with a unique #dbref.)"
                )
            elif obj not in objs:
                objs.append(obj)

        if objs and ("force" not in self.switches and type(self).confirm):
            confirm = "Are you sure you want to destroy "
            if len(objs) == 1:
                confirm += objs[0].get_display_name(caller)
            elif len(objs) < 5:
                confirm += ", ".join([obj.get_display_name(caller) for obj in objs])
            else:
                confirm += ", ".join(["#{}".format(obj.id) for obj in objs])
            confirm += " [yes]/no?" if self.default_confirm == "yes" else " yes/[no]"
            answer = ""
            answer = yield (confirm)
            answer = self.default_confirm if answer == "" else answer

            if answer and answer not in ("yes", "y", "no", "n"):
                caller.msg(
                    "Canceled: Either accept the default by pressing return or specify yes/no."
                )
                delete = False
            elif answer.strip().lower() in ("n", "no"):
                caller.msg("Canceled: No object was destroyed.")
                delete = False

        if delete:
            results = []
            for obj in objs:
                results.append(delobj(obj))

            if results:
                caller.msg("".join(results).strip())


class CmdWipe(ObjManipCommand):
    """
    clear all attributes from an object

    Usage:
      wipe <object>[/<attr>[/<attr>...]]

    Example:
      wipe box
      wipe box/colour

    Wipes all of an object's attributes, or optionally only those
    matching the given attribute-wildcard search string.
    """

    key = "@wipe"
    locks = "cmd:perm(wipe) or perm(Builder)"
    help_category = "Building"

    def func(self):
        """
        inp is the dict produced in ObjManipCommand.parse()
        """

        caller = self.caller

        if not self.args:
            caller.msg("Usage: wipe <object>[/<attr>/<attr>...]")
            return
        

        # get the attributes set by our custom parser
        objname = self.lhs_objattr[0]["name"]
        attrs = self.lhs_objattr[0]["attrs"]

        obj = caller.search(objname)

        if not obj:
            return
        if isinstance(obj, PlayerCharacter):
            caller.msg("This command is disabled on player characters for safety.")
            return
        if not (obj.access(caller, "control") or obj.access(caller, "edit")):
            caller.msg("You are not allowed to do that.")
            return
        if not attrs:
            # wipe everything
            obj.attributes.clear()
            string = f"Wiped all attributes on {obj.name}."
        else:
            for attrname in attrs:
                obj.attributes.remove(attrname)
            string = f"Wiped attributes {','.join(attrs)} on {obj.name}."
        caller.msg(string)

class CmdUnLink(CmdLink):
    """
    remove exit-connections between rooms

    Usage:
      @unlink <Object>

    Unlinks an object, for example an exit, disconnecting
    it from whatever it was connected to.
    """

    # this is just a child of CmdLink

    key = "@unlink"
    locks = "cmd:perm(unlink) or perm(Builder)"
    help_key = "Building"

    def func(self):
        """
        All we need to do here is to set the right command
        and call func in CmdLink
        """

        caller = self.caller

        if not self.args:
            caller.msg("Usage: unlink <object>")
            return

        # This mimics 'link <obj> = ' which is the same as unlink
        self.rhs = ""

        # call the link functionality
        super().func()