
import re

import d20

from .command import MuxCommand, Command

_ONE_RE = re.compile(r'\*\*(1)\*\*')
_MAX_RE = re.compile(r'\*\*(\d+)\*\*')
_SUM_RE = re.compile(r'`(\d+)`')

class CmdDice(MuxCommand):
    """
    Roll dice and report the result to the room unless /private is flagged. For help with the dice
    perser's syntax, please see https://d20.readthedocs.io/en/latest/start.html#dice-syntax
    
    Usage:
        +dice <dice expression>
        +dice/private <dice expression>
        +dice/priv <dice expression>
    
    Examples:
        +dice 3d6+1
        +dice/priv 6d3+5
    """
    key = "+dice"
    aliases = ['+roll']
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        args = self.args.strip()
        
        private = True if 'priv' in self.switches or 'private' in self.switches else False

        try: 
            result = d20.roll(args)
        except d20.errors.TooManyRolls:
            self.caller.msg("That's too many dice.")
            return
        except d20.errors.RollError:
            self.caller.msg("Something was wrong with the dice expression.")
            return
            
        result = str(result)

        result = _ONE_RE.sub(r"|R\1|x", result)
        result = _MAX_RE.sub(r"|G\1|x", result)
        result = _SUM_RE.sub(r"|w\1|n", result)
        result = result.replace('(', '|x(')
        result = result.replace(')', ')|n')
        
        if private:
            self.caller.msg(f"|Y<Dice-Private>|n {result}")
        else:
            self.caller.location.msg_contents(
                "|Y<Dice>|n {sender} rolled " + result + '.', mapping={'sender': self.caller}, from_obj=self.caller,
            )