#returns a list of directions, as strings, for the enemy to follow to reach the player
def enemy_movement(room, start_pos, end_pos, available_movement):
    path = pathfinding(room, start_pos, end_pos)
    if path == 'No path':
        return []
    directions = {
        'Up' : (1, 0),
        'Down' : (-1, 0),
        'Right' : (0, 1),
        'Left' : (0, -1)
    }
    direction_list = []
    for movement in range(available_movement):
        if movement == (len(path) - 1):
            break
        target_coordinate = path[movement + 1]
        for direction in directions:
            test_coordinate = [path[movement][0], path[movement][1]]
            row_change = directions[direction][0]
            column_change = directions[direction][1]
            test_coordinate[0] += row_change
            test_coordinate[1] += column_change

            if test_coordinate == target_coordinate:
                direction_list.append(direction)

    return direction_list

#checks if an attack can hit and if the range is sufficient
def raytracing(room, start_pos, end_pos, attack_range):
    coordinates = line_algorithm(start_pos, end_pos)

    if len(coordinates) > attack_range:
        return 'Out of range'

    for coordinate in coordinates:
        if room[coordinate[0]][coordinate[1]] != 'Empty':
            if room[coordinate[0]][coordinate[1]] == 'Enemy':
                return 'Hits enemy'
            else:
                return 'Hits wall'

#returns the approx distance between two points
def distance(start_pos, end_pos):
    coordinates = line_algorithm(start_pos, end_pos)
    effective_distance = len(coordinates)
    return effective_distance


#the program will return a list of tuples which include coordinates for the shortest path to a goal
#room requires a map where passable terrain is marked by 'Empty'
#start_pos and end_pos require tuples
def pathfinding(room, start_pos, end_pos):
    bfs_room = []

    #creates a nested list with 1s and 0s. 1 means impassable terrain, 0 means passable terrain
    #if type is not none, for raytracing, everything will be passable
    for row in room:
        bfs_column = []
        for column in row:
            if column == 'Empty':
                bfs_column.append(0)
            else:
                bfs_column.append(1)
        bfs_room.append(bfs_column)

    #r is up down, c is left right (r, c)
    directions = {
        'Up' : (1, 0),
        'Down' : (-1, 0),
        'Right' : (0, 1),
        'Left' : (0, -1)
    }
    path = {
        (start_pos[0], start_pos[1]) : None
    }
    queue = [(start_pos[0], start_pos[1])]
    base_location = [start_pos[0], start_pos[1]]
    while True:
        for direction in directions:
            search_location = base_location.copy()
            row_change = directions[direction][0]
            column_change = directions[direction][1]

            search_location[0] += row_change
            search_location[1] += column_change
            #makes sure that the coordinates of search_location are within bounds
            if (0 <= search_location[0] < len(bfs_room)) and (0 <= search_location[1] < len(bfs_room[0])):
                if bfs_room[search_location[0]][search_location[1]] == 0 and (search_location[0],search_location[1]) not in path:
                    path[(search_location[0],search_location[1])] = (base_location[0], base_location[1])
                    queue.append((search_location[0],search_location[1]))

        if (end_pos[0], end_pos[1]) in path:
            complete_path = [(end_pos[0], end_pos[1])]
            previous_space = path[end_pos[0], end_pos[1]]
            while previous_space != None:
                complete_path.append(previous_space)
                previous_space = path[previous_space]
            complete_path.reverse()
            return complete_path
        elif len(queue) > 0:
            base_location = queue.pop(0)
        else:
            return 'No path'

#finds a line between two points, and returns all of the coordinates
def line_algorithm(start_pos, end_pos):
    point_1_x = start_pos[0]
    point_1_y = start_pos[1]
    point_2_x = end_pos[0]
    point_2_y = end_pos[1]

    #initial calculations
    change_x = abs(point_1_x - point_2_x)
    change_y = abs(point_1_y - point_2_y)
    if point_1_x < point_2_x:
        horizontal_change = 1
    else:
        horizontal_change = -1
    if point_1_y < point_2_y:
        vertical_change = 1
    else:
        vertical_change = -1
    error = change_x - change_y
    coordinates = []
    temp_x = point_1_x
    temp_y = point_1_y

    while True:
        if temp_x == point_2_x and temp_y == point_2_y:
            return coordinates

        doubled_error = error * 2

        #written by ChatGPT
        # Check whether we should move horizontally
        if doubled_error > -change_y:
            error -= change_y
            temp_x += horizontal_change

        # Check whether we should move vertically
        if doubled_error < change_x:
            error += change_x
            temp_y += vertical_change

        coordinates.append((temp_x, temp_y))