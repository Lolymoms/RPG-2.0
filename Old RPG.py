import random
import sys
import time
#creates available for the directions() function
available = 0
#creates row and column for dungeon_1
#row is up and down
row = 0
#column is left to right
column = 0

#creates action variable for general use
action = 0
#creates random variable for random numbers
randomnum = 0
#creates damage variable for damage
damage = 0
#creates direction_chosen variable, which will turn False when a valid direction is chosen
direction_chosen = False
#creates dead, which will turn true when a monster dies
fighting = True
#creates gold, which will be used for gold stuff
gold = 0
#creates the many_enemies list, which will be used for when you fight multiple enemies
many_enemies = []
#creates a list that will be used for the directions() function
possible_directions = []
#creates a variable used in empty_room()
empty_room_number = 1
#amount of experience needed to level up
level_up_experience = 100
#used to track if the player has seen the blacksmith before, used in blacksmith()
visited_blacksmith = False
#creates ranged and melee variables, used in player_data
ranged = 'Bow'
melee = 'Sword'
#creates lists with all ranged and melee items
melee_items = ['Sword', 'Longsword', 'Dagger', 'Mace', 'Scimitar', 'Legendary sword']
ranged_items = ['Bow', 'Longbow', 'Crossbow', 'Throwing star', 'Blowgun']
#creates list with all current items
current_melee = []
current_ranged = []
#creates a variable that tracks the player's current dungeon level
dungeon_level = 1
#creates a variable used much later
fighting_patrolling_goblins = False

shop_inventory = {
    'Dagger' : {
        'Price' : 5,
        'Damage' : 3,
        'Type' : 'Melee',
        'Quantity' : 1
    },

    'Mace' : {
        'Price' : 12,
        'Damage' : 9,
        'Type' : 'Melee',
        'Quantity' : 1
    },

    'Longbow' : {
        'Price' : 15,
        'Damage' : 12,
        'Type' : 'Ranged',
        'Quantity' : 1
    },

    'Arrows' : {
        'Price' : 1,
        'Quantity' : 20,
        'Type' : 'Consumable'
    },

    'Special attack potion' : {
        'Price' : 10,
        'Quantity' : 1,
        'Type' : 'Consumable'
    },

    'Strength potion' : {
        'Price' : 10,
        'Quantity' : 2,
        'Type' : 'Consumable'
    },

    'Health potion' : {
        'Price' : 6,
        'Quantity' : 3,
        'Type' : 'Consumable'
    }
}

#creates an inventory for the player
player_inventory = {
    'Bow' : 7,
    'Sword' : 5,
    'Arrows' : 20,
}

#creates player data
player_data = {
    'Health' : 20,
    'Max Health' : 20,
    'Defense' : 5,
    'Max Defense' : 5,
    'Armor' : 1,
    'Strength' : 0,
    'Gold' : 0,
    'Level' : 1,
    'Experience' : 0,
    'Special Attack' : 'Basic',
    'Special Attack Available' : True
}


#creates a lot of enemies' dictionaries
goblins = {
    'name_enc' : 'Goblins',
    'health' : 4,
    'damage_enc' : 3,
    'damage_enc_ranged' : 0,
    'defense' : 5,
    'strength' : 2,
    'armor_enc' : 1,
    'cl_enc' : 1,
}

feral_dog = {
   'name_enc' : 'Feral Dog',
   'health' : 10,
   'damage_enc' : 5,
   'damage_enc_ranged' : 0,
   'defense' : 3,
   'strength' : 3,
   'armor_enc' : 1,
   'cl_enc' : 1,
}


baby_orc = {
   'name_enc' : 'Baby Orc',
   'health' : 15,
   'damage_enc' : 6,
   'damage_enc_ranged' : 0,
   'defense' : 3,
   'strength' : 4,
   'armor_enc' : 2,
   'cl_enc' : 2,
}


#all the functions for the program

#this essentially makes it so that only numbers work, and there's an optional parameter function
def number(asking, parameter=None):
    while True:
        try:
            action = int(input(asking))
            if parameter is None or action in parameter:
                return action
            else:
                print("Please enter a valid number!")

        except ValueError:
            print("Please enter a valid number!")


#uses coordinates to find what directions the player can go
def find_directions():
    possible_directions = [1, 2, 3, 4]
    if dungeon_level == 1:
        #edges of the map
        if row == 0:
            possible_directions.remove(1)
        if row == 3:
            possible_directions.remove(4)
        if column == 0:
            possible_directions.remove(2)
        if column == 3:
            possible_directions.remove(3)

        #wall logic
        if row == 2 and column == 1:
            possible_directions.remove(3)
        if row == 3 and column == 1:
            possible_directions.remove(3)

        if row == 1 and column == 2:
            possible_directions.remove(4)

        #makes the player fight the boss if they don't pry open the gates
        if column == 3 and row > 0:
            possible_directions.clear()
            possible_directions.append(4)
    elif dungeon_level == 2:
        #edges of the map
        if row == 0:
            possible_directions.remove(1)
        if row == 4:
            possible_directions.remove(4)
        if column == 0:
            possible_directions.remove(2)
        if column == 4:
            possible_directions.remove(3)

        #wall logic
        if row == 2 and column == 0:
            possible_directions.remove(4)
        if row == 2 and column == 1:
            possible_directions.remove(4)
        if row == 3 and column == 2:
            possible_directions.remove(2)

        if row == 0 and column == 2:
            possible_directions.remove(3)
        if row == 1 and column == 2:
            possible_directions.remove(3)
        if row == 2 and column == 3:
            possible_directions.remove(1)
        if row == 1 and column == 4:
            possible_directions.remove(2)
        if row == 0 and column == 4:
            possible_directions.remove(2)

        #boss logic
        if row == 4 and column < 2:
            possible_directions.clear()
            possible_directions.append(2)
        
    return possible_directions

#created directions(), inputs will determine what directions are shown
def directions(*available):
    print(f"You see {len(available)} exits to this room.")

    if 1 in available:
        print("1) Up")

    if 2 in available:
        print("2) Left")

    if 3 in available:
        print("3) Right")

    if 4 in available:
        print("4) Down")

    direction_chosen = True

    while direction_chosen:
        direction = number("Where do you go? ", available)
        if direction in available:
            direction_chosen = False
            return direction
        else:
            print("Please pick a valid direction.")

#function for if the player dies
def death():
    print("You have died.")
    input("")
    print("Your statistics were as follows.")
    #chatGPT made this
    for stat, value in player_data.items():
        print(f"{stat}: {value}")
    input("")
    print("Do not have fear! Try again, Ravenport needs you!")
    input("")
    sys.exit("Game over.")

#function for a room with gold in it
def gold_room():
    print("You walk into a room with a chest in it.")
    action = input("What do you want to do? (Open/Leave) ").capitalize()

    if action == 'Open':
        #generates a random number to determine reward/mimic
        randomnum = random.randint(1,10)
        #if the random number is 4 or below, it's 5 gold
        if randomnum < 5:
            print("You open the chest and find some gold!")
            print("+5 gold")
            player_data['Gold'] += 5
            print(f"You have {player_data['Gold']} gold.")
            input()
        #if the random number is 5-9, it's a mimic
        elif randomnum >= 5 and randomnum < 10:
            print("You open the chest and are attacked by a mimic!")
            damage = max(0, (4 - player_data["Armor"]))
            print(f"You lose {damage} HP.")
            player_data['Health'] -= damage
            print(f"You have {player_data['Health']} health left.")
            input()
        #if the random number is 10, there's a suit of armor
        elif randomnum == 10:
            print("You find an old suit of armor!")
            print("The suit has 8 defense")
            print(f"You have {player_data['Defense']}")
            take_or_leave = input("Take it or leave it? (Take/Leave) ").capitalize()
            #logic for taking or leaving the armor
            if take_or_leave == 'Take':
                print("You took the old armor")
                player_data['Max Defense'] = 8
                player_data['Defense'] = player_data["Max Defense"]
            else:
                print("You decide not to take the old armor")
        #if the player dies, kills them
        if player_data["Health"] <= 0:
            death()

        print("There seems to be nothing else in the room.")
        input()
    else:
        print("You decide to leave the chest.")

