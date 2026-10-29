import sys
import random

level_up_experience = 100

#creates player data
class Player:
    def __init__(self, class_name, name, level, experience, gold, health, dexterity, strength, armor, melee_skill, ranged_skill, intelligence, melee, ranged, special_attack, special_attack_available, class_action, class_action_available):
        self.class_name = class_name
        self.name = name
        self.level = level
        self.experience = experience
        self.gold = gold
        self.health = health
        self.max_health = health
        self.dexterity = dexterity
        self.max_dexterity = dexterity
        self.strength = strength
        self.max_strength = strength
        self.armor = armor
        self.melee_skill = melee_skill
        self.ranged_skill = ranged_skill
        self.intelligence = intelligence
        self.mana = intelligence
        self.max_mana = self.mana
        self.known_spells = []
        self.melee = melee
        self.ranged = ranged
        self.special_attack = special_attack
        self.special_attack_available = special_attack_available
        self.class_action = class_action
        self.class_action_available = class_action_available

    def stat_modifier(self, stat):
        return (stat - 10)//2

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            print("You have died.")
            input("")
            print("Your statistics were as follows.")
            #chatGPT made this
            for stat, value in self.__dict__.items():
                print(f"{stat.capitalize()}: {value}")
            input("")
            print("Do not have fear! Try again, Ravenport needs you!")
            input("")
            sys.exit("Game over.")

    def heal(self, healing):
        self.health += healing
        if self.health > self.max_health:
            self.health = self.max_health

    def add_gold(self, gold):
        self.gold += gold

    def add_armor(self, armor_adding):
        self.armor += armor_adding

    def level_up_experience_calculator(self):
        return (level_up_experience - self.experience)

    def add_experience(self, exp):
        global level_up_experience
        self.experience += exp
        while self.experience >= level_up_experience:
            self.dexterity = self.max_dexterity
            self.strength = self.max_strength
            stats = {
                "Melee skill" : "melee_skill",
                "Ranged skill" : "ranged_skill",
                "Dexterity" : "dexterity",
                "Strength" : "strength",
                "Intelligence" : 'intelligence'
            }
            stats_selected = []
            stats_remaining = 2

            #this makes the player pick two stats to increase, and then puts it itno the stats_selected list
            print("You level up! Of the following stats, pick two you would like to increase.")
            while stats_remaining > 0:
                for stat in stats:
                    print(stat)

                stat_increase = input(f"Which stat would you like to increase? ({stats_remaining} left) ").capitalize()
                if stat_increase in stats:
                    print(f"You increase {stat_increase}!")
                    stats_selected.append(stats[stat_increase])
                    del stats[stat_increase]
                    stats_remaining -= 1
                else:
                    print("Please pick a valid stat!")

            #this adds +2 to the stat or +1 to the skill selected by the player
            number = 0
            while number < 2:
                if stats_selected[number] in ('melee_skill', 'ranged_skill'):
                    setattr(self, stats_selected[number], (getattr(self, stats_selected[number]) + 1))
                else:
                    setattr(self, stats_selected[number], (getattr(self, stats_selected[number]) + 2))
                number += 1

            #this adds health depending on class to the player
            if self.class_name == 'Barbarian':
                self.max_health += 12
            elif self.class_name == 'Hunter':
                self.max_health += 10
            else:
                self.max_health += 8

            #this increases the player level and required EXP for the next level
            self.level += 1
            self.experience -= level_up_experience
            level_up_experience = int(level_up_experience * 1.5)

            #this increases max strength and dex to the amount they should be at
            self.max_dexterity = self.dexterity
            self.max_strength = self.strength
            self.health = self.max_health

            #increases max mana and resets mana to max mana
            self.max_mana = self.intelligence
            self.mana = self.max_mana

            #this prints your new stats
            print("Here are your new stats!")
            #chatGPT made this
            for stat, value in self.__dict__.items():
                print(f"{stat.capitalize()}: {value}")
            input()

    def rage(self):
        self.dexterity -= 3
        self.strength += 3

    def rage_end(self):
        self.dexterity = self.max_dexterity
        self.strength = self.max_strength

    def rest(self):
        self.health += (self.max_health // 2)
        if self.health > self.max_health:
            self.health = self.max_health
        self.special_attack_available = True
        self.class_action_available = True
        self.mana = self.max_mana

    def learn_spell(self, spell):
        self.known_spells.append(spell)


class Item:
    def __init__(self, name, type, amount=1, healing=0, damage=0, damage_type='None', attack_type='Medium'):
        self.name = name
        self.type = type
        self.damage = damage
        self.damage_type = damage_type
        self.attack_type = attack_type
        self.amount = amount
        self.healing = healing

    def add_item(self, amount):
        self.amount += amount

    def use_item(self, amount):
        self.amount -= amount

    def amount_healing(self):
        return random.randint(self.healing[0], self.healing[1])


sword = Item('Sword', 'Melee', damage=6, damage_type='Slashing')
dagger = Item('Dagger', 'Melee', damage=4, damage_type='Slashing', attack_type='Light')
bow = Item('Bow', 'Ranged', damage=8, damage_type='Piercing')
arrows = Item('Arrows', 'Usable', 20)
healing_potion = Item('Healing potion', 'Consumable', 0, healing=(4,8))

player_inventory = [sword, bow, arrows, healing_potion]

class Spell:
    def __init__(self, name, mana_cost, spell_description, spell_type, damage=0, damage_type='None', healing=0, action='Action'):
        self.name = name
        self.mana_cost = mana_cost
        self.spell_description = spell_description
        self.spell_type = spell_type
        self.damage = damage
        self.damage_type = damage_type
        self.healing = healing
        self.action = action

    #returns either 'Spell fails', 'Healing', 'Spell hits', 'Spell misses', or 'Support'
    def cast_spell(self, player, spell_bonus, enemy_AC):
        if self.mana_cost <= player.mana:
            player.mana -= self.mana_cost
            print(f"You cast {self.name.lower()}! You have {player.mana} mana left.")
            if self.spell_type == 'Healing':
                heal_amount = random.randint(self.healing[0], self.healing[1])
                player.heal(heal_amount)
                print(f"You heal {heal_amount} HP.")
                return 'Healing'
            elif self.damage > 0:
                if spell_bonus >= enemy_AC:
                    return 'Spell hits'
                else:
                    print(f"You cast {self.name.lower()} but it misses!")
                    return 'Spell misses'
            elif self.spell_type == 'Support':
                return 'Support'
        else:
            print("Not enough mana!")
            print("Spellcasting failed.")
            input()
            return 'Spell fails'


minor_healing_spell = Spell('Minor healing', 2, 'Heals 4-8 HP', 'Healing', healing=(4,8), action='Bonus action')
firebolt = Spell('Firebolt', 4, 'Shoots a small ball of fire towards your enemy', 'Offensive', 6, 'Fire')
freeze = Spell('Freeze', 6, 'Freezes your enemy for 2 turns', 'Support', 2, 'Cold')
poison = Spell('Poison', 5, 'Creates a cloud of poisonous gas that damages enemies', 'Offensive', 12, 'Poison') #not currently working as intended, it should do this damage over 2-3 turns
tornado = Spell('Tornado', 4, 'Creates a whirlpool which pulls in enemies', 'Support', 2, 'Force') #doesn't work at all
shield = Spell('Shield', 3, 'Creates a magical shield which protects you from enemy attacks', 'Support', action='Bonus action')
searing_smite = Spell('Searing smite', 3, 'Enchants your melee weapon, increasing its damage for 2 turns', 'Support', action='Bonus action')
fireball = Spell('Fireball', 8, 'Shoots a large ball of fire towards your enemy, possibly damaging surrounding enemies.', 'Offensive', 16, 'Fire')
earth_spike = Spell('Earth spike', 6, 'Creates a large spike out of the ground which damages an enemy', 'Offensive', 12, 'Force')
arcane_blast = Spell('Arcane blast', 2, 'Creates a bolt of arcane magic which damages your enemies', 'Offensive', 3, 'Force')


#the idea is that when there are more spells, you can pick or exchange them when you level up. Upcasting might become a thing too
spellbook = {
    1 : {
    'Barbarian' : [searing_smite, earth_spike],
    'Ranger' : [shield, freeze, arcane_blast], #tornado too
    'Rogue' : [freeze, searing_smite, poison, arcane_blast],
    'Hunter' : [freeze, poison, shield, earth_spike],
    'Mage' : [minor_healing_spell, firebolt, freeze, poison, shield, searing_smite, fireball, earth_spike, arcane_blast] #tornado too 
    },
}

def player_selection(dev):
    if dev != 'dev':
        name = input("What would you like to be called adventurer? ")
        print(f"Welcome {name}! It's time to choose your class! Here are the options.")
        print("Barbarian. A strong, tanky, and melee based class. If you want to smash stuff, you're a barbarian.")
        input()
        print("Ranger. A quick, smart, and ranged based class. If you want to dodge attacks and shoot from afar, you're a ranger.")
        input()
        print("Rogue. A sneaky, quiet, and ambush based class. If you want to sneak up to an enemy to kill it, you're a rogue.")
        input()
        print("Mage. A smart spellcaster that uses spells to attack enemies. If you want to use your intelligence as your power, you're a mage.")
        input()
        print("Hunter. Last but not least, the hunter. A jack of all trades, but master of none. If you don't know what to pick, you're a hunter.")
    else:
        name = 'dev'
        
    while True:
        class_selection = input("What would you like to be? ").capitalize()
        if class_selection == 'Barbarian':
            print("You are now a Barbarian!")
            return Player('Barbarian', name, 1, 0, 0, 24, 7, 14, 2, 1, 0, 6, sword, bow, 'Basic', True, 'Basic', True)
        elif class_selection == 'Ranger':
            print("You are now a Ranger!")
            return Player('Ranger', name, 1, 0, 0, 18, 15, 8, 1, 0, 2, 12, sword, bow, 'Basic', True, 'Basic', True)
        elif class_selection == 'Rogue':
            print("You are now a Rogue!")
            player_inventory.remove(sword)
            player_inventory.append(dagger)
            return Player('Rogue', name, 1, 0, 0, 20, 17, 12, 1, 1, 0, 10, dagger, bow, 'Basic', True, 'Basic', True)
        elif class_selection == 'Mage':
            print("You are now a Mage!")
            return Player('Mage', name, 1, 0, 0, 18, 10, 8, 2, 0, 2, 15, sword, bow, 'Basic', True, 'Basic', True)
        elif class_selection == 'Hunter':
            print("You are now a Hunter!")
            return Player('Hunter', name, 1, 0, 5, 22, 12, 12, 1, 1, 1, 12, sword, bow, 'Basic', True, 'Basic', True)
        else:
            print("Please select a valid class!")