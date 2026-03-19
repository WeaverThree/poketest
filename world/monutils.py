
import itertools

from evennia import GLOBAL_SCRIPTS
from evennia.utils import evtable


def type_vuln_table(type1, type2="", show_header=True, show_nochange=True):
    """
    Returns a formatted block showing the type vulnerabilities for the given type/doubletype.
    
    Only accepts full type names.
    
    show_header - optional header line
    show_nowchange - if false, hides the 1x damage row from the output for space saving
    """

    types = GLOBAL_SCRIPTS.mondata.types
    typenames = GLOBAL_SCRIPTS.mondata.typenames
        
    typevulns = [1.0 for type in typenames]
    
    for i, type in enumerate(typenames):
        typevulns[i] = typevulns[i] * types[type]['vs'][type1]
    
    if type2:
        for i, type in enumerate(typenames):
            typevulns[i] = typevulns[i] * types[type]['vs'][type2]

    invuln = []
    quarter = []
    half = []
    one = []
    two = []
    four = []
    huh = []

    def _appendwrap(list,data):
        if len(list) > 1 and len(list) % 8 == 0:
            list.append('\n          ')
        list.append(data)

    for type, vuln in zip(typenames, typevulns):
        if vuln == 0.0:
            _appendwrap(invuln,types[type]['colortoken'])
        elif vuln == 0.25:
            _appendwrap(quarter,types[type]['colortoken'])
        elif vuln == 0.5:
            _appendwrap(half,types[type]['colortoken'])
        elif vuln == 1.0:
            _appendwrap(one,types[type]['colortoken'])
        elif vuln == 2.0:
            _appendwrap(two,types[type]['colortoken'])
        elif vuln == 4.0:
            _appendwrap(four,types[type]['colortoken'])
        else:
            _appendwrap(huh,types[type]['colortoken'])
        

    out = []
    if type2:
        typetoken = f"{types[type1]['colortoken']}{types[type2]['colortoken']}"
    else:
        typetoken = types[type1]['doubletoken']
        
    if show_header:
        out.append(f"\n|wVulnerabilities for >|n{typetoken}|w<|n")
    if one and show_nochange: 
        out.append(f"NO CHANGE:{''.join(one)}")
    if invuln:
        out.append(f"   |wINVULN|n:{''.join(invuln)}")
    if quarter:
        out.append(f"  |bQUARTER|n:{''.join(quarter)}")
    if half:
        out.append(f"     |gHALF|n:{''.join(half)}")
    if two:
        out.append(f"   |yDOUBLE|n:{''.join(two)}")
    if four:
        out.append(f"     |rQUAD|n:{''.join(four)}")
    if huh:
        out.append(f"    |[r|XERROR|n:{''.join(huh)}")

    return '\n'.join(out)


def get_display_mon_name(mon):
    
    from typeclasses.characters import Character
    
    # We're distingushing betweend dicts and characters here so can't use is_typeclass
    if not mon:
        name = "????"
        subtype = None
        form = None
    elif isinstance(mon, Character):
        name = mon.species if mon.species else "????"
        subtype = mon.subtype
        form = mon.form
    else:
        name = mon['name']
        subtype = mon['subtype']
        form = mon['form']
    
    subtype = f"|Y{subtype}|n " if subtype else ""
    form = f"|R{form}|n " if form else ""
    return f"{form}{subtype}|w{name}|n"


def get_display_mon_type(mon):

    from typeclasses.characters import Character

    # We're distingushing betweend dicts and characters here so can't use is_typeclass
    if not mon: 
        type1 = None
        type2 = None
    elif isinstance(mon, Character):
        type1 = mon.type1
        type2 = mon.type2
    else:
        type1 = mon['type1']
        type2 = mon['type2']
    
    types = GLOBAL_SCRIPTS.mondata.types
    if not type1:
        return f"|r{'????':^12}|n"
    if not type2:
        return types[type1]['doubletoken']
    else:
        return types[type1]['colortoken'] + types[type2]['colortoken']
    

def get_display_mon_banner(mon):

    from typeclasses.characters import Character

    # We're distingushing betweend dicts and characters here so can't use is_typeclass
    if not mon:
        return f"{get_display_mon_type(mon)} #? {get_display_mon_name(mon)}"
    elif isinstance(mon, Character):
        return f"{get_display_mon_type(mon)} #{mon.dexno if mon.dexno else '?'} {get_display_mon_name(mon)}"
    else:
        return f"{get_display_mon_type(mon)} #{mon['dexno']} {get_display_mon_name(mon)}"


def moves_table(movelist, usedlist=None, useheader=True):
    """
    Returns a table of nicely formated moves. If usedlist is provided, it will show remaining moves.

    Usedlist should be a list of integers corresponding to the listed moves. 
    We will also accept a movelist that is a dictionary {movename: used, ...}
    """

    mondata = GLOBAL_SCRIPTS.mondata
    
    try:
        # See if the format given is a dict of {movename: used, ...}
        movelist, usedlist = zip(*movelist.items())
    except AttributeError:
        pass
        
    names = []
    movetypes = []
    categories = []
    priorities = []
    useslist = []
    potentcies = []
    accuracies = []

    usedlist = usedlist if usedlist else []

    for move, used in itertools.zip_longest(movelist, usedlist):

        if isinstance(move, str):
            move = mondata.moves[move]

        names.append(move['name'])
        movetypes.append(mondata.types[move['type']]['colortoken'])
        categories.append(move['category_token'])

        prio = move['priority']
        if prio:
            prio = f"|b+{prio}|n" if prio > 0 else f"|r{prio}|n"
        else:
            prio = ""
        priorities.append(prio)

        uses = move['uses']
        if used is not None:
            remain = uses - used
            if remain <= 0:
                color = '|[R|X'
            elif remain < uses / 4:
                color = '|r'
            elif remain < uses / 2:
                color = '|y'
            else:
                color = ''
            remaintext = f"{color}{remain}{'|n' if color else ''}/"
        else:
            remaintext = ''
        useslist.append(f"{remaintext}{uses}")

        pot = move['potentcy']
        pot = pot if pot else "---"
        pot = "∞" if pot == 999 else pot
        potentcies.append(pot)

        acc = move['accuracy']
        acc = acc if acc else "---"
        acc = "∞" if acc == 999 else acc
        accuracies.append(acc)
    
    sortlist = sorted(zip(names,movetypes,categories,priorities,useslist,potentcies,accuracies)) 
    
    header = ("|wMove|n","|w Type|n","|w Cat|n","|wPrio|n","|wPP|n","|wPow|n","|wAcc|n",) if useheader else ()

    table = evtable.EvTable(
        *header,
        table=[list(col) for col in zip(*sortlist)],
        border_width=0,
    )
    table.reformat_column(0, width=20)
    table.reformat_column(1, align="a", width=8)
    table.reformat_column(2, align="a", width=8)
    table.reformat_column(3, align="r", width=6)
    table.reformat_column(4, align="r", width=7)
    table.reformat_column(5, align="r", width=5)
    table.reformat_column(6, align="r", width=5)

    return table