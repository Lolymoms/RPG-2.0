import player_data
import enemy_data
import dungeon_1

#row is up and down
row = 0
#column is left to right
column = 0
#used for the movement for loop
in_dungeon_1 = True

#gives all possible directions for a map of any size
def movement(map):
    global row
    global column
    
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

        if local_row > max_direction or local_row < 0:
            pass
        elif local_column > max_direction or local_column < 0:
            pass
        elif map[local_row][local_column] == 'Wall':
            pass
        else:
            possible_directions.append(direction)

    print(f"You see {len(possible_directions)} exits to this room.")

    #adds every direction as text to a list, and prints them
    for direction, text in text_directions.items():
        if direction in possible_directions:
            possible_directions_text.append(text)
            print(f"{direction}) {text}")

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

    for direction, (row_change, column_change) in directions.items():
        if direction == player_direction:
            row += row_change
            column += column_change
            return

#creates a map room variable which shows the player a map of where they've been to, works for any sized map
def map(dungeon_map, dungeon_visited):
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
                #most of these functions don't exist, so they're commented out for now
                # if dungeon_map[row_local][column_local] == enemy_room:
                #     map_room_list[row_local][column_local] = 'x'
                # elif dungeon_map[row_local][column_local] == empty_room:
                #     map_room_list[row_local][column_local] = ' '
                # elif dungeon_map[row_local][column_local] == gold_room:
                #     map_room_list[row_local][column_local] = '$'
                # elif dungeon_map[row_local][column_local] == 'Entrance':
                #     map_room_list[row_local][column_local] = ' '
                # elif dungeon_map[row_local][column_local] == miniboss:
                #     map_room_list[row_local][column_local] = 'X'
                # elif dungeon_map[row_local][column_local] == rest_room:
                #     map_room_list[row_local][column_local] = '*'
                #else:
                map_room_list[row_local][column_local] = ' '
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

player = player_data.player_selection()

#selection between moving, map, and inventory
while in_dungeon_1:
    action = input("What would you like to do? (Move/Map/Inventory) ").capitalize()

    if action == 'Move':
        movement(dungeon_1.dungeon_map_1)
    elif action == 'Map':
        map(dungeon_1.dungeon_map_1, dungeon_1.dungeon_visited_1)
    elif action == 'Inventory':
        pass
    else:
        print("Please enter a valid option!")

    #copied from old_RPG, remember to make this work for the new version
    if action == 'Move' or action == 'Run':
        #if the player has never been to a room, trigger the action in the room
        if dungeon_1.dungeon_visited_1[dungeon_1.row][dungeon_1.column] == False:
            dungeon_1.dungeon_visited_1[dungeon_1.row][dungeon_1.column] ==True
            action = dungeon_1.dungeon_map_1[dungeon_1.row][dungeon_1.column]()
        #if the player has been to a room, don't trigger anything
        elif dungeon_1.dungeon_visited_1[dungeon_1.row][dungeon_1.column] == True:
            if action == 'Move':
                print("You've been here before! There's nothing more to do.")
                print("")


dungeon_1.encounter(player, enemy_data.feral_dog)