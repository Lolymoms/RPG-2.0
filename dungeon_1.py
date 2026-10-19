import random
import time
import enemy_data
import player_data
import copy

#tracks if the player has pried open the gates to escape the bossfight
boss_gate = True
#gives the player a different piece of lore every time
lore_counter = 1
#tracks how many times a player has been in a chest room
chest_counter = 1

def enemy_room(player, row, column):
    print("You walk into the room and see something in the shadows...")
    input()
    number = random.randint(1, 60)

    # #impossible for right now since it's a group
    # if number <= 20: 
    #     print("You walk further into the room and see a group of goblins!")
    #     action = encounter(player) #insert goblins here
    #     #insert goblins function here
    if number <= 40:
        print("You walk further into the room and see a feral dog!")
        action = encounter(player, copy.deepcopy(enemy_data.feral_dog))
    else:
        print("You walk further into the room and see a cave spider!")
        action = encounter(player, copy.deepcopy(enemy_data.cave_spider))

    if action == 'Victory':
        dungeon_action_1[row][column] = True
        return
    elif action == 'Run':
        return 'Run'

def chest_room(player, row, column):
    global chest_counter
    print("You walk into a room with a chest in it.")
    action = input("What do you want to do? (Open/Leave) ").capitalize()

    if action == 'Open':
        dungeon_action_1[row][column] = True
        #generates a random number to determine reward/mimic
        randomnum = random.randint(1,10)
        #if the random number is 4 or below, it's 5 gold
        if chest_counter == 1:
            print("You open the chest and find a health potion!")
            player_data.healing_potion.add_item(1)
            print(f"You have {player_data.healing_potion.amount} health potions.")
            input()
            chest_counter += 1
        else:
            if randomnum < 7:
                print("You open the chest and find some gold!")
                print("+5 gold")
                player.add_gold(5)
                print(f"You have {player.gold} gold.")
                input()
            #if the random number is 5-9, it's a mimic
            elif randomnum >= 7 and randomnum < 9:
                print("You open the chest and are attacked by a mimic!")
                damage = max(0, (4 - player.armor))
                print(f"You lose {damage} HP.")
                player.take_damage(damage)
                print(f"You have {player.health} health left.")
                input()
            #if the random number is 10, there's a suit of armor
            elif randomnum == 10:
                print("You find an old suit of armor!")
                print("The armor will give you +1 armor")
                print(f"You have {player.armor}")
                take_or_leave = input("Take it or leave it? (Take/Leave) ").capitalize()
                #logic for taking or leaving the armor
                if take_or_leave == 'Take':
                    print("You took the old armor")
                    player.add_armor(1)
                else:
                    print("You decide not to take the old armor")
                    
        print("There seems to be nothing else in the room.")
        input()
    else:
        print("You decide to leave the chest.")

def lore_room(player, row, column):
    global lore_counter
    if lore_counter == 1:
        print("You walk into the room and it seems mainly empty. In the corner you see a drawing etched into the stone.")
        print("You recognize it as a man holding up a sword. The man also has a long flowing cape. Seems impractical for a dungeon.")
        input()
        print("The room seems empty otherwise, you decide to leave.")
        lore_counter += 1
        dungeon_action_1[row][column] = True
    elif lore_counter == 2:
        print("You walk into the room and see a large mural covering the wall. It depicts a man with a sword and cape fighting some creature.")
        print("It looks like a golem, with spikes protruding from its head and arms. It towers over the man.")
        print("There's an inscription. 'Horas confronts the Warden without fear.' You recognize the name Horas from somewhere...")
        input()
        print("You can't place it. There's nothing else in the room, and you decide to leave.")
        dungeon_action_1[row][column] = True

def rest_room(player, row, column):
    print("You walk into the room and see a small firepit on the floor. It seems to have been lit before.")
    action = input("Do you want to light the firepit? (Yes/No) ").capitalize()
    if action == 'Yes':
        dungeon_action_1[row][column] = True
        print("You light the firepit. You heal 50% max HP and regain all of your special abilities!")
        player.rest()
        print(f"You now have {player.health} health.")
        print("There's nothing else in this room. You stay by the fireside for a bit, and then decide to leave.")
        input()
    else:
        print("You decide to leave the firepit.")
        input()

