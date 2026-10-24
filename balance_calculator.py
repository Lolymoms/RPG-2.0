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

Every class (now including the Mage, with its spells) is simulated at three player levels:
enemy level - 1, enemy level, enemy level + 1.

SPELLS: type a spell's name from player_data.py (e.g.  firebolt), a whole  Spell(...)  line, or  spell: ('Name', ...)
to see whether it is too weak / too strong compared with your other spells, with a suggested fix.
Type  spells  to compare every spell at once.
Everything you are likely to want to tweak is in the CONFIG section just below.
"""

import ast
import contextlib
import copy
import io
import math
import random
import re
import sys
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
WEAPON_DAMAGE_PER_LEVEL = 2     # +damage on BOTH weapons for every level above 1
POTIONS_PER_LEVEL = 1           # a level 2 player starts the fight with 2 healing potions
POTION_HEAL = (4, 8)            # each potion heals randint(a, b)

# Which two stats each class raises at every level-up (any two different ones of:
# 'strength', 'dexterity', 'melee_skill', 'ranged_skill'). Stats give +2, skills give +1.
LEVEL_UP_PICKS = {
    'Barbarian': ['strength', 'melee_skill'],
    'Ranger':    ['dexterity', 'ranged_skill'],
    'Rogue':     ['dexterity', 'melee_skill'],
    'Hunter':    ['strength', 'ranged_skill'],
    # Your game's level-up menu has no Intelligence option yet, so a Mage can only pick from the same four stats.
    # If you add one, put 'intelligence' in here to see what it does to mana and spell hit chance.
    'Mage':      ['dexterity', 'ranged_skill'],
}
# max HP gained per level (copied from Player.add_experience)
HP_PER_LEVEL = {'Barbarian': 12, 'Hunter': 10}
HP_PER_LEVEL_DEFAULT = 8

# ---- player behaviour ----
HEAL_BELOW_FRACTION = 0.35      # drink a potion at/under this fraction of max HP (or if the enemy's
                                # next hit could kill you) - unless you expect to kill the enemy this turn
BARBARIAN_RAGE = 'smart'  # 'immediately' | 'smart' (only if it saves turns) | 'never'
HUNTER_NET = 'smart'            # 'immediately' | 'smart' (only if it saves turns) | 'never'
HUNTER_NET_ROUNDS = 2           # how many rounds of the Hunter's attacks the net affects

# ---- spells ----
# Which spells each class has learned (names from player_data.py). In your game a class learns
# (intelligence // 3) - 1 of them: Barbarian 1, Rogue 2, Ranger 3, Hunter 3, Mage 4. Change these to test other picks.
SPELL_LOADOUTS = {
    'Barbarian': ['Searing smite'],
    'Ranger':    ['Shield', 'Freeze', 'Arcane blast'],
    'Rogue':     ['Searing smite', 'Arcane blast'],
    'Hunter':    ['Poison', 'Shield', 'Earth spike'],
    'Mage':      ['Minor healing', 'Firebolt', 'Poison', 'Arcane blast'],
}
# (These are the best picks I found by trying every legal combination - a smart player. A careless one does worse.)
SPELL_DAMAGE_PER_LEVEL = 0      # like WEAPON_DAMAGE_PER_LEVEL, but for spells. 0 = spells never get stronger (as in the game now)
START_MANA_FRACTION = 1.0       # fraction of the mana pool you start each fight with. 1.0 = fresh from a campfire.
                                # Lower it (e.g. 0.5) to model a dungeon where you fight several times between rests.
# Your game lets you do a 0.5 'bonus' action (potion, class action, shield, searing smite, minor healing) and then still
# attack in the same turn. True = the simulation does that. False = a bonus action uses up your whole turn (how this
# tool used to work before spells existed).
BONUS_ACTIONS_STACK = True
BUFF_MIN_TURNS = 2              # only cast Shield / Searing smite if the fight should last at least this many more turns
FREEZE_MIN_TURNS = 3            # only cast Freeze if the fight should last at least this many more turns

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


def default_loadout(class_name):
    known = spells_by_name()
    return tuple(known[name] for name in SPELL_LOADOUTS.get(class_name, []) if name in known)


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

    with mock.patch('builtins.input', fake_input), contextlib.redirect_stdout(io.StringIO()):
        p = player_data.player_selection('dev')

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


class Fight:
    def __init__(self, pl, en, rng):
        self.pl, self.en, self.rng = pl, en, rng
        self.hp = pl.max_hp
        self.str, self.dex = pl.strength, pl.dexterity     # "live" values (rage changes these)
        self.n_enemies = max(1, int(en.amount))      # swarms: several copies of the same enemy
        self.e_hps = [en.health] * self.n_enemies
        self.e_special = [en.special_attack_available] * self.n_enemies
        self.e_dex = en.dexterity                    # (net halves dex for the whole group)
        self.potions = pl.level * POTIONS_PER_LEVEL
        self.special_ready = True
        self.class_ready = True
        self.class_used = False
        self.rage_counter = 0
        self.ranger_bonus = False
        self.net_active = False
        self.net_counter = 0
        self.dmg_taken = 0
        self.potions_used = 0
        self.rounds = 0
        # spells
        self.mana = int(pl.intelligence * START_MANA_FRACTION)
        self.mana_used = 0
        self.shield = False            # shield spell is up
        self.smite = 0                 # melee hits left with searing smite
        self.skip = 0                  # enemy turns still skipped (freeze)
        self.freeze_pending = False    # freeze was cast this round: the enemy still attacks once, THEN it's frozen
        # encounter() works these out ONCE at the start of the fight
        self.p_melee_bonus = mod(pl.strength) + pl.level // 2
        self.p_ranged_bonus = mod(pl.dexterity) + pl.level // 2
        self.p_spell_bonus = mod(pl.intelligence) + pl.level // 2
        self.p_ac = 10 + mod(pl.dexterity)
        self.e_melee_bonus = mod(en.strength) + en.level // 2
        self.e_ranged_bonus = mod(en.dexterity) + en.level // 2
        self.e_ac_start = 10 + mod(en.dexterity)

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
        if self.net_active:
            return 10 + mod(self.e_dex)
        return self.e_ac_start

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
        """Average damage of each way to attack. capped=True ignores damage beyond the target's remaining HP -
        that's how the simulated player chooses (a 12-damage spell is no better than a 4-damage arrow on a 3 HP enemy)."""
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

    def best_damage_spell(self, capped=False):
        """The affordable attack spell with the highest average damage, and that damage."""
        best, val = None, 0
        for s in self.pl.spells:
            if s.spell_type == 'Offensive' and self.can_cast(s):
                v = self.spell_value(s, capped)
                if v > val:
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
        """('spell', Spell) or ('potion', None) or None. Healing spells first: mana comes back at the campfire."""
        for s in self.pl.spells:
            if s.spell_type == 'Healing' and self.can_cast(s):
                return ('spell', s)
        if self.potions > 0:
            return ('potion', None)
        return None

    def want_heal(self, top):
        if self.hp >= self.pl.max_hp or self.heal_source() is None:
            return False
        if self.hp > max(HEAL_BELOW_FRACTION * self.pl.max_hp, self.enemy_max_hit()):
            return False
        return top < self.e_hp          # if we'll probably finish it this turn, just attack

    def want_class_action(self, best):
        if not self.class_ready:
            return False
        cls, e = self.pl.class_name, self.e_hp
        # turns the class action costs you: 0 if bonus actions stack with an attack, otherwise a whole turn
        lost = 0 if BONUS_ACTIONS_STACK else 1
        base_turns = turns_needed(e, [], best)
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
            return turns_needed(e, [(0, lost), (raged, 2)], best) < base_turns
        if cls == 'Ranger':
            self.ranger_bonus = True
            boosted = self.best_attack()[1]
            self.ranger_bonus = False
            return turns_needed(e, [(0, lost)], boosted) < base_turns
        if cls == 'Hunter':
            if HUNTER_NET == 'never':
                return False
            if HUNTER_NET == 'immediately':
                return True
            self.net_active = True
            netted = self.best_attack()[1]
            self.net_active = False
            return turns_needed(e, [(0, lost), (netted, HUNTER_NET_ROUNDS)], best) < base_turns
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
            self.net_active = True
            self.net_counter = HUNTER_NET_ROUNDS + 1     # ticks down at the top of each round, like rage

    def cast(self, spell):
        """Same rules as Spell.cast_spell + the effects in encounter()."""
        rng, pl, en = self.rng, self.pl, self.en
        self.mana -= spell.mana_cost
        self.mana_used += spell.mana_cost
        if spell.spell_type == 'Healing':
            self.hp = min(pl.max_hp, self.hp + rng.randint(*spell.healing))
        elif spell.damage > 0:
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
        ac = self.enemy_ac()
        if option == 'Special attack':
            t = roll_reaction(rng)
            mult = 1.25 if t <= 35 else 1 if t <= 60 else 0.75 if t <= 80 else 0.5
            self.damage_target(int(max(1, pl.melee_dmg * 2 * mult - en.armor)))
            self.special_ready = False
        else:
            kind = 'ranged' if option == 'Ranged' else 'melee'
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
    def take_turn(self):
        """Your game lets you do a 0.5 'bonus' action (potion, class action, shield, searing smite, minor healing)
        and THEN a full action in the same turn, as long as you still have action left (BONUS_ACTIONS_STACK).
        The simulated player takes at most one bonus action, then one full action."""
        points = 1.0
        _, plain_best = self.best_attack()                       # un-capped: used to judge class actions
        option, best = self.best_attack(capped=True)             # capped: used to choose what to do
        spell, spell_val = self.best_damage_spell(capped=True)
        special = self.special_value(capped=True) if self.special_ready else 0
        top = max(best, spell_val, special)
        turns_left = turns_needed(self.e_hp, [], max(plain_best, top))

        # ----- bonus action (at most one) -----
        took_bonus = True
        if self.want_heal(top):
            self.do_heal()
        elif self.want_class_action(plain_best):
            self.use_class_action()
        else:
            buff = self.pick_buff(option, best, spell_val, turns_left)
            if buff:
                self.cast(buff)
            else:
                took_bonus = False
        if took_bonus:
            points = points - 0.5 if BONUS_ACTIONS_STACK else 0
        if points <= 0:
            return

        # ----- full action -----
        # the bonus action may have changed things (smite, rage...), so look again
        freeze = self.want_freeze(turns_left)
        if freeze:
            self.cast(freeze)
            return
        option, best = self.best_attack(capped=True)
        spell, spell_val = self.best_damage_spell(capped=True)
        special = self.special_value(capped=True) if self.special_ready else 0
        if spell is not None and spell_val > max(best, special):
            self.cast(spell)
        elif self.special_ready and special >= best:
            self.attack('Special attack')
        else:
            self.attack(option)

    # ---------- the fight ----------
    def run(self):
        pl, en, rng = self.pl, self.en, self.rng
        while self.rounds < MAX_ROUNDS:
            self.rounds += 1
            # start-of-round bookkeeping, same order as encounter()
            self.rage_counter -= 1
            if self.net_counter > 0:
                self.net_counter -= 1
                if self.net_counter == 0:
                    self.net_active = False
            if not self.net_active:
                self.e_dex = en.dexterity
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
    for _ in range(n):
        f = Fight(pl, en, rng)
        wins += f.run()
        rounds += f.rounds
        dmg += f.dmg_taken
        potions += f.potions_used
        used += f.class_used
        mana += f.mana_used
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
              f"{'Hit% you/foe':>14}  {'Ability%':>8}  {'Mana':>4}  Rating")
        rows = []
        for cls in CLASSES:
            r = simulate(build_fighter(cls, lvl), en, n, rng)
            rows.append(r)
            rating = rate(r['win'], r['dmg_pct'])
            print(f"  {cls:<10}{r['hp']:>4}  {r['win']:>6.1f}  {r['dmg']:>7.1f} ({r['dmg_pct']:>3.0f}%)  "
                  f"{r['rounds']:>6.1f}  {r['potions']:>7.1f}  "
                  f"{r['you_hit']:>5.0f}/{r['foe_hit']:<3.0f} ({r['weapon']})  {r['ability']:>8.0f}  {r['mana']:>4.0f}  {rating}")
        avg_win = sum(r['win'] for r in rows) / len(rows)
        avg_loss = sum(r['dmg_pct'] for r in rows) / len(rows)
        overall = rate(avg_win, avg_loss)
        print(f"  {'Average':<10}{'':>4}  {avg_win:>6.1f}  {'':>7} ({avg_loss:>3.0f}%)  "
              f"{sum(r['rounds'] for r in rows) / len(rows):>6.1f}  {'':>7}  {'':>14}  {'':>8}  {'':>4}  {overall}")
        summary.append((label, overall))
        if delta == 0:
            at_level = (avg_win, avg_loss, overall)
    print()
    print("Overall: " + "  |  ".join(f"{l.title()}: {o if o else 'n/a'}" for l, o in summary))
    print("(Hit%: M/R/S = best attack for that class: melee, ranged or a spell. Boss specials always hit and aren't in 'foe'.)")
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
# spells: balancing
# =====================================================================================
#
# How a spell is judged
#   Everything is measured in TURNS OF FIGHTING, so damage, healing and buffs can be compared:
#     damage        = damage dealt / what your best weapon does per turn      (kills the enemy that much sooner)
#     healing       = HP healed / what the enemy does to you per turn          (keeps you alive that much longer)
#     Freeze        = its damage + the enemy turns it skips                   (each skipped turn is a turn gained)
#     Shield        = 25% of one enemy hit, as turns of enemy damage
#     Searing smite = the extra damage on your next 2 melee hits / weapon damage per turn
#   NET: an 'Action' spell is cast INSTEAD of attacking, so subtract the 1 turn your weapon attack would have been worth.
#        A 'Bonus action' spell doesn't cost your attack (see BONUS_ACTIONS_STACK), so nothing is subtracted.
#   NET PER MANA: mana is the shared budget, so this is the fair way to compare spells.
#   The verdict compares that with the MEDIAN of all your other spells (SPELL_BAND = how far off still counts as 'in line').
# It's measured for the classes that can learn the spell, against REFERENCE_ENEMIES (each at its own level, so weapons
# have grown by the same amount as in the enemy tester).

