#fully written by claude! I did not make this

"""
enemy_tester.py - balance-testing tool for the text RPG.

Put this file in the same folder as enemy_data.py and player_data.py, then run:

    python enemy_tester.py

and paste an enemy's stats, e.g.

    ('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic')

(with or without the outer brackets, or as a full  Enemy(...)  line, or the name of an
enemy that already exists in enemy_data.py, like  feral_dog).
You can also run it with the stats as an argument:

    python enemy_tester.py "'Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic'"

Every class is simulated at three player levels: enemy level - 1, enemy level, enemy level + 1.
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

CLASSES = ['Barbarian', 'Ranger', 'Rogue', 'Hunter']
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
def exp_hit(base, stat_mod, armor, dmg_type, vulnerable, resistant):
    """Average damage of one successful normal attack (same maths as damage_calc)."""
    lo, hi = int(base * 0.7), int(base * 1.3)
    total = 0
    for r in range(lo, hi + 1):
        d = max(1, r + stat_mod - armor)
        if dmg_type == vulnerable:
            d *= 2
        elif dmg_type == resistant:
            d //= 2
        total += d
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
    melee_dmg: int
    melee_type: str
    melee_light: bool
    ranged_dmg: int
    ranged_type: str


@lru_cache(maxsize=None)
def build_fighter(class_name, level):
    """Creates the real level-1 Player from player_data (so class stats stay in sync with your game),
    then applies the modelled level-ups."""
    def fake_input(prompt=''):
        if 'called' in prompt:
            return 'Tester'
        if 'like to be' in prompt:
            return class_name
        return ''

    with mock.patch('builtins.input', fake_input), contextlib.redirect_stdout(io.StringIO()):
        p = player_data.player_selection()

    for _ in range(level - 1):
        for stat in LEVEL_UP_PICKS[class_name]:
            setattr(p, stat, getattr(p, stat) + (1 if stat.endswith('_skill') else 2))
        p.max_health += HP_PER_LEVEL.get(class_name, HP_PER_LEVEL_DEFAULT)
    bonus = WEAPON_DAMAGE_PER_LEVEL * (level - 1)
    return Fighter(
        class_name, level, p.max_health, p.strength, p.dexterity, p.armor,
        p.melee_skill, p.ranged_skill,
        p.melee.damage + bonus, p.melee.damage_type, p.melee.attack_type == 'Light',
        p.ranged.damage + bonus, p.ranged.damage_type,
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
        # encounter() works these out ONCE at the start of the fight
        self.p_melee_bonus = mod(pl.strength) + pl.level // 2
        self.p_ranged_bonus = mod(pl.dexterity) + pl.level // 2
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

    def hit_exp(self, kind):
        pl, en = self.pl, self.en
        if kind == 'melee':
            return exp_hit(pl.melee_dmg, mod(self.str), en.armor, pl.melee_type, en.vulnerable, en.resistant)
        return exp_hit(pl.ranged_dmg, mod(self.dex), en.armor, pl.ranged_type, en.vulnerable, en.resistant)

    def option_values(self):
        ac = self.enemy_ac()
        vals = {
            'Melee': self.attack_count('melee') * hit_prob(self.p_melee_bonus, ac) * self.hit_exp('melee'),
            'Ranged': self.attack_count('ranged') * hit_prob(self.p_ranged_bonus, ac) * self.hit_exp('ranged'),
        }
        if self.can_sneak():
            first = hit_prob(mod(self.dex), ac + self.en.level) * (self.hit_exp('melee') + self.pl.melee_dmg)
            rest = (self.attack_count('melee') - 1) * hit_prob(self.p_melee_bonus, ac) * self.hit_exp('melee')
            vals['Sneak attack'] = first + rest
        return vals

    def special_value(self):
        base = self.pl.melee_dmg * 2
        mults = (1.25, 1.0, 0.75, 0.5)
        return sum(p * int(max(1, base * m - self.en.armor)) for p, m in zip(reaction_bands(), mults))

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
    def best_attack(self):
        vals = self.option_values()
        name = max(vals, key=vals.get)
        return name, vals[name]

    def want_heal(self, best):
        if self.potions <= 0 or self.hp >= self.pl.max_hp:
            return False
        if self.hp > max(HEAL_BELOW_FRACTION * self.pl.max_hp, self.enemy_max_hit()):
            return False
        top = max(best, self.special_value() if self.special_ready else 0)
        return top < self.e_hp          # if we'll probably finish it this turn, just attack

    def want_class_action(self, best):
        if not self.class_ready:
            return False
        cls, e = self.pl.class_name, self.e_hp
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
            return turns_needed(e, [(0, 1), (raged, 2)], best) < base_turns
        if cls == 'Ranger':
            self.ranger_bonus = True
            boosted = self.best_attack()[1]
            self.ranger_bonus = False
            return turns_needed(e, [(0, 1)], boosted) < base_turns
        if cls == 'Hunter':
            if HUNTER_NET == 'never':
                return False
            if HUNTER_NET == 'immediately':
                return True
            self.net_active = True
            netted = self.best_attack()[1]
            self.net_active = False
            return turns_needed(e, [(0, 1), (netted, HUNTER_NET_ROUNDS)], best) < base_turns
        return False    # Rogue's class action only reveals info - no combat effect

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
                        self.damage_target(self.player_hit_damage('melee') + pl.melee_dmg)
                elif rng.randint(1, 20) + bonus >= ac:
                    self.damage_target(self.player_hit_damage(kind))

    def enemy_turn(self):
        en, rng, pl = self.en, self.rng, self.pl
        for i, h in enumerate(self.e_hps):
            if h <= 0:
                continue
            act = self.enemy_action(i)
            dmg = 0
            if act == 'special':
                t = roll_reaction(rng)
                mult = 0.5 if t <= 35 else 0.75 if t <= 60 else 1
                dmg = int(max(1, en.melee * 2 * mult - pl.armor))
                self.e_special[i] = False
            elif act == 'melee':
                if rng.randint(1, 20) + self.e_melee_bonus >= self.p_ac:
                    dmg = max(1, rng.randint(int(en.melee * 0.7), int(en.melee * 1.3)) + mod(en.strength) - pl.armor)
            else:
                if rng.randint(1, 20) + self.e_ranged_bonus >= self.p_ac:
                    dmg = max(1, rng.randint(int(en.ranged * 0.7), int(en.ranged * 1.3)) + mod(self.e_dex) - pl.armor)
            self.hp -= dmg
            self.dmg_taken += dmg
            if self.hp <= 0:
                return

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

            option, best = self.best_attack()
            if self.want_heal(best):
                self.potions -= 1
                self.potions_used += 1
                self.hp = min(pl.max_hp, self.hp + rng.randint(*POTION_HEAL))
            elif self.want_class_action(best):
                self.use_class_action()
            elif self.special_ready and self.special_value() >= best:
                self.attack('Special attack')
            else:
                self.attack(option)

            if self.e_hp <= 0:
                return True
            self.enemy_turn()
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
    for cls in CLASSES:
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
    wins = rounds = dmg = potions = used = 0
    for _ in range(n):
        f = Fight(pl, en, rng)
        wins += f.run()
        rounds += f.rounds
        dmg += f.dmg_taken
        potions += f.potions_used
        used += f.class_used
    probe = Fight(pl, en, rng)
    vals = {k: v for k, v in probe.option_values().items() if k in ('Melee', 'Ranged')}
    kind = max(vals, key=vals.get)
    you_hit = hit_prob(probe.p_ranged_bonus if kind == 'Ranged' else probe.p_melee_bonus, probe.e_ac_start)
    foe_bonus = probe.e_ranged_bonus if en.ranged > 0 and en.boss else probe.e_melee_bonus
    foe_hit = hit_prob(foe_bonus, probe.p_ac)
    win_pct = 100 * wins / n
    avg_dmg = dmg / n
    return {
        'win': win_pct, 'dmg': avg_dmg, 'dmg_pct': 100 * avg_dmg / pl.max_hp, 'rounds': rounds / n,
        'potions': potions / n, 'you_hit': 100 * you_hit, 'foe_hit': 100 * foe_hit,
        'weapon': kind[0], 'hp': pl.max_hp, 'ability': 100 * used / n,
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
              f"{'Hit% you/foe':>14}  {'Ability%':>8}  Rating")
        rows = []
        for cls in CLASSES:
            r = simulate(build_fighter(cls, lvl), en, n, rng)
            rows.append(r)
            rating = rate(r['win'], r['dmg_pct'])
            print(f"  {cls:<10}{r['hp']:>4}  {r['win']:>6.1f}  {r['dmg']:>7.1f} ({r['dmg_pct']:>3.0f}%)  "
                  f"{r['rounds']:>6.1f}  {r['potions']:>7.1f}  "
                  f"{r['you_hit']:>5.0f}/{r['foe_hit']:<3.0f} ({r['weapon']})  {r['ability']:>8.0f}  {rating}")
        avg_win = sum(r['win'] for r in rows) / len(rows)
        avg_loss = sum(r['dmg_pct'] for r in rows) / len(rows)
        overall = rate(avg_win, avg_loss)
        print(f"  {'Average':<10}{'':>4}  {avg_win:>6.1f}  {'':>7} ({avg_loss:>3.0f}%)  "
              f"{sum(r['rounds'] for r in rows) / len(rows):>6.1f}  {'':>7}  {'':>14}  {'':>8}  {overall}")
        summary.append((label, overall))
        if delta == 0:
            at_level = (avg_win, avg_loss, overall)
    print()
    print("Overall: " + "  |  ".join(f"{l.title()}: {o if o else 'n/a'}" for l, o in summary))
    print("(Hit%: M/R = best weapon for that class, melee or ranged. Boss specials always hit and aren't in 'foe'.)")
    print("(Ability% = how often the class action was worth using. Dmg taken is raw, before potions.)")
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


def main():
    args = sys.argv[1:]
    if args:
        try:
            forced, text = split_type(' '.join(args))
            report(parse_enemy(text), forced_type=forced)
        except Exception as e:
            print(f"Couldn't read that enemy: {e}")
        return

    print("Enemy tester. Paste an enemy's stats, for example:")
    print("  ('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic')")
    print(f"Order: {STAT_ORDER}")
    print("You can also type the name of an enemy from enemy_data.py (e.g. feral_dog). Type 'quit' to exit.")
    print("To force a type instead of auto-detecting, put it first:  glass cannon: ('Name', ...)")
    print("For a swarm, set the 3rd number (amount) above 1.")
    while True:
        try:
            line = input("\nEnemy> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ('q', 'quit', 'exit'):
            break
        try:
            forced, text = split_type(line)
            enemy = parse_enemy(text)
        except Exception as e:
            print(f"Couldn't read that enemy: {e}")
            continue
        report(enemy, forced_type=forced)


if __name__ == '__main__':
    main()