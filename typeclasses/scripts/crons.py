
import time
import datetime

from django.conf import settings

from evennia import AttributeProperty
from evennia.utils import logger

from . import Script

from typeclasses.characters import PlayerCharacter, Character

class Crons(Script):
    key = 'crons'

    next_refresh = AttributeProperty(0)
    next_sweep = AttributeProperty(0)


    def at_server_start(self):
        """ 
        Happens on both server start and reload.
        """
        self.clear_approve_locks()

        if not self.next_sweep:
            self.next_sweep = time.time() + settings.SWEEP_CHECK_TIME
        if not self.next_refresh:
            nexttime = datetime.datetime.combine(
                datetime.date.today() + datetime.timedelta(days=1),
                datetime.time(hour=settings.REFRESH_HOUR))
            self.next_refresh = nexttime.timestamp()


    def clear_approve_locks(self):
        """
        Clean up approval locks that got lost because a server restart interrupted an admin
        approving a character, so that people don't get stuck forever.
        """
        for player in PlayerCharacter.objects.all():
            if player.approvelocked:
                logger.log_info(f"Unlocking {player.name} from approvelock.")
                player.approvelocked = False
                player.approved = False


    def at_repeat(self, **kwargs):
        now = time.time()
        if now > self.next_sweep:
            self.sweep()

        if now > self.next_refresh:
            self.refresh()

    
    def sweep(self):
        now = time.time()

        self.next_sweep = now + settings.SWEEP_CHECK_TIME

        cutoff_time = now - settings.SWEEP_TIME
        nosweep_tag = settings.ROOM_TAG_NOSWEEP
        homeable_tag = settings.ROOM_TAG_HOMEABLE

        for character in PlayerCharacter.objects.all_family():
            if not character.has_account:
                if character.last_puppeted < cutoff_time:
                    oldloc = character.location
                    if oldloc.is_ic_room and not oldloc.tags.has(nosweep_tag) and not oldloc.tags.has(homeable_tag):
                        if character.move_to(character.home, move_type="sweep"):
                            
                            icmsg = ""
                            if oldloc.is_ic_room and not character.location.is_ic_room:
                                character.last_ic_room = oldloc
                                icmsg = (
                                    f"\nThis moved {character.get_display_name(character)} OOC, "
                                    f"so you can use |b+ic|n to return."
                                )

                            msg = (
                                f"{character.get_display_name(character)} |Mwas left logged off for a long time in a "
                                f"room that's not allowed in, so they were moved to their home at|n "
                                f"{character.location.get_display_name(character)}.{icmsg}"
                            )

                            character.register_post_command_message(msg)
                            
                        else:
                            logger.log_err(f"SWEEPER: Could not move {character.name} to their home.")



    def refresh(self):

        nexttime = datetime.datetime.combine(
            datetime.date.today() + datetime.timedelta(days=1),
            datetime.time(hour=settings.REFRESH_HOUR))
        self.next_refresh = nexttime.timestamp()

        for character in Character.objects.all_family():
            online_msg = []
            offline_msg = []
            if character.refresh_all_moves():
                online_msg.append(
                    f"|MThe PP of all of|n {character.get_display_name(character)}|M's moves has been restored!|n"
                )
                offline_msg.append(
                    f"|MAll of|n {character.get_display_name(character)}|M's moves had their PP restored.|n"
                )

            if character.refresh_votes():
                online_msg.append(
                    f"{character.get_display_name(character)}|M's daily votes have been restored!|n"
                )
                offline_msg.append(
                    f"{character.get_display_name(character)}|M's daily votes were restored.|n"
                )

            if character.has_account:
                if online_msg:
                    character.msg (f"|MDaily refresh!|n {' '.join(online_msg)}")
            else:
                if offline_msg:
                    character.register_post_command_message(
                        f"|MDaily refresh happened while you were away.|n {' '.join(offline_msg)}"
                    )
 