SPELL_BAND = 0.30               # +-30% of the median spell is "IN LINE"
SPELL_SIMS = 1500               # fights per class per enemy for the 'what does it do in fights' check
SPELL_MAX_STEPS = 10            # how far the tuner is allowed to move one number
UNFINISHED_SPELLS = ('Tornado',)        # not implemented in dungeon_1.py yet - left out of the comparison
# The enemies spells are measured against. Names from enemy_data.py, or full Enemy(...) lines
# (the miniboss and boss live inside dungeon_1.py, so they are copied in here).
REFERENCE_ENEMIES = [
    "feral_dog",
    "cave_spider",
    "('Gelatinous Cube', 1, 1, 40, 6, 3, 11, 6, 0, 'Slashing', 'None', True, 'Basic')",
    "('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic')",
]
FREEZE_SKIPPED_TURNS = 2        # how many enemy turns Freeze takes away (matches dungeon_1.py)


def reference_enemies():
    found = []
    for text in REFERENCE_ENEMIES:
        try:
            found.append(parse_enemy(text))
        except Exception as e:
            print(f"(skipping reference enemy {text!r}: {e})")
    return found


def enemy_hit_stats(f):
    """(chance one enemy hits this fighter, average damage when it does) - normal attacks only."""
    en = f.en
    if en.ranged > en.melee:
        base, m, bonus = en.ranged, mod(en.dexterity), f.e_ranged_bonus
    else:
        base, m, bonus = en.melee, mod(en.strength), f.e_melee_bonus
    lo, hi = int(base * 0.7), int(base * 1.3)
    avg_hit = _avg(max(1, r + m - f.pl.armor) for r in range(lo, hi + 1))
    return hit_prob(bonus, f.p_ac), avg_hit


