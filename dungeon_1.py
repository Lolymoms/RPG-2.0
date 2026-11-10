import random
import copy
import enemy_data
import player_data
import combat

#tracks if the player has pried open the gates to escape the bossfight
boss_gate = True
#gives the player a different piece of lore every time
lore_counter = 1
#tracks how many times a player has been in a chest room
chest_counter = 1

def get_string(text, options):
    while True:
        selection = input(text).capitalize()
        if selection in options:
            return selection
        else:
            print("Please pick a valid option")

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
        dog_1 = copy.deepcopy(enemy_data.feral_dog)
        room_data_dog = {
            'Player' : (0, 0),
            'Size' : (4, 4),
            'Walls' : [(1, 2), (2, 2), (2, 1)],
            'Enemies': {
                dog_1 : (3, 3),
            }
        }
        action = combat.encounter(player, dog_1, room_data_dog)
    else:
        print("You walk further into the room and see a cave spider!")
        spider_1 = copy.deepcopy(enemy_data.cave_spider)
        room_data_spider = {
            'Player' : (0, 0),
            'Size' : (4, 5),
            'Walls' : [(1, 2), (2, 1), (1, 3)],
            'Enemies': {
                spider_1 : (3, 4),
            }
        }
        action = combat.encounter(player, spider_1, room_data_spider)

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
        if chest_counter == 1:
            print("You open the chest and find a health potion!")
            player_data.healing_potion.add_item(1)
            print(f"You have {player_data.healing_potion.amount} health potions.")
            input()
            chest_counter += 1
        else:
            #if the random number is below 7, it's 5 gold
            if randomnum < 7:
                print("You open the chest and find some gold!")
                print("+5 gold")
                player.add_gold(5)
                print(f"You have {player.gold} gold.")
                input()
            #if the random number is 7-9, it's a mimic
            elif randomnum >= 7 and randomnum <= 9:
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
        gelatinous_cube = Enemy("Gelatinous Cube", 1, 1, 40, 6, 3, 11, 6, 0, 0, 'Slashing', 'None', True, 'Basic')
        room_data_cube = {
            'Player' : (0, 0),
            'Size' : (5, 3),
            'Walls' : [],
            'Enemies': {
                gelatinous_cube : (4, 2),
            }
        }
        combat.encounter(player, gelatinous_cube, room_data_cube)
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
    room_data_warden = {
        'Player' : (0, 0),
        'Size' : (6, 6),
        'Walls' : [(2, 1), (2, 2), (2, 3), (2, 4), (1, 4)],
        'Enemies': {
            warden_boss : (3, 4),
        }
    }
    combat.encounter(player, warden_boss, room_data_warden)
    return 'Boss'

def staircase_1(player, row, column):
    print("You see a staircase ahead of you. After all you've been through, you decide to descend.")
    print(f"Congratulations {player.name}! You have successfully beaten the first layer of the great coil.")
    print("Before continuing your adventures, a break.")
    #makes the player level up
    player.add_experience(player.level_up_experience_calculator())
    return 'Staircase'

def shop_1(player):
    print("You descend the staircase and see a strange house with a green man sleeping. As you approach, he stirrs.")
    print("He jumps at your sight, and exclaims excitedly.")
    print("'My my! Another adventurer!' he says 'Come in, come in!'")
    print("He motions for you to enter the house. You decide to do so.")
    print("'You're the first adventurer I've seen in... years!' He yelps, 'I didn't think the warden would go down so soon... well that's not important!'")
    print("'I can tell you're new here, let me give you something to aid in your travels.' He says.")
    free_item_selection = get_string("What do you want? (Melee/Ranged/Armor) ", ('Melee', 'Ranged', 'Armor'))
    if free_item_selection == 'Melee':
        print("'Oh a melee weapon! Good choice!' Says the shopkeeper.")
        print("He hands over a sword that's shiny, and unnaturally light.")
        print("(Equip the longsword in the inventory menu!)")
        from player_data import Item
        longsword = Item('Longsword', 'Melee', damage=8, damage_type='Slashing')
        player_data.player_inventory.append(longsword)
    elif free_item_selection == 'Ranged':
        print("'Ah, a ranged weapon. You dont like to get hurt huh?' Says the shopkeeper.")
        print("He hands over what looks to be a crossbow, but it's a bit old")
        print("(Equip the crossbow in the inventory menu!)")
        from player_data import Item
        crossbow = Item('Crossbow', 'Ranged', damage=10, damage_type='Piercing')
        player_data.player_inventory.append(crossbow)
    elif free_item_selection == 'Armor':
        print("'Ah, the humble suit of armor. May this protect you for many days.' The shopkeeper says.")
        print("He hands over a suit of what looks to be chainmail. It's heavy, but definitely better than your current armor.")
        player.add_armor(2)

    print("Well I'd love to give you more stuff, but I wouldn't be in buisness if I gave everything away for free! I'll sell you things though.")
    open_shop = get_string("Open the shop? (Yes/No) ", ('Yes', 'No'))
    if open_shop == 'No':
        return
    elif open_shop == 'Yes':
        pass

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