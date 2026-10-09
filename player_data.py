import sys

level_up_experience = 100

#modifier = (stat - 10)/2

#creates player data
class Player:
    def __init__(self, class_name, level, experience, gold, health, dexterity, strength, armor, melee_skill, ranged_skill, intelligence, melee, ranged, special_attack, special_attack_available, class_action, class_action_available):
        self.class_name = class_name
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
        self.melee = melee
        self.ranged = ranged
        self.special_attack = special_attack
        self.special_attack_available = special_attack_available
        self.class_action = class_action
        self.class_action_available = class_action_available

    def stat_modifier(self, stat):
        return (stat - 10)//2

    def skill_modifier(self, skill):
        return skill - 2

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

    def add_experience(self, exp):
        self.experience += exp
        if self.experience >= level_up_experience:
            print("You level up! make the logic later lowk")

    def rage(self):
        self.dexterity -= 3
        self.strength += 3

    def rage_end(self):
        self.dexterity = self.max_dexterity
        self.strength = self.max_strength


class Item:
    def __init__(self, name, type, amount=1, healing=0, damage=0, damage_type='None', attack_type='None'):
        self.name = name
        self.type = type
        self.damage = damage
        self.damage_type = damage_type
        self.attack_type = attack_type
        self.amount = amount
        self.healing = healing

sword = Item('Sword', 'Melee', damage=6, damage_type='Slashing', attack_type='Normal')
bow = Item('Bow', 'Ranged', damage=8, damage_type='Piercing')
arrows = Item('Arrows', 'Consumable', 20)

player_inventory = [sword, bow, arrows]

def player_selection():
    print("It's time to choose your class! Here are the options.")
    print("Barbarian. A strong, tanky, and melee based class. If you want to smash stuff, you're a barbarian.")
    input()
    print("Ranger. A quick, smart, and ranged based class. If you want to dodge attacks and shoot from afar, you're a ranger.")
    input()
    print("Rogue. A sneaky, quiet, and ambush based class. If you want to sneak up to an enemy to kill it, you're a rogue.")
    input()
    print("Last but not least, the hunter. A jack of all trades, but master of none. If you don't know what to pick, you're a hunter.")
    while True:
        class_selection = input("What would you like to be? ").capitalize()
        if class_selection == 'Barbarian':
            print("You are now a Barbarian!")
            return Player('Barbarian', 1, 0, 0, 24, 7, 15, 2, 2, 0, 6, sword, bow, 'Basic', True, 'Basic', True)
        elif class_selection == 'Ranger':
            print("You are now a Ranger!")
            return Player('Ranger', 1, 0, 0, 18, 15, 8, 1, 1, 3, 12, sword, bow, 'Basic', True, 'Basic', True)
        elif class_selection == 'Rogue':
            print("You are now a Rogue!")
            return Player('Rogue', 1, 0, 0, 20, 15, 12, 0, 2, 1, 10, sword, bow, 'Basic', True, 'Basic', True)
        elif class_selection == 'Hunter':
            print("You are now a Hunter!")
            return Player('Hunter', 1, 0, 5, 22, 12, 10, 1, 2, 2, 12, sword, bow, 'Basic', True, 'Basic', True)
        else:
            print("Please select a valid class!")