def spell_cast_value(spell, pl, en):
    """What ONE cast is worth against this enemy, in turns of fighting.
    Returns (value, net, hit chance %, weapon damage per turn)."""
    f = Fight(pl, en, random.Random(0))
    weapon = max(v for k, v in f.option_values().items() if k in ('Melee', 'Ranged'))
    w = max(weapon, 0.1)                               # your damage per turn
    turns_to_kill = en.health / w
    p_hit = hit_prob(f.p_spell_bonus, f.e_ac_start)
    foe_hit, foe_dmg = enemy_hit_stats(f)
    d = max(foe_hit * foe_dmg, 0.1)                    # the enemy's damage per turn against you
    hit = 100
    if spell.spell_type == 'Healing':
        value = ((spell.healing[0] + spell.healing[1]) / 2) / d
    elif spell.damage > 0:
        base = spell.damage + SPELL_DAMAGE_PER_LEVEL * (pl.level - 1)
        value = p_hit * exp_spell(base, mod(pl.intelligence), en.armor, spell.damage_type, en.vulnerable, en.resistant) / w
        hit = 100 * p_hit
        if spell.name == 'Freeze':
            value += p_hit * min(FREEZE_SKIPPED_TURNS, max(0.0, turns_to_kill - 1))     # enemy turns skipped
    elif spell.name == 'Shield':
        value = 0.25 * min(1.0, turns_to_kill * foe_hit) / foe_hit if foe_hit > 0 else 0.0
    elif spell.name == 'Searing smite':
        p_melee = hit_prob(f.p_melee_bonus, f.e_ac_start)
        hits = min(2.0, f.attack_count('melee') * turns_to_kill * p_melee)
        value = 0.5 * f.hit_exp('melee') * hits / w
    else:
        value = 0.0                 # an effect this tool doesn't know how to value
    replaces_attack = spell.action != 'Bonus action' or not BONUS_ACTIONS_STACK
    net = value - (1.0 if replaces_attack else 0.0)
    return value, net, hit, weapon


