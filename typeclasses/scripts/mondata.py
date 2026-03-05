"""
Mondata - the source for all IP-specific mon information. This expects the following CSVs to exist in world/mondata:

## Master-Type-Matrix.csv
Contains the type system for the game. Fromat is a square grid, left hand attacker, top defender.
The primary cells e.g. 1->2 below, the value for type 1 attacking type 2, are multipliers, typically 0.0, 0.5, 1.0, 2.0
Colors in ---- column are evennia color code strings.
Names in --- Column must match names across top.
Names in -- and - columns are short names (4-char capital, 2-char minimal) for tags and tables
```
---  , --  , - , Type1, Type2, Type3, ----
Type1, TYP1, To, 1->1 , 1->2 , 1->3 , Color1
Type2, TYP2, Tt, 2->1 , 2->2 , 2->3 , Color2
Type3, TYP3, Th, 3->1 , 3->2 , 3->3 , Color3
```

## Master-Mon-List.csv
Contains all of the mons that a player can choose. Asterisks mark rquired fields. 

Subtypes are prefixes to the species that are permanent.
Forms are prefixes to the species that are variable.
Types must match types from the master type list.

```
Dex No.*, Subtype, Form, Species Name*, Type1*, Type 2, 
Ability1*, Ability2, Hidden Ability,
Alt Ability1, Alt Ability2, Alt Hidden Ability,
[Stat Bases] Health*, Physical Attack*, Physical Defense*, Special Attack*, Special Defense*, Speed*
```

## Master-Move-List.csv
Containes all of the moves that can be created by players.
Types must match types from the master type list.
Category should be Physical, Special, Status, or ??? [Not Implemented].
Priority should be integers from around -10 to 10. It's zero if not listed.
Nonstandard Move Types include Z-Moves and Max Moves, as well as the unselectable move Struggle.
Special moves are currently ignored and not loaded into the move database.

It's unlikely special processing will ever be created for moves.
We can do basic calculations but you'll need to understand what the move is meant to do and how it works.

```
Move No.*, Move Name*, Priority [0 Default], Type*, Category*, Uses*, Potentcy, Accuracy, Nonstandard Move Type
```

## Master-Nature-List.csv
Fairly straightforward. If favored and neglected match nothing happens. If flavors match there's no preference.
Flavors are currently not implemented.
```
Nature Name*, Favored Stat*, Neglected Stat*, Favored Flavor*, Disliked Flavor*
```
"""

import csv
import os

from evennia.utils import logger

_TYPE_MATRIX_FILE = "world/mondata/Master-Type-Matrix.csv"
_MON_LIST_FILE = "world/mondata/Master-Mon-List.csv"
_MOVE_LIST_FILE = "world/mondata/Master-Move-List.csv"
_NATURE_LIST_FILE = "world/mondata/Master-Nature-List.csv"

_FALLBACK_TYPE_MATRIX = [
    ["---","--","-","Fire","Water","Grass","----"],
    ["Fire","FIRE","Fr",1.0,0.5,2.0,"|[#E62829|w"],
    ["Water","WATR","Wa",2.0,1.0,0.5,"|[#2980EF|w"],
    ["Grass","GRAS","Gs",0.5,2.0,1.0,"|[#3FA129|w"],
]

_FALLBACK_MON_LIST = [
    ["1","","","Plant Monster","Grass","","Grass Ability","","Hidden Ability","","","","40","40","40","60","60","40"],
    ["2","","","Fire Winger","Fire","","Fire Ability","","Hidden Ability","","","","30","50","40","60","50","60"],
    ["3","","","Water Tank","Water","","Water Ability","","Secret Ability","","","","40","40","60","50","60","40"],
]

_FALLBACK_MOVE_LIST = [
    ["1","Fire Attack","","Fire","Physical","10","40","100",""],
    ["2","Water Bomb","-2","Water","Special","10","100","60",""],
    ["3","Undergrowth","1","Grass","Status","10","","100",""],
]

_FALLBACK_NATURE_LIST = [
    ["Sanquine","Physical Attack","Physical Attack","Spicy","Spicy"],
    ["Macabre","Special Attack","Physical Attack","Dry","Spicy"],
]

from . import Script

