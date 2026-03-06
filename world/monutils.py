


from evennia import GLOBAL_SCRIPTS


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