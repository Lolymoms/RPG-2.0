#fully written by claude! I did not make this

"""
balance_calculator.py - balance-testing tool for the text RPG. It balances ENEMIES and SPELLS.

Put this file in the same folder as enemy_data.py and player_data.py, then run:

    python balance_calculator.py

ENEMIES: paste an enemy's stats, e.g.

    ('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic')

(with or without the outer brackets, or as a full  Enemy(...)  line, or the name of an
enemy that already exists in enemy_data.py, like  feral_dog).
You can also run it with the stats as an argument:

    python balance_calculator.py "'Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic'"

Every class (including the Mage, with its spells) is simulated at three player levels:
enemy level - 1, enemy level, enemy level + 1.  The simulated players are "reasonable":
  * Rogue and Hunter pick melee or ranged (or a spell) every turn, whichever does the most damage right now
    (the Rogue's dagger sneak attack on round 1, then usually the bow).
  * Turns follow your game's action rules: a full action costs 1, a bonus action costs 0.5, so a turn is
    "one action", "bonus action + action" or "two bonus actions" (bonus actions always come first).
  * Casters spend mana on the best attack spell they can afford, drink potions / cast healing when low,
    and only use buff spells (Shield, Searing smite) when they make sense.
  * Dodging is ignored completely.

SPELLS: type the name of an OFFENSIVE spell from player_data.py (e.g.  firebolt), a whole  Spell(...)  line, or
        spell: ('Name', 4, 'description', 'Offensive', 6, 'Fire')
to see whether it is too weak / too strong compared with your other attack spells AND your weapons
(sword, dagger, bow), with a suggested fix. Type  spells  to compare every attack spell at once.
Healing and Support spells are not balanced - they can't be measured in damage.
Type  loadouts  to find the best spell picks for every class.
Everything you are likely to want to tweak is in the CONFIG section just below.
"""

import ast
import contextlib
import copy
import io
import itertools
import math
import random
import re
import sys
from collections import namedtuple
from dataclasses import dataclass
from functools import lru_cache
from unittest import mock

import enemy_data
import player_data

# =====================================================================================
# CONFIG  (edit these)
# =====================================================================================

SIMULATIONS = 5000          # fights simulated per class per level. More = smoother numbers, slower.
SEED = None                 # set to a number (e.g. 1) to get repeatable results

# ---- player progression ----
WEAPON_DAMAGE_PER_LEVEL = 2     # +damage on ALL weapons for every level above 1
POTIONS_PER_LEVEL = 1           # a level 2 player starts the fight with 2 healing potions
POTION_HEAL = (4, 8)            # each potion heals randint(a, b)

# Which two stats each class raises at every level-up (any two different ones of:
# 'strength', 'dexterity', 'intelligence', 'melee_skill', 'ranged_skill'). Stats give +2, skills give +1.
# (Intelligence is now on the level-up menu in player_data.py: it gives more mana and better spell hit/damage.)
LEVEL_UP_PICKS = {
    'Barbarian': ['strength', 'melee_skill'],
    'Ranger':    ['dexterity', 'ranged_skill'],
    'Rogue':     ['dexterity', 'melee_skill'],
    'Hunter':    ['strength', 'ranged_skill'],
    'Mage':      ['intelligence', 'dexterity'],
}
# max HP gained per level (copied from Player.add_experience)
HP_PER_LEVEL = {'Barbarian': 12, 'Hunter': 10}
HP_PER_LEVEL_DEFAULT = 8

# ---- player behaviour ----
HEAL_BELOW_FRACTION = 0.35      # drink a potion at/under this fraction of max HP (or if the enemy's
                                # next hit could kill you) - unless you expect to kill the enemy this turn
BARBARIAN_RAGE = 'smart'  # 'immediately' | 'smart' (only if it saves turns) | 'never'
HUNTER_NET = 'smart'            # 'immediately' | 'smart' (only if it improves your attacks) | 'never'
RANGER_MULTIATTACK = 'smart'    # 'immediately' | 'smart' (only if your next attack is a ranged one) | 'never'
HUNTER_NET_ROUNDS = 2           # how many of the Hunter's ATTACKS the net lasts for. In your game the net only counts
                                # down when you pick Attack (hunter_net -= 1 sits inside the Attack branch), and it
                                # ends as soon as it is at or below 0.

# ---- spells ----
# Which spells each class has learned (names from player_data.py). In your game a class learns
# (intelligence // 3) - 1 of them: Barbarian 1, Rogue 2, Ranger 3, Hunter 3, Mage 4.
# Type  loadouts  in the tool to find the best picks, or change these to test other picks.
SPELL_LOADOUTS = {
    'Barbarian': ['Searing smite'],
    'Ranger':    ['Shield', 'Freeze', 'Arcane blast'],
    'Rogue':     ['Searing smite', 'Arcane blast'],
    'Hunter':    ['Poison', 'Shield', 'Earth spike'],
    'Mage':      ['Minor healing', 'Firebolt', 'Poison', 'Arcane blast'],
}
SPELL_DAMAGE_PER_LEVEL = 0      # like WEAPON_DAMAGE_PER_LEVEL, but for spells. 0 = spells never get stronger (as in the game now)
START_MANA_FRACTION = 1.0       # fraction of the mana pool you start each fight with. 1.0 = fresh from a campfire.
                                # Lower it (e.g. 0.5) to model a dungeon where you fight several times between rests.
BUFF_MIN_TURNS = 2              # only cast Shield / Searing smite if the fight should last at least this many more turns
FREEZE_MIN_TURNS = 3            # only cast Freeze if the fight should last at least this many more turns
LOADOUT_SIMS = 300              # fights per class per enemy when the  loadouts  command tries every spell combination

# ---- reaction-time minigames (special attacks) ----
# Your game measures reaction time in hundredths of a second (35 = 0.35s).
# Assumed to be a normal distribution. Measure yourself and tweak!
REACTION_MEAN = 35
REACTION_SD = 10

# ---- fight rating ----
#   DEADLY: win% < DEADLY_BELOW      HARD: win% < HARD_BELOW
#   FAIR:   win% < FAIR_BELOW  or  you lose >= FAIR_HP_LOSS % of your max HP on average
#   EASY:   everything else
DEADLY_BELOW = 50
HARD_BELOW = 80
FAIR_BELOW = 95
FAIR_HP_LOSS = 40

CLASSES = ['Barbarian', 'Ranger', 'Rogue', 'Hunter', 'Mage']   # every class that is simulated, shown and averaged
# The classes used to decide an enemy's TYPE (tank, glass cannon...). Left at the original four so adding the Mage
# doesn't change what kind of enemy something is.
TYPE_CLASSES = ['Barbarian', 'Ranger', 'Rogue', 'Hunter']
MAX_ROUNDS = 30  # safety valve so a stalemate can't loop forever (counts as a loss)

# =====================================================================================
# helpers
# =====================================================================================


def mod(stat):
    return (stat - 10) // 2


def hit_prob(bonus, ac):
    """Chance that d20 + bonus >= ac."""
    return min(20, max(0, 21 - (ac - bonus))) / 20


def type_adjust(dmg, dmg_type, enemy):
    if dmg_type == enemy.vulnerable:
        return dmg * 2
    if dmg_type == enemy.resistant:
        return dmg // 2
    return dmg


@lru_cache(maxsize=None)
def exp_hit(base, stat_mod, armor, dmg_type, vulnerable, resistant, cap=None):
    """Average damage of one successful normal attack (same maths as damage_calc).
    cap = the target's remaining HP: damage past that is wasted, so it isn't counted."""
    lo, hi = int(base * 0.7), int(base * 1.3)
    total = 0
    for r in range(lo, hi + 1):
        d = max(1, r + stat_mod - armor)
        if dmg_type == vulnerable:
            d *= 2
        elif dmg_type == resistant:
            d //= 2
        total += d if cap is None else min(d, cap)
    return total / (hi - lo + 1)


@lru_cache(maxsize=None)
def exp_spell(base, stat_mod, armor, dmg_type, vulnerable, resistant, cap=None):
    """Average damage of one spell that hits (same maths as damage_calc's 'Spell' branch: rolls base..base*1.3)."""
    lo, hi = base, int(base * 1.3)
    total = 0
    for r in range(lo, hi + 1):
        d = max(1, r + stat_mod - armor)
        if dmg_type == vulnerable:
            d *= 2
        elif dmg_type == resistant:
            d //= 2
        total += d if cap is None else min(d, cap)
    return total / (hi - lo + 1)


def _cdf(x):
    return 0.5 * (1 + math.erf((x - REACTION_MEAN) / (REACTION_SD * math.sqrt(2))))


def reaction_bands():
    """P(time <= 35), P(35 < time <= 60), P(60 < time <= 80), P(time > 80). Times are whole numbers."""
    a, b, c = _cdf(36), _cdf(61), _cdf(81)
    return a, b - a, c - b, 1 - c


def roll_reaction(rng):
    return int(max(0, min(100, rng.gauss(REACTION_MEAN, REACTION_SD))))


def turns_needed(hp, phases, tail):
    """Rough number of turns to deal `hp` damage. phases = [(dmg per turn, number of turns), ...],
    then `tail` damage per turn forever after."""
    t = 0
    for d, n in phases:
        for _ in range(n):
            if hp <= 0:
                return t
            hp -= d
            t += 1
    if hp <= 0:
        return t
    if tail <= 0:
        return 999
    return t + math.ceil(hp / tail)


# =====================================================================================
# building players
# =====================================================================================