def classes_for(spell_name):
    """Classes that can learn this spell (from player_data.spellbook). Not in the spellbook -> every class."""
    book = player_data.spellbook.get(1, {})
    found = [cls for cls in CLASSES if spell_name in [s.name for s in book.get(cls, [])]]
    return found or list(CLASSES), bool(found)


def spell_scores(spell, enemies=None):
    """Per class: averages over the reference enemies. Returns (rows, overall net-per-mana or None)."""
    enemies = enemies or reference_enemies()
    classes, _ = classes_for(spell.name)
    rows = []
    for cls in classes:
        vals, nets, hits, weps, lvls = [], [], [], [], []
        for en in enemies:
            pl = build_fighter(cls, max(1, en.level))
            v, n, h, w = spell_cast_value(spell, pl, en)
            vals.append(v); nets.append(n); hits.append(h); weps.append(w)
        mana = build_fighter(cls, 1).intelligence
        casts = mana // spell.mana_cost
        rows.append(dict(cls=cls, mana=mana, casts=casts, hit=_avg(hits), value=_avg(vals),
                         weapon=_avg(weps), net=_avg(nets), per_mana=_avg(nets) / spell.mana_cost))
    usable = [r['per_mana'] for r in rows if r['casts'] > 0]
    return rows, (_avg(usable) if usable else None)


