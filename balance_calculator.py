#fully written by Claude! I did not make this

"""
balance.py - balance calculator for your RPG.

Put this file in the same folder as player_data.py and enemy_data.py, then run:

    python balance.py                                   # typical build, every class, levels 1-3, every enemy
    python balance.py --classes Barbarian Rogue --levels 1 2 --enemies "Feral Dog"
    python balance.py --builds --classes Ranger --levels 4 --enemies "Warden Boss"
                                                        # best & worst possible level-up choices
    python balance.py --special --potions 1             # open with special attack, carry 1 potion
    python balance.py --runs 20000 --seed 1             # more precise / repeatable numbers

It reads your real Player and Enemy classes, so when you change a class's starting stats in
player_data.py or add an enemy to enemy_data.py, the numbers update automatically.

NOTE: the LEVEL-UP RULES below (stat gains and HP per level) are the planned design. If
player_data.py still has the old rules (+3 to two stats, +50%/+25% HP), update it to match.

WHAT IS MODELLED (matches encounter() and damage_calc() in dungeon_1.py)
  - hitting: d20 + stat modifier + level // 2 must be >= the target's AC (10 + dex modifier)
  - the 70%-130% damage roll, armor, vulnerable/resistant
  - stat modifiers come from the game's own stat_modifier() methods, so if you change those in
    player_data.py or enemy_data.py, the calculator follows automatically
  - the enemy's choice between melee / ranged / special attack (enemy_action_determiner)
  - the player attacking every round with their best weapon (or melee/ranged if you force it)

WHAT IS NOT MODELLED (yet)
  - Dodge, class actions (rage, multiattack, net), consumables beyond --potions, running away
"""
import argparse
import builtins
import contextlib
import copy
import io
import itertools
import random
from collections import Counter
from statistics import mean

import enemy_data
import player_data
from enemy_data import Enemy

# ======================= SETTINGS YOU CAN EDIT =======================
RUNS = 5000                  # fights simulated per matchup (normal tables)
BUILD_RUNS = 2000            # fights per build when testing every build (--builds)
MAX_ROUNDS = 200             # safety stop so a stalemate can't loop forever

# ---- LEVEL-UP RULES ----
# Each level-up, the player picks two different stats from this list. Gain per pick:
STAT_GAIN = {'strength': 2, 'dexterity': 2, 'melee_skill': 1, 'ranged_skill': 1}
# Flat max HP gained per level, by class:
HP_PER_LEVEL = {'Barbarian': 12, 'Hunter': 10, 'Ranger': 8, 'Rogue': 8}

# The "typical" build used in the normal tables: the two stats each class tends to pick.
# (Skills don't affect hitting or damage in the current formulas, so these are stat-only.
#  If you make skills matter, swap them back in.)
LEVEL_UP_PRIORITY = {
    'Barbarian': ('strength', 'dexterity'),
    'Ranger':    ('dexterity', 'strength'),
    'Rogue':     ('dexterity', 'strength'),
    'Hunter':    ('dexterity', 'strength'),
}

# ---- HIT RULES ----
# Your current hit formulas don't use melee_skill / ranged_skill. Set True to also add
# skill_modifier(skill) (= skill - 2) to the attack bonus, to see what skills would do.
SKILLS_ADD_TO_HIT = False
# Optional "natural roll" rules. Both off = exactly your current code (0% and 100% are possible).
NAT_20_ALWAYS_HITS = False
NAT_1_ALWAYS_MISSES = False

# Special attack minigame: damage multiplier you're assumed to get on average
PLAYER_SPECIAL_MULT = 1.0    # your special attack (1.25 perfect ... 0.5 terrible)
ENEMY_SPECIAL_MULT = 0.75    # how well you dodge the enemy's special (0.5 great ... 1.0 awful)

POTION_HEAL = 6              # average healing_potion heal (it rolls 4-8)
POTION_BELOW = 0.4           # drink a potion when HP is at or below this fraction of max