def miniboss_1(player, row, column):
    print("As you enter the room, you feel a sense of unease.")
    action = input("Are you sure you want to continue? (Yes/No) ").capitalize()
    if action == 'Yes':
        dungeon_action_1[row][column] = True
        from enemy_data import Enemy
        gelatinous_cube = Enemy("Gelatinous Cube", 1, 1, 40, 6, 3, 11, 6, 0, 'Slashing', 'None', True, 'Basic')
        encounter(player, gelatinous_cube)
    else:
        print("You decide to come back another time. You return to the room you came from.")
        return 'Miniboss'

def key_room(player, row, column):
    print("You walk into the room and see a key in a cabinet. It seems to shimmer in the dim torchlight.")
    action = input("Take it? (Yes/No) ").capitalize()
    if action == 'Yes':
        dungeon_action_1[row][column] = True
        from player_data import Item
        from player_data import player_inventory
        key = Item('Strange key', 'Item')
        player_inventory.append(key)
        print("You take the key. It's strangely heavy.")
    else:
        print("You decide to leave the key.")

    print("There's nothing else to do in this room. You decide to leave.")
    input()

def vault_room(player, row, column):
    print("You walk into the room and see a large door. It reminds you of a bank vault. It has a single keyhole.")
    from player_data import player_inventory
    for item in player_inventory:
        if item.name == 'Strange key':
            action = input("Use your strange key? (Yes/No) ").capitalize()
            if action == 'Yes':
                dungeon_action_1[row][column] = True
                player_inventory.remove(item)
                print("You use all of your might to open the vault.")
                input()
                print("After almost a minute of struggling, the vault opens!")
                print("+50 EXP!")
                player.add_experience(50)
                print("Inside you find 12 gold and a health potion.")
                player.add_gold(12)
                from player_data import healing_potion
                healing_potion.add_item(1)
                print(f"You have {player.gold} gold.")
                print(f"You also have {healing_potion.amount} healing potions.")
                input()
                print("There's nothing else. You decide to leave.")
                return
            else:
                print("You decide not to use your key. You leave.")
                input()
                return

    print("You don't have anything to open the door with. You decide to leave.")
    input()

def boss_entrance_1(player, row, column):
    global boss_gate
    if player.level < 2:
        print("You approach a strange red doorway. A deep sense of dread fills you. You feel weak and unprepared for the challenge that lies ahead.")
        action = input("Are you sure you want to continue? (Yes/No) ").capitalize()
        if action != 'Yes':
            return 'Boss escape'
    else:
        action = 'Continue'

    if action == 'Continue':
        print("You walk into the room and all of your exits are cut off by gates! There's a strange red doorway ahead of you.")
        print("You feel a deep sense of dread from the doorway. You notice that there's nothing holding the gates down.")
        if boss_gate:
            action = input("Try to pry open the gates to escape? (Yes/No) ").capitalize()
        else:
            print("You don't think it's a good idea to try and open the gates again, however. You decide it's better to face your fate.")
            return 'Boss'

        if action == 'Yes' and boss_gate:
            if (random.randint(1,20) + player.stat_modifier(player.strength)) > 15:
                print("With all of your might, you manage to pry the gates open! You can now escape.")
                print("You also feel yourself get stronger. +25 EXP!")
                player.add_experience(25)
                boss_gate = False
                input()
                return 'Boss escape'
            else:
                print("You try to open the gates, but aren't strong enough.")
    print("You decide to face your fate. You feel ready.")
    return 'Boss'

