import player_data
import dungeon_1
import random

#row is up and down
row = 0
#column is left to right
column = 0
#used mainly for the miniboss escape
previous_direction = 0

#gives all possible directions for a map of any size
def movement(map, action):
    global row
    global column
    global previous_direction
    
    possible_directions = []
    possible_directions_text = []
    directions = {
        1: (-1, 0),
        2: (0, -1),
        3: (1, 0),
        4: (0, 1)
    }
    text_directions = {
        1: 'Up',
        2: 'Left',
        3: 'Down',
        4: 'Right'
    }
    #figures out how big the map is
    max_direction = (len(map) - 1)
    #1 is up, 2 is left, 3 is down, 4 is right

    #finds out which directions are valid for the player's position, heavily helped by chatgpt
    for direction, (row_change, column_change) in directions.items():
        local_row = row
        local_column = column

        local_row += row_change
        local_column += column_change

        #makes sure the player doesn't walk into the border of the map
        if local_row > max_direction or local_row < 0:
            pass
        elif local_column > max_direction or local_column < 0:
            pass
        #makes sure the player doesn't walk into a map wall
        elif map[local_row][local_column] == 'Wall':
            pass
        else:
            possible_directions.append(direction)

    #makes sure the player doesn't walk into the boss room
    if action == 'Boss escape':
        possible_directions.remove(3)
        action = 'Move'
    #makes sure the player walks into the boss room
    elif action == 'Boss':
        possible_directions.clear()
        possible_directions.append(3)
        action = 'Move'

    if action == 'Move':
        print(f"You see {len(possible_directions)} exits to this room.")

        #adds every direction as text to a list, and prints them
        for direction, text in text_directions.items():
            if direction in possible_directions:
                possible_directions_text.append(text)
                print(f"{direction}) {text}")

        #takes an input from the player to decide where to go, works with text and number
        while True:
            player_direction = input("Where do you go? ")
            try:
                player_direction = int(player_direction)
                if player_direction in possible_directions:
                    break
                else:
                    print("Please pick a valid direction!")
            except ValueError:
                player_direction = player_direction.capitalize()
                if player_direction in possible_directions_text:
                    for direction, text in text_directions.items():
                        if player_direction == text:
                            player_direction = direction
                            break
                    break
                else:
                    print("Please pick a valid direction!")
    elif action == 'Run':
        player_direction = random.choice(possible_directions)
    elif action == 'Miniboss':
        if previous_direction == 3:
            player_direction = 1
        elif previous_direction == 4:
            player_direction = 2

    previous_direction = player_direction

    for direction, (row_change, column_change) in directions.items():
        if direction == player_direction:
            row += row_change
            column += column_change
            return

#creates a map room variable which shows the player a map of where they've been to, works for any sized map
def player_map(dungeon_map, dungeon_visited):
    map_size = len(dungeon_map)
    #creates LOCAL rows and columns, used for later logic
    row_local = -1
    column_local = 0

    row_adder = 0
    column_adder = 0

    map_room_list = []
    empty_room_list = []

    seperator = ''
    print_room = ''

    #creates a list with the same size as the dungeon and fills it with ?
    for number in range(map_size):
        empty_room_list =[]
        for number in range(map_size):
            empty_room_list.append('?')
        map_room_list.append(empty_room_list)

    for room in dungeon_map:
        #sets row_local and column_local to 0
        row_local += 1
        column_local = 0
        for subroom in room:
            #checks every room in dungeon_1_visited, and if you've been there adds the corresponding symbol
            if dungeon_visited[row_local][column_local] == True:
                if dungeon_map[row_local][column_local] == dungeon_1.enemy_room:
                     map_room_list[row_local][column_local] = 'x'
                elif dungeon_map[row_local][column_local] == dungeon_1.lore_room:
                     map_room_list[row_local][column_local] = '"'
                elif dungeon_map[row_local][column_local] == dungeon_1.chest_room:
                     map_room_list[row_local][column_local] = '$'
                elif dungeon_map[row_local][column_local] == 'Entrance':
                     map_room_list[row_local][column_local] = ' '
                elif dungeon_map[row_local][column_local] == dungeon_1.miniboss_1:
                     map_room_list[row_local][column_local] = 'X'
                elif dungeon_map[row_local][column_local] == dungeon_1.rest_room:
                     map_room_list[row_local][column_local] = '*'
                else:
                    map_room_list[row_local][column_local] = ' '

            if dungeon_map[row_local][column_local] == 'Wall':
                map_room_list[row_local][column_local] = '#'
            if row == row_local and column == column_local:
                map_room_list[row_local][column_local] = '@'
            column_local += 1

    #displays the map with the symbols filled in depending on where you've been
    print("You open your map. You fill it in with everywhere you've been so far.")
    input()
    print("Your player is represented by the @ symbol")
    row_local = 0
    column_local = 0

    for number in range(0, map_size):
        #creates a seperator of the appropriate size
        if seperator == '':
            for number_again in range(map_size):
                seperator += '+---'
                if number_again == (map_size - 1):
                    seperator += '+'

        #prints the contents of the room if you're been there
        while row_adder == number:
            print_room += f'| {map_room_list[row_local + row_adder][column_local + column_adder]} '
            column_adder += 1
            if column_adder == map_size:
                column_adder = 0
                row_adder += 1
                print_room += '|'

        print(seperator)
        print(print_room)
        print_room = ''
        if number == (map_size - 1):
            print(seperator)

    input()