# Enemies that are built inside functions in dungeon_1.py. Copied here so they get tested too.
# (If you move them into enemy_data.py as module-level variables you can delete this.)
EXTRA_ENEMIES = [
    Enemy("Gelatinous Cube", 2, 1, 35, 6, 2, 11, 4, 0, 'Slashing', 'None', True, 'Basic'),
    Enemy('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic'),
]
# =====================================================================

LEVEL_UP_STATS = tuple(STAT_GAIN)          # the stats a player can choose from
NICE_NAMES = {'strength': 'STR', 'dexterity': 'DEX', 'melee_skill': 'melee skill',
              'ranged_skill': 'ranged skill'}


def all_enemies():
    found = {}
    for value in vars(enemy_data).values():
        if isinstance(value, Enemy):
            found[value.name] = value
    for enemy in EXTRA_ENEMIES:
        found[enemy.name] = enemy
    return found


_base_players = {}


def base_player(class_name):
    """A fresh level 1 Player, built by running player_selection() with fake input."""
    if class_name not in _base_players:
        def fake_input(prompt=''):
            if 'called' in prompt:
                return 'Sim'
            if 'like to be' in prompt:
                return class_name
            return ''

        real_input = builtins.input
        builtins.input = fake_input
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                _base_players[class_name] = player_data.player_selection()
        finally:
            builtins.input = real_input
    return copy.copy(_base_players[class_name])


def make_player(class_name, level, picks=None):
    """A player of the given level. picks = one pair of stats per level-up (default: typical build)."""
    if picks is None:
        picks = [LEVEL_UP_PRIORITY[class_name]] * (level - 1)
    player = base_player(class_name)
    for pair in picks:
        for stat in pair:
            setattr(player, stat, getattr(player, stat) + STAT_GAIN[stat])
        player.max_health += HP_PER_LEVEL[class_name]
    player.level = level
    player.health = player.max_health
    return player


def all_builds(level):
    """Every possible set of level-up choices (order doesn't matter, so no duplicates)."""
    pairs = list(itertools.combinations(LEVEL_UP_STATS, 2))
    return itertools.combinations_with_replacement(pairs, level - 1)


def describe_picks(picks):
    counts = Counter(stat for pair in picks for stat in pair)
    if not counts:
        return '(no level-ups yet)'
    return ', '.join(f"{NICE_NAMES[stat]} x{n}" for stat, n in counts.most_common())


# ---------------------------- exact maths ----------------------------

def hit_chance(attack_bonus, armor_class_value):
    """Exact chance that d20 + attack_bonus >= armor class (checks all 20 rolls)."""
    hits = 0
    for roll in range(1, 21):
        if roll == 20 and NAT_20_ALWAYS_HITS:
            hits += 1
        elif roll == 1 and NAT_1_ALWAYS_MISSES:
            continue
        elif roll + attack_bonus >= armor_class_value:
            hits += 1
    return hits / 20


def damage_rolls(base, damage_mod, armor, vulnerable=False, resistant=False):
    """Every possible damage value for one hit (each equally likely), like damage_calc()."""
    rolls = []
    for roll in range(int(base * 0.7), int(base * 1.3) + 1):
        damage = int(max(1, roll + damage_mod - armor))
        if vulnerable:
            damage *= 2
        elif resistant:
            damage //= 2
        rolls.append(damage)
    return rolls


def armor_class(creature):
    """AC = 10 + dex modifier. Works for a Player or an Enemy (each has its own stat_modifier)."""
    return 10 + creature.stat_modifier(creature.dexterity)


def player_attack_bonus(player, kind):
    stat = player.strength if kind == 'Melee' else player.dexterity
    bonus = player.stat_modifier(stat) + player.level // 2
    if SKILLS_ADD_TO_HIT:
        skill = player.melee_skill if kind == 'Melee' else player.ranged_skill
        bonus += player.skill_modifier(skill)
    return bonus