def median(xs):
    xs = sorted(xs)
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


def spell_target(exclude_name=None, enemies=None):
    """The median net-value-per-mana of every finished spell in player_data.py (except `exclude_name`)."""
    scores = []
    for name, sp in spells_by_name().items():
        if name in UNFINISHED_SPELLS or name == exclude_name:
            continue
        overall = spell_scores(sp, enemies)[1]
        if overall is not None:
            scores.append(overall)
    return median(scores) if scores else None


def spell_rating(per_mana, target):
    if per_mana is None:
        return 'UNUSABLE'
    if target is None or target <= 0:
        return 'IN LINE'
    ratio = per_mana / target
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
        if spell.damage <= 0 or spell.damage + sign < 1:
            return None
        new.damage = spell.damage + sign
        return new, ('damage', spell.damage, new.damage)
    if lever == 'healing':
        lo, hi = spell.healing
        if lo + sign < 1:
            return None
        new.healing = (lo + sign, hi + sign)
        return new, ('healing', f"{lo}-{hi}", f"{lo + sign}-{hi + sign}")
    if lever == 'mana':
        cost = spell.mana_cost - sign          # a buff makes it CHEAPER
        if cost < 1:
            return None
        new.mana_cost = cost
        return new, ('mana cost', spell.mana_cost, cost)
    return None


