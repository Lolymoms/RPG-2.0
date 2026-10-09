import sys

#creates player data
class Player:
    def __init__(self, class_name, level, experience, gold, health, max_health, dexterity, strength, melee_skill, ranged_skill, intelligence, melee, ranged):
        self.class_name = class_name
        self.level = level
        self.experience = experience
        self.gold = gold
        self.health = health
        self.max_health = max_health
        self.dexterity = dexterity
        self.strength = strength
        self.melee_skill = melee_skill
        self.ranged_skill = ranged_skill
        self.intelligence = intelligence
        self.melee = melee
        self.ranged = ranged

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
            return Player('Barbarian', 1, 0, 0, 25, 25, 8, 12, 15, 4, 4, sword, bow)
        elif class_selection == 'Ranger':
            print("You are now a Ranger!")
            return Player('Ranger', 1, 0, 0, 16, 16, 12, 6, 2, 12, 12, sword, bow)
        elif class_selection == 'Rogue':
            print("You are now a Rogue!")
            return Player('Rogue', 1, 0, 0, 18, 18, 16, 12, 10, 10, 6, sword, bow)
        elif class_selection == 'Hunter':
            print("You are now a Hunter!")
            return Player('Hunter', 1, 0, 0, 20, 20, 10, 10, 10, 10, 10, sword, bow)
        else:
            print("Please select a valid class!")