@dataclass
class Fighter:
    class_name: str
    level: int
    max_hp: int
    strength: int
    dexterity: int
    armor: int
    melee_skill: int
    ranged_skill: int
    intelligence: int           # mana pool = intelligence (like Player.__init__), also the spell bonus
    melee_dmg: int
    melee_type: str
    melee_light: bool
    ranged_dmg: int
    ranged_type: str
    spells: tuple               # Spell objects this fighter knows


def spells_by_name():
    """Every Spell defined in player_data.py, e.g. {'Firebolt': <Spell>, ...}"""
    found = {}
    for value in vars(player_data).values():
        if isinstance(value, player_data.Spell):
            found[value.name] = value
    return found


def weapons_in_game():
    """Every weapon (Item of type Melee or Ranged) defined in player_data.py - sword, dagger, bow..."""
    return [v for v in vars(player_data).values()
            if isinstance(v, player_data.Item) and v.type in ('Melee', 'Ranged')]


def spell_slots(intelligence):
    """How many spells a class may learn - same formula as spell_selection() in main.py."""
    return max(0, (intelligence // 3) - 1)


def default_loadout(class_name):
    known = spells_by_name()
    return tuple(known[name] for name in SPELL_LOADOUTS.get(class_name, []) if name in known)


def check_loadouts():
    """Warns (doesn't stop) if SPELL_LOADOUTS has something your game wouldn't allow."""
    known = spells_by_name()
    book = player_data.spellbook.get(1, {})
    for cls, names in SPELL_LOADOUTS.items():
        if cls not in CLASSES:
            continue
        slots = spell_slots(build_fighter(cls, 1).intelligence)
        allowed = [s.name for s in book.get(cls, [])]
        for name in names:
            if name not in known:
                print(f"(warning: SPELL_LOADOUTS[{cls!r}] has {name!r}, which isn't a spell in player_data.py)")
            elif name not in allowed:
                print(f"(warning: {cls} can't learn {name} - it's not in that class's spellbook)")
        if len(names) > slots:
            print(f"(warning: a {cls} can only learn {slots} spell(s) but SPELL_LOADOUTS lists {len(names)})")


@lru_cache(maxsize=None)
def build_fighter(class_name, level, spells=None):
    """Creates the real level-1 Player from player_data (so class stats stay in sync with your game),
    then applies the modelled level-ups.  `spells` = a tuple of Spell objects, or None for the class's
    default loadout from SPELL_LOADOUTS."""
    def fake_input(prompt=''):
        if 'called' in prompt:
            return 'Tester'
        if 'like to be' in prompt:
            return class_name
        return ''

    # player_selection() changes the shared player_inventory list for some classes. We only want the Player
    # it returns, so put the inventory back exactly as it was (otherwise building a second Ranger crashes).
    saved_inventory = list(player_data.player_inventory)
    try:
        with mock.patch('builtins.input', fake_input), contextlib.redirect_stdout(io.StringIO()):
            p = player_data.player_selection('dev')
    finally:
        player_data.player_inventory[:] = saved_inventory

    for _ in range(level - 1):
        for stat in LEVEL_UP_PICKS[class_name]:
            setattr(p, stat, getattr(p, stat) + (1 if stat.endswith('_skill') else 2))
        p.max_health += HP_PER_LEVEL.get(class_name, HP_PER_LEVEL_DEFAULT)
    bonus = WEAPON_DAMAGE_PER_LEVEL * (level - 1)
    if spells is None:
        spells = default_loadout(class_name)
    return Fighter(
        class_name, level, p.max_health, p.strength, p.dexterity, p.armor,
        p.melee_skill, p.ranged_skill, p.intelligence,
        p.melee.damage + bonus, p.melee.damage_type, p.melee.attack_type == 'Light',
        p.ranged.damage + bonus, p.ranged.damage_type, spells,
    )


# =====================================================================================
# one fight
# =====================================================================================

# What the simulated player knows at the start of an action (see Fight.look)
Look = namedtuple('Look', 'plain_best option best spell spell_val special top turns_left')


class Fight:
    def __init__(self, pl, en, rng):
        self.pl, self.en, self.rng = pl, en, rng
        self.hp = pl.max_hp
        self.str, self.dex = pl.strength, pl.dexterity     # "live" values (rage changes these)
        self.n_enemies = max(1, int(en.amount))      # swarms: several copies of the same enemy
        self.e_hps = [en.health] * self.n_enemies
        self.e_special = [en.special_attack_available] * self.n_enemies
        self.e_dex = en.dexterity                    # (the net halves dex for the whole group)
        self.potions = pl.level * POTIONS_PER_LEVEL
        self.special_ready = True
        self.class_ready = True
        self.class_used = False
        self.rage_counter = 0
        self.ranger_bonus = False      # the Ranger's one extra arrow is waiting for the next ranged attack
        self.net_counter = 0           # = hunter_net in encounter(): counts down once per Attack-menu action
        self.dmg_taken = 0
        self.potions_used = 0
        self.rounds = 0
        self.mix = {'melee': 0, 'ranged': 0, 'spell': 0}     # which kind of attack action was chosen
        # spells
        self.mana = int(pl.intelligence * START_MANA_FRACTION)
        self.mana_used = 0
        self.shield = False            # shield spell is up
        self.smite = 0                 # melee hits left with searing smite
        self.skip = 0                  # enemy turns still skipped (freeze)
        self.freeze_pending = False    # freeze was cast this round: the enemy still attacks once, THEN it's frozen
        self.p_spell_bonus = mod(pl.intelligence) + pl.level // 2
        self.e_melee_bonus = mod(en.strength) + en.level // 2
        self.e_ranged_bonus = mod(en.dexterity) + en.level // 2
        self.e_ac_start = 10 + mod(en.dexterity)

    # encounter() recalculates these whenever rage starts or ends, so they follow the "live" strength/dexterity
    @property
    def p_melee_bonus(self):
        return mod(self.str) + self.pl.level // 2

    @property
    def p_ranged_bonus(self):
        return mod(self.dex) + self.pl.level // 2

    @property
    def p_ac(self):
        return 10 + mod(self.dex)

    @property
    def e_hp(self):
        """Total HP left across all enemies."""
        return sum(self.e_hps)

    def damage_target(self, dmg):
        """Damage goes to the first enemy still standing."""
        for i, h in enumerate(self.e_hps):
            if h > 0:
                self.e_hps[i] = max(0, h - dmg)
                return

    # ---------- expectations used by the "rational player" ----------
    def enemy_ac(self):
        return 10 + mod(self.e_dex)        # the net halves e_dex, which lowers this

    def attack_count(self, kind):
        pl = self.pl
        if kind == 'melee':
            return (2 if pl.melee_skill >= 5 else 1) + (1 if pl.melee_light else 0)
        return (2 if pl.ranged_skill >= 5 else 1) + (1 if self.ranger_bonus else 0)

    def can_sneak(self):
        return self.pl.class_name == 'Rogue' and self.pl.melee_light

    def target_hp(self):
        """HP of the enemy that would take the next hit."""
        for h in self.e_hps:
            if h > 0:
                return h
        return 0

    def hit_exp(self, kind, capped=False):
        pl, en = self.pl, self.en
        cap = self.target_hp() if capped else None
        if kind == 'melee':
            return exp_hit(pl.melee_dmg, mod(self.str), en.armor, pl.melee_type, en.vulnerable, en.resistant, cap)
        return exp_hit(pl.ranged_dmg, mod(self.dex), en.armor, pl.ranged_type, en.vulnerable, en.resistant, cap)

    def option_values(self, capped=False):
        """Average damage of each way to attack with a weapon. capped=True ignores damage beyond the target's
        remaining HP - that's how the simulated player chooses (a 12-damage spell is no better than a 4-damage
        arrow on a 3 HP enemy)."""
        ac = self.enemy_ac()
        vals = {
            'Melee': self.attack_count('melee') * hit_prob(self.p_melee_bonus, ac) * self.hit_exp('melee', capped),
            'Ranged': self.attack_count('ranged') * hit_prob(self.p_ranged_bonus, ac) * self.hit_exp('ranged', capped),
        }
        if self.can_sneak() and self.rounds <= 1:       # in the game the sneak attack is only offered in round 1
            first = hit_prob(mod(self.dex), ac + self.en.level) * (self.hit_exp('melee', capped) * 3)    # and it does x3 damage
            rest = (self.attack_count('melee') - 1) * hit_prob(self.p_melee_bonus, ac) * self.hit_exp('melee', capped)
            vals['Sneak attack'] = first + rest
        return vals

    def special_value(self, capped=False):
        base = self.pl.melee_dmg * 2
        mults = (1.25, 1.0, 0.75, 0.5)
        cap = self.target_hp() if capped else 10 ** 9
        return sum(p * min(cap, int(max(1, base * m - self.en.armor))) for p, m in zip(reaction_bands(), mults))

    # ---------- spell expectations ----------
    def spell_base(self, spell):
        """Base damage of a spell for this player's level (SPELL_DAMAGE_PER_LEVEL, like weapons)."""
        return spell.damage + SPELL_DAMAGE_PER_LEVEL * (self.pl.level - 1)

    def can_cast(self, spell):
        return spell.mana_cost <= self.mana

    def spell_named(self, name):
        for s in self.pl.spells:
            if s.name == name:
                return s
        return None

    def spell_value(self, spell, capped=False):
        """Average damage of one cast of an attack spell (hit chance x damage)."""
        cap = self.target_hp() if capped else None
        dmg = exp_spell(self.spell_base(spell), mod(self.pl.intelligence), self.en.armor,
                        spell.damage_type, self.en.vulnerable, self.en.resistant, cap)
        return hit_prob(self.p_spell_bonus, self.enemy_ac()) * dmg

    def best_damage_spell(self, capped=False, bonus=False):
        """The affordable attack spell with the highest average damage, and that damage.
        bonus=False looks at spells that cost a full action, bonus=True at bonus-action ones.
        If two spells are equally good the cheaper one wins (no point wasting mana)."""
        best, val = None, 0
        for s in self.pl.spells:
            if s.spell_type != 'Offensive' or (s.action == 'Bonus action') != bonus or not self.can_cast(s):
                continue
            v = self.spell_value(s, capped)
            if v > val + 1e-9 or (best is not None and abs(v - val) <= 1e-9 and s.mana_cost < best.mana_cost):
                best, val = s, v
        return best, val

    def enemy_action(self, i=0):
        en = self.en
        if en.boss and self.e_special[i]:
            return 'special'
        if en.boss and en.ranged > 0:
            return 'ranged'
        if en.boss:
            return 'melee'
        if self.e_hps[i] < self.hp and en.ranged > 0:
            return 'ranged'
        return 'melee'

    def enemy_max_hit(self):
        """Worst case damage if every enemy still standing hits for its maximum."""
        en, total = self.en, 0
        for i, h in enumerate(self.e_hps):
            if h <= 0:
                continue
            act = self.enemy_action(i)
            if act == 'special':
                total += max(1, int(en.melee * 2) - self.pl.armor)
                continue
            base, m = (en.ranged, mod(self.e_dex)) if act == 'ranged' else (en.melee, mod(en.strength))
            total += max(1, int(base * 1.3) + m - self.pl.armor)
        return total

    # ---------- player decisions ----------
    def best_attack(self, capped=False):
        vals = self.option_values(capped)
        name = max(vals, key=vals.get)
        return name, vals[name]

    def heal_source(self):
        """('spell', Spell) or ('potion', None) or None. A healing BONUS-action spell comes first: mana comes back
        at the campfire, potions don't."""
        for s in self.pl.spells:
            if s.spell_type == 'Healing' and s.action == 'Bonus action' and self.can_cast(s):
                return ('spell', s)
        if self.potions > 0:
            return ('potion', None)
        return None

    def action_heal_spell(self):
        """A healing spell that costs a FULL action (none exist yet), if one is affordable."""
        for s in self.pl.spells:
            if s.spell_type == 'Healing' and s.action != 'Bonus action' and self.can_cast(s):
                return s
        return None

    def want_heal(self, top):
        if self.hp >= self.pl.max_hp or self.heal_source() is None:
            return False
        if self.hp > max(HEAL_BELOW_FRACTION * self.pl.max_hp, self.enemy_max_hit()):
            return False
        return top < self.e_hp          # if we'll probably finish it this turn, just attack

    def want_class_action(self, plain_best):
        """Is the class action (a bonus action) worth using right now?"""
        if not self.class_ready:
            return False
        cls, e = self.pl.class_name, self.e_hp
        base_turns = turns_needed(e, [], plain_best)
        if cls == 'Barbarian':
            if BARBARIAN_RAGE == 'never':
                return False
            if BARBARIAN_RAGE == 'immediately':
                return True
            old = (self.str, self.dex)
            self.str += 3
            self.dex -= 3
            raged = self.best_attack()[1]
            self.str, self.dex = old
            # rage lasts this round and the next two
            return turns_needed(e, [(raged, 3)], plain_best) < base_turns
        if cls == 'Ranger':
            if RANGER_MULTIATTACK == 'never':
                return False
            if RANGER_MULTIATTACK == 'immediately':
                return True
            # the extra arrow is used up by the next RANGED attack, so only cast it when that's what we're about to do
            self.ranger_bonus = True
            option = self.best_attack()[0]
            self.ranger_bonus = False
            return option == 'Ranged' and base_turns > 1
        if cls == 'Hunter':
            if HUNTER_NET == 'never':
                return False
            if HUNTER_NET == 'immediately':
                return True
            old = self.e_dex
            self.e_dex //= 2
            netted = self.best_attack()[1]
            self.e_dex = old
            return netted > plain_best and base_turns > 1
        return False    # Rogue's class action only reveals info - no combat effect (and the Mage has none yet)

    def pick_buff(self, option, best, spell_val, turns_left):
        """A bonus-action buff spell (Shield / Searing smite) worth casting this turn, or None."""
        if turns_left < BUFF_MIN_TURNS:
            return None             # the fight is nearly over - don't waste mana
        attack_costs = [s.mana_cost for s in self.pl.spells if s.spell_type == 'Offensive']
        reserve = min(attack_costs) if attack_costs else 0   # never spend the mana you need for your next attack spell
        for s in self.pl.spells:
            if not self.can_cast(s) or self.mana - s.mana_cost < reserve:
                continue
            if s.name == 'Shield' and not self.shield:
                return s
            if s.name == 'Searing smite' and self.smite == 0 and option == 'Melee' and best >= spell_val:
                return s
        return None

    def want_freeze(self, turns_left):
        s = self.spell_named('Freeze')
        if s is None or not self.can_cast(s) or self.skip > 0 or self.freeze_pending:
            return None
        return s if turns_left >= FREEZE_MIN_TURNS else None

    def look(self):
        """Everything the simulated player works out before choosing an action."""
        _, plain_best = self.best_attack()                       # un-capped: used to judge class actions
        option, best = self.best_attack(capped=True)             # capped: used to choose what to do
        spell, spell_val = self.best_damage_spell(capped=True)
        special = self.special_value(capped=True) if self.special_ready else 0
        top = max(best, spell_val, special)
        turns_left = turns_needed(self.e_hp, [], max(plain_best, top))
        return Look(plain_best, option, best, spell, spell_val, special, top, turns_left)

    # ---------- actions ----------
    def use_class_action(self):
        self.class_ready = False
        self.class_used = True
        cls = self.pl.class_name
        if cls == 'Barbarian':
            self.str += 3
            self.dex -= 3
            self.rage_counter = 3
        elif cls == 'Ranger':
            self.ranger_bonus = True
        elif cls == 'Hunter':
            self.e_dex //= 2
            self.net_counter = HUNTER_NET_ROUNDS

    def cast(self, spell):
        """Same rules as Spell.cast_spell + the effects in encounter()."""
        rng, pl, en = self.rng, self.pl, self.en
        self.net_counter -= 1          # every spell is cast from the Attack menu, which is where hunter_net counts down
        self.mana -= spell.mana_cost
        self.mana_used += spell.mana_cost
        if spell.spell_type == 'Healing':
            self.hp = min(pl.max_hp, self.hp + rng.randint(*spell.healing))
        elif spell.damage > 0:
            self.mix['spell'] += 1
            if rng.randint(1, 20) + self.p_spell_bonus >= self.enemy_ac():
                base = self.spell_base(spell)
                d = max(1, rng.randint(base, int(base * 1.3)) + mod(pl.intelligence) - en.armor)
                self.damage_target(type_adjust(d, spell.damage_type, en))
                if spell.name == 'Freeze':
                    self.freeze_pending = True
        elif spell.name == 'Shield':
            self.shield = True
        elif spell.name == 'Searing smite':
            self.smite = 2

    def do_heal(self):
        kind, spell = self.heal_source()
        if kind == 'spell':
            self.cast(spell)
        else:
            self.potions -= 1
            self.potions_used += 1
            self.hp = min(self.pl.max_hp, self.hp + self.rng.randint(*POTION_HEAL))

    def player_hit_damage(self, kind):
        pl, en = self.pl, self.en
        if kind == 'melee':
            base, m, t = pl.melee_dmg, mod(self.str), pl.melee_type
        else:
            base, m, t = pl.ranged_dmg, mod(self.dex), pl.ranged_type
        d = max(1, self.rng.randint(int(base * 0.7), int(base * 1.3)) + m - en.armor)
        return type_adjust(d, t, en)

    def attack(self, option):
        pl, en, rng = self.pl, self.en, self.rng
        self.net_counter -= 1          # picking Attack is what counts the Hunter's net down
        ac = self.enemy_ac()
        if option == 'Special attack':
            self.mix['melee'] += 1
            t = roll_reaction(rng)
            mult = 1.25 if t <= 35 else 1 if t <= 60 else 0.75 if t <= 80 else 0.5
            self.damage_target(int(max(1, pl.melee_dmg * 2 * mult - en.armor)))
            self.special_ready = False
            return
        kind = 'ranged' if option == 'Ranged' else 'melee'
        self.mix[kind] += 1
        bonus = self.p_ranged_bonus if kind == 'ranged' else self.p_melee_bonus
        for i in range(self.attack_count(kind)):
            if self.e_hp <= 0:
                break
            if option == 'Sneak attack' and i == 0:
                if rng.randint(1, 20) + mod(self.dex) >= ac + en.level:
                    self.damage_target(self.player_hit_damage('melee') * 3)
            elif rng.randint(1, 20) + bonus >= ac:
                dmg = self.player_hit_damage(kind)
                if option == 'Melee' and self.smite > 0:      # searing smite: x1.5, counts hits
                    dmg = int(dmg * 1.5)
                    self.smite -= 1
                self.damage_target(dmg)
        if kind == 'ranged':
            self.ranger_bonus = False      # the Ranger's extra arrow was part of that volley; it's used up

    def enemy_turn(self):
        en, rng, pl = self.en, self.rng, self.pl
        if self.skip > 0:           # frozen
            self.skip -= 1
            return
        for i, h in enumerate(self.e_hps):
            if h <= 0:
                continue
            act = self.enemy_action(i)
            dmg = 0
            if act == 'special':
                t = roll_reaction(rng)
                if self.shield:
                    t //= 2
                    self.shield = False
                mult = 0.5 if t <= 35 else 0.75 if t <= 60 else 1
                dmg = int(max(1, en.melee * 2 * mult - pl.armor))
                self.e_special[i] = False
            elif act == 'melee':
                if rng.randint(1, 20) + self.e_melee_bonus >= self.p_ac:
                    dmg = max(1, rng.randint(int(en.melee * 0.7), int(en.melee * 1.3)) + mod(en.strength) - pl.armor)
                    if self.shield:
                        dmg = int(dmg * 0.75)
                        self.shield = False
            else:
                if rng.randint(1, 20) + self.e_ranged_bonus >= self.p_ac:
                    dmg = max(1, rng.randint(int(en.ranged * 0.7), int(en.ranged * 1.3)) + mod(self.e_dex) - pl.armor)
                    if self.shield:
                        dmg = int(dmg * 0.75)
                        self.shield = False
            self.hp -= dmg
            self.dmg_taken += dmg
            if self.hp <= 0:
                return

    # ---------- one turn of the player ----------
    def pick_bonus(self, sit, number):
        """The next bonus action (each costs 0.5), or None. number = how many bonus actions were already taken."""
        if number == 0:
            if self.want_heal(sit.top):
                return ('heal', None)
            if self.want_class_action(sit.plain_best):
                return ('class', None)
            buff = self.pick_buff(sit.option, sit.best, sit.spell_val, sit.turns_left)
            if buff:
                return ('spell', buff)
            spell, _ = self.best_damage_spell(capped=True, bonus=True)      # a bonus-action attack spell, if one ever exists
            if spell is not None:
                return ('spell', spell)
            return None
        # A SECOND bonus action ends the turn with no attack, so it's only worth it to avoid dying: heal again.
        if (self.heal_source() is not None and self.hp < self.pl.max_hp
                and self.hp <= self.enemy_max_hit() and sit.top < self.e_hp):
            return ('heal', None)
        return None

    def take_turn(self):
        """Your game's turn: a full action costs 1 and a bonus action 0.5, and the turn ends when you run out.
        So a turn is one action, a bonus action THEN an action, or two bonus actions (bonus actions come first -
        after a full action you're out of points). The simulated player follows exactly that."""
        points = 1.0
        taken = 0
        while points > 0 and taken < 2:
            act = self.pick_bonus(self.look(), taken)
            if act is None:
                break
            kind, spell = act
            if kind == 'heal':
                self.do_heal()
            elif kind == 'class':
                self.use_class_action()
            else:
                self.cast(spell)
            taken += 1
            points -= 0.5
            if self.e_hp <= 0:
                return
        if points <= 0:
            return                      # two bonus actions used the whole turn

        # ----- full action -----
        sit = self.look()               # the bonus action may have changed things (smite, rage, net...), so look again
        heal_spell = self.action_heal_spell()
        if heal_spell and self.hp <= self.enemy_max_hit() and sit.top < self.e_hp:
            self.cast(heal_spell)
            return
        freeze = self.want_freeze(sit.turns_left)
        if freeze:
            self.cast(freeze)
            return
        if sit.spell is not None and sit.spell_val > max(sit.best, sit.special):
            self.cast(sit.spell)
        elif self.special_ready and sit.special >= sit.best:
            self.attack('Special attack')
        else:
            self.attack(sit.option)

    # ---------- the fight ----------
    def run(self):
        pl, en = self.pl, self.en
        while self.rounds < MAX_ROUNDS:
            self.rounds += 1
            # start-of-round bookkeeping, same order as encounter()
            self.rage_counter -= 1
            if self.net_counter <= 0:
                self.e_dex = en.dexterity          # the net has run out (<= 0, like your game: it can't be skipped over)
            if self.rage_counter == 0:
                self.str, self.dex = pl.strength, pl.dexterity

            self.take_turn()
            if self.e_hp <= 0:
                return True
            self.enemy_turn()
            if self.freeze_pending:         # the enemy gets one last attack, then it's frozen for 2 turns
                self.skip = 2
                self.freeze_pending = False
            if self.hp <= 0:
                return False
        return False


# =====================================================================================
# enemy types + tuning suggestions
# =====================================================================================

# How an enemy is judged (all measured against the four classes at the enemy's own level):
#   D = rounds an average player needs to kill ONE of this enemy IF EVERY ATTACK LANDED
#       (HP + armor only, so dexterity is judged separately by P)       (higher = tougher)
#   L = rounds this enemy needs to kill an average player           (higher = weaker hitter)
#   P = average % chance the players' best weapon hits it           (lower = harder to hit)
#   N = how many of them there are (the 3rd stat, "amount")
# Edit the numbers below to change what counts as which type.
#   Each type has a (low, high) range for D, L, P, N. An enemy that fits a type's ranges is that type,
#   and the tuner will never push a stat outside the type's ranges (that would change its identity).
# Types are checked in this order; the first one that fits wins. 'Balanced' is the fallback.
ENEMY_TYPES = {
    #                D range      L range      P range       N range
    'Swarm':        dict(D=(0, 1.5),  L=(6, 99),  P=(0, 100), N=(2, 12),
                         buff=['amount', 'damage', 'hp'],         nerf=['amount', 'damage', 'hp'],
                         blurb="weak alone, dangerous in numbers"),
    'Glass cannon': dict(D=(0, 2.0),  L=(2.0, 5.5), P=(0, 100), N=(1, 1),
                         buff=['damage', 'hp', 'dex'],            nerf=['damage', 'hp', 'dex'],
                         blurb="low HP, hits very hard"),
    'Sneaky':       dict(D=(0, 2.5),  L=(5.5, 14), P=(30, 58), N=(1, 1),
                         buff=['dex', 'damage', 'hp'],            nerf=['dex', 'damage', 'hp'],
                         blurb="hard to hit, moderate damage, low HP"),
    'Tank':         dict(D=(3.5, 9),  L=(9, 99),  P=(0, 100), N=(1, 1),
                         buff=['hp', 'armor', 'damage'],          nerf=['hp', 'armor', 'damage'],
                         blurb="lots of HP/armor, hits fairly weakly"),
    'Balanced':     dict(D=(1.5, 6),  L=(4, 12),  P=(0, 100), N=(1, 1),
                         buff=['damage', 'hp', 'armor'],          nerf=['damage', 'hp', 'armor'],
                         blurb="no real strength or weakness"),
}
# While tuning a Balanced enemy, alternate between its levers instead of finishing one first.
INTERLEAVE = {'Balanced'}
# How far the tuner is allowed to push the tweakable stats
ARMOR_CAP = 4
DEX_CAP = 22            # enemy dexterity won't be pushed above this (AC 16)
TUNE_TARGET = 'FAIR'        # the at-level rating the tuner aims for
TUNE_SIMS = 800             # fights per class per tuning step (higher = slower, less noisy)
TUNE_MAX_STEPS = 60


def _avg(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def enemy_metrics(en):
    """Returns (D, L, P, N) for an enemy against the four classes at the enemy's own level."""
    rng = random.Random(0)
    dpr, hit, hp, foe = [], [], [], []
    bands = reaction_bands()
    for cls in TYPE_CLASSES:
        pl = build_fighter(cls, en.level)
        f = Fight(pl, en, rng)
        vals = {k: v for k, v in f.option_values().items() if k in ('Melee', 'Ranged')}
        kind = max(vals, key=vals.get)
        k = kind.lower()
        dpr.append(f.attack_count(k) * f.hit_exp(k))
        hit.append(hit_prob(f.p_ranged_bonus if kind == 'Ranged' else f.p_melee_bonus, f.e_ac_start))
        hp.append(pl.max_hp)
        # what one enemy does to this class per round
        if en.ranged > en.melee:
            base, m, bonus = en.ranged, mod(en.dexterity), f.e_ranged_bonus
        else:
            base, m, bonus = en.melee, mod(en.strength), f.e_melee_bonus
        lo, hi = int(base * 0.7), int(base * 1.3)
        avg_hit = _avg(max(1, r + m - pl.armor) for r in range(lo, hi + 1))
        normal = hit_prob(bonus, f.p_ac) * avg_hit
        foe.append((normal, pl.armor))
    d_rounds = en.health / _avg(dpr)
    foe_dpr = []
    for (normal, armor) in foe:
        if en.special_attack != 'None':
            special = sum(p * max(1, int(en.melee * 2 * mult - armor)) for p, mult in zip(bands[:3], (0.5, 0.75, 1.0)))
            special += bands[3] * max(1, int(en.melee * 2 - armor))
            rounds = max(1.0, d_rounds)
            foe_dpr.append((special + (rounds - 1) * normal) / rounds)
        else:
            foe_dpr.append(normal)
    l_rounds = _avg(hp) / max(0.01, _avg(foe_dpr))
    return d_rounds, l_rounds, 100 * _avg(hit), max(1, int(en.amount))


def _fits(spec, D, L, P, N):
    return (spec['D'][0] <= D <= spec['D'][1] and spec['L'][0] <= L <= spec['L'][1]
            and spec['P'][0] <= P <= spec['P'][1] and spec['N'][0] <= N <= spec['N'][1])


def classify(en):
    D, L, P, N = enemy_metrics(en)
    if N > 1:
        return 'Swarm'
    for name, spec in ENEMY_TYPES.items():
        if name != 'Swarm' and name != 'Balanced' and _fits(dict(spec, N=(1, 99)), D, L, P, N):
            return name
    if D <= ENEMY_TYPES['Swarm']['D'][1] and L >= ENEMY_TYPES['Swarm']['L'][0]:
        return 'Swarm'      # a lone swarm unit
    return 'Balanced'


def apply_lever(en, lever, direction):
    """Returns (new enemy, description of the change) or None if the lever can't move that way."""
    sign = 1 if direction == 'buff' else -1
    new = copy.deepcopy(en)
    if lever == 'damage':
        attr = 'ranged' if en.ranged > en.melee else 'melee'
        old = getattr(en, attr)
        if old + sign < 1:
            return None
        setattr(new, attr, old + sign)
        return new, (f"{attr} damage", old, old + sign)
    if lever == 'hp':
        step = max(1, round(en.health * 0.1))
        if en.health + sign * step < 1:
            return None
        new.health = en.health + sign * step
        return new, ("health", en.health, new.health)
    if lever == 'armor':
        if not 0 <= en.armor + sign <= ARMOR_CAP:
            return None
        new.armor = en.armor + sign
        return new, ("armor", en.armor, new.armor)
    if lever == 'dex':
        if not 1 <= en.dexterity + 2 * sign <= max(DEX_CAP, en.dexterity):
            return None
        new.dexterity = en.dexterity + 2 * sign
        new.max_dexterity = new.dexterity
        return new, ("dexterity", en.dexterity, new.dexterity)
    if lever == 'amount':
        if not 1 <= en.amount + sign <= 12:
            return None
        new.amount = en.amount + sign
        return new, ("amount", en.amount, new.amount)
    return None


METRIC_FOR = {'damage': 'L', 'hp': 'D', 'armor': 'D', 'dex': 'P', 'amount': 'N'}


def _allowed(lever, cur, new, spec):
    """May this lever step be taken without breaking the enemy's type?"""
    key = METRIC_FOR[lever]
    idx = 'DLPN'.index(key)
    lo, hi = spec[key]
    a, b = cur[idx], new[idx]
    if lo <= b <= hi:
        return True
    dist = lambda x: max(lo - x, x - hi, 0)
    return dist(b) < dist(a)          # already out of range: only allow moves back toward it


def at_level_result(en, n, seed=12345):
    rng = random.Random(seed)
    wins, losses = [], []
    for cls in CLASSES:
        r = simulate(build_fighter(cls, en.level), en, n, rng)
        wins.append(r['win'])
        losses.append(r['dmg_pct'])
    w, l = _avg(wins), _avg(losses)
    return w, l, rate(w, l)


def tune(en, etype, rating, n=None, relaxed=False):
    """Finds the smallest change(s) that move the at-level fight to TUNE_TARGET, using the type's lever order.
    Returns (list of changes, resulting enemy, resulting (win, hp loss, rating)) or None."""
    n = n or TUNE_SIMS
    spec = dict(ENEMY_TYPES[etype])
    if relaxed:
        spec.update(D=(0, 99), L=(0, 99), P=(0, 100), N=(1, 12))
    direction = 'buff' if rating == 'EASY' else 'nerf'
    levers = list(spec[direction])
    if etype != 'Swarm':
        levers = [x for x in levers if x != 'amount']
    cur, changes, notes = copy.deepcopy(en), [], []
    cur_m = enemy_metrics(cur)
    i = 0
    for _ in range(TUNE_MAX_STEPS):
        if not levers:
            break
        lever = levers[i % len(levers)] if etype in INTERLEAVE else levers[0]
        step = apply_lever(cur, lever, direction)
        if step is None:
            levers.remove(lever)
            continue
        if not _allowed(lever, cur_m, enemy_metrics(step[0]), spec):
            notes.append(lever)
            levers.remove(lever)
            continue
        i += 1
        prev = cur
        cur, (what, old, new_val) = step[0], step[1]
        cur_m = enemy_metrics(cur)
        # merge consecutive steps of the same stat into one line
        for j, c in enumerate(changes):
            if c[0] == what:
                changes[j] = (what, c[1], new_val)
                break
        else:
            changes.append((what, old, new_val))
        w, l, r = at_level_result(cur, n)
        if r == TUNE_TARGET:
            return changes, cur, (w, l, r), notes
        overshot = (direction == 'buff' and r in ('HARD', 'DEADLY')) or (direction == 'nerf' and r == 'EASY')
        if overshot:
            # the last step jumped over the target - back it out, call it close enough
            return changes, cur, (w, l, r), notes
    return changes, cur, (at_level_result(cur, n) if changes else None), notes


# =====================================================================================
# running a batch + reporting
# =====================================================================================


def rate(win_pct, hp_loss_pct):
    if win_pct < DEADLY_BELOW:
        return 'DEADLY'
    if win_pct < HARD_BELOW:
        return 'HARD'
    if win_pct < FAIR_BELOW or hp_loss_pct >= FAIR_HP_LOSS:
        return 'FAIR'
    return 'EASY'


def simulate(pl, en, n, rng):
    wins = rounds = dmg = potions = used = mana = 0
    mix = {'melee': 0, 'ranged': 0, 'spell': 0}
    for _ in range(n):
        f = Fight(pl, en, rng)
        wins += f.run()
        rounds += f.rounds
        dmg += f.dmg_taken
        potions += f.potions_used
        used += f.class_used
        mana += f.mana_used
        for k in mix:
            mix[k] += f.mix[k]
    total_attacks = max(1, sum(mix.values()))
    probe = Fight(pl, en, rng)
    vals = {k: v for k, v in probe.option_values().items() if k in ('Melee', 'Ranged')}
    kind = max(vals, key=vals.get)
    you_hit = hit_prob(probe.p_ranged_bonus if kind == 'Ranged' else probe.p_melee_bonus, probe.e_ac_start)
    spell, spell_val = probe.best_damage_spell()
    if spell is not None and spell_val > vals[kind]:       # casters: their best attack is a spell
        kind = 'Spell'
        you_hit = hit_prob(probe.p_spell_bonus, probe.e_ac_start)
    foe_bonus = probe.e_ranged_bonus if en.ranged > 0 and en.boss else probe.e_melee_bonus
    foe_hit = hit_prob(foe_bonus, probe.p_ac)
    win_pct = 100 * wins / n
    avg_dmg = dmg / n
    return {
        'win': win_pct, 'dmg': avg_dmg, 'dmg_pct': 100 * avg_dmg / pl.max_hp, 'rounds': rounds / n,
        'potions': potions / n, 'you_hit': 100 * you_hit, 'foe_hit': 100 * foe_hit,
        'weapon': kind[0], 'hp': pl.max_hp, 'ability': 100 * used / n, 'mana': mana / n,
        'mix': tuple(100 * mix[k] / total_attacks for k in ('melee', 'ranged', 'spell')),
    }


LEVER_TEXT = {
    'damage': "damage", 'hp': "HP", 'armor': "armor", 'dex': "dexterity (harder to hit)",
    'amount': "how many there are",
}


def report(enemy, n=None, rng=None, forced_type=None):
    n = n or SIMULATIONS
    rng = rng or random.Random(SEED)
    en = enemy
    traits = []
    if en.boss:
        traits.append('boss')
    if en.special_attack != 'None':
        traits.append(f"special: {en.special_attack}")
    if en.vulnerable != 'None':
        traits.append(f"weak to {en.vulnerable}")
    if en.resistant != 'None':
        traits.append(f"resists {en.resistant}")
    if en.amount > 1:
        traits.append(f"x{en.amount} (swarm)")
    print()
    print('=' * 82)
    print(f"{en.name}  (level {en.level})  HP {en.health}  AC {10 + mod(en.dexterity)}  armor {en.armor}  "
          f"STR {en.strength}  melee {en.melee}  ranged {en.ranged}" + (f"  [{', '.join(traits)}]" if traits else ''))
    print(f"{n} fights per class per level | players start at full HP/abilities with "
          f"{POTIONS_PER_LEVEL} potion(s) per level")
    print('=' * 82)
    summary = []
    at_level = None
    for label, delta in (('UNDERLEVELED', -1), ('AT LEVEL', 0), ('OVERLEVELED', 1)):
        lvl = en.level + delta
        print(f"\n{label} - player level {lvl}")
        if lvl < 1:
            print("  (not possible - the player can't be below level 1)")
            summary.append((label, None))
            continue
        print(f"  {'Class':<10}{'HP':>4}  {'Win %':>6}  {'Dmg taken':>15}  {'Rounds':>6}  {'Potions':>7}  "
              f"{'Hit% you/foe':>14}  {'Attacks M/R/Sp%':>15}  {'Ability%':>8}  {'Mana':>4}  Rating")
        rows = []
        for cls in CLASSES:
            r = simulate(build_fighter(cls, lvl), en, n, rng)
            rows.append(r)
            rating = rate(r['win'], r['dmg_pct'])
            print(f"  {cls:<10}{r['hp']:>4}  {r['win']:>6.1f}  {r['dmg']:>7.1f} ({r['dmg_pct']:>3.0f}%)  "
                  f"{r['rounds']:>6.1f}  {r['potions']:>7.1f}  "
                  f"{r['you_hit']:>5.0f}/{r['foe_hit']:<3.0f} ({r['weapon']})  "
                  f"{r['mix'][0]:>4.0f}/{r['mix'][1]:>3.0f}/{r['mix'][2]:>3.0f}  {r['ability']:>8.0f}  {r['mana']:>4.0f}  {rating}")
        avg_win = sum(r['win'] for r in rows) / len(rows)
        avg_loss = sum(r['dmg_pct'] for r in rows) / len(rows)
        overall = rate(avg_win, avg_loss)
        print(f"  {'Average':<10}{'':>4}  {avg_win:>6.1f}  {'':>7} ({avg_loss:>3.0f}%)  "
              f"{sum(r['rounds'] for r in rows) / len(rows):>6.1f}  {'':>7}  {'':>14}  {'':>15}  {'':>8}  {'':>4}  {overall}")
        summary.append((label, overall))
        if delta == 0:
            at_level = (avg_win, avg_loss, overall)
    print()
    print("Overall: " + "  |  ".join(f"{l.title()}: {o if o else 'n/a'}" for l, o in summary))
    print("(Hit%: M/R/S = best attack for that class: melee, ranged or a spell. Boss specials always hit and aren't in 'foe'.)")
    print("(Attacks M/R/Sp% = share of attack actions that were melee (incl. sneak/special attacks) / ranged / damage spells -")
    print(" the Rogue and Hunter switch between them each turn, whichever does the most damage.)")
    print("(Ability% = how often the class action was worth using. Mana = average mana spent. Dmg taken is raw, before potions.)")
    print("(Spells used: " + "; ".join(f"{c}: {', '.join(s.name for s in default_loadout(c)) or 'none'}" for c in CLASSES) + ")")
    suggest(en, at_level, forced_type)


def suggest(en, at_level, forced_type=None):
    D, L, P, N = enemy_metrics(en)
    etype = forced_type or classify(en)
    spec = ENEMY_TYPES[etype]
    print()
    print('-' * 82)
    print(f"ENEMY TYPE: {etype} - {spec['blurb']}" + ("  (set by you)" if forced_type else "  (auto-detected)"))
    each = " each" if N > 1 else ""
    print(f"  An average player needs ~{D:.1f} rounds to kill it{each} if every attack landed; it needs ~{L:.1f} rounds{each} to "
          f"kill an average player; players hit it ~{P:.0f}% of the time." + (f" There are {N}." if N > 1 else ""))
    if not forced_type:
        print("  (Wrong type? Put the type first, e.g.   tank: ('Name', 2, 1, ...)   Types: "
              + ", ".join(t.lower() for t in ENEMY_TYPES) + ")")
    win, loss, rating = at_level
    verdict = {'EASY': 'too easy', 'FAIR': 'on target', 'HARD': 'too hard', 'DEADLY': 'too deadly'}[rating]
    print(f"AT-LEVEL FIGHT: {rating} (avg win {win:.0f}%, avg HP loss {loss:.0f}%) - {verdict}.")
    if rating == TUNE_TARGET:
        print("No changes suggested.")
        return
    direction = 'buff' if rating == 'EASY' else 'nerf'
    print(f"Working out the smallest {'buff' if direction == 'buff' else 'nerf'}... ", end='', flush=True)
    changes, new_en, result, notes = tune(en, etype, rating)
    print()
    _print_changes(etype, direction, changes, result, notes, relaxed=False)
    if not result or result[2] != TUNE_TARGET:
        print(f"  Staying a {etype} isn't enough on its own. If you're willing to change its identity:")
        changes2, new2, result2, _ = tune(en, etype, rating, relaxed=True)
        _print_changes(etype, direction, changes2, result2, [], relaxed=True)


def _print_changes(etype, direction, changes, result, notes, relaxed):
    word = 'raise' if direction == 'buff' else 'lower'
    if relaxed:
        head = "  Without keeping the type:"
    elif result and result[2] == TUNE_TARGET:
        head = f"SUGGESTED CHANGES (keeps it a {etype}):"
    else:
        head = f"BEST I CAN DO while staying a {etype}:"
    print(head)
    if not changes:
        print("  (nothing to change within the type's limits)")
    for i, (what, old, new) in enumerate(changes, 1):
        print(f"  {i}. {word.capitalize()} {what}: {old} -> {new}")
    for lever in notes:
        print(f"  - {LEVER_TEXT[lever].capitalize()} was already at the limit for a {etype}, so I moved on to the next lever.")
    if result:
        w, l, r = result
        print(f"  Predicted at-level result: avg win ~{w:.0f}%, avg HP loss ~{l:.0f}% -> {r}"
              + ("" if r == TUNE_TARGET else f" (target {TUNE_TARGET})"))


# =====================================================================================
# reading the enemy stats
# =====================================================================================

STAT_ORDER = "name, level, amount, health, dexterity, armor, strength, melee  (then optional: ranged, vulnerable, resistant, boss, special_attack)"


def parse_enemy(text):
    text = text.strip().rstrip(';')
    # an existing enemy from enemy_data.py, e.g.  feral_dog
    existing = getattr(enemy_data, text, None)
    if text.isidentifier() and isinstance(existing, enemy_data.Enemy):
        return copy.deepcopy(existing)

    m = re.search(r'Enemy\s*\((.*)\)\s*$', text, re.S)
    if m:
        inner = m.group(1)
    else:
        inner = text
        if inner.startswith('(') and inner.endswith(')'):
            inner = inner[1:-1]
    call = ast.parse(f"f({inner})", mode='eval').body
    args = [ast.literal_eval(a) for a in call.args]
    kwargs = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
    try:
        en = enemy_data.Enemy(*args, **kwargs)
    except TypeError as e:
        raise ValueError(f"{e}\n  Expected: {STAT_ORDER}")
    for attr in ('vulnerable', 'resistant'):       # 'slashing' -> 'Slashing'
        v = getattr(en, attr)
        if isinstance(v, str) and v.lower() != 'none':
            setattr(en, attr, v.capitalize())
    if en.level < 1:
        raise ValueError("level must be 1 or higher")
    return en


def split_type(text):
    """'tank: ('Golem', ...)'  ->  ('Tank', "('Golem', ...)")"""
    m = re.match(r'^\s*([A-Za-z ]+?)\s*:\s*(.*)$', text, re.S)
    if m:
        for name in ENEMY_TYPES:
            if m.group(1).strip().lower() == name.lower():
                return name, m.group(2)
    return None, text


# =====================================================================================
# spells: balancing  (OFFENSIVE spells only)
# =====================================================================================
#
# Healing and Support spells (Minor healing, Shield, Freeze, Searing smite...) can't be balanced by a number, so
# only spells whose type is 'Offensive' are judged here. (They are still USED by the simulated players in the
# enemy tester, so they do change the enemy results.)
#
# How an attack spell is judged
#   Everything is measured as AVERAGE DAMAGE PER ACTION: hit chance x damage, for the classes that can learn the spell,
#   against REFERENCE_ENEMIES (each at its own level, so weapons have grown by the same amount as in the enemy tester).
#   A spell and a weapon attack both cost a full action, but a weapon is free and a spell costs mana, and mana is
#   limited - so a spell should do MORE damage than a weapon, and the more mana it costs the more it should do.
#   We find "how much more" from what you already have:
#       * every weapon (sword, dagger, bow) is a point at 0 mana,
#       * every OTHER attack spell is a point at its own mana cost,
#       * a straight line is drawn through those points. The spell is compared with the line at its own mana cost.
#   (The line is never allowed below your best weapon, so a spell that costs mana can't be expected to do less
#   than a free attack.)
#   The verdict compares the spell with that line (SPELL_BAND = how far off still counts as "in line").
#   It also tells you how it compares with your best weapon on its own.

SPELL_BAND = 0.30               # +-30% of the line is "IN LINE"
SPELL_SIMS = 1500               # fights per class per enemy for the 'what does it do in fights' check
SPELL_MAX_STEPS = 10            # how far the tuner is allowed to move one number
UNFINISHED_SPELLS = ('Tornado',)        # not implemented in dungeon_1.py yet - left out of the comparison
SPELL_NOTES = {
    'Poison': "Poison does all 12 damage at once in dungeon_1.py right now (your note says it should be spread over "
              "2-3 turns), so it looks stronger here than it will be once it's finished.",
}
# The enemies spells are measured against. Names from enemy_data.py, or full Enemy(...) lines
# (the miniboss and boss live inside dungeon_1.py, so they are copied in here).
REFERENCE_ENEMIES = [
    "feral_dog",
    "cave_spider",
    "('Gelatinous Cube', 1, 1, 40, 6, 3, 11, 6, 0, 'Slashing', 'None', True, 'Basic')",
    "('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic')",
]


def reference_enemies():
    found = []
    for text in REFERENCE_ENEMIES:
        try:
            found.append(parse_enemy(text))
        except Exception as e:
            print(f"(skipping reference enemy {text!r}: {e})")
    return found


def offensive_spells():
    """{'Firebolt': <Spell>, ...} - only the spells that can be balanced by damage."""
    return {n: s for n, s in spells_by_name().items()
            if s.spell_type == 'Offensive' and s.damage > 0 and n not in UNFINISHED_SPELLS}


def classes_for(spell_name):
    """Classes that can learn this spell (from player_data.spellbook). Not in the spellbook -> every class."""
    book = player_data.spellbook.get(1, {})
    found = [cls for cls in CLASSES if spell_name in [s.name for s in book.get(cls, [])]]
    return found or list(CLASSES), bool(found)


def weapon_attack_value(f, w):
    """Average damage of one ACTION with weapon `w` for fighter-in-a-fight `f` (all its attacks, hit chance included)."""
    pl, en = f.pl, f.en
    dmg = w.damage + WEAPON_DAMAGE_PER_LEVEL * (pl.level - 1)
    if w.type == 'Melee':
        n = (2 if pl.melee_skill >= 5 else 1) + (1 if w.attack_type == 'Light' else 0)
        p, m = hit_prob(f.p_melee_bonus, f.e_ac_start), mod(pl.strength)
    else:
        n = 2 if pl.ranged_skill >= 5 else 1
        p, m = hit_prob(f.p_ranged_bonus, f.e_ac_start), mod(pl.dexterity)
    return n * p * exp_hit(dmg, m, en.armor, w.damage_type, en.vulnerable, en.resistant)


def spell_attack_value(f, sp):
    """(average damage of one cast, hit chance) of attack spell `sp` for fighter-in-a-fight `f`."""
    base = sp.damage + SPELL_DAMAGE_PER_LEVEL * (f.pl.level - 1)
    p = hit_prob(f.p_spell_bonus, f.e_ac_start)
    return p * exp_spell(base, mod(f.pl.intelligence), f.en.armor, sp.damage_type, f.en.vulnerable, f.en.resistant), p


def fit_line(points):
    """Least-squares straight line through (x, y) points -> (a, b) for y = a + b * x."""
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    sxx = sum((x - mx) ** 2 for x, _ in points)
    if sxx == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in points) / sxx
    return my - b * mx, b


class SpellContext:
    """What a spell is measured against: the classes that can learn it, the reference enemies, what the weapons do for
    those classes, what every OTHER attack spell does for them, and the straight line through all of that."""

    def __init__(self, spell_name, classes, enemies):
        self.classes, self.enemies = list(classes), list(enemies)
        self.fights = {cls: [Fight(build_fighter(cls, max(1, en.level)), en, random.Random(0)) for en in self.enemies]
                       for cls in self.classes}
        self.weapon_list = weapons_in_game()
        self.weapons = {w.name: self.weapon_avg(w) for w in self.weapon_list}
        self.others = {n: s for n, s in offensive_spells().items() if n != spell_name}
        self.other_values = {n: self.value(s)[0] for n, s in self.others.items()}
        points = [(0, v) for v in self.weapons.values()]
        points += [(self.others[n].mana_cost, v) for n, v in self.other_values.items()]
        self.a, self.b = fit_line(points)
        self.best_weapon_name = max(self.weapons, key=self.weapons.get)
        self.best_weapon = self.weapons[self.best_weapon_name]

    def all_fights(self):
        return [f for fights in self.fights.values() for f in fights]

    def weapon_avg(self, w, cls=None):
        fights = self.fights[cls] if cls else self.all_fights()
        return _avg(weapon_attack_value(f, w) for f in fights)

    def value(self, spell, cls=None):
        """(average damage per cast, average hit %) over the classes (or just `cls`) and enemies."""
        fights = self.fights[cls] if cls else self.all_fights()
        vals = [spell_attack_value(f, spell) for f in fights]
        return _avg(v for v, _ in vals), 100 * _avg(p for _, p in vals)

    def expected(self, cost):
        """How much damage per action a spell of this mana cost should do."""
        return max(self.a + self.b * cost, self.best_weapon)

    def ratio(self, spell):
        return self.value(spell)[0] / self.expected(spell.mana_cost)


def spell_rating(ratio):
    if ratio < 1 - SPELL_BAND:
        return 'TOO WEAK'
    if ratio > 1 + SPELL_BAND:
        return 'TOO STRONG'
    return 'IN LINE'


def apply_spell_lever(spell, lever, direction):
    """Returns (new spell, (what, old, new)) or None if the lever can't move that way."""
    sign = 1 if direction == 'buff' else -1
    new = copy.deepcopy(spell)
    if lever == 'damage':
        if spell.damage + sign < 1:
            return None
        new.damage = spell.damage + sign
        return new, ('damage', spell.damage, new.damage)
    if lever == 'mana':
        cost = spell.mana_cost - sign          # a buff makes it CHEAPER
        if cost < 1:
            return None
        new.mana_cost = cost
        return new, ('mana cost', spell.mana_cost, cost)
    return None


def tune_spell(spell, ctx, rating):
    """For each lever on its own, the smallest change that gets the spell IN LINE (or as close as it gets)."""
    direction = 'buff' if rating == 'TOO WEAK' else 'nerf'
    start_gap = abs(ctx.ratio(spell) - 1)
    options = []
    for lever in ('damage', 'mana'):
        cur, first, last, steps, best = spell, None, None, 0, None
        for _ in range(SPELL_MAX_STEPS):
            step = apply_spell_lever(cur, lever, direction)
            if step is None:
                break
            cur = step[0]
            steps += 1
            first = step[1] if first is None else first
            last = step[1]
            ratio = ctx.ratio(cur)
            r = spell_rating(ratio)
            gap = abs(ratio - 1)
            if best is None or gap < best[0]:
                best = (gap, steps, (first[0], first[1], last[2]), ratio, r, cur)
            if r == 'IN LINE':
                break
            if (direction == 'buff' and r == 'TOO STRONG') or (direction == 'nerf' and r == 'TOO WEAK'):
                break           # that step jumped over the target - the smaller one is the closest we get
        if best and best[0] < start_gap:        # a lever that makes things worse isn't a fix - leave it out
            options.append(best)
    options.sort(key=lambda o: (o[4] != 'IN LINE', o[1]))
    return options


def fight_impact(spell, enemies, classes):
    """For each class that can learn the spell: avg at-level win % with the spell in its loadout vs without it."""
    rows = []
    for cls in classes:
        base = [s for s in default_loadout(cls) if s.name != spell.name]
        with_it, without = tuple([spell] + base), tuple(base)
        w_with, w_without = [], []
        for en in enemies:
            lvl = max(1, en.level)
            w_with.append(simulate(build_fighter(cls, lvl, with_it), en, SPELL_SIMS, random.Random(7))['win'])
            w_without.append(simulate(build_fighter(cls, lvl, without), en, SPELL_SIMS, random.Random(7))['win'])
        rows.append((cls, _avg(w_without), _avg(w_with), [b - a for a, b in zip(w_without, w_with)]))
    return rows


def describe_spell(sp):
    bits = [f"{sp.spell_type}", f"cost {sp.mana_cost} mana", sp.action]
    if sp.damage > 0:
        bits.append(f"damage {sp.damage}-{int(sp.damage * 1.3)} {sp.damage_type}")
    return ', '.join(bits)


def not_balanceable(spell):
    """The message for a spell that can't be balanced by damage, or None if it can."""
    if spell.spell_type != 'Offensive':
        return (f"{spell.name} is a {spell.spell_type} spell. Only Offensive spells are balanced here - healing and "
                f"support effects can't be measured as damage.\n"
                f"  Attack spells you can check: {', '.join(offensive_spells())}  (or type  spells  to compare them all).")
    if spell.damage <= 0:
        return f"{spell.name} is Offensive but has no damage, so there is nothing to measure. Give it a damage number."
    return None


def report_spell(spell):
    problem = not_balanceable(spell)
    if problem:
        print()
        print(problem)
        return
    enemies = reference_enemies()
    classes, in_book = classes_for(spell.name)
    ctx = SpellContext(spell.name, classes, enemies)
    print()
    print('=' * 94)
    print(f"SPELL: {spell.name}  ({describe_spell(spell)})")
    if not in_book:
        print("(not in player_data.spellbook yet, so it is tested on every class)")
    print(f"Classes that can learn it: {', '.join(classes)}")
    print(f"Measured against: " + ", ".join(f"{e.name} (L{e.level})" for e in enemies))
    print('=' * 94)
    if spell.name in SPELL_NOTES:
        print("Note: " + SPELL_NOTES[spell.name])

    # ---- per class ----
    wnames = [w.name for w in ctx.weapon_list]
    print(f"  {'Class':<10}{'Mana':>5}{'Casts':>6}{'Hit%':>6}{'Spell':>7}  " + "".join(f"{n:>8}" for n in wnames)
          + f"{'Best wpn':>10}{'Spell/wpn':>11}")
    usable = False
    for cls in classes:
        v, hit = ctx.value(spell, cls)
        wvals = {w.name: ctx.weapon_avg(w, cls) for w in ctx.weapon_list}
        best = max(wvals.values())
        mana = build_fighter(cls, 1).intelligence
        casts = mana // spell.mana_cost
        usable = usable or casts > 0
        extra = "   <- can't afford a single cast!" if casts == 0 else ''
        print(f"  {cls:<10}{mana:>5}{casts:>6}{hit:>6.0f}{v:>7.2f}  " + "".join(f"{wvals[n]:>8.2f}" for n in wnames)
              + f"{best:>10.2f}{v / best:>10.2f}x{extra}")
    print("  (Everything after 'Hit%' is average damage per ACTION. Weapons are free; the spell costs mana.)")

    # ---- the comparison table ----
    value, hit = ctx.value(spell)
    rows = [(w, 0, v, None) for w, v in ctx.weapons.items()]
    rows += [(n, ctx.others[n].mana_cost, v, v / ctx.others[n].mana_cost) for n, v in ctx.other_values.items()]
    rows.append((spell.name, spell.mana_cost, value, value / spell.mana_cost))
    rows.sort(key=lambda r: (r[1], r[2]))
    print()
    print(f"HOW IT COMPARES (average over {', '.join(classes)}):")
    print(f"    {'Attack':<16}{'Mana':>5}{'Dmg/action':>12}{'Dmg/mana':>10}")
    for name, cost, v, per_mana in rows:
        mark = '>>' if name == spell.name else '  '
        pm = f"{per_mana:>10.2f}" if per_mana is not None else f"{'(free)':>10}"
        print(f"  {mark}{name:<16}{cost:>5}{v:>12.2f}{pm}" + ("   <-- this spell" if name == spell.name else ''))

    # ---- verdict ----
    print()
    print('-' * 94)
    if not usable:
        print("VERDICT: UNUSABLE - none of the classes that learn it have enough mana to cast it once.")
        print("  Lower its mana cost, or raise the mana (intelligence) of those classes.")
        return
    expected = ctx.expected(spell.mana_cost)
    ratio = value / expected
    rating = spell_rating(ratio)
    print(f"VERDICT: {rating} - it does {value:.2f} damage per action. Your weapons and other attack spells say a "
          f"{spell.mana_cost}-mana spell should do about {expected:.2f} ({100 * ratio:.0f}% of that).")
    vs_weapon = value / ctx.best_weapon
    if vs_weapon < 1:
        print(f"  WARNING: it does LESS than a free {ctx.best_weapon_name} attack ({ctx.best_weapon:.2f}) - "
              f"there's no reason to spend mana on it.")
    else:
        print(f"  vs weapons: it does {100 * (vs_weapon - 1):.0f}% more than the best weapon here "
              f"({ctx.best_weapon_name}, {ctx.best_weapon:.2f}) for {spell.mana_cost} mana.")
    if rating != 'IN LINE':
        direction = 'buff' if rating == 'TOO WEAK' else 'nerf'
        print(f"Working out the smallest {direction}... ", end='', flush=True)
        options = tune_spell(spell, ctx, rating)
        print()
        if not options:
            print("  (no lever can move it that way)")
        for i, (gap, steps, (what, old, new), r_new, r, _) in enumerate(options, 1):
            tag = '' if r == 'IN LINE' else f' (best it gets: {r})'
            raising = (direction == 'buff') != (what == 'mana cost')    # a buff LOWERS the mana cost
            print(f"  Option {i}: {'raise' if raising else 'lower'} {what}: {old} -> {new}   "
                  f"=> {100 * r_new:.0f}% of the line -> {r}{tag}")
        print("  (A cheaper spell can be cast more often, a pricier one less often - the tool judges one cast at a time.)")

    # ---- fight impact ----
    print()
    print("IN FIGHTS (average win % at-level vs the reference enemies, class with vs without this spell):")
    print(f"  {'Class':<10}{'Without':>9}{'With':>8}{'Change':>9}   Change per enemy: " + ", ".join(e.name for e in enemies))
    for cls, w0, w1, per_enemy in fight_impact(spell, enemies, classes):
        print(f"  {cls:<10}{w0:>8.1f}%{w1:>7.1f}%{w1 - w0:>+8.1f}   " + "  ".join(f"{d:+.1f}" for d in per_enemy))
    print("  (Classes keep their normal spell loadout from SPELL_LOADOUTS; the spell is added or removed.)")


def report_all_spells():
    enemies = reference_enemies()
    spells = offensive_spells()
    print()
    print('=' * 100)
    print("ALL ATTACK SPELLS vs WEAPONS - average damage per action against " + ", ".join(e.name for e in enemies))
    print('=' * 100)
    print("(Only Offensive spells are balanced. Healing and Support spells can't be measured as damage.)")
    print(f"  {'Spell':<14}{'Cost':>5}  {'Learnable by':<22}{'Dmg/action':>11}{'Best weapon':>15}{'vs wpn':>8}"
          f"{'Should be':>11}{'vs line':>9}  Rating")
    table = []
    for name, sp in spells.items():
        classes, in_book = classes_for(name)
        ctx = SpellContext(name, classes, enemies)
        v, _ = ctx.value(sp)
        table.append((sp.mana_cost, name, sp, classes, in_book, ctx, v))
    for cost, name, sp, classes, in_book, ctx, v in sorted(table, key=lambda t: (t[0], t[1])):
        expected = ctx.expected(cost)
        who = ', '.join(classes) if in_book else 'nobody yet'
        can = any(build_fighter(c, 1).intelligence // cost > 0 for c in classes)
        rating = spell_rating(v / expected) if can else 'UNUSABLE'
        print(f"  {name:<14}{cost:>5}  {who:<22}{v:>11.2f}{ctx.best_weapon:>8.2f} {ctx.best_weapon_name[:6]:<6}"
              f"{v / ctx.best_weapon:>7.2f}x{expected:>11.2f}{100 * v / expected:>8.0f}%  {rating}")
    print()
    print("WEAPONS for reference (average damage per action, same enemies):")
    weapons = weapons_in_game()
    print(f"  {'Class':<10}" + "".join(f"{w.name:>9}" for w in weapons))
    for cls in CLASSES:
        fights = [Fight(build_fighter(cls, max(1, en.level)), en, random.Random(0)) for en in enemies]
        print(f"  {cls:<10}" + "".join(f"{_avg(weapon_attack_value(f, w) for f in fights):>9.2f}" for w in weapons))
    print()
    print("'Should be' = what the weapons and the OTHER attack spells imply a spell of that mana cost should do (see the")
    print(f"notes above the SPELLS section in the code). IN LINE = within +-{int(SPELL_BAND * 100)}% of it.")
    print("Type a spell's name (e.g. firebolt) to see the details and a suggested fix for just that spell.")


def report_loadouts():
    """Tries every legal combination of spells for every class and shows the best ones."""
    enemies = reference_enemies()
    book = player_data.spellbook.get(1, {})
    print()
    print('=' * 94)
    print("BEST SPELL PICKS - every legal combination, fought at-level vs " + ", ".join(e.name for e in enemies))
    print(f"({LOADOUT_SIMS} fights per class per enemy per combination. Ranked by average win %, then by HP lost.)")
    print('=' * 94)
    for cls in CLASSES:
        pool = [s for s in book.get(cls, []) if s.name not in UNFINISHED_SPELLS]
        slots = min(spell_slots(build_fighter(cls, 1).intelligence), len(pool))
        results = []
        for combo in itertools.combinations(pool, slots):
            wins, losses = [], []
            for en in enemies:
                r = simulate(build_fighter(cls, max(1, en.level), tuple(combo)), en, LOADOUT_SIMS, random.Random(11))
                wins.append(r['win'])
                losses.append(r['dmg_pct'])
            results.append((_avg(wins), _avg(losses), combo))
        results.sort(key=lambda t: (-t[0], t[1]))
        current = [s.name for s in default_loadout(cls)]
        print(f"\n{cls} (learns {slots} of {len(pool)}):  your SPELL_LOADOUTS has: {', '.join(current) or 'none'}")
        for i, (w, l, combo) in enumerate(results[:3], 1):
            same = ' <-- same as SPELL_LOADOUTS' if sorted(s.name for s in combo) == sorted(current) else ''
            print(f"  {i}. {', '.join(s.name for s in combo):<48} win {w:>5.1f}%  HP lost {l:>3.0f}%{same}")
        mine = [r for r in results if sorted(s.name for s in r[2]) == sorted(current)]
        if mine and results and mine[0] is not results[0] and mine[0][0] < results[0][0] - 1:
            rank = results.index(mine[0]) + 1
            print(f"     (yours ranks #{rank} of {len(results)}: win {mine[0][0]:.1f}%)")
    print("\nA careless player picks worse than this; the enemy tester uses SPELL_LOADOUTS, so copy any of these in there.")


# =====================================================================================
# reading spells
# =====================================================================================

SPELL_ORDER = "name, mana_cost, spell_description, spell_type  (then optional: damage, damage_type, healing, action)"


def parse_spell(text):
    text = text.strip().rstrip(';')
    existing = getattr(player_data, text, None)
    if text.isidentifier() and isinstance(existing, player_data.Spell):
        return copy.deepcopy(existing)
    known = spells_by_name()
    for name, sp in known.items():                      # also accept the spell's display name: "Fire bolt"/"Firebolt"
        if text.lower() == name.lower():
            return copy.deepcopy(sp)

    m = re.search(r'Spell\s*\((.*)\)\s*$', text, re.S)
    inner = m.group(1) if m else text
    if not m and inner.startswith('(') and inner.endswith(')'):
        inner = inner[1:-1]
    call = ast.parse(f"f({inner})", mode='eval').body
    args = [ast.literal_eval(a) for a in call.args]
    kwargs = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
    try:
        return player_data.Spell(*args, **kwargs)
    except TypeError as e:
        raise ValueError(f"{e}\n  Expected: {SPELL_ORDER}")


def looks_like_spell(line):
    low = line.strip().lower()
    if low.startswith('spell:') or re.match(r'^\s*spell\s*\(', line, re.I):
        return True
    if line.strip().isidentifier() and isinstance(getattr(player_data, line.strip(), None), player_data.Spell):
        return True
    return low in {n.lower() for n in spells_by_name()}


SPELL_COMMANDS = ('spells', 'spell list', 'all spells')


def handle_spell_line(line):
    low = line.strip().lower()
    if low in SPELL_COMMANDS:
        report_all_spells()
        return
    if low in ('loadouts', 'loadout', 'best spells'):
        report_loadouts()
        return
    if low.startswith('spell:'):
        line = line.strip()[6:]
    report_spell(parse_spell(line))


def is_command(line):
    return line.strip().lower() in SPELL_COMMANDS + ('loadouts', 'loadout', 'best spells')


def main():
    check_loadouts()
    args = sys.argv[1:]
    if args:
        try:
            line = ' '.join(args)
            if looks_like_spell(line) or is_command(line):
                handle_spell_line(line)
                return
            forced, text = split_type(line)
            report(parse_enemy(text), forced_type=forced)
        except Exception as e:
            print(f"Couldn't read that: {e}")
        return

    print("Balance calculator - enemies AND spells.")
    print("SPELLS: type an ATTACK spell's name (e.g. firebolt), or  spells  for the whole list. A new one:")
    print("        spell: ('Name', 4, 'desc', 'Offensive', 6, 'Fire')     (healing/support spells aren't balanced)")
    print("        loadouts  = the best spell picks for every class")
    print()
    print("ENEMIES: paste an enemy's stats, for example:")
    print("  ('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic')")
    print(f"Order: {STAT_ORDER}")
    print("You can also type the name of an enemy from enemy_data.py (e.g. feral_dog). Type 'quit' to exit.")
    print("To force a type instead of auto-detecting, put it first:  glass cannon: ('Name', ...)")
    print("For a swarm, set the 3rd number (amount) above 1.")
    while True:
        try:
            line = input("\nEnemy or spell> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ('q', 'quit', 'exit'):
            break
        try:
            if looks_like_spell(line) or is_command(line):
                handle_spell_line(line)
                continue
            forced, text = split_type(line)
            enemy = parse_enemy(text)
        except Exception as e:
            print(f"Couldn't read that: {e}")
            continue
        report(enemy, forced_type=forced)


if __name__ == '__main__':
    main()