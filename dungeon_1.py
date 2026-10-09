import random
import main

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

##damage
#hitting - (d10 * weapon proficciency) + strength
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
    class_action_text = '/Class action'
    player_options = ['Use item', 'Run', 'Attack', 'Dodge', 'Class action']
    if enemy.boss == True:
        run_text = ''
        player_options.remove('Run')

    if player.level < enemy.level:
        underleveled = True
    else:
        underleveled = False
    print(f"You are fighting a {enemy.name}!")

    while fighting:
        action = player_action(f"It is your turn. What do you do? (Use item/Attack/Dodge{class_action_text}{run_text})", player_options)
        if action == 'Run':
            if underleveled and ((player.dexterity + enemy.level) + random.randint(1,10)) > (enemy.dexterity + random.randint(1,10)):
                print("You manage to escape. You run into a random room.")
                return 'Run'
            elif (player.dexterity + random.randint(1,10)) > (enemy.dexterity + random.randint(1,10)):
                print("You manage to escape. You run into a random room.")
                return 'Run'
            else:
                print(f"You don't manage to escape. The {enemy.name} prepares to attack...")
        elif action == 'Use item':
            print("This functionality will become available when the inventory becomes available. So not rn")
        elif action == 'Dodge':
            print("This requires a quick time action function, which doesn't exist.")
        elif action == 'Class action':
            print("This requires me to make class actions, which don't exist.")
        elif action == 'Attack':
            print("This requires a lot of logic, and I am tired.")
