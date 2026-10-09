import random
import time

dungeon_map_1 = [
    ['Entrance' , 'Empty', 'Empty', 'Empty'],
    ['Empty' , 'Empty', 'Empty', 'Empty'],
    ['Empty' , 'Empty', 'Empty', 'Empty'],
    ['Empty' , 'Empty', 'Empty', 'Staircase']
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
        damage = int(max(1, (random.randint(int(player.melee.damage * 0.7),int(player.melee.damage * 1.3))+ player.stat_modifier(player.strength) - enemy.armor)))
        enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        input()
        return
    elif type == 'Ranged':
        print(f"You hit the {enemy.name}.")
        damage = int(max(1, (random.randint(int(player.ranged.damage * 0.7),int(player.ranged.damage * 1.3))+ player.stat_modifier(player.dexterity) - enemy.armor)))
        enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        input()
        return
    elif type == 'Enemy melee':
        damage = max(1, (random.randint(int(enemy.melee * 0.7),int(enemy.melee * 1.3))+ enemy.stat_modifier(enemy.strength) - player.armor))
        player.take_damage(damage)
        print(f"The {enemy.name} hits you with a melee attack for {damage} damage.")
        print(f"You have {player.health} health left.")
        input()
        return
    elif type == 'Enemy ranged':
        damage = max(1, (random.randint(int(enemy.ranged * 0.7),int(enemy.ranged * 1.3))+ enemy.stat_modifier(enemy.dexterity) - player.armor))
        player.take_damage(damage)
        print(f"The {enemy.name} hits you with a ranged attack for {damage} damage.")
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
    run_text = '/Run'
    special_attack_text = ''
    class_action_text = '/Class action'
    player_options = ['Use item', 'Run', 'Attack', 'Dodge', 'Class action']
    attack_options = ['Melee', 'Ranged']
    if player.special_attack_available:
        special_attack_text = '/Special attack'
        attack_options.append('Special attack')
    if enemy.boss:
        run_text = ''
        player_options.remove('Run')

    if player.level < enemy.level:
        underleveled = True
    else:
        underleveled = False
    print(f"You are fighting a {enemy.name}!")

    while fighting:
        dodged = False
        print(f"The {enemy.name} has {enemy.health} health left.")
        action = player_action(f"It is your turn. What do you do? (Use item/Attack/Dodge{class_action_text}{run_text}) ", player_options)
        if action == 'Run':
            if underleveled and ((player.stat_modifier(player.dexterity) + (enemy.level - player.level)) + random.randint(1,10)) > (enemy.stat_modifier(enemy.dexterity) + random.randint(1,10)):
                print("You manage to escape. You run into a random room.")
                return 'Run'
            elif (player.stat_modifier(player.dexterity) + random.randint(1,10)) > (enemy.stat_modifier(enemy.dexterity) + random.randint(1,10)):
                print("You manage to escape. You run into a random room.")
                return 'Run'
            else:
                print(f"You don't manage to escape. The {enemy.name} prepares to attack...")
        elif action == 'Use item':
            print("This functionality will become available when the inventory becomes available. So not rn")
        elif action == 'Dodge':
            time_taken = reaction_time('Dodge')
            if time_taken < 40:
                print("You manage to dodge the attack!")
                dodged = True
            else:
                print("You don't manage to dodge the attack.")
        elif action == 'Class action':
            print("This requires me to make class actions, which don't exist.")
        elif action == 'Attack':
            action = player_action(f"How do you want to attack? (Melee/Ranged{special_attack_text}) ", attack_options)
            if action == 'Melee':
                if (random.randint(1,10) + player.stat_modifier(player.strength) + player.skill_modifier(player.melee_skill)) > (random.randint(1,10) + enemy.stat_modifier(enemy.dexterity)):
                    damage_calc(enemy, player, 'Melee')
                else:
                    print("You miss.")
                    input()
            elif action == 'Ranged':
                if (random.randint(1,10) + player.stat_modifier(player.dexterity) + player.skill_modifier(player.ranged_skill)) > (random.randint(1,10) + enemy.stat_modifier(enemy.dexterity)):
                    damage_calc(enemy, player, 'Ranged')
                else:
                    print("You miss.")
                    input()
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


        if enemy.health > 0 and dodged == False:
            enemy_action = enemy_action_determiner(enemy, player)
            if enemy_action == 'Melee attack': 
                if (random.randint(1,10) + enemy.stat_modifier(enemy.strength) + (enemy.level - 1)) > (random.randint(1,10) + player.stat_modifier(player.dexterity)):
                    damage_calc(enemy, player, 'Enemy melee')
                else:
                    print(f"The {enemy.name} misses its attack.")
                    input()
            elif enemy_action == 'Ranged attack':
                if (random.randint(1,10) + enemy.stat_modifier(enemy.dexterity) + (enemy.level - 1)) > (random.randint(1,10) + player.stat_modifier(player.dexterity)):
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
            return 'Victory'
        