def player_profiles(player, enemy):
    profiles = {}
    for kind in ('Melee', 'Ranged'):
        weapon = player.melee if kind == 'Melee' else player.ranged
        stat = player.strength if kind == 'Melee' else player.dexterity
        vulnerable = weapon.damage_type != 'None' and weapon.damage_type == enemy.vulnerable
        resistant = weapon.damage_type != 'None' and weapon.damage_type == enemy.resistant
        hit = hit_chance(player_attack_bonus(player, kind), armor_class(enemy))
        rolls = damage_rolls(weapon.damage, player.stat_modifier(stat), enemy.armor, vulnerable, resistant)
        profiles[kind] = {'hit': hit, 'rolls': rolls, 'avg': mean(rolls), 'per_round': hit * mean(rolls)}
    return profiles


def enemy_profiles(enemy, player):
    player_ac = armor_class(player)
    melee_bonus = enemy.stat_modifier(enemy.strength) + enemy.level // 2
    profiles = {
        'Melee': {'hit': hit_chance(melee_bonus, player_ac),
                  'rolls': damage_rolls(enemy.melee, enemy.stat_modifier(enemy.strength), player.armor)},
    }
    if enemy.ranged > 0:
        ranged_bonus = enemy.stat_modifier(enemy.dexterity) + enemy.level // 2
        profiles['Ranged'] = {'hit': hit_chance(ranged_bonus, player_ac),
                              'rolls': damage_rolls(enemy.ranged, enemy.stat_modifier(enemy.dexterity),
                                                    player.armor)}
    for profile in profiles.values():
        profile['avg'] = mean(profile['rolls'])
        profile['per_round'] = profile['hit'] * profile['avg']
    return profiles


def enemy_choice(enemy, enemy_hp, player_hp, special_ready):
    """Same decision as enemy_action_determiner() in dungeon_1.py."""
    if enemy.boss and special_ready:
        return 'Special'
    if enemy.boss:
        return 'Ranged' if enemy.ranged > 0 else 'Melee'
    if enemy_hp < player_hp and enemy.ranged > 0:
        return 'Ranged'
    return 'Melee'


# ---------------------------- simulation ----------------------------

def simulate_fight(player, enemy, mine, theirs, kind, use_special, potions, rng):
    """One fight. Returns (won, rounds, damage_taken)."""
    player_hp = player.max_health
    enemy_hp = enemy.health
    enemy_special_ready = enemy.special_attack_available
    special_left = use_special
    taken = 0
    special_damage = int(max(1, player.melee.damage * 2 * PLAYER_SPECIAL_MULT - enemy.armor))
    enemy_special_damage = int(max(1, enemy.melee * 2 * ENEMY_SPECIAL_MULT - player.armor))

    for rounds in range(1, MAX_ROUNDS + 1):
        # --- your turn ---
        if potions > 0 and player_hp <= player.max_health * POTION_BELOW:
            player_hp = min(player.max_health, player_hp + POTION_HEAL)
            potions -= 1
        elif special_left:
            enemy_hp -= special_damage
            special_left = False
        elif rng.random() < mine[kind]['hit']:
            enemy_hp -= rng.choice(mine[kind]['rolls'])
        if enemy_hp <= 0:
            return True, rounds, taken

        # --- enemy's turn ---
        choice = enemy_choice(enemy, enemy_hp, player_hp, enemy_special_ready)
        if choice == 'Special':
            damage = enemy_special_damage
            enemy_special_ready = False
        elif rng.random() < theirs[choice]['hit']:
            damage = rng.choice(theirs[choice]['rolls'])
        else:
            damage = 0
        taken += min(damage, player_hp)
        player_hp -= damage
        if player_hp <= 0:
            return False, rounds, taken
    return False, MAX_ROUNDS, taken


def verdict(win_rate, hp_lost_pct):
    if win_rate < 0.5:
        return 'DEADLY'
    if win_rate < 0.9:
        return 'HARD'
    if hp_lost_pct > 60:
        return 'TOUGH'
    if hp_lost_pct < 20:
        return 'EASY'
    return 'FAIR'