def spell_levers(spell):
    levers = []
    if spell.spell_type == 'Healing':
        levers.append('healing')
    elif spell.damage > 0:
        levers.append('damage')
    levers.append('mana')
    return levers


def tune_spell(spell, rating, target, enemies):
    """For each lever on its own, the smallest change that gets the spell IN LINE (or as close as it gets)."""
    direction = 'buff' if rating == 'TOO WEAK' else 'nerf'
    start = spell_scores(spell, enemies)[1]
    start_gap = abs(start - target) if start is not None else 1e9
    options = []
    for lever in spell_levers(spell):
        cur, first, last, steps = spell, None, None, 0
        best = None
        for _ in range(SPELL_MAX_STEPS):
            step = apply_spell_lever(cur, lever, direction)
            if step is None:
                break
            cur = step[0]
            steps += 1
            first = step[1] if first is None else first
            last = step[1]
            per_mana = spell_scores(cur, enemies)[1]
            r = spell_rating(per_mana, target)
            gap = abs(per_mana - target) if per_mana is not None else 1e9
            if best is None or gap < best[0]:
                best = (gap, steps, (first[0], first[1], last[2]), per_mana, r, cur)
            if r == 'IN LINE':
                break
            overshot = (direction == 'buff' and r == 'TOO STRONG') or (direction == 'nerf' and r == 'TOO WEAK')
            if overshot:
                break
        if best and best[0] < start_gap:        # a lever that makes things worse (e.g. cheaper mana on a spell
            options.append(best)                # that is worse than your weapon) isn't a fix - leave it out
    options.sort(key=lambda o: (o[4] != 'IN LINE', o[1]))
    return options


def fight_impact(spell, enemies):
    """For each class that can learn the spell: avg at-level win % with the spell in its loadout vs without it."""
    classes, _ = classes_for(spell.name)
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
    if sp.spell_type == 'Healing':
        bits.append(f"heals {sp.healing[0]}-{sp.healing[1]}")
    elif sp.damage > 0:
        bits.append(f"damage {sp.damage}-{int(sp.damage * 1.3)} {sp.damage_type}")
    return ', '.join(bits)


def report_spell(spell, forced_target=None):
    enemies = reference_enemies()
    print()
    print('=' * 82)
    print(f"SPELL: {spell.name}  ({describe_spell(spell)})")
    classes, in_book = classes_for(spell.name)
    if not in_book:
        print("(not in player_data.spellbook yet, so it is tested on every class)")
    print(f"Measured against: " + ", ".join(f"{e.name} (L{e.level})" for e in enemies))
    print('=' * 82)
    if spell.name in UNFINISHED_SPELLS:
        print("Note: this spell isn't implemented in dungeon_1.py yet, so its numbers don't mean much.")

    rows, overall = spell_scores(spell, enemies)
    print(f"  {'Class':<10}{'Mana':>5}{'Casts':>6}{'Hit%':>6}{'Value':>7}{'Net':>7}{'Net/mana':>10}{'Weapon dmg/turn':>17}")
    for r in rows:
        extra = "   <- can't afford a single cast!" if r['casts'] == 0 else ''
        print(f"  {r['cls']:<10}{r['mana']:>5}{r['casts']:>6}{r['hit']:>6.0f}{r['value']:>7.2f}{r['net']:>7.2f}"
              f"{r['per_mana']:>10.3f}{r['weapon']:>17.1f}{extra}")
    print("  (Value = turns of fighting one cast is worth. Net = Value minus the 1 turn a weapon attack would have been")
    print("   worth - bonus-action spells give up nothing. Net/mana is what gets compared between spells.)")

    target = forced_target if forced_target is not None else spell_target(spell.name, enemies)
    rating = spell_rating(overall, target)
    print()
    print('-' * 82)
    if overall is None:
        print("VERDICT: UNUSABLE - none of the classes that learn it have enough mana to cast it once.")
        print("  Lower its mana cost, or raise the mana of those classes (intelligence).")
        return
    pct = 100 * overall / target if target else 0
    print(f"VERDICT: {rating} - net value per mana {overall:.3f}, your other spells' median is {target:.3f} ({pct:.0f}% of it).")
    if rating != 'IN LINE':
        direction = 'buff' if rating == 'TOO WEAK' else 'nerf'
        print(f"Working out the smallest {direction}... ", end='', flush=True)
        options = tune_spell(spell, rating, target, enemies)
        print()
        if not options:
            print("  (no lever can move it that way)")
        for i, (gap, steps, (what, old, new), per_mana, r, _) in enumerate(options, 1):
            tag = '' if r == 'IN LINE' else f' (best it gets: {r})'
            raising = (direction == 'buff') != (what == 'mana cost')    # a buff LOWERS the mana cost
            print(f"  Option {i}: {'raise' if raising else 'lower'} {what}: {old} -> {new}   "
                  f"=> net/mana {per_mana:.3f} -> {r}{tag}")
        if spell.damage <= 0 and spell.spell_type != 'Healing':
            print(f"  (The strength of {spell.name} is coded in dungeon_1.py, so only its mana cost is a lever here.)")

    print()
    print("IN FIGHTS (average win % at-level vs the reference enemies, class with vs without this spell):")
    print(f"  {'Class':<10}{'Without':>9}{'With':>8}{'Change':>9}   Change per enemy: " + ", ".join(e.name for e in enemies))
    for cls, w0, w1, per_enemy in fight_impact(spell, enemies):
        print(f"  {cls:<10}{w0:>8.1f}%{w1:>7.1f}%{w1 - w0:>+8.1f}   " + "  ".join(f"{d:+.1f}" for d in per_enemy))
    print("  (Classes keep their normal spell loadout from SPELL_LOADOUTS; the spell is added or removed.)")