def boss_1(player, row, column):
    print("You enter the room and sense an evil presence ahead. You see a small red liquid on the floor.")
    action = input("Drink the red liquid? (Yes/No) ").capitalize()
    if action == 'Yes':
        print("You drink the red liquid. It tastes faintly like strawberry lemonade... It reminds you of home.")
        print("You heal 50% max HP!")
        player.heal((player.max_health // 2))
        print(f"You have {player.health} health.")
        input()
    else:
        print("You decide not to drink the potion.")

    print("You prepare yourself, and continue...")
    from enemy_data import Enemy
    warden_boss = Enemy('Warden Boss', 2, 1, 35, 14, 2, 15, 5, boss=True, special_attack='Basic')
    encounter(player, warden_boss)
    return 'Boss'

def staircase_1(player, row, column):
    print("You see a staircase ahead of you. After all you've been through, you decide to descend.")
    print(f"Congratulations {player.name}! You have sucessfully beaten the first layer of the great coil.")
    print("Before continuing your adventures, a break.")
    #makes the player level up
    player.add_experience(player.level_up_experience_calculator())
    return 'Staircase'

#all code below this comment is for the encounter() function except for the three dungeon maps

def player_action(text, options):

    while True:
        choice = input(text).capitalize()
        if choice in options:
            return choice
        else:
            print("Invalid choice!")

def damage_calc(enemy, player, type):
    if type == 'Melee':
        print(f"You hit the {enemy.name}.")
        damage = int(max(1, (random.randint(int(player.melee.damage * 0.7),int(player.melee.damage * 1.3)) + player.stat_modifier(player.strength) - enemy.armor)))
        #if an enemy is vulnerable or resistant to a certain attack, deal double or half damage
        if player.melee.damage_type == enemy.vulnerable:
            damage *= 2
            print("This attack does especially well!")
        elif player.melee.damage_type == enemy.resistant:
            damage //= 2
            print("This attack seems less impactful.")
        enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        input()
        return
    elif type == 'Ranged':
        print(f"You hit the {enemy.name}.")
        damage = int(max(1, (random.randint(int(player.ranged.damage * 0.7),int(player.ranged.damage * 1.3)) + player.stat_modifier(player.dexterity) - enemy.armor)))
        #if an enemy is vulnerable or resistant to a certain attack, deal double or half damage
        if player.ranged.damage_type == enemy.vulnerable:
            damage *= 2
            print("This attack does especially well!")
        elif player.ranged.damage_type == enemy.resistant:
            damage //= 2
            print("This attack seems less impactful.")
        enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        input()
        return
    elif type == 'Sneak attack':
        print(f"You manage to sneak up on the {enemy.name} and do a sneak attack!")
        damage = int(max(1, (random.randint(int(player.melee.damage * 0.7),int(player.melee.damage * 1.3)) + player.stat_modifier(player.strength) - enemy.armor)))
        #if an enemy is vulnerable or resistant to a certain attack, deal double or half damage
        if player.melee.damage_type == enemy.vulnerable:
            damage *= 2
            print("This attack does especially well!")
        elif player.melee.damage_type == enemy.resistant:
            damage //= 2
            print("This attack seems less impactful.")
        damage *= 2
        enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        input()
        return
    elif type == 'Enemy melee':
        damage = int(max(1, (random.randint(int(enemy.melee * 0.7),int(enemy.melee * 1.3))+ enemy.stat_modifier(enemy.strength) - player.armor)))
        print(f"The {enemy.name} hits you with a melee attack for {damage} damage.")
        player.take_damage(damage)
        print(f"You have {player.health} health left.")
        input()
        return
    elif type == 'Enemy ranged':
        damage = int(max(1, (random.randint(int(enemy.ranged * 0.7),int(enemy.ranged * 1.3))+ enemy.stat_modifier(enemy.dexterity) - player.armor)))
        print(f"The {enemy.name} hits you with a ranged attack for {damage} damage.")
        player.take_damage(damage)
        print(f"You have {player.health} health left.")
        input()
        return


def enemy_action_determiner(enemy, player):
    if enemy.boss and enemy.special_attack_available:
        return 'Special attack'
    elif enemy.boss and enemy.ranged > 0:
        return 'Ranged attack'
    elif enemy.boss:
        return 'Melee attack'

    if enemy.health < player.health and enemy.ranged > 0:
        return 'Ranged attack'
    else:
        return 'Melee attack'

#function that returns a value 1-100 based on how fast the player reacted to a prompt
def reaction_time(type):
    #gets a random number and divides by 10. This is used as the random amount of time waited
    time_waiting = random.randint(5,30)
    time_waiting = time_waiting / 10
    if type == 'Dodge':
        print("You prepare to dodge the enemy's attack.")
        input("Prepare to dodge! Press enter to continue... ")
    elif type == 'Special attack':
        print("You prepare a special attack.")
        input("Prepare to hit! Press enter to continue... ")
    elif type == 'Enemy dodge':
        print("The enemy is trying to attack you with a special attack!")
        input("Prepare to dodge! Press enter to continue... ")
    #pauses the game for a random amount of time
    time.sleep(time_waiting)
    start = time.time()

    input("Press enter!")

    end = time.time()
    #takes the amount of time between start and end and provides a number
    total = end - start
    total *= 100
    total = int(total)
    if total > 100:
        total = 100
    return total

##damage
#hitting melee - (d10 * weapon proficciency) + strength compared to enemy d10 + dex
#hitting ranged - (d10 * weapon proficciency) + dex compared to enemy d10 + dex
#dodging - d10 + dex
#damage - max between randomint(half damage, double damage) and strength // 2, all of that - armor
#special attack - damage is determined by minigame, always hits

##actions
#engage
    #attack
        #special attack
        #ranged
        #melee
    #dodge
    #class action
#run
#use item
def encounter(player, enemy):
    fighting = True
    hunter_net = 0
    ranger_class_action = False
    barb_rage = 0
    rounds = 0
    turn_counter = 0
    player_options = ['Use consumable', 'Run', 'Attack', 'Dodge']
    attack_options = ['Melee', 'Ranged']

    enemy_melee = (enemy.stat_modifier(enemy.strength) + (enemy.level // 2))
    enemy_ranged = (enemy.stat_modifier(enemy.dexterity) + (enemy.level // 2))
    enemy_AC = (10 + enemy.stat_modifier(enemy.dexterity))

    player_melee = (player.stat_modifier(player.strength) + (player.level // 2))
    player_ranged = (player.stat_modifier(player.dexterity) + (player.level // 2))
    player_AC = (10 + player.stat_modifier(player.dexterity))

    if player.class_name == 'Rogue' and player.melee.attack_type == 'Light':
        attack_options.append('Sneak attack')
        sneak_attack_text = '/Sneak attack'
    else:
        sneak_attack_text = ''

    if player.melee_skill >= 5:
        melee_attack_turns = 2
    else:
        melee_attack_turns = 1

    if player.ranged_skill >= 5:
        ranged_attack_turns = 2
    else:
        ranged_attack_turns = 1

    if player.melee.attack_type == 'Light':
        melee_attack_turns += 1

    #if the player can use a class action, adds the respective text and option
    if player.class_action_available:
        class_action_text = '/Class action'
        player_options.append('Class action')
    else:
        class_action_text = ''

    #if the player can use a special attack, adds the respective text and option
    if player.special_attack_available:
        special_attack_text = '/Special attack'
        attack_options.append('Special attack')
    else:
        special_attack_text = ''

    #if the enmy is a boss, removes the run text and actual ability to run
    if enemy.boss:
        run_text = ''
        player_options.remove('Run')
    else:
        run_text = '/Run'

    print(f"You are fighting a {enemy.name}!")

    #if the player is underleveled, allows them to run away more easily
    if player.level < enemy.level and enemy.boss == False:
        underleveled = True
        print("You are underleveled! Running will be easier")
    else:
        underleveled = False

    while fighting:
        barb_rage -= 1
        if barb_rage >= 1:
            print(f"You have {barb_rage} rounds of rage left.")

        if hunter_net >= 1:
            print(f"You have {hunter_net} rounds of your net left.")

        if hunter_net == 0:
            enemy_AC = enemy.restore_dex()

        if barb_rage == 0:
            player.rage_end()
            player_melee = (player.stat_modifier(player.strength) + (player.level // 2))
            player_ranged = (player.stat_modifier(player.dexterity) + (player.level // 2))
            player_AC = (10 + player.stat_modifier(player.dexterity))

        dodged = False
        print(f"The {enemy.name} has {enemy.health} health left.")
        action = player_action(f"It is your turn. What do you do? (Attack/Dodge/Use consumable{class_action_text}{run_text}) ", player_options)
        if action == 'Run':
            if underleveled:
                if ((player.stat_modifier(player.dexterity) + (enemy.level - player.level)) + random.randint(1,10)) > (enemy.stat_modifier(enemy.dexterity) + random.randint(1,10)):
                    print("You manage to escape. You run into a random room.")
                    player.rage_end()
                    return 'Run'
                else:
                    print(f"You don't manage to escape. The {enemy.name} prepares to attack...")
            elif (player.stat_modifier(player.dexterity) + random.randint(1,10)) > (enemy.stat_modifier(enemy.dexterity) + random.randint(1,10)):
                print("You manage to escape. You run into a random room.")
                player.rage_end()
                return 'Run'
            else:
                print(f"You don't manage to escape. The {enemy.name} prepares to attack...")
        elif action == 'Use consumable':
            acessing_consumables = True
            consumables = []
            for item in player_data.player_inventory:
                if item.type == 'Consumable' and item.amount > 0:
                    print(f"Name: {item.name} - Amount: {item.amount} - Healing: {item.healing}")
                    consumables.append(item)
            if len(consumables) == 0:
                print("You have no consumables to use!")
                input()
                acessing_consumables = False
                dodged = True

            while acessing_consumables:
                inventory_selection_2 = input("What would you like to use? ").capitalize()
                if inventory_selection_2 == 'Leave':
                    acessing_consumables = False
                    dodged = True
                else:
                    for item in consumables:
                        if item.name == inventory_selection_2:
                            print(f"You use a {inventory_selection_2}.")
                            healing = item.amount_healing()
                            player.heal(healing)
                            item.use_item(1)
                            print(f"You heal {healing} HP! You now have {player.health} HP.")
                            acessing_consumables = False
                            input()

                    if acessing_consumables:
                        print("Please enter a valid consumable! Type leave to leave.")

        elif action == 'Dodge':
            time_taken = reaction_time('Dodge')
            if time_taken < 40:
                print("You manage to dodge the attack!")
                dodged = True
            else:
                print("You don't manage to dodge the attack.")
        elif action == 'Class action':
            class_action_text = ''
            player.class_action_available = False
            player_options.remove('Class action')
            if player.class_action == 'Basic':
                if player.class_name == 'Barbarian':
                    print(f"You are enraged! Your strength increases, but your dexterity decreases for 2 turns.")
                    player.rage()
                    player_melee = (player.stat_modifier(player.strength) + (player.level // 2))
                    player_ranged = (player.stat_modifier(player.dexterity) + (player.level // 2))
                    player_AC = (10 + player.stat_modifier(player.dexterity))
                    barb_rage = 3
                    input()
                elif player.class_name == 'Ranger':
                    print("You now have a multiattack! You can now shoot an extra arrow per turn.")
                    ranger_class_action = True
                    input()
                elif player.class_name == 'Rogue':
                    print("You inspect your enemy to take advantage of it's vulnerabilities and spot its resistences.")
                    print(f"The {enemy.name} is vulnerable to {(enemy.vulnerable).lower()} attacks.")
                    print(f"The {enemy.name} is resistant to {(enemy.resistant).lower()} attacks.")
                    input()
                    if player.level > 2:
                        print("You can also glean some more information about the enemy's statistics.")
                        print(f"The enemy has a dexterity of {enemy.dexterity} and a strength of {enemy.strength}.")
                elif player.class_name == 'Hunter':
                    print("You deploy a net on your enemy. Their dexterity is halved for two rounds.")
                    enemy_AC = enemy.half_dex()
                    hunter_net = 2
                    input()
        elif action == 'Attack':
            hunter_net -=1
            action = player_action(f"How do you want to attack? (Melee/Ranged{sneak_attack_text}{special_attack_text}) ", attack_options)
            if action == 'Melee':
                while rounds < melee_attack_turns:
                    rounds += 1
                    if (random.randint(1,20) + player_melee) >= enemy_AC:
                        damage_calc(enemy, player, 'Melee')
                    else:
                        print("You miss.")
                        input()
                rounds = 0
            elif action == 'Ranged':
                while rounds < ranged_attack_turns:
                    rounds += 1
                    if ranger_class_action:
                        print("You use your multiattack!")
                        ranger_class_action = False
                        
                        if (random.randint(1,20) + player_ranged) >= enemy_AC:
                            damage_calc(enemy, player, 'Ranged')
                        else:
                            print("You miss.")
                            input()

                    if (random.randint(1,20) + player_ranged) >= enemy_AC:
                        damage_calc(enemy, player, 'Ranged')
                    else:
                        print("You miss.")
                        input()
                rounds = 0
            elif action == 'Special attack':
                time_taken = reaction_time('Special attack')
                if time_taken <= 35:
                    multiplier = 1.25
                    print("You hit dead center! 25% more damage.")
                elif time_taken <= 60:
                    multiplier = 1
                    print("You hit near the chest! Regular hit.")
                elif time_taken <= 80:
                    multiplier = 0.75
                    print("You hit an arm! -25% damage")
                else:
                    multiplier = 0.5
                    print("You barely hit! -50% damage")
                damage = int(max(1,((player.melee.damage * 2) * multiplier) - enemy.armor))
                enemy.take_damage(damage)
                print(f"You deal {damage} damage!")
                player.special_attack_available = False
                special_attack_text = ''
                attack_options.remove('Special attack')
            elif action == 'Sneak attack':
                while rounds < melee_attack_turns:
                    if rounds == 0:
                        if (random.randint(1,20) + player.stat_modifier(player.dexterity)) >= (enemy_AC + enemy.level):
                            damage_calc(enemy, player, 'Sneak attack')
                        else:
                            print(f"You try to sneak up on the {enemy.name}, but fail!")
                            input()
                    else:
                        if (random.randint(1,20) + player_melee) >= enemy_AC:
                            damage_calc(enemy, player, 'Melee')
                        else:
                            print("You miss.")
                            input()
                    rounds += 1
                rounds = 0

        if enemy.health > 0 and dodged == False:
            enemy_action = enemy_action_determiner(enemy, player)
            if enemy_action == 'Melee attack': 
                if (random.randint(1,20) + enemy_melee) >= player_AC:
                    damage_calc(enemy, player, 'Enemy melee')
                else:
                    print(f"The {enemy.name} misses its attack.")
                    input()
            elif enemy_action == 'Ranged attack':
                if (random.randint(1,20) + enemy_ranged) >= player_AC:
                    damage_calc(enemy, player, 'Enemy ranged')
                else:
                    print(f"The {enemy.name} misses its attack.")
                    input()
            elif enemy_action == 'Special attack':
                time_taken = reaction_time('Enemy dodge')
                if time_taken <= 35:
                    multiplier = 0.5
                    print("You manage to dodge well! -50% damage")
                elif time_taken <= 60:
                    multiplier = 0.75
                    print("You manage to dodge slightly. -25% damage")
                else:
                    multiplier = 1
                    print("You don't manage to dodge well. 100% damage")
                damage = int(max(1, ((enemy.melee * 2) * multiplier) - player.armor))
                player.take_damage(damage)
                print(f"You take {damage} damage. You have {player.health} health left.")
                input()
                enemy.special_attack_available = False

        if enemy.health <= 0:
            print(f"The {enemy.name} has died!")
            fighting = False
            gold = random.randint(enemy.level,(enemy.level * 5))
            print(f"Encounter over. You get {gold} gold")
            player.add_gold(gold)
            print(f"You have {player.gold} gold.")
            input()
            experience = (enemy.level * 50)
            print(f"You also gain {experience} experience!")
            player.add_experience(experience)
            print(f"You have {player.experience} experience.")
            input()
            player.rage_end()
            return 'Victory'

        if 'Sneak attack' in attack_options:
            attack_options.remove('Sneak attack')
            sneak_attack_text = ''


dungeon_map_1 = [
    ['Entrance' , chest_room, vault_room, rest_room],
    [enemy_room , lore_room, chest_room, boss_entrance_1],
    [key_room , rest_room, 'Wall', boss_1],
    [lore_room , miniboss_1, 'Wall', staircase_1]
]

dungeon_action_1 = [
    [True, False, False, False],
    [False, False, False, False],
    [False, False, False, False],
    [False, False, False, False]
]

dungeon_visited_1 = [
    [True, False, False, False],
    [False, False, False, False],
    [False, False, False, False],
    [False, False, False, False]
]