def analyse(player, enemy, args, rng, runs):
    mine = player_profiles(player, enemy)
    kind = args.weapon.capitalize()
    if args.weapon == 'best':
        kind = max(mine, key=lambda k: mine[k]['per_round'])
    theirs = enemy_profiles(enemy, player)

    results = [simulate_fight(player, enemy, mine, theirs, kind, args.special, args.potions, rng)
               for _ in range(runs)]
    win_rate = mean(1 if won else 0 for won, _, _ in results)
    avg_taken = mean(taken for _, _, taken in results)
    hp_lost_pct = avg_taken / player.max_health * 100

    first = enemy_choice(enemy, enemy.health, player.max_health, False)
    my_per_round = mine[kind]['per_round']
    their_per_round = theirs[first]['per_round']
    return {
        'class': player.class_name, 'level': player.level, 'hp': player.max_health, 'weapon': kind,
        'stats': (player.strength, player.dexterity, player.melee_skill, player.ranged_skill, player.armor,
                  armor_class(player)),
        'my_hit': mine[kind]['hit'] * 100, 'my_dmg': mine[kind]['avg'],
        'rounds_to_kill': enemy.health / my_per_round if my_per_round else float('inf'),
        'their_hit': theirs[first]['hit'] * 100, 'their_dmg': theirs[first]['avg'],
        'rounds_to_die': player.max_health / their_per_round if their_per_round else float('inf'),
        'win': win_rate * 100, 'hp_lost': hp_lost_pct,
        'in_a_row': player.max_health / avg_taken if avg_taken else float('inf'),
        'verdict': verdict(win_rate, hp_lost_pct),
    }


# ---------------------------- printing ----------------------------

def fmt(value, places=1):
    if value == float('inf') or value > 99:
        return '99+'
    return f'{value:.{places}f}'


def print_table(enemy, rows):
    print(f"\n=== {enemy.name}  (level {enemy.level}, {enemy.health} HP, armor {enemy.armor}, "
          f"AC {armor_class(enemy):g}, dex {enemy.dexterity}, str {enemy.strength}, boss: {enemy.boss}) ===")
    print(f"{'Class':<10}{'Lv':>3}{'HP':>4} {'Weap':<6}| "
          f"{'Hit%':>5}{'Dmg':>6}{'RtK':>6} | {'Hit%':>5}{'Dmg':>6}{'RtD':>6} | "
          f"{'Win%':>6}{'HPlost%':>8}{'InARow':>7}  Verdict")
    print(f"{'':<10}{'':>3}{'':>4} {'':<6}| {'--- YOU HIT THEM ---':^17} | "
          f"{'--- THEY HIT YOU ---':^17} | {'------- OVERALL -------':^23}")
    for r in rows:
        print(f"{r['class']:<10}{r['level']:>3}{r['hp']:>4} {r['weapon']:<6}| "
              f"{r['my_hit']:>5.0f}{r['my_dmg']:>6.1f}{fmt(r['rounds_to_kill']):>6} | "
              f"{r['their_hit']:>5.0f}{r['their_dmg']:>6.1f}{fmt(r['rounds_to_die']):>6} | "
              f"{r['win']:>6.1f}{r['hp_lost']:>8.0f}{fmt(r['in_a_row']):>7}  {r['verdict']}")


def print_build(title, r):
    strength, dexterity, melee_skill, ranged_skill, armor, ac = r['stats']
    print(f"  {title}: {describe_picks(r['picks'])}")
    print(f"    Stats:  HP {r['hp']} | STR {strength} | DEX {dexterity} | "
          f"melee skill {melee_skill} | ranged skill {ranged_skill} | armor {armor} | AC {ac:g}")
    print(f"    You:    {r['weapon']} hits {r['my_hit']:.0f}% for {r['my_dmg']:.1f} avg "
          f"-> kill it in ~{fmt(r['rounds_to_kill'])} rounds")
    print(f"    Enemy:  hits {r['their_hit']:.0f}% for {r['their_dmg']:.1f} avg "
          f"-> kills you in ~{fmt(r['rounds_to_die'])} rounds")
    print(f"    Result: win {r['win']:.1f}% | lose {r['hp_lost']:.0f}% of your HP per fight | "
          f"{fmt(r['in_a_row'])} fights in a row | {r['verdict']}")


