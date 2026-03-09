

from django.conf import settings # type: ignore

from evennia.commands.default.help import CmdHelp, HelpCategory, create
from evennia.locks.lockhandler import LockException
from evennia.utils.eveditor import EvEditor
from evennia.utils.utils import (
    class_from_module,
    inherits_from,
)

from .command import MuxCommand

# Sethelp - @ command now

DEFAULT_HELP_CATEGORY = settings.DEFAULT_HELP_CATEGORY


def _loadhelp(caller):
    entry = caller.db._editing_help
    if entry:
        return entry.entrytext
    else:
        return ""


def _savehelp(caller, buffer):
    entry = caller.db._editing_help
    caller.msg("Saved help entry.")
    if entry:
        entry.entrytext = buffer


def _quithelp(caller):
    caller.msg("Closing the editor.")
    del caller.db._editing_help

class CmdSetHelp(CmdHelp):
    """
    Edit the help database.

    Usage:
      @sethelp[/switches] <topic>[[;alias;alias][,category[,locks]]
                [= <text or new value>]
    Switches:
      edit - open a line editor to edit the topic's help text.
      replace - overwrite existing help topic.
      append - add text to the end of existing topic with a newline between.
      extend - as append, but don't add a newline.
      category - change category of existing help topic.
      locks - change locks of existing help topic.
      delete - remove help topic.

    Examples:
      @sethelp lore = In the beginning was ...
      @sethelp/append pickpocketing,Thievery = This steals ...
      @sethelp/replace pickpocketing, ,attr(is_thief) = This steals ...
      @sethelp/edit thievery
      @sethelp/locks thievery = read:all()
      @sethelp/category thievery = classes

    If not assigning a category, the `settings.DEFAULT_HELP_CATEGORY` category
    will be used. If no lockstring is specified, everyone will be able to read
    the help entry.  Sub-topics are embedded in the help text.

    Note that this cannot modify command-help entries - these are modified
    in-code, outside the game.

    # SUBTOPICS

    ## Adding subtopics

    Subtopics helps to break up a long help entry into sub-sections. Users can
    access subtopics with |whelp topic/subtopic/...|n Subtopics are created and
    stored together with the main topic.

    To start adding subtopics, add the text '# SUBTOPICS' on a new line at the
    end of your help text. After this you can now add any number of subtopics,
    each starting with '## <subtopic-name>' on a line, followed by the
    help-text of that subtopic.
    Use '### <subsub-name>' to add a sub-subtopic and so on. Max depth is 5. A
    subtopic's title is case-insensitive and can consist of multiple words -
    the user will be able to enter a partial match to access it.

    For example:

    | Main help text for <topic>
    |
    | # SUBTOPICS
    |
    | ## about
    |
    | Text for the '<topic>/about' subtopic'
    |
    | ### more about-info
    |
    | Text for the '<topic>/about/more about-info sub-subtopic
    |
    | ## extra
    |
    | Text for the '<topic>/extra' subtopic

    """

    key = "@sethelp"
    aliases = []
    switch_options = ("edit", "replace", "append", "extend", "category", "locks", "delete")
    locks = "cmd:perm(Helper)"
    help_category = "Building"
    arg_regex = None

    def parse(self):
        """We want to use the default parser rather than the CmdHelp.parse"""
        return MuxCommand.parse(self)

    def func(self):
        """Implement the function"""

        switches = self.switches
        lhslist = self.lhslist
        rhslist = self.rhslist

        if not self.args:
            self.msg(
                "Usage: @sethelp[/switches] <topic>[[;alias;alias][,category[,locks]] [= <text or new category>]"
            )
            return

        nlist = len(lhslist)
        topicstr = lhslist[0] if nlist > 0 else ""
        if not topicstr:
            self.msg("You have to define a topic!")
            return
        topicstrlist = topicstr.split(";")
        topicstr, aliases = (
            topicstrlist[0],
            topicstrlist[1:] if len(topicstr) > 1 else [],
        )
        aliastxt = ("(aliases: %s)" % ", ".join(aliases)) if aliases else ""
        old_entry = None

        # check if we have an old entry with the same name

        cmd_help_topics, db_help_topics, file_help_topics = self.collect_topics(
            self.caller, mode="query"
        )
        # db-help topics takes priority over file-help
        file_db_help_topics = {**file_help_topics, **db_help_topics}
        # commands take priority over the other types
        all_topics = {**file_db_help_topics, **cmd_help_topics}
        # get all categories
        all_categories = list(
            set(HelpCategory(topic.help_category) for topic in all_topics.values())
        )
        # all available help options - will be searched in order. We also check # the
        # read-permission here.
        entries = list(all_topics.values()) + all_categories

        # default setup
        category = lhslist[1] if nlist > 1 else DEFAULT_HELP_CATEGORY
        lockstring = ",".join(lhslist[2:]) if nlist > 2 else "read:all()"

        # search for existing entries of this or other types
        old_entry = None
        for querystr in topicstrlist:
            match, _ = self.do_search(querystr, entries)
            if match:
                warning = None
                if isinstance(match, HelpCategory):
                    warning = (
                        f"'{querystr}' matches (or partially matches) the name of "
                        f"help-category '{match.key}'. If you continue, your help entry will "
                        "take precedence and the category (or part of its name) *may* not "
                        "be usable for grouping help entries anymore."
                    )
                elif inherits_from(match, "evennia.commands.command.Command"):
                    warning = (
                        f"'{querystr}' matches (or partially matches) the key/alias of "
                        f"Command '{match.key}'. Command-help take precedence over other "
                        "help entries so your help *may* be impossible to reach for those "
                        "with access to that command."
                    )
                elif inherits_from(match, "evennia.help.filehelp.FileHelpEntry"):
                    warning = (
                        f"'{querystr}' matches (or partially matches) the name/alias of the "
                        f"file-based help topic '{match.key}'. File-help entries cannot be "
                        "modified from in-game (they are files on-disk). If you continue, "
                        "your help entry may shadow the file-based one's name partly or "
                        "completely."
                    )
                if warning:
                    # show a warning for a clashing help-entry type. Even if user accepts this
                    # we don't break here since we may need to show warnings for other inputs.
                    # We don't count this as an old-entry hit because we can't edit these
                    # types of entries.
                    self.msg(f"|rWarning:\n|r{warning}|n")
                    repl = yield ("|wDo you still want to continue? Y/[N]?|n")
                    if repl.lower() in ("y", "yes"):
                        # find a db-based help entry if one already exists
                        db_topics = {**db_help_topics}
                        db_categories = list(
                            set(HelpCategory(topic.help_category) for topic in db_topics.values())
                        )
                        entries = list(db_topics.values()) + db_categories
                        match, _ = self.do_search(querystr, entries)
                        if match:
                            old_entry = match
                    else:
                        self.msg("Aborted.")
                        return
                else:
                    # a db-based help entry - this is OK
                    old_entry = match
                    category = lhslist[1] if nlist > 1 else old_entry.help_category
                    lockstring = ",".join(lhslist[2:]) if nlist > 2 else old_entry.locks.get()
                    break

        category = category.lower()

        if "edit" in switches:
            # open the line editor to edit the helptext. No = is needed.
            if old_entry:
                topicstr = old_entry.key
                if self.rhs:
                    # we assume append here.
                    old_entry.entrytext += "\n%s" % self.rhs
                helpentry = old_entry
            else:
                helpentry = create.create_help_entry(
                    topicstr,
                    self.rhs if self.rhs is not None else "",
                    category=category,
                    locks=lockstring,
                    aliases=aliases,
                )
            self.caller.db._editing_help = helpentry

            EvEditor(
                self.caller,
                loadfunc=_loadhelp,
                savefunc=_savehelp,
                quitfunc=_quithelp,
                key="topic {}".format(topicstr),
                persistent=True,
            )
            return

        if "append" in switches or "merge" in switches or "extend" in switches:
            # merge/append operations
            if not old_entry:
                self.msg(f"Could not find topic '{topicstr}'. You must give an exact name.")
                return
            if not self.rhs:
                self.msg("You must supply text to append/merge.")
                return
            if "merge" in switches:
                old_entry.entrytext += " " + self.rhs
            else:
                old_entry.entrytext += "\n%s" % self.rhs
            old_entry.aliases.add(aliases)
            self.msg(f"Entry updated:\n{old_entry.entrytext}{aliastxt}")
            return

        if "category" in switches:
            # set the category
            if not old_entry:
                self.msg(f"Could not find topic '{topicstr}'{aliastxt}.")
                return
            if not self.rhs:
                self.msg("You must supply a category.")
                return
            category = self.rhs.lower()
            old_entry.help_category = category
            self.msg(f"Category for entry '{topicstr}'{aliastxt} changed to '{category}'.")
            return

        if "locks" in switches:
            # set the locks
            if not old_entry:
                self.msg(f"Could not find topic '{topicstr}'{aliastxt}.")
                return
            show_locks = not rhslist
            clear_locks = rhslist and not rhslist[0]
            if show_locks:
                self.msg(f"Current locks for entry '{topicstr}'{aliastxt} are: {old_entry.locks}")
                return
            if clear_locks:
                old_entry.locks.clear()
                old_entry.locks.add("read:all()")
                self.msg(f"Locks for entry '{topicstr}'{aliastxt} reset to: read:all()")
                return
            lockstring = ",".join(rhslist)
            # locks.validate() does not throw an exception for things like "read:id(1),read:id(6)"
            # but locks.add() does
            existing_locks = old_entry.locks.all()
            old_entry.locks.clear()
            try:
                old_entry.locks.add(lockstring)
            except LockException as e:
                old_entry.locks.add(existing_locks)
                self.msg(str(e) + " Locks not changed.")
            else:
                self.msg(f"Locks for entry '{topicstr}'{aliastxt} changed to: {lockstring}")
            return

        if "delete" in switches or "del" in switches:
            # delete the help entry
            if not old_entry:
                self.msg(f"Could not find topic '{topicstr}'{aliastxt}.")
                return
            old_entry.delete()
            self.msg(f"Deleted help entry '{topicstr}'{aliastxt}.")
            return

        # at this point it means we want to add a new help entry.
        if not self.rhs:
            self.msg("You must supply a help text to add.")
            return
        if old_entry:
            if "replace" in switches:
                # overwrite old entry
                old_entry.key = topicstr
                old_entry.entrytext = self.rhs
                old_entry.help_category = category
                old_entry.locks.clear()
                old_entry.locks.add(lockstring)
                old_entry.aliases.add(aliases)
                old_entry.save()
                self.msg(f"Overwrote the old topic '{topicstr}'{aliastxt}.")
            else:
                self.msg(
                    f"Topic '{topicstr}'{aliastxt} already exists. Use /edit to open in editor, or "
                    "/replace, /append and /merge to modify it directly."
                )
        else:
            # no old entry. Create a new one.
            new_entry = create.create_help_entry(
                topicstr, self.rhs, category=category, locks=lockstring, aliases=aliases
            )
            if new_entry:
                self.msg(f"Topic '{topicstr}'{aliastxt} was successfully created.")
                if "edit" in switches:
                    # open the line editor to edit the helptext
                    self.caller.db._editing_help = new_entry
                    EvEditor(
                        self.caller,
                        loadfunc=_loadhelp,
                        savefunc=_savehelp,
                        quitfunc=_quithelp,
                        key="topic {}".format(new_entry.key),
                        persistent=True,
                    )
                    return
            else:
                self.msg(f"Error when creating topic '{topicstr}'{aliastxt}! Contact an admin.")