#a function that returns the damage dealt
def attack(name_enc, defense, armor_enc, attack_type='Player', strength=0, damage_enc=0, damage_enc_ranged=0):
    if attack_type == 'Monster':
        if (strength + random.randint(1, 20)) > (player_data["Defense"] + random.randint(1,10)):
            damage = max((strength // 2), (damage_enc - player_data["Armor"]))
            player_data["Health"] -= damage
            print(f"The {name_enc} hits you! It deals {damage} damage.")
            print(f"You have {player_data['Health']} health left")
            input("")
        else:
            print("The monster misses its attack!")
            damage = 0
    elif attack_type == 'Monster ranged':
        if (random.randint(1,20)) > (player_data["Defense"] + random.randint(1,10)):
            damage = max((strength // 2), (damage_enc_ranged - player_data["Armor"]))
            player_data["Health"] -= damage
            print(f"You have {player_data['Health']} health left")
            input("")
        else:
            print("The monster misses its attack!")
            damage = 0
    elif attack_type == 'Player':
        if (random.randint(1,20) + player_data["Strength"]) > (defense + random.randint(1,10)):
            damage = max((player_data['Strength'] // 2), (player_inventory[melee] - armor_enc))
            print(f"You hit the {name_enc}! You deal {damage} damage")
            input("")
        else:
            print("You miss.")
            damage = 0
    elif attack_type == 'Ranged':
        if (random.randint(1,20)) > (defense + random.randint(1,10)):
            damage = max((player_data['Strength'] // 2), (player_inventory[ranged] - armor_enc))
            print(f"You hit the {name_enc}! You deal {damage} damage")
        else:
            print("You miss.")
            damage = 0
    return damage

def dodge():
    #gets a random number and divides by 10. This is used as the random amount of time waited
    time_waiting = random.randint(5,30)
    time_waiting = time_waiting / 10
    print("Your enemy is trying to attack you with a special attack!")
    input("Prepare to dodge! Press enter to continue...")
    #pauses the game for a random amount of time
    time.sleep(time_waiting)
    start = time.time()

    input("Press enter!")

    end = time.time()
    #takes the amount of time between start and end and provides a number
    total = end - start
    total *= 100
    total = int(total)
    return total

def monster_action_determiner(health, max_health, cl_enc, boss, special_attack, ranged):
    min_health = max_health // 4
    if boss == True and special_attack == False:
        monster_action = 'Special attack'
    elif health < player_data['Health'] and health < min_health and ranged:
        monster_action = 'Ranged attack'
    else:
        monster_action = 'Melee attack'

    if cl_enc > 3 and special_attack == False:
        if health < min_health:
            monster_action = 'Special attack'
        elif player_data['Special Attack Available'] == False:
            monster_action = 'Special attack'
        elif player_data['Level'] < cl_enc:
            monster_action = 'Special attack'

    return monster_action

#a function that allows the player to fight enemies. Takes inputs (from a dictionary) and then allows the player to fight
#there are 3 attack types, ranged, melee, and special, and they all have different stats
#if there's more than one enemy, the logic changes and it allows the player to fight more than one enemy at once
def encounter(name_enc, health, damage_enc, damage_enc_ranged, defense, strength, armor_enc, cl_enc, special_attack='None', flying=False, boss=False, amount=1):
    global fighting_patrolling_goblins
    global moving_enemy_alive_2
    returning = 0
    many_enemies = False
    fighting = True
    text = "/Special attack"
    run_text = '/Run'
    underleveled = False
    can_use_ranged = True
    max_health = health
    max_defense = defense
    special_attack_monster = False
    player_data["Defense"] = player_data["Max Defense"]
    defending = False
    preparing_attack = False
    special_attack_preparing = 0

    if damage_enc_ranged == 0:
        ranged_attack = False
    else:
        ranged_attack = True

    #removes the monster's special attack if it doesn't have one
    if special_attack == 'None':
        special_attack_monster = True

    if cl_enc > player_data["Level"] and boss == False:
        print("You are underleveled for this fight! Running will be easier.")
        input("")
        underleveled = True

    #if you are fighting more than one enemy, turns on many_enemies mode
    if amount > 1:
        many_enemies = True
        current_amount = amount
        enemy_HP = []
        #creates a list with the HP of every enemy
        for enemies in range(1, amount+1):
            enemy_HP.append(health)

    if many_enemies == False:
        print(f"You are fighting a {name_enc}!")
    else:
        print(f"You are fighting {name_enc}!")

    if boss == True:
        print("This monster is a boss! You cannot run.")
        run_text = ''

    #this while loop will run until the monster is dead
    while fighting:
        defending = False
        if player_inventory["Arrows"] <= 0:
            can_use_ranged = False
        if many_enemies == True:
            #for plurality, add s to current amount and make all enemies names singular 
            print(f"There are {current_amount} {name_enc} fighting you!")
        else:
            print(f"The {name_enc} has {health} HP.")
        action = input(f"It is your turn, what will you do? (Attack/Defend{run_text}) ").capitalize()
        #logic for if the player tries to run
        if action == 'Run' and boss == False:
            randomnum = random.randint(1,20) + player_data["Strength"]
            if randomnum > strength+2 and underleveled == False:
                print("You manage to escape!")
                fighting = False
                returning = 1
                fighting_patrolling_goblins = False
            #easier to run if you are underleveled
            elif randomnum+2 > strength and underleveled:
                print("You manage to escape! Lucky for you.")
                fighting = False
                returning = 1
                fighting_patrolling_goblins = False
            else:
                print(f"You don't manage to escape! You have to fight the {name_enc} after all...")
                input("")
        elif action == 'Run' and boss == True:
            print("This is a boss! You cannot run.")
            input()
        #attacking code block
        elif action == 'Attack':
            if player_data["Special Attack Available"] == False:
                text = ""
            attack_type = input(f"How do you want to attack? (Melee/Ranged{text}) ").capitalize()
            #multiple enemy logic
            if many_enemies == True:
                list_for_this_one_specific_thing = range(1, current_amount+1)
                many_attacking = number(f"There are {current_amount} {name_enc}. Which do you want to attack? (1-{current_amount}) ", list_for_this_one_specific_thing)
                many_attacking -= 1

            if attack_type == 'Melee' and flying == False:
                print(f"You try to attack the {name_enc} with your melee weapon...")
                damage = attack(name_enc, defense, armor_enc)
                if many_enemies == True:
                    enemy_HP[many_attacking] -= damage
                    #if the enemy dies, removes it from the list
                    if enemy_HP[many_attacking] <= 0:
                        del enemy_HP[many_attacking]
                        current_amount = len(enemy_HP)
                        #if there are no enemies left, trigger the death XP rewards and end the battle
                        if current_amount <= 0:
                            print("You killed all of the enemies!")
                            health = 0
                        else:
                            print(f"You killed an enemy! There are {current_amount} enemies left.")
                else:
                    health -= damage
            elif attack_type == 'Melee' and flying == True:
                print("This is a flying enemy! You cannot attack it with a melee weapon.")
            elif attack_type == 'Ranged' and can_use_ranged:
                print(f"You try to attack the {name_enc} with your ranged weapon and use an arrow.")
                player_inventory["Arrows"] -= 1
                print(f"You have {player_inventory['Arrows']} left.")
                #similar logic to the melee attack but you get a d20 and no strength bonus unless the creature is flying
                if flying == True:
                    #uses melee attack formula to not punish the player, you can only attack with ranged weapons
                    damage = attack(name_enc, defense, armor_enc)
                    if many_enemies == True:
                        enemy_HP[many_attacking] -= damage
                        #if the enemy dies, removes it from the list
                        if enemy_HP[many_attacking] <= 0:
                            del enemy_HP[many_attacking]
                            current_amount = len(enemy_HP)
                            #if there are no enemies left, trigger the death XP rewards and end the battle
                            if current_amount <= 0:
                                print("You killed all of the enemies!")
                                health = 0
                            else:
                                print(f"You killed an enemy! There are {current_amount} enemies left.")
                    else:
                        health -= damage
                else:
                    damage = attack(name_enc, defense, armor_enc, 'Ranged')
                    if many_enemies == True:
                        enemy_HP[many_attacking] -= damage
                        #if the enemy dies, removes it from the list
                        if enemy_HP[many_attacking] <= 0:
                            del enemy_HP[many_attacking]
                            current_amount = len(enemy_HP)
                            #if there are no enemies left, trigger the death XP rewards and end the battle
                            if current_amount <= 0:
                                print("You killed all of the enemies!")
                                health = 0
                            else:
                                print(f"You killed an enemy! There are {current_amount} enemies left.")
                    else:
                        health -= damage
                    input("")
            elif attack_type == 'Ranged' and can_use_ranged == False:
                print("You try to shoot your ranged weapon, but have no arrows!")
                print("You miss your turn.")
                input()
            elif attack_type == 'Special attack' and player_data["Special Attack Available"] == True:
                player_data["Special Attack Available"] = False
                print("You use your special attack! Your defense is reduced by 3 for one round.")
                damage = max((player_data['Strength'] * 2), ((player_inventory[melee] * 2) - armor_enc))
                print(f"You hit the {name_enc} and deal {damage} damage!")
                if many_enemies == True:
                    enemy_HP[many_attacking] -= damage
                    #going negative is intentional, this is just to make it simpler
                    if current_amount > 1:
                        enemy_HP[many_attacking-1] -= damage
                    #if the enemy dies, removes it from the list
                    surviving_enemies = []
                    old_amount = len(enemy_HP)
                    for enemies in enemy_HP:
                        if enemies > 0:
                            surviving_enemies.append(enemies)
                    enemy_HP = surviving_enemies
                    current_amount = len(enemy_HP)
                    if old_amount > current_amount:
                        print(f"You killed an enemy! There are {current_amount} enemies left.")
                        #if there are no enemies left, trigger the death XP rewards and end the battle
                    if current_amount <= 0:
                        print("You killed all of the enemies!")
                        health = 0
                else:
                    health -= damage
                player_data["Defense"] -= 3
                input()
            elif attack_type == 'Special attack' and player_data["Special Attack Available"] == False:
                print("You already used your special attack! You miss this turn.")
            else:
                print("You didn't choose a valid attack type. You miss this turn.")
        elif action == 'Defend':
            print("You hunker down and try to defend better against the next enemy attack.")
            player_data['Defense'] += (2 * player_data["Level"])
            defending = True
        else:
            print("You didn't choose a valid option. You miss this turn.")

        if health > 0 and fighting:
            defense = max_defense
            #determines what the monster will do
            monster_action = monster_action_determiner(health, max_health, cl_enc, boss, special_attack_monster, ranged_attack)
            #monster tries to attack
            if preparing_attack == False:
                if monster_action == 'Melee attack':
                    if many_enemies == False:
                        attack(name_enc, defense, armor_enc, 'Monster', strength, damage_enc)
                    elif many_enemies == True and cl_enc >= 4:
                        enemy_turns = current_amount
                        while enemy_turns != 0:
                            if player_data["Health"] <= 0:
                                death()
                            if (strength + random.randint(1, 20)) > (player_data["Defense"] + random.randint(1,10)):
                                damage = max((strength // 2), (damage_enc - player_data["Armor"]))
                                player_data["Health"] -= damage
                                print(f"One of the {name_enc} hits you! It deals {damage} damage.")
                                print(f"You have {player_data['Health']} health left")
                                input("")
                            else:
                                print(f"One of the {name_enc} tries to hit you, but misses!")
            
                            enemy_turns -= 1
                    else:
                        if ((strength + (current_amount -1) ) + random.randint(1,20)) > (player_data["Defense"] + random.randint(1,10)):
                            #this is a crazy line of code, but essentially the min damage is half of strength, otherwise it takes the amount of enemies -2 and multiplies it by damage
                            #another max() variable makes sure it's not negative
                            damage = max((strength // 2), (max((damage_enc - player_data["Armor"]), ((damage_enc * (current_amount - 2)) - player_data["Armor"]))))
                            print(f"The {name_enc} hit you! You take {damage} damage.")
                            player_data["Health"] -= damage
                            print(f"You have {player_data['Health']} health left")
                            if player_data["Health"] <= 0:
                                death()
                            input("")
                        else:
                            print(f"The {name_enc} try to hit you, but miss.")
                elif monster_action == 'Ranged attack':
                    if many_enemies == False:
                        attack(name_enc, defense, armor_enc, 'Monster ranged', strength, damage_enc, damage_enc_ranged)
                    else:
                        print("No current ranged attack for multiple units.")
                elif monster_action == 'Special attack':
                    preparing_attack = True
                    special_attack_monster = True
                    print(f"The {name_enc} is preparing a special attack...")

            if preparing_attack:
                special_attack_preparing += 1

            if special_attack_preparing == 2:
                defense -= 3
                damage = max((strength * 2), ((damage_enc * 2) - player_data["Armor"]))
                dodging = dodge()
                if defending:
                    dodging = int(dodging / 1.5)
                
                if dodging < 30:
                    damage //=  2
                    print("You managed to dodge the attack very well!")
                elif dodging < 60:
                    damage = int(damage / 1.5)
                    print("You slightly managed to dodge the attack.")
                else:
                    print("You did not manage to dodge the attack.")
                print(f"You take {damage} damage.")
                player_data["Health"] -= damage
                preparing_attack = False
                special_attack_preparing = 0

        if health <= 0:
            fighting = False
            gold = random.randint(cl_enc,(cl_enc * 5))
            if many_enemies == True:
                print(f"The {name_enc} are dead! You are free!")
            else:
                print(f"The {name_enc} is dead! You are free!")
            print(f"Encounter over. You get {gold} gold")
            player_data['Gold'] += gold
            print(f"You have {player_data['Gold']} gold.")
            input()
            if many_enemies == True:
                experience = int((((cl_enc / 4)*amount)*50))
            else:
                experience = (cl_enc * 50)
            print(f"You also gain {experience} experience!")
            player_data["Experience"] += experience
            print(f"You have {player_data['Experience']} experience.")
            if fighting_patrolling_goblins == True:
                moving_enemy_alive_2 = False
            input()

        if player_data['Health'] <= 0:
            death()

        player_data["Defense"] = player_data["Max Defense"]

    return returning


#function for a room with an enemy in it
def enemy_room():
    returning = 0
    print("You walk into the room and see something in the shadows...")
    input("")
    randomnum = random.randint(1,(40 + (player_data["Level"] * 10)))
    if name == 'dev':
        print("Goblins are 1-19, dog is 20-39, orc is 40-59. Etc etc")
        randomnum = int(input("Choose your enemy. "))

    if randomnum <= 20: 
        print("You walk further into the room and see a group of goblins!")
        returning = encounter(**goblins, amount=random.randint(2,4))
        #insert goblins function here
    elif randomnum <= 40:
        print("You walk further into the room and see a feral dog!")
        returning = encounter(**feral_dog)
        #insert feral_dog function here
    elif randomnum <= 60:
        print("You walk further into the room and see an orc")
        print("Lucky for you, it's a small orc...")
        returning = encounter(**baby_orc)
        #insert baby_orc function here
    elif randomnum <= 80:
        print("You walk further into the room and see a strange man")
        print("not done for now, if you see this just ignore :3")
        #do this later
        #insert wizard function here. There should be a way to talk your way out of this one
    elif randomnum <= 99:
        print("You walk further into the room and see a giant snake!")
        print("You cannot determine if it's a python...")
        returning = encounter('Small Python', 25, 15, 6, 5, 3, 3)
        #insert small_python function here
    elif randomnum > 99:
        print("You have a bad feeling about this one...")
        input("")
        print("You walk further into the room and see an orc")
        print("Unlucky for you, it's a full sized orc!")
        returning = encounter ('Orc', 40, 20, 0, 6, 3, 5)
        #insert orc function here
    else:
        print("Something broke")

    return returning

#miniboss room, it's a gelatinous cube intended for a level 1 player
def miniboss():
    print("You walk into the room. You have a bad feeling about this...")
    action = input("Do you want to continue? (Yes/No) ").capitalize()

    if action == 'Yes':
        print("You feel ready. You enter the room.")

        cube_miniboss = {
        'name_enc' : 'Gelatinous Cube',
        'health' : 20,
        'damage_enc' : 5,
        'damage_enc_ranged' : 0,
        'defense' : 2,
        'strength' : 5,
        'armor_enc' : 0,
        'cl_enc' : 1,
        'boss' : True,
        'special_attack' : 'Yes'
    }
        
        return encounter(**cube_miniboss)
    else:
        dungeon_1_visited[row][column] = False
        print("You don't want to enter the room. You'll come back another time.")
        return

#creates an empty room variable that will give a different description every time. The actual text is written by ChatGPT, the code is mine
def empty_room():
    global empty_room_number
    if empty_room_number == 1:
        print("You enter the room and notice a thin layer of dust covering everything. It seems like nobody has been here for years.")
        input()
        empty_room_number += 1
    elif empty_room_number == 2:
        print("You walk into the room and find an old wooden chair sitting in the middle of it. You have no idea why it's there.")
        input()
        empty_room_number += 1
    elif empty_room_number == 3:
        print("You enter the room and see a skeleton slumped against the wall. You decide it's probably best not to touch it.")
        input()
        empty_room_number += 1
    elif empty_room_number == 4:
        print("The room is completely empty, except for a small puddle of water dripping from the ceiling.")
        input()
        empty_room_number += 1
    elif empty_room_number == 5:
        print("You walk into the room and find several scratches carved into the stone wall. Whatever made them was probably not very friendly.")
        input()
        empty_room_number += 1
    elif empty_room_number == 6:
        print("You step into the room and hear the faint sound of wind, even though there are no windows or openings anywhere.")
        input()
        empty_room_number += 1
    elif empty_room_number == 7:
        print("You enter the room and notice a single candle sitting on the floor. Somehow, the flame is still burning.")
        input()
        empty_room_number += 1
    elif empty_room_number == 8:
        print("You walk into the room and find an old pile of broken weapons scattered across the floor. Nothing useful remains.")
        input()
        empty_room_number += 1
    else:
        print("Either something broke, or I was too lazy to write another empty room descriptor. This room is empty")
        input()

#creates a map room variable which shows the player a map of where they've been to
def map():
    #makes a 4x4 grid, used on the first floor
    if dungeon_level == 1:
        #creates LOCAL rows and columns, used for later logic
        row_local = -1
        column_local = 0
        #creates a list with the same size as the dungeon and fills it with ?
        map_room_list = [
            ['?', '?', '?', '?'],
            ['?', '?', '?', '?'],
            ['?', '?', '?', '?'],
            ['?', '?', '?', '?'],
        ]

        for room in dungeon_1:
            #sets row_local and column_local to 0
            row_local += 1
            column_local = 0
            for subroom in room:
                #checks every room in dungeon_1_visited, and if you've been there adds the corresponding symbol
                if dungeon_1_visited[row_local][column_local] == True:
                    if dungeon_1[row_local][column_local] == enemy_room:
                        map_room_list[row_local][column_local] = 'x'
                    elif dungeon_1[row_local][column_local] == empty_room:
                        map_room_list[row_local][column_local] = ' '
                    elif dungeon_1[row_local][column_local] == gold_room:
                        map_room_list[row_local][column_local] = '$'
                    elif dungeon_1[row_local][column_local] == 'Entrance':
                        map_room_list[row_local][column_local] = ' '
                    elif dungeon_1[row_local][column_local] == miniboss:
                        map_room_list[row_local][column_local] = 'X'
                    elif dungeon_1[row_local][column_local] == rest_room:
                        map_room_list[row_local][column_local] = '*'
                    else:
                        map_room_list[row_local][column_local] = ' '
                if row == row_local and column == column_local:
                    map_room_list[row_local][column_local] = '@'
                column_local += 1

        #displays the map with the symbols filled in depending on where you've been
        print("You open your map. You fill it in with everywhere you've been so far.")
        input()
        print("Your player is represented by the @ symbol")
        print("The exit staircase is represented by the % symbol")
        print("+---+---+---+---+")
        print(f"| {map_room_list[0][0]} | {map_room_list[0][1]} | {map_room_list[0][2]} | {map_room_list[0][3]} |")
        print("+---+---+---+---+")
        print(f"| {map_room_list[1][0]} | {map_room_list[1][1]} | {map_room_list[1][2]} | {map_room_list[1][3]} |")
        print("+---+---+---+---+")
        print(f"| {map_room_list[2][0]} | {map_room_list[2][1]} |###| {map_room_list[2][3]} |")
        print("+---+---+---+---+")
        print(f"| {map_room_list[3][0]} | {map_room_list[3][1]} |###| % |")
        print("+---+---+---+---+")
        input()
    
    #for floor 2 of the dungeon, makes a 5x5 grid instead of a 4x4 grid
    elif dungeon_level == 2:
        #creates LOCAL rows and columns, used for later logic
        row_local = -1
        column_local = 0
        #creates a list with the same size as the dungeon and fills it with ?
        map_room_list = [
            ['?', '?', '?', '?', '?'],
            ['?', '?', '?', '?', '?'],
            ['?', '?', '?', '?', '?'],
            ['?', '?', '?', '?', '?'],
            ['?', '?', '?', '?', '?']
        ]

        for room in dungeon_2:
            #sets row_local and column_local to 0
            row_local += 1
            column_local = 0
            for subroom in room:
                #checks every room in dungeon_1_visited, and if you've been there adds the corresponding symbol
                if dungeon_2_visited[row_local][column_local] == True:
                    if dungeon_2[row_local][column_local] == enemy_room:
                        map_room_list[row_local][column_local] = 'x'
                    elif dungeon_2[row_local][column_local] == empty_room:
                        map_room_list[row_local][column_local] = ' '
                    elif dungeon_2[row_local][column_local] == gold_room:
                        map_room_list[row_local][column_local] = '$'
                    elif dungeon_2[row_local][column_local] == 'Entrance':
                        map_room_list[row_local][column_local] = ' '
                    elif dungeon_2[row_local][column_local] == miniboss:
                        map_room_list[row_local][column_local] = 'X'
                    elif dungeon_2[row_local][column_local] == rest_room:
                        map_room_list[row_local][column_local] = '*'
                    else:
                        map_room_list[row_local][column_local] = ' '
                if row == row_local and column == column_local:
                    map_room_list[row_local][column_local] = '@'
                column_local += 1

        #displays the map with the symbols filled in depending on where you've been
        print("You open your map. You fill it in with everywhere you've been so far.")
        input()
        print("Your player is represented by the @ symbol")
        print("The exit staircase is represented by the % symbol")
        print("+---+---+---+---+---+")
        print(f"| {map_room_list[0][0]} | {map_room_list[0][1]} | {map_room_list[0][2]} |###| {map_room_list[0][4]} |")
        print("+---+---+---+---+---+")
        print(f"| {map_room_list[1][0]} | {map_room_list[1][1]} | {map_room_list[1][2]} |###| {map_room_list[1][4]} |")
        print("+---+---+---+---+---+")
        print(f"| {map_room_list[2][0]} | {map_room_list[2][1]} | {map_room_list[2][2]} | {map_room_list[2][3]} | {map_room_list[2][4]} |")
        print("+---+---+---+---+---+")
        print(f"|###|###| {map_room_list[3][2]} | {map_room_list[3][3]} | {map_room_list[3][4]} |")
        print("+---+---+---+---+---+")
        print(f"| % | {map_room_list[4][1]} | {map_room_list[4][2]} | {map_room_list[4][3]} | {map_room_list[4][4]} |")
        print("+---+---+---+---+---+")
        input()

#entrance to the boss room, has a mini puzzle thing
def entrance_boss():
    if player_data["Level"] >= 2:
        print("You walk into a room and see a glowing red door. You walk closer to inspect it, but all of your exits are cut off by gates!")
        print("There's only one exit, the glowing red door, unless you want to try and pull the gates open?")
        action = input("Do you want to try to open the gates? (Yes/No) ").capitalize()
    else:
        print("You walk into a room and see a glowing red door. Don't feel ready.")
        action = input("What do you do? (Continue/Leave) ").capitalize()

    if action == 'Yes':
        randomnum = (random.randint(1,20) + player_data["Strength"])
        if randomnum > 15:
            print("You manage to pry open the exits! You can leave now.")
            return 2
        else:
            print("You can't open the exits. You only have one way forward...")
    if action == 'Leave' and player_data["Level"] == 1:
        print("You decide to leave.")
        return 2

    print("You prepare yourself for what lies ahead. Good luck!")
    input()

#makes the player fight a boss, and lets them heal if they trust the game
def boss_1():
    print("You walk into the room and feel a deep sense of unease...")
    action = input("You see a red bottle on the floor. Drink it? (Yes/No) ").capitalize()
    if action == 'Yes':
        print("You drink the bottle...")
        input()
        player_data["Health"] = player_data["Max Health"]
        print(f"You are healed! You have {player_data['Health']} health.")
    else:
        print("You decide to leave the bottle alone.")
    input()
    print("You continue forward and see a Warden!")

    warden_boss = {
   'name_enc' : 'Warden Boss',
   'health' : 25,
   'damage_enc' : 5,
   'damage_enc_ranged' : 0,
   'defense' : 3,
   'strength' : 4,
   'armor_enc' : 1,
   'cl_enc' : 2,
   'boss' : True,
   'special_attack' : 'Yes'
}
    encounter(**warden_boss)
    return 3

#short descriptor about the staircase, and allows the player to level up
def staircase():
    print("You walk forward and see a staircase leading down. After the fight you just had, you decide it's a good idea to descend.")
    input()
    print(f"Congratulations {name}! You have completed the first floor of the dungeon! Many adventures await you yet, but first a break...")
    player_data["Experience"] += (level_up_experience - player_data["Experience"])
    return 4

def rest_room():
    print("You walk into the room and see a small firepit on the floor.")
    action = input("Try to light it? (Yes/No) ").capitalize()
    if action == 'Yes':
        player_data["Special Attack Available"] = True
        print("You light the firepit and rest. +50% HP.")
        player_data["Health"] += (player_data["Max Health"] // 2)
        if player_data["Health"] > player_data["Max Health"]:
            player_data["Health"] = player_data["Max Health"]
        print(f"You have {player_data['Health']} HP.")
        print("You also regenerate your special attack!")
        input()
    else:
        print("You decide to leave the firepit.")

def shop():
    if dungeon_level == 1:
        print("You descend the stairs after killing the warden and see a fairly small area with a shop")
        print("A strange creature sits at the counter. He looks very bored.")
        print("As soon as he sees you, his eyes light up.")
        print("'Hello adventurer!' he beams, 'You're the first person I've seen in weeks!'")
        print("'Well, since you're here, let me give you something!'")
        selection = input("What would you like? (Melee/Ranged/Armor) ").capitalize()

        if selection == 'Ranged':
            player_inventory['Crossbow'] = 9
            print("The man gives you a crossbow. It looks old, but functional.")
            print("Hint: Use inventory to equip the crossbow!")
            input()
        elif selection == 'Armor':
            print("The man gives you a piece of armor.")
            print("It gives you 3 armor.")
            print(f"You currently have {player_data['Armor']}.")
            selection_2 = input("Do you want to take the armor? (Yes/No)").capitalize()
            if selection_2 == 'No':
                print("You decide not to take the armor.")
                input()
            else:
                player_data["Armor"] = 3
                print("You decide to take and equip the armor. You now have 3 armor.")
                input()
        else:
            player_inventory['Longsword'] = 7
            print("The man gives you a longsword. It's slightly rusty, but sharp.")
            print("Hint: Use inventory to equip the longsword!")
            input()

        print("Well I wish I could give you more, but I have a business to run!")
        print("If you want, I have some things to sell you.")
    shopping = input("Do you want to open the shop? (Yes/No) ").capitalize()

    if shopping == 'No':
        print("There's nothing else to do here but leave.")
        return

    for item, stats in shop_inventory.items():
        if 'Damage' in stats and stats["Quantity"] > 0:
            print(f"{item} - {stats['Price']} gold - {stats.get('Damage', 'N/A')} damage - {stats['Quantity']} left")
        elif 'Damage' not in stats and stats["Quantity"] > 0:
            print(f"{item} - {stats['Price']} gold - {stats['Quantity']} left")

    bought_something = False
    while shopping:
        buying_more_than_one_thing = False
        #chatGPT made this
        if bought_something == True:
            for item, stats in shop_inventory.items():
                if 'Damage' in stats and stats["Quantity"] > 0:
                    print(f"{item} - {stats['Price']} gold - {stats.get('Damage', 'N/A')} damage - {stats['Quantity']} left")
                elif 'Damage' not in stats and stats["Quantity"] > 0:
                    print(f"{item} - {stats['Price']} gold - {stats['Quantity']} left")
        print("")
        bought_something = False
        
        print("(Type leave to leave)")
        shopping_selection = input("What would you like to buy? ").capitalize()
        if shopping_selection == 'Leave':
            return
        elif shopping_selection not in shop_inventory:
            print("Not a valid item!")
            valid_item = False
        elif shop_inventory[shopping_selection]['Quantity'] <= 0:
            print(f"There are no {shopping_selection} left!")
            valid_item = False
        else:
            valid_item = True

        if valid_item and shop_inventory[shopping_selection]['Quantity'] > 1:
            one_time_list = range(1, shop_inventory[shopping_selection]['Quantity']+1)
            amount_buying = number("How many would you like to buy? ", one_time_list)
            if amount_buying > 1:
                buying_more_than_one_thing = True

        if buying_more_than_one_thing and valid_item:
            if player_data["Gold"] >= (shop_inventory[shopping_selection]['Price'] * amount_buying):
                player_inventory[shopping_selection] = player_inventory.get(shopping_selection, 0) + amount_buying
                shop_inventory[shopping_selection]['Quantity'] -= amount_buying
                player_data['Gold'] -= (shop_inventory[shopping_selection]['Price'] * amount_buying)
                print(f"You buy {amount_buying} {shopping_selection}.")
                print(f"You have {player_data['Gold']} gold left.")
                bought_something = True
            else:
                print("You can't afford this!")
        elif valid_item:
            if player_data["Gold"] >= shop_inventory[shopping_selection]['Price']:
                if shop_inventory[shopping_selection]['Type'] == 'Melee' or shop_inventory[shopping_selection]['Type'] == 'Ranged':
                    player_inventory[shopping_selection] = shop_inventory[shopping_selection]['Damage']
                else:
                    #chat GPT made the .get part
                    player_inventory[shopping_selection] = player_inventory.get(shopping_selection, 0) + 1
                shop_inventory[shopping_selection]['Quantity'] -= 1
                player_data['Gold'] -= shop_inventory[shopping_selection]['Price']
                print(f"You buy a {shopping_selection}.")
                print(f"You have {player_data['Gold']} gold left.")
                bought_something = True
            else:
                print("You can't afford this!")

        if bought_something == True:
            if input("Would you like to buy more? (Yes/No) ").capitalize() == 'No':
                shopping = False
            else:
                print("")

    print("There's nothing else to do here but leave.")

def level_up():
    global level_up_experience
    player_data["Level"] += 1
    player_data["Experience"] -= level_up_experience
    player_data["Max Health"] += (5 + (2 * player_data["Level"]))
    player_data["Health"] = player_data['Max Health']
    player_data["Strength"] += 3
    player_data['Max Defense'] += 3
    player_data["Defense"] = player_data["Max Defense"]
    level_up_experience = int(level_up_experience * 1.5)
    print(f"Level up! You are now level {player_data['Level']}.")
    print(f"You have been healed, and your max HP has been increased! Your health is {player_data['Health']}")
    level_up = input("What do you want to increase further? (Strength/Health/Defense) ").capitalize()
    if level_up == 'Strength':
        player_data["Strength"] += 3
        print("You train and increase your strength.")
        input()
    elif level_up == 'Health':
        player_data["Max Health"] += 10
        player_data["Health"] = player_data["Max Health"]
        print("You drink some homemade stew and can take more of a beating.")
        input()
    elif level_up == 'Defense':
        player_data['Max Defense'] += 3
        player_data["Defense"] = player_data["Max Defense"]
        print("You train your dodging and increase your defense")
        input()
    else:
        player_data["Strength"] += 3
        print("You aren't sure what to do, so you train and increase your strength.")
        input()

    print("Here are your new player stats.")
    #chatGPT made this
    for stat, value in player_data.items():
        print(f"{stat}: {value}")
    input()

#creates dungeon_1 map
dungeon_1 = [
    ['Entrance', gold_room, enemy_room, rest_room],
    [enemy_room, empty_room, gold_room, entrance_boss],
    [empty_room, rest_room, 'Wall', boss_1],
    [gold_room, miniboss, 'Wall', staircase]
]

dungeon_1_visited = [
    [True, False, False, False],
    [False, False, False, False],
    [False, False, False, False],
    [False, False, False, False]
]


#asks for player name
name = input("Please enter your name adventurer! ")

#intro text, if they are a developer then open a debug panel 
if name == 'dev' or name == 'onetimedev':
    print("Welcome to the dev panel! Choose your coordinates please")
    dungeon_level = int(input("Input dungeon layer "))
    row = int(input("Input row (up and down) "))
    column = int(input("Input column (left and right) "))
    player_data["Gold"] = int(input("Input gold "))
    dev_level = int(input("What level would you like? "))
    dev_level -= 1
    player_data["Experience"] = ((100 * 1.5)* dev_level)
    if dev_level > 0:
        while player_data["Experience"] > level_up_experience:
            level_up()
else:
    tutorial = input(f"Welcome {name}! Would you like a tutorial? (Yes/No) ").capitalize()
    if tutorial == 'Yes':
        print("This is a text based RPG, or roleplaying game. Your goal is to get to the core of the dungeon you have entered.")
        print("There are multiple layers to this dungeon, and every layer has a staircase leading to the next floor.")
        print("In between dungeon layers there will be a rest layer, where you can spend your gold and heal yourself.")
        print("The first floor of the dungeon is a 4x4 grid. As you go deeper, this grid will get bigger.")
        print("When you are asked to go up, right, left, or down, that is from a birdseye view of the grid.")
        print("In your journeys, you might find that the program stops without asking anything! If this happens, just press enter.")
        print("Try it now!")
        input()
        print("Great! Next up are the stats of your player! You start off with the following stats.")
        #chatGPT made this
        for stat, value in player_data.items():
            print(f"{stat}: {value}")
        input()
        print("You don't need to know what all of that means, but the important ones are as follows.")
        print("Your strength is how easy it is for you to hit an enemy, you start off with no strength!")
        print("Your damage is how much damage you will do if you hit an enemy.")
        print("Your defense is the opposite, how hard it is for enemies to hit you. You start off with 5 defense.")
        print("Your armor is how much damage will be reduced if you do get hit.")
        print("Finally, your health is how much damage you can take before you die. Max health is the max health you can have at one time.")
        print("When you defeat enemies, you gain experience. If you get enough experience, you will level up.")
        print("When you level up, almost all of these stats will increase! Damage and armor are primarily from items however.")
        input()
        print("Finally, you might find enemies in your path. Fear not, as you can beat almost any enemy you find!")
        print("However, if you find yourself low on health or fear that the enemies are too strong for you, you can always try to run.")
        print("You cannot run from bosses though, so if you feel uneasy about something, make sure you're ready!")
        input()
        print("You also start with a special attack! Your special attack can change with training.")
        print("Your special attack will always hit and deal extra damage to your enemy!")
        print("However this comes with a downside. You are vulnerable for your next turn to all attacks.")
        print("You also can only use this special attack once per rest.")
        print("When fighting more than one enemy, the special attack will hit two enemies at once!")
        input()
        print("You can also decide between a ranged and melee attack.")
        print("Ranged attacks do more damage, but you're less likely to hit.")
        print("If you're fighting a flying enemy, you can only use your ranged attack.")
        print("Melee attacks do less damage, but you're more likely to hit.")
        print("That is all for now, good luck adventurer!")
        input()
    print("In the Kingdom of Ravenport the dungeons of The Great Coil are infamous for consuming adventurers in their depths never to be seen again.")
    print(f"But nevertheless, you, {name}, decide to brave the depths and slay the python at its core.") 
    print("You leave your hometown with nothing but an old piece of armor you found and a rusty sword. Let's see if you made the right decision...")
    input("")
    print("You enter the dungeon and find yourself in a dark room no larger than 2 meters long on either side. You barely fit.")

action = 99
#action loop, the player can choose between opening their map, moving, and accessing their inventory
if dungeon_level == 1:
    direction_chosen = True
while direction_chosen:

    possible_directions = find_directions()

    if name == 'dev':
        print("Dev panel again!")
        print(f"You are currently in row {row} and column {column}")
        print(f"possible directions returned {possible_directions}")
        input()
        print("Dungeon visited currently has")
        print(dungeon_1_visited)
        input()

    #if a player runs from a fight, makes them go a random direction
    if action == 1:
        dungeon_1_visited[row][column] = False
        direction = random.choice(possible_directions)
        action = 0
        movement = 'Run'
        print("You run into a random room.")
        input()
    #lets the player escape if they did so in entrance_boss
    elif action == 2:
        possible_directions = [1, 2]
        action = 0
        movement = 'Move'
        dungeon_1_visited[row][column] = False
    elif action == 99:
        movement = 'Move'
        action = 0
    else:
        movement = input("What would you like to do? (Inventory/Move/Map) ").capitalize()
    

    if movement == 'Inventory':
        print("This is your inventory.")
        #chatGPT made this
        for item, value in player_inventory.items():
            print(f"{item}: {value}")
        inventory_action = input(f"What would you like to do? (Melee/Ranged/Leave) ").capitalize()
        if inventory_action == 'Melee':
            current_melee.clear()
            for item in player_inventory:
                if item in melee_items:
                    current_melee.append(item)
                    print(item)
            melee_change = input("What melee item would you like to equip? ").capitalize()
            if melee_change in current_melee:
                melee = melee_change
                print(f"{melee} equipped!")
                input()
            else:
                print("Not a valid item!")
        elif inventory_action == 'Ranged':
            current_ranged.clear()
            for item in player_inventory:
                if item in ranged_items:
                    current_ranged.append(item)
                    print(item)
            ranged_change = input("What ranged item would you like to equip? ").capitalize()
            if ranged_change in current_ranged:
                ranged = ranged_change
                print(f"{ranged} equipped!")
                input()
            else:
                print("Not a valid item!")
    elif movement == 'Move':
        direction = directions(*possible_directions)

        if direction == 1:
            row -= 1
        elif direction == 2:
            column -= 1
        elif direction == 3:
            column += 1
        elif direction == 4:
            row += 1
    elif movement == 'Map':
        map()
    elif movement == 'Run':
        if direction == 1:
            row -= 1
        elif direction == 2:
            column -= 1
        elif direction == 3:
            column += 1
        elif direction == 4:
            row += 1
    else:
        print("Please select a valid option!")

    if movement == 'Move' or movement == 'Run':
        #if the player has never been to a room, trigger the action in the room
        if dungeon_1_visited[row][column] == False:
            dungeon_1_visited[row][column] = True
            action = dungeon_1[row][column]()
        #if the player has been to a room, don't trigger anything
        elif dungeon_1_visited[row][column] == True:
            if movement == 'Move':
                print("You've been here before! There's nothing more to do.")
                print("")

    if player_data["Experience"] >= level_up_experience:
        level_up()

    if action == 3:
        action = staircase()
    if action == 4:
        shop()
        direction_chosen = False

print("You leave the shop and descend the staircase.")
print(f"Congratulations {name}! You have finished the first layer of the Great Coil.")
descending_action = input("What would you like to do? (Continue/Inventory) ").capitalize()
if descending_action == 'Inventory':
    acessing_inventory = True
else:
    acessing_inventory = False

while acessing_inventory:
    print("This is your inventory.")
    #chatGPT made this
    for item, value in player_inventory.items():
        print(f"{item}: {value}")
    inventory_action = input(f"What would you like to do? (Melee/Ranged/Leave) ").capitalize()
    if inventory_action == 'Melee':
        current_melee.clear()
        for item in player_inventory:
            if item in melee_items:
                current_melee.append(item)
                print(item)
        melee_change = input("What melee item would you like to equip? ").capitalize()
        if melee_change in current_melee:
            melee = melee_change
            print(f"{melee} equipped!")
            input()
        else:
            print("Not a valid item!")
    elif inventory_action == 'Ranged':
        current_ranged.clear()
        for item in player_inventory:
            if item in ranged_items:
                current_ranged.append(item)
                print(item)
        ranged_change = input("What ranged item would you like to equip? ").capitalize()
        if ranged_change in current_ranged:
            ranged = ranged_change
            print(f"{ranged} equipped!")
            input()
        else:
            print("Not a valid item!")
    elif inventory_action == 'Leave':
        acessing_inventory = False
    else:
        print("Not a valid option!")


print("You continue through the staircase and walk into a new room...")
dungeon_level = 2
row = 1
column = 0


##creates a bunch of rooms used on layer 2

def vault_room():
    print("You walk into the room and see a strange fixture on the wall.")
    print("It looks like a keyhole.")
    if 'Key' in player_inventory:
        use_key = input("Use key? (Yes/No) ").capitalize()
        if use_key == 'Yes':
            print("You put the key in and turn it...")
            input()
            print("It opens!")
            print("You find 15 gold and a health potion.")
            #chatgpt made the .get part
            player_inventory['Health potion'] = player_inventory.get('Health potion', 0) + 1
            player_data['Gold'] += 15
            print(f"You now have {player_data['Gold']} gold.")
            input()
        else:
            print("You decide not to use your key.")
    else:
        print("There doesn't seem to be anything else to do here.")

def key_room():
    print("You see a key on the floor. Do you take it?")
    take_key = input("Pick up the key? (Yes/No) ").capitalize()
    if take_key == 'Yes':
        print("You take the key. It's strangely heavy.")
        player_inventory['Key'] = 1
    else:
        print("You decide to leave the key. You don't trust it anyways.")

def lore_room():
    if dungeon_level == 2:
        if row == 0 and column == 1:
            print("You walk into the room and see something written on the walls.")
            print("It says 'GET OUT. TRUST NOBODY'")
            print("It has a date. Almost 200 years ago.")
            input()
            print("You decide to leave.")
        elif row == 2 and column == 1:
            print("You walk into the room and see a journal on the floor.")
            print("Most of the journal entries are pretty boring, just normal adventuring.")
            print("The author of the journal then enters the great coil.")
            print("The journal does a great job of documenting his mental decline.")
            print("Near the end the journal is filled with one word, repeated over and over.")
            print("Olran. Olran. Olran. Olran. Olran")
            take_journal = input("Creepy. Do you want to take the journal? (Yes/No)").capitalize()
            if take_journal == 'Yes':
                print("You take the journal with you.")
                player_inventory['Old journal'] = 1
                print("There's nothing else in the room, so you decide to leave.")
            else:
                print("You're too creeped out to take the journal. You decide to leave it.")

def moving_enemy():
    global fighting_patrolling_goblins
    if row == moving_enemy_row and moving_enemy_alive_2 == True:
        print("You encounter a group of patrolling goblins!")
        fighting_patrolling_goblins = True
        return encounter(**goblins, amount=random.randint(3,6))
    else:
        print("You don't see anything, but you recognize this as an enemy patrol route.")
        print("You decide to leave before you encounter them.")
        input()

def shortcut():
    global row
    global column
    dungeon_2_visited[row][column] = False
    print("You see a door that looks to take you somewhere else in the dungeon.")
    use_shortcut = input("Walk through? (Yes/No) ").capitalize()
    if use_shortcut == 'No':
        return
    elif column == 0:
        column = 4
        print("You walk through and find yourself somewhere new.")
    elif column == 4:
        column = 0
        print("You walk through and find yourself somewhere new.")

def miniboss_2():
    print("You walk into the room and feel a strong sense of unease.")
    approach_encounter = input("Are you sure you want to continue? (Yes/No) ").capitalize()
    if approach_encounter == 'Yes':
        print("You walk forward. You see a large snake!")
        snake_miniboss = {
    'name_enc' : 'Cobra',
    'health' : 12,
    'damage_enc' : 12,
    'damage_enc_ranged' : 0,
    'defense' : 0,
    'strength' : 3,
    'armor_enc' : 1,
    'cl_enc' : 2,
    'flying' : False,
    'boss' : True,
    'amount' : 1,
    'special_attack' : 'Yes'
    }
        encounter(**snake_miniboss)
    else:
        print("You decide not to continue.")
        return 2
    
def miniboss_chest():
    print("You enter the room and see a strange item on a table and a chest.")
    print("You go closer and see the handle of what seems like a sword.")
    take_things = input("Take the sword handle? (Yes/No) ").capitalize()
    if take_things == 'No':
        print("You decide to leave the sword handle.")
    else:
        player_inventory['Legendary sword piece'] = 1
        print("You take the sword handle.")
        input()
    print("You also open the chest in the room. You open it and see some gold and a crossbow!")
    take_things = input("Take the gold and crossbow? (Yes/No) ").capitalize()
    if take_things == 'No':
        print("You decide to leave the valuable and very useful items.")
    else:
        print("You take the gold and crossbow.")
        player_data['Gold'] += 12
        print(f"You have {player_data['Gold']} gold.")
        #still chatgpt for .get
        player_inventory['Crossbow'] = 9

def blacksmith():
    global visited_blacksmith
    visited_blacksmith = True
    print("You walk into the room and see a house. You notice a fire from inside, and a man humming.")
    print("You decide to enter. You walk in and see a large and muscular man.")
    print("He turns slowly...")
    input()
    print("He turns to you. You see his face, gruff and covered in coal.")
    input()
    print("He smiles warmly.")
    print("'Hello adventurer!' He says, 'How did you find your way over here?'")
    print("Well it matters not. I can sharpen your weapon if you'd like..?")
    sharpen_weapon = input("Would you like to sharpen your weapon? (Yes/No) ").capitalize()
    if sharpen_weapon == 'No':
        print("'I understand why. Trusting people in this dungeon is a bad idea...' the man says")
        print("'Well in any case I'll be on my way soon. Maybe we'll see each other later!'")
    else:
        player_inventory[melee] += 2
        print("'Amazing!' He says, 'I'll get straight to work!'")
        input()
        print("5 minutes pass...")
        input()
        print("10 minutes...")
        input()
        print("15 minutes...")
        input()
        print("After a long time waiting, standing uncomfortably, the man returns with a sharpened weapon.")
        print("'Here you go!' He says, beaming, 'Well, I have to go, but maybe we'll see each other again!'")
        input()

    print("There's nothing more to do, you decide to leave")

def entrance_boss_2():
    print("You see an ominous door. You feel uneasy.")
    if player_data["Level"] < 3:
        print("You don't feel ready for this fight. You should train more")
    fight_boss = input("Enter the room? (Yes/No) ").capitalize()
    if fight_boss == 'Yes':
        print("You enter the room...")
        return 3
    else:
        print("You decide not to enter for now.")
        return 4

def boss_2():
    orc_boss = {
   'name_enc' : 'Orc Boss',
   'health' : 35,
   'damage_enc' : 10,
   'damage_enc_ranged' : 0,
   'defense' : 1,
   'strength' : 6,
   'armor_enc' : 4,
   'cl_enc' : 4,
   'boss' : True,
   'special_attack' : 'Yes'
}
    encounter(**orc_boss)

def staircase_2():
    print("You finally see a staircase. You decide to go down.")
    return 10

dungeon_2 = [
    [vault_room,lore_room, moving_enemy,'###', miniboss_chest,],
    ['Entrance',gold_room, moving_enemy,'###', miniboss_2,],
    [shortcut, lore_room, moving_enemy, rest_room, shortcut,],
    ['###','###', gold_room, empty_room, key_room,],
    [staircase_2, boss_2, entrance_boss_2, enemy_room, blacksmith,]
]

dungeon_2_visited = [
    [False, False, False, False, False],
    [True, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False],
    [False, False, False, False, False]
]

moving_enemy_row = 0
moving_enemy_direction = 'Down'
moving_enemy_alive_2 = True
action = 99
direction_chosen = True
#layer 2 movement loop
while direction_chosen:

    possible_directions = find_directions()

    if name == 'dev' and input("Open dev panel? ") == 'Yes':
        print("Dev panel again!")
        print(f"You are currently in row {row} and column {column}")
        print(f"possible directions returned {possible_directions}")
        input()
        print("Dungeon visited currently has")
        print(dungeon_2_visited)
        input()

    #if a player runs from a fight, makes them go a random direction
    if action == 1:
        dungeon_2_visited[row][column] = False
        direction = random.choice(possible_directions)
        action = 0
        movement = 'Run'
        print("You run into a random room.")
        input()
    #if the player leaves the miniboss, removes the ability to go up and allows the player to still fight it later
    elif action == 2:
        dungeon_2_visited[row][column] = False
        possible_directions.remove(1)
        movement = 'Move'
        action = 0
    elif action == 3:
        possible_directions.clear()
        possible_directions.append(2)
        movement = 'Move'
        action = 0
    elif action == 4:
        dungeon_2_visited[row][column] = False
        possible_directions.remove(2)
    elif action == 10:
        direction_chosen = False
        break
    #makes the player move on their first entrance to the new level
    elif action == 99:
        movement = 'Move'
        action = 0
    else:
        movement = input("What would you like to do? (Inventory/Move/Map) ").capitalize()
    

    if movement == 'Inventory':
        print("This is your inventory.")
        #chatGPT made this
        for item, value in player_inventory.items():
            print(f"{item}: {value}")
        inventory_action = input(f"What would you like to do? (Melee/Ranged/Leave) ").capitalize()
        if inventory_action == 'Melee':
            current_melee.clear()
            for item in player_inventory:
                if item in melee_items:
                    current_melee.append(item)
                    print(item)
            melee_change = input("What melee item would you like to equip? ").capitalize()
            if melee_change in current_melee:
                melee = melee_change
                print(f"{melee} equipped!")
                input()
            else:
                print("Not a valid item!")
        elif inventory_action == 'Ranged':
            current_ranged.clear()
            for item in player_inventory:
                if item in ranged_items:
                    current_ranged.append(item)
                    print(item)
            ranged_change = input("What ranged item would you like to equip? ").capitalize()
            if ranged_change in current_ranged:
                ranged = ranged_change
                print(f"{ranged} equipped!")
                input()
            else:
                print("Not a valid item!")
    elif movement == 'Move':
        direction = directions(*possible_directions)

        if direction == 1:
            row -= 1
        elif direction == 2:
            column -= 1
        elif direction == 3:
            column += 1
        elif direction == 4:
            row += 1

        if column == 2 and row == moving_enemy_row and moving_enemy_alive_2 == True:
            print("You walked into a group of patrolling goblins!")
            input()
            fighting_patrolling_goblins = True
            action = encounter(**goblins, amount=random.randint(3,6))

    elif movement == 'Map':
        map()
    elif movement == 'Run':
        if direction == 1:
            row -= 1
        elif direction == 2:
            column -= 1
        elif direction == 3:
            column += 1
        elif direction == 4:
            row += 1
    else:
        print("Please select a valid option!")

    if movement == 'Move' or movement == 'Run':
        #if the player has never been to a room, trigger the action in the room
        if dungeon_2_visited[row][column] == False:
            dungeon_2_visited[row][column] = True
            action = dungeon_2[row][column]()
        #if the player has been to a room, don't trigger anything
        elif dungeon_2_visited[row][column] == True:
            #allows the player to be attacked by moving enemies even if they've already been there
            if column == 2 and row <= 2 and movement == 'Move':
                action = dungeon_2[row][column]()
            elif movement == 'Move':
                print("You've been here before! There's nothing more to do.")
                print("")

    if player_data["Experience"] >= level_up_experience:
        level_up()

    #creates logic for moving enemy row, used in moving_enemy
    #if moving up and not at 3, move up
    if moving_enemy_row < 2 and moving_enemy_direction == 'Up':
        moving_enemy_row += 1
    #if at 3, start moving down
    elif moving_enemy_row == 2:
        moving_enemy_direction = 'Down'
        moving_enemy_row -= 1
    #if at 0, start moving up
    elif moving_enemy_row == 0:
        moving_enemy_direction = 'Up'
        moving_enemy_row += 1
    #if moving down and not at 0, move down
    else:
        moving_enemy_row -= 1

    if row == moving_enemy_row and column == 2 and moving_enemy_alive_2 == True:
        print("Patrolling goblins found you!")
        input()
        fighting_patrolling_goblins = True
        action = encounter(**goblins, amount=random.randint(3,6))


print("Thank you for playtesting! That is the whole game for now.")