def best_and_worst(class_name, level, enemy, args):
    results = []
    for picks in all_builds(level):
        # same dice for every build, so differences come from the build and not from luck
        rng = random.Random(args.seed if args.seed is not None else 12345)
        player = make_player(class_name, level, picks)
        result = analyse(player, enemy, args, rng, args.build_runs)
        result['picks'] = picks
        results.append(result)
    # best = wins most often, then loses the least HP
    results.sort(key=lambda r: (-r['win'], r['hp_lost']))

    print(f"\n=== {class_name}, level {level} vs {enemy.name}: {len(results)} possible "
          f"build{'s' if len(results) != 1 else ''} tested ===")
    if len(results) == 1:
        print("  (level 1 has no level-up choices)")
    print_build('BEST ', results[0])
    if len(results) > 1:
        print_build('WORST', results[-1])
        print(f"  Average build: win {mean(r['win'] for r in results):.1f}% | "
              f"lose {mean(r['hp_lost'] for r in results):.0f}% of HP per fight")


LEGEND = """
How to read it:
  Hit%     chance an attack lands.            Dmg   average damage when it does land
  RtK      rounds for YOU to kill THEM        RtD   rounds for THEM to kill YOU (both on average, no healing)
  Win%     how often you win the whole fight  HPlost%  average % of your max HP lost per fight
  InARow   how many of these fights you could take back-to-back on average before dying (no resting)
  Verdict  DEADLY (<50% wins) / HARD (<90%) / TOUGH (lose >60% HP) / EASY (lose <20% HP) / FAIR
Hit% uses d20 + modifier + level//2 vs AC (10 + dex modifier). Armor only reduces damage.
Normal tables use each class's "typical build" (LEVEL_UP_PRIORITY). Use --builds to see every build.
Not modelled: dodging, class actions, running away. Use --special / --potions to add those options."""


def main():
    parser = argparse.ArgumentParser(description="Balance calculator for the RPG")
    parser.add_argument('--classes', nargs='+', default=list(LEVEL_UP_PRIORITY))
    parser.add_argument('--levels', nargs='+', type=int, default=[1, 2, 3])
    parser.add_argument('--enemies', nargs='+', default=None,
                        help='enemy names (use quotes for names with spaces)')
    parser.add_argument('--builds', action='store_true',
                        help='try every possible level-up choice and show the best and worst build')
    parser.add_argument('--runs', type=int, default=RUNS)
    parser.add_argument('--build-runs', type=int, default=BUILD_RUNS, dest='build_runs')
    parser.add_argument('--weapon', choices=['best', 'melee', 'ranged'], default='best')
    parser.add_argument('--special', action='store_true', help='open each fight with your special attack')
    parser.add_argument('--potions', type=int, default=0, help='potions carried into each fight')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    enemies = all_enemies()
    if args.enemies:
        wanted = {name.lower() for name in args.enemies}
        enemies = {n: e for n, e in enemies.items() if n.lower() in wanted}
        if not enemies:
            raise SystemExit("No enemy matched. Available: " + ', '.join(all_enemies()))

    classes = [c.capitalize() for c in args.classes]
    if args.builds:
        for enemy in enemies.values():
            for class_name in classes:
                for level in args.levels:
                    best_and_worst(class_name, level, enemy, args)
        return

    rng = random.Random(args.seed)
    for enemy in enemies.values():
        rows = [analyse(make_player(c, lv), enemy, args, rng, args.runs)
                for c in classes for lv in args.levels]
        print_table(enemy, rows)
    print(LEGEND)


if __name__ == '__main__':
    main()