def report_all_spells():
    enemies = reference_enemies()
    print()
    print('=' * 82)
    print("ALL SPELLS - net value per mana against " + ", ".join(e.name for e in enemies))
    print('=' * 82)
    table = []
    for name, sp in spells_by_name().items():
        if name in UNFINISHED_SPELLS:
            continue
        rows, overall = spell_scores(sp, enemies)
        table.append((name, sp, rows, overall))
    target = median([t[3] for t in table if t[3] is not None])
    print(f"  {'Spell':<15}{'Type':<10}{'Cost':>5}  {'Action':<13}{'Net/mana':>9}  {'vs median':>9}  {'Rating':<12}Who can learn it")
    for name, sp, rows, overall in sorted(table, key=lambda t: -(t[3] if t[3] is not None else -99)):
        who = ', '.join(r['cls'] + ('' if r['casts'] else ' (can\'t afford)') for r in rows)
        if overall is None:
            print(f"  {name:<15}{sp.spell_type:<10}{sp.mana_cost:>5}  {sp.action:<13}{'n/a':>9}  {'':>9}  {'UNUSABLE':<12}{who}")
            continue
        pct = f"{100 * overall / target:.0f}%" if target else ''
        print(f"  {name:<15}{sp.spell_type:<10}{sp.mana_cost:>5}  {sp.action:<13}{overall:>9.3f}  {pct:>9}  "
              f"{spell_rating(overall, target):<12}{who}")
    print(f"\nMedian net value per mana: {target:.3f} (turns of fighting). 'IN LINE' = within +-{int(SPELL_BAND * 100)}% of it.")
    print("Type a spell's name (e.g. firebolt) to see the details and a suggested fix for just that spell.")


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


def handle_spell_line(line):
    low = line.strip().lower()
    if low in ('spells', 'spell list', 'all spells'):
        report_all_spells()
        return
    if low.startswith('spell:'):
        line = line.strip()[6:]
    report_spell(parse_spell(line))


def main():
    args = sys.argv[1:]
    if args:
        try:
            line = ' '.join(args)
            if looks_like_spell(line) or line.strip().lower() in ('spells', 'spell list', 'all spells'):
                handle_spell_line(line)
                return
            forced, text = split_type(line)
            report(parse_enemy(text), forced_type=forced)
        except Exception as e:
            print(f"Couldn't read that enemy: {e}")
        return

    print("Balance calculator - enemies AND spells.")
    print("SPELLS: type a spell name (e.g. firebolt) or  spells  for the whole list. A new one:  spell: ('Name', 4, 'desc', 'Offensive', 6, 'Fire')")
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
            if looks_like_spell(line) or line.lower() in ('spells', 'spell list', 'all spells'):
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