def inventory():
    player_options = ['Melee', 'Ranged', 'Use consumable', 'Leave']
    consumables = []
    melee_weapons = []
    ranged_weapons = []
    print("Your current iventory is as follows.")
    for item in player_data.player_inventory:
        if item.amount > 0:
            print(item.name, ':', item.amount)

    while True:
        inventory_selection = input('What would you like to do? (Melee/Ranged/Use consumable) ').capitalize()
        if inventory_selection in player_options:
            break
        else:
            print("Please select a valid option! Type leave to leave.")

    if inventory_selection == 'Leave':
        return
    #for right now, consumables are only healing potions. This will be changed later
    elif inventory_selection == 'Use consumable':
        for item in player_data.player_inventory:
            if item.type == 'Consumable' and item.amount > 0:
                print(f"Name: {item.name} - Amount: {item.amount} - Healing: {item.healing[0]}-{item.healing[1]}")
                consumables.append(item)

        if len(consumables) == 0:
            print("You have no consumables to use!")
            input()
            return
        
        while True:
            inventory_selection_2 = input("What would you like to use? ").capitalize()
            if inventory_selection_2 == 'Leave':
                return
            else:
                for item in consumables:
                    if item.name == inventory_selection_2:
                        print(f"You use a {inventory_selection_2}.")
                        healing = item.amount_healing()
                        player.heal(healing)
                        item.use_item(1)
                        print(f"You heal {healing} HP! You now have {player.health} HP.")
                        return

                print("Please enter a valid consumable! Type leave to leave.")
    else:
        for item in player_data.player_inventory:
            if item.type == inventory_selection:
                print(f"Name: {item.name} - Damage: {item.damage} {item.damage_type} - Attack type: {item.attack_type}")
                if inventory_selection == 'Melee':
                    melee_weapons.append(item)
                else:
                    ranged_weapons.append(item)

        inventory_selection = inventory_selection.lower()
        inventory_selection_2 = input(f"Would you like to equip a new {inventory_selection} weapon? (Yes/No) ").capitalize()
        if inventory_selection_2 == 'Yes':
            while True:
                inventory_selection_2 = input("What would you like to equip? ").capitalize()
                for item in player_data.player_inventory:
                    if item.type.lower() == inventory_selection:
                        if item.name == inventory_selection_2:
                            inventory_selection_2 = inventory_selection_2.lower()
                            print(f"You equip the {inventory_selection_2}!")
                            print(f"You now deal {item.damage} damage.")
                            if inventory_selection == 'melee':
                                player.melee = item
                            else:
                                player.ranged = item
                            return
                    
                print("Please pick a valid item.")
        else:
            return

#intro text
print("Hello adventurer! Welcome to this python text based RPG! Your goal is to descend a dungeon filled with enemies and puzzles to slay the monster at its heart.")
print("This game is fairly complicated, and has many different systems which interact with each other.")
tutorial = input("Would you like a tutorial? ").capitalize()
if tutorial == 'Yes':
    tutorial_sections = {
        'General' : False,
        'Combat' : False,
        'Movement' : False,
        'Inventory' : False,
        'Classes' : False,
    }
    in_tutorial = True

    while in_tutorial:
        number = 0
        for section in tutorial_sections:
            if tutorial_sections[section]:
                print(section, '(Done!)')
                number += 1
            else:
                print(section)

        if number == 5:
            print("You've read all of the tutorials! You're ready to face the challenge that lies ahead, good luck!")
            in_tutorial = False
            break

        tutorial = input("What would you like to learn about? ").capitalize()
        if tutorial == 'Leave':
            in_tutorial = False
        elif tutorial == 'General':
            print("Welcome to the great coil, adventurer! This tutorial will explain all of the basic features of this game.")
            print("Firstly, selecting an option. When the game stops and asks you a question, you will need to input an answer.")
            print("The possible options will usually be within parenthesis, like this. (Yes/No)")
            print("Capitalization does not matter, but spelling does. Make sure you spell your selection correctly!")
            print("The game might sometimes stop without asking anything. This is to not overwhelm you with information all at once.")
            print("If this happens, just press enter. Try it now!")
            input()
            print("Great! Next are the player stats. Every player, and enemy, has the following basic stats.")
            print("First is health, or HP. This is how much damage you have taken, and how long you can survive.")
            print("If your health drops to 0, you die. Similarly, if your enemy's health drops to 0, they will die!")
            print("Next is dexterity. This is how maneuverable you are. The higher dexterity you have, the harder you are to hit.")
            print("It's also used for ranged combat! The higher dexterity you have, the more damage your ranged attacks do.")
            print("Similarly, next up is strength. The higher strength you have, the more damage you do, and the more likely your melee attacks are to hit.")
            print("Next is armor. Armor is how much damage gets reduced after a sucessfull attack.")
            print("For example, if you have 2 armor and an enemy hits you for 6 damage, you will only take 4 damage instead!")
            input()
            print("Next are the skills. Both melee and ranged weapons have skills attached to them. At levels 3, 5, 7, and 9 you will unlock a new ability!")
            print("Notably, at level 5 you can make an extra attack with that type of weapon, so having a melee skill level of 5 will allow you to attack twice with any melee weapon!")
            print("Next is intelligence. Intelligence doesn't have a use yet, but it'll be used for spells when those exist")
            print("Next is gold. Gold can be used to buy things at shops. You can find gold by killing enemies or while exploring the dungeon.")
            print("Last but not least is experience. You gain experience by killing enemies, solving puzzles, or solving an encounter!")
            print("If you get enough experience, you will level up! Leveling up allows you to increase nearly all of your stats.")
            input()
            print("Before use, stats are converted into a bonus, which will be used to calculate the benefit you get from the given stat.")
            print("The exact calculation is (stat - 10)/2. In plain terms, this means that a stat of 10 is +0. Every 2 points above 10 will give you an extra benefit.")
            print("So 12 gives you +1, 14 gives you +2, 16 gives you +3 etc etc. This means that two stats, like 12 and 13, can give the same bonus, in this case +2.")
            print("This works the other way around too! An 8 is -1, a 6 is -2, etc etc.")
            input()
            print("Those are all the basic things you need to know! For more detailed tutorials, select what you would like to learn from the menu!")
            input()
            tutorial_sections['General'] = True
        elif tutorial == 'Combat':
            print("When adventuring through the dungeons of the great coil, you may find yourself fighting a variety of enemies.")
            print("All enemies have the following stats.")
            print("Firstly enemies have vulnerabilities. Vulnerabilities are what the enemy is least prepared to protect against.")
            print("Put simply, if you attack an enemy with the same attack type it's vulnerable against, it'll take double damage.")
            print("On the other end of the spectrum, there are resistances. These are what the enemy is most prepared to protect against.")
            print("If you attack an enemy with the same attack as it's resistant to, it'll take half damage.")
            input()
            print("Next up are special attacks. A special attacks are generally only available to bosses. If an enemy uses a special attack, it'll always hit.")
            print("However, you can dodge it! If you press enter fast enough, the enemy's attack will be less effective against you.")
            print("Finally are all the stats shared with the player! All enemies have strength, dexterity, armor, melee and ranged attacks, and last but not least health.")
            print("To learn about these, read the classes tutorial.")
            input()
            print("You should also know that most optional bosses can be skipped before entering the fight.")
            print("While you can't run from a boss, most miniboss rooms will warn you, so if you feel uneasy about something, make sure you're ready!")
            print("Most minibosses will have a campfire nearby, where you can heal. This is where you regenerate your special attack!")
            print("That's all there is to know about enemies. Good luck adventurer!")
            input()
            tutorial_sections['Combat'] = True
        elif tutorial == 'Movement':
            print("When you enter the dungeon, you are entering a grid of rooms arranged in a square.")
            print("The first floor is 4 rooms by 4 rooms. This may seem scary, but fear not! You have a map available to you at all times.")
            print("Here's what it looks like!")
            player_map(dungeon_1.dungeon_map_1, dungeon_1.dungeon_visited_1)
            print("When you move, either up, down, left, or right, you are moving as seen from a birdseye perspective.")
            print("In between rooms, you have the ability to select between moving, opening your map, or acessing your inventory.")
            print("That's all there is to know about movement!")
            input()
            tutorial_sections['Movement'] = True
        elif tutorial == 'Inventory':
            print("In between rooms, you are given the option to pick between moving, opening your map, or acessing your inventory.")
            print("To learn about movement and maps, read the movement tutorial.")
            print("In the inventory section, you can do three things.")
            print("1) You can use a consumable item. Currently, the only consumable is a health potion. If you drink it, it'll heal you!")
            print("2) Change your melee weapon. If you have more than one melee weapon, you can choose which one to equip!")
            print("When in combat, you'll only use the weapon you have equipped, not the ones in your inventory.")
            print("You can't change the weapon you have equipped in combat, so choose wisely!")
            print("3) Change your ranged weapon. This is much the same as changing your melee weapon, but it's for your ranged weapon!")
            input()
            print("More generally, you can hold an unlimited amount of things in your inventory. Weapons are unstackable however.")
            print("That's all you need to know about the inventory!")
            input()
            tutorial_sections['Inventory'] = True
        elif tutorial == 'Classes':
            print("At the beginning of any game, you will be able to pick between 4 different classes. They are as follows.")
            print("Barbarian. The barbarian starts with extra health, specifically 24, and it gains 12 health per level.")
            print("It has a strength of 15, and it starts with an armor level of 2 with a melee skill level of 1.")
            print("The downsides are that it has a low dexterity, at 7, and has an intelligence of only 6.")
            print("The barbarian, like all classes, has a class action. The barbarian class action is a rage effect!")
            print("The rage effect increases your strength but decreases your dexterity for 2 turns.")
            print("Nevertheless, if you want a tanky and strong melee fighter, the barbarian is for you.")
            input()
            print("On the complete opposite side of the spectrum is the ranger.")
            print("The ranger has an extremely high dexterity of 15, and has a skill level of 2 with ranged weapons off the bat.")
            print("It also has a fairly high intelligence at 12, and it has an armor level of 1.")
            print("The downsides are that it has a low health at only 18, and it only gains 8 health per level.")
            print("It also has a strength of only 8.")
            print("The ranger has a class action which allows it to have a multiattack with ranged weapons")
            print("If you want to attack enemies from a distance without getting hit, the ranger is for you.")
            input()
            print("If you prefer not to be seen as you kill, the rogue might be your class.")
            print("With a dexterity of 15, equal to that of the ranger, and a strength of 12, you're hard to hit and deal quite a blow.")
            print("The downsides are that you have no armor, and you start with a health of 20 which only increases by 8 per level.")
            print("You also start with a dagger, though, which can do two lower damage attacks per turn.")
            print("The rogue has a class action which allows it to see enemy vulnerabilities and resistances.")
            print("It also has a passive ability! The rogue can sneak up on an enemy and perform a sneak attack if they can remain undetected and are using a light weapon.")
            print("This ability can be used as many times as you want, without needing to recharge! It can only be the first attack for every encounter however.")
            print("If you want to hide in the shadows and sneak up on your enemies to attack, the rogue is for you.")
            input()
            print("Last but not least is the hunter.")
            print("The hunter has base stats of 10 for most of its stats, the exceptions being dexterity, intelligence, and gold.")
            print("The hunter has a health of 22 which increases by 10 every level.")
            print("The hunter also has a dexterity and intelligence of 12, and it also starts off with 5 gold.")
            print("It also has a skill level of 1 in both ranged and melee attacks. All in all, the hunter is a jack of all trades, but master of none.")
            print("The hunter has a class action which allows it to ensnare an enemy in a net, halving its dexterity for 2 turns.")
            print("If you want to be a melee and ranged fighter, and don't want to have to choose, the hunter is for you.")
            input()
            print("Class actions can only be used once per rest, similar to special attacks.")
            print("All classes also have a special attack. This can change with training, but the basic one allows you to deal extra damage to any enemy.")
            print("The attack will always hit, but it can only be used once per rest. You can regenerate special attacks in campfires")
            print("That's all there is to know about classes! Good luck, and pick the class that speaks to you most!")
            input()
            tutorial_sections['Classes'] = True
        else:
            print("Please pick a valid tutorial section!")
            print("(Type leave to leave)")
            input()
elif tutorial == 'Dev':
    print("Welcome dev!")
    player = player_data.player_selection('dev')
    row = int(input("Please input row (up and down) "))
    column = int(input("Please input column (left and right) "))

if tutorial != 'Dev':
    player = player_data.player_selection(None)

#creates three variables required for the while loop
in_dungeon_1 = True
action = 0
room_action = None

#selection between moving, map, and inventory
while in_dungeon_1:
    if room_action == None:
        action = input("What would you like to do? (Move/Map/Inventory) ").capitalize()
    #if the player runs from a fight, makes them go a random direction
    elif room_action == 'Run':
        movement(dungeon_1.dungeon_map_1, room_action)
        action = 'Move'
        room_action = 'Move'
    #if the player runs from the miniboss, makes them go to the room they were in before
    elif room_action == 'Miniboss':
        movement(dungeon_1.dungeon_map_1, room_action)
        action = 'Move'
        room_action = 'Move'
    #if the player escapes from the boss, lets them escape
    elif room_action == 'Boss escape':
        movement(dungeon_1.dungeon_map_1, room_action)
        action = 'Move'
        room_action = 'Move'
    #if the player goes through the boss gates, removes their escape possibilities
    elif room_action == 'Boss':
        movement(dungeon_1.dungeon_map_1, room_action)
        action = 'Move'
        room_action = 'Move'
    elif room_action == 'Staircase':
        print("That is all for now. Thank you for playtesting!")
        in_dungeon_1 = False
        break

    if room_action == 'Move':
        room_action = None
    elif action == 'Move':
        movement(dungeon_1.dungeon_map_1, action)
    elif action == 'Map':
        player_map(dungeon_1.dungeon_map_1, dungeon_1.dungeon_visited_1)
        action = 0
    elif action == 'Inventory':
        inventory()
        action = 0
    else:
        print("Please enter a valid option!")
        action = 0

    #if the player has taken an action in a room, skip it. Otherwise perform the action in the room
    if action == 'Move':
        #if the player has never been to a room, trigger the action in the room
        if dungeon_1.dungeon_action_1[row][column] == False:
            dungeon_1.dungeon_visited_1[row][column] = True
            room_action = dungeon_1.dungeon_map_1[row][column](player, row, column)
        #if the player has been to a room, don't trigger anything
        elif dungeon_1.dungeon_action_1[row][column] == True:
            if action == 'Move':
                print("You've been here before! There's nothing more to do.")
                print("")