class MonData(Script):
    key = 'mondata'

    def at_server_start(self):
        """ 
        Happens on both server start and reload.

        We don't store any persistent data so we need to reload everything from disk each time.
        This also means that if you update the spreadsheets you can run reload to update the data.
        """

        self.load_data()


    def load_data(self):
        """Loads all data files into object attributes.
        
        This basically needs to happen before anyone tries to access anything on this object, and
        load_type_matrix needs to be done before everything else because tere are things that rely
        on the types existing. 
        """

        if os.path.exists(_TYPE_MATRIX_FILE): 
            with open(_TYPE_MATRIX_FILE) as infile:
                self.load_type_matrix(csv.reader(infile))
        else:
            logger.log_warn(f"Using type matrix fallback because no file at {_TYPE_MATRIX_FILE}.")
            self.load_type_matrix(iter(_FALLBACK_TYPE_MATRIX))

        if os.path.exists(_MON_LIST_FILE): 
            with open(_MON_LIST_FILE) as infile:
                self.load_mon_list(csv.reader(infile))
        else:
            logger.log_warn(f"Using mon list fallback because no file at {_MON_LIST_FILE}.")
            self.load_mon_list(iter(_FALLBACK_MON_LIST))
       
        if os.path.exists(_MOVE_LIST_FILE): 
            with open(_MOVE_LIST_FILE) as infile:
                self.load_move_list(csv.reader(infile))
        else:
            logger.log_warn(f"Using move list fallback because no file at {_MOVE_LIST_FILE}.")
            self.load_move_list(iter(_FALLBACK_MOVE_LIST))
        
        if os.path.exists(_NATURE_LIST_FILE): 
            with open(_NATURE_LIST_FILE) as infile:
                self.load_nature_list(csv.reader(infile))
        else:
            logger.log_warn(f"Using nature list fallback because no file at {_NATURE_LIST_FILE}.")
            self.load_nature_list(iter(_FALLBACK_NATURE_LIST))
        

    def load_type_matrix(self, csvdata):
        """csvdata -> self.{types,typenames,typelookup}"""

        types = {}
        typenames = []
        typelookup = {}

        header = [cell.strip() for cell in next(csvdata)]
        if not (header[0] == '---' and header[1] == '--' and header[2] == '-', header[-1] == '----'):
            raise ValueError("Type matrix CSV header bad")
        
        for type in header[3:-1]:
            if type in ['-', '--', '---', '----']:
                raise ValueError("Type matrix CSV header bad")
            typenames.append(type)
        
        curtype = 0
        for row in csvdata:
            row = [cell.strip() for cell in row]
            name, token, short = row[:3]
            color = row [-1]
            if name != typenames[curtype]:
                raise ValueError("Type matrix types Don't match")
            curtype += 1

            vs = {x:float(y) for x,y in zip(typenames, row[3:-1])}

            newtype = {'name':name, 'token':token, 'short':short, 'color':color, 'vs':vs,
                       'colortoken':f"{color}{token:^6}|n", 'doubletoken':f"{color}{name.upper():^12}|n"}
            types[name] = newtype
            typelookup[name.lower()] = name
            typelookup[token.lower()] = name
            typelookup[short.lower()] = name

        if curtype != len(typenames):
            raise ValueError("Type matrix types Don't match")
        
        self.types = types
        self.typenames = typenames
        self.typelookup = typelookup


    def load_mon_list(self, csvdata):
        """csvdata -> self.mons"""
        mons = []

        for row in csvdata:
            row = [cell.strip() for cell in row]
            dexno = int(row[0])
            subtype, form, name = row[1:4]
            if not dexno or not name:
                raise ValueError(f"Bad mon data on row {row}")
            
            type1, type2 = row[4:6]
            if not type1:
                raise ValueError(f"Bad mon data on row {row}")
            
            if type1 not in self.typenames:
                raise ValueError(f"No such type '{type1}' on row {row}")
            if type2 and type2 not in self.typenames:
                raise ValueError(f"No such type '{type2}' on row {row}")


            ability1, ability2, abilityh = row[6:9]
            ability1b, ability2b, abilityhb = row[9:12]
            if not ability1:
                raise ValueError(f"Bad mon data on row {row}")
            
            base_stats = {
                'health': int(row[12]),
                'physical attack': int(row[13]),
                'physical defense': int(row[14]),
                'special attack': int(row[15]),
                'special defense': int(row[16]),
                'speed': int(row[17]),
            }

            newmon = {
                'dexno': dexno, 'subtype': subtype, 'form': form, 'name': name,
                'type1': type1, 'type2': type2,
                'abilities': [ability1, ability2, ability1b, ability2b],
                'hidden_abilities': [abilityh, abilityhb],
                'base_stats': base_stats,
            }
            
            mons.append(newmon)
        
        self.mons = mons


    def load_move_list(self, csvdata):
        """csvdata -> self.moves"""
        moves = {}
        for row in csvdata:
            row = [cell.strip() for cell in row]
            moveno = int(row[0])
            name = row[1]
            priority = int(row[2]) if row[2] else 0
            movetype, category = row[3:5]
            uses = int(row[5]) if row[5] else None
            
            if row[6] == '∞':
                # Using a dumb flag value for now
                potentcy = 999
            elif row[6]:
                potentcy = int(row[6])
            else:
                potentcy = None
            
            if row[7] == '∞':
                # Using a dumb flag value for now
                accuracy = 999
            elif row[7]:
                accuracy = int(row[7])
            else:
                accuracy = None
            
            nonstandard = row[8]

            if nonstandard:
                # Nonstandard moves are currently ignored and not loaded
                continue

            if not all((moveno, name, movetype, category, uses)):
                raise ValueError(f"Bad move data on row {row}")
            if movetype not in self.typenames:
                raise ValueError(f"No such type '{movetype}' on row {row}")
            
            moves[name] = {
                'moveno':moveno, 'name':name, 'priority':priority, 'type':movetype, 'category':category,
                'uses':uses, 'potentcy':potentcy, 'accuracy':accuracy, 'nonstandard':nonstandard,
            }
        self.moves = moves


    def load_nature_list(self, csvdata):
        """csvdata -> self.natures"""
        natures = {}
        for row in csvdata:
            row = [cell.strip() for cell in row]
            name, favored_stat, neglected_stat, favored_flavor, disliked_flavor = row

            if not all((name, favored_stat, neglected_stat, favored_flavor, disliked_flavor)):
                raise ValueError(f"Bad nature data on row {row}")
            
            natures[name] = {
                'name':name, 'favored_stat':favored_stat, 'neglected_stat':neglected_stat,
                'favored_flavor':favored_flavor, 'disliked_flavor': disliked_flavor,
            }
        self.natures = natures
                    

        







        


        
