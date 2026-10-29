import random
import time
import player_data

def player_action(text, options):

    while True:
        choice = input(text).capitalize()
        if choice in options:
            return choice
        else:
            print("Invalid choice!")

def damage_calc(enemy, player, type, spell=0):
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

        if spell > 0:
            print("The searing smite on your weapon increases the damage you deal!")
            damage = int(damage * 1.5)

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
        damage *= 3
        enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        input()
        return
    elif type == 'Spell':
        damage = int(max(1, (random.randint(spell.damage, int(spell.damage * 1.3)) + player.stat_modifier(player.intelligence) - enemy.armor)))
        if spell.damage_type == enemy.vulnerable:
            damage *= 2
            print("This attack does especially well!")
        elif spell.damage_type == enemy.resistant:
            damage //= 2
            print("This attack seems less impactful.")
        enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        input()
        return
    elif type == 'Enemy melee':
        damage = int(max(1, (random.randint(int(enemy.melee * 0.7),int(enemy.melee * 1.3))+ enemy.stat_modifier(enemy.strength) - player.armor)))
        if spell:
            damage = int(damage * 0.75)
            print("You feel your shield protecting you! You take less damage. The shield is used up in the process.")
        print(f"The {enemy.name} hits you with a melee attack for {damage} damage.")
        player.take_damage(damage)
        print(f"You have {player.health} health left.")
        input()
        return
    elif type == 'Enemy ranged':
        damage = int(max(1, (random.randint(int(enemy.ranged * 0.7),int(enemy.ranged * 1.3))+ enemy.stat_modifier(enemy.dexterity) - player.armor)))
        if spell:
            damage = int(damage * 0.75)
            print("You feel your shield protecting you! You take less damage. The shield is used up in the process.")
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

def class_action(player, enemy):
    if player.class_action == 'Basic':
        if player.class_name == 'Barbarian':
            print(f"You are enraged! Your strength increases, but your dexterity decreases for 2 turns.")
            player.rage()
            input()
            return 'Barb'
        elif player.class_name == 'Ranger':
            print("You now have a multiattack! You can now shoot an extra arrow per turn.")
            input()
            return 'Ranger'
        elif player.class_name == 'Rogue':
            print("You inspect your enemy to take advantage of its vulnerabilities and spot its resistances.")
            print(f"The {enemy.name} is vulnerable to {(enemy.vulnerable).lower()} attacks.")
            print(f"The {enemy.name} is resistant to {(enemy.resistant).lower()} attacks.")
            input()
            if player.level > 2:
                print("You can also glean some more information about the enemy's statistics.")
                print(f"The enemy has a dexterity of {enemy.dexterity} and a strength of {enemy.strength}.")
            return 'Rogue'
        elif player.class_name == 'Hunter':
            print("You deploy a net on your enemy. Their dexterity is halved for two rounds.")
            input()
            return 'Hunter'

def encounter(player, enemy):
    fighting = True
    hunter_net = 0
    ranger_class_action = False
    barb_rage = 0
    searing_smite = 0
    frozen = False
    shield_spell = False
    rounds = 0
    action_turns = 1
    skip_turn = 0
    player_options = ['Use consumable', 'Run', 'Attack', 'Dodge']
    attack_options = ['Melee', 'Ranged', 'Cast spell']

    enemy_melee = (enemy.stat_modifier(enemy.strength) + (enemy.level // 2))
    enemy_ranged = (enemy.stat_modifier(enemy.dexterity) + (enemy.level // 2))
    enemy_AC = (10 + enemy.stat_modifier(enemy.dexterity))

    player_melee = (player.stat_modifier(player.strength) + (player.level // 2))
    player_ranged = (player.stat_modifier(player.dexterity) + (player.level // 2))
    player_spell_bonus = (player.stat_modifier(player.intelligence) + (player.level // 2))
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

    #if the enemy is a boss, removes the run text and actual ability to run
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

        if hunter_net <= 0:
            enemy.restore_dex()
            enemy_AC = (10 + enemy.stat_modifier(enemy.dexterity))

        if barb_rage == 0:
            player.rage_end()
            player_melee = (player.stat_modifier(player.strength) + (player.level // 2))
            player_ranged = (player.stat_modifier(player.dexterity) + (player.level // 2))
            player_AC = (10 + player.stat_modifier(player.dexterity))

        print(f"The {enemy.name} has {enemy.health} health left.")
        while action_turns > 0:
            action = player_action(f"It is your turn. What do you do? (Attack/Dodge/Use consumable{class_action_text}{run_text}) ", player_options)
            if action == 'Run':
                action_turns -= 1
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
                action_turns -= 0.5
                accessing_consumables = True
                consumables = []
                for item in player_data.player_inventory:
                    if item.type == 'Consumable' and item.amount > 0:
                        print(f"Name: {item.name} - Amount: {item.amount} - Healing: {item.healing}")
                        consumables.append(item)
                if len(consumables) == 0:
                    print("You have no consumables to use!")
                    input()
                    accessing_consumables = False
                    action_turns += 0.5

                while accessing_consumables:
                    inventory_selection_2 = input("What would you like to use? ").capitalize()
                    if inventory_selection_2 == 'Leave':
                        accessing_consumables = False
                        action_turns += 0.5
                    else:
                        for item in consumables:
                            if item.name == inventory_selection_2:
                                print(f"You use a {inventory_selection_2}.")
                                healing = item.amount_healing()
                                player.heal(healing)
                                item.use_item(1)
                                print(f"You heal {healing} HP! You now have {player.health} HP.")
                                accessing_consumables = False
                                input()

                        if accessing_consumables:
                            print("Please enter a valid consumable! Type leave to leave.")
            elif action == 'Dodge':
                time_taken = reaction_time('Dodge')
                if time_taken < 40:
                    print("You manage to dodge the attack!")
                    skip_turn = 1
                else:
                    print("You don't manage to dodge the attack.")
                    #I will rework dodging in the future, for rn ignore
            elif action == 'Class action':
                action_turns -= 0.5
                class_action_text = ''
                player.class_action_available = False
                player_options.remove('Class action')
                class_action_selection = class_action(player, enemy)
                if class_action_selection == 'Barb':
                    player_melee = (player.stat_modifier(player.strength) + (player.level // 2))
                    player_ranged = (player.stat_modifier(player.dexterity) + (player.level // 2))
                    player_AC = (10 + player.stat_modifier(player.dexterity))
                    barb_rage = 3
                elif class_action_selection == 'Ranger':
                    ranger_class_action = True
                elif class_action_selection == 'Hunter':
                    enemy.half_dex()
                    enemy_AC = (10 + enemy.stat_modifier(enemy.dexterity))
                    hunter_net = 2
            elif action == 'Attack':
                hunter_net -=1
                action = player_action(f"How do you want to attack? (Melee/Ranged/Cast spell{sneak_attack_text}{special_attack_text}) ", attack_options)
                if action == 'Melee':
                    action_turns -= 1
                    while rounds < melee_attack_turns:
                        rounds += 1
                        if (random.randint(1,20) + player_melee) >= enemy_AC:
                            damage_calc(enemy, player, 'Melee', searing_smite)
                            if searing_smite > 0:
                                searing_smite -= 1
                                print(f"You have {searing_smite} turns of searing smite left.")
                        else:
                            print("You miss.")
                            input()
                    rounds = 0
                elif action == 'Ranged':
                    action_turns -= 1
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
                    action_turns -= 1
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
                    action_turns -= 1
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
                elif action == 'Cast spell':
                    print(f"Current mana - {player.mana}")
                    print("")
                    for spell in player.known_spells:
                        print(spell.name, '-', spell.spell_type, '-', 'Mana:', spell.mana_cost)
                    print("")
                    attempting_cast = True
                    while attempting_cast:
                        spell_status = None
                        spell_cast = None
                        player_spell = input("Which spell would you like to cast? ").capitalize()
                        if player_spell == 'Leave':
                            attempting_cast = False
                            break
                        #checks for the spell the player selected
                        for spell in player.known_spells:
                            if spell.name == player_spell:
                                #takes the corresponding amount of actions depending on the spell type
                                if spell.action == 'Bonus action':
                                    action_turns -= 0.5
                                    spell_cast_action = 'Bonus'
                                else:
                                    action_turns -= 1
                                    spell_cast_action = 'Action'
                                spell_cast_name = spell.name
                                spell_cast = spell
                                #attempts to cast the spell, if the player doesn't have enough mana it fails. If it's a healing spell it heals directly
                                spell_status = spell.cast_spell(player, player_spell_bonus, enemy_AC)
                                break

                        #if the player can cast the spell, applies the corresponding effect
                        if spell_status == 'Support':
                            if spell_cast_name == 'Shield':
                                print("You cover yourself in magical energy. The next enemy attack that hits you will be less effective")
                                shield_spell = True
                                input()
                            elif spell_cast_name == 'Searing smite':
                                print("You see your weapon glow with magical energy. It will do more damage for two attacks!")
                                searing_smite = 2
                        elif spell_status == 'Spell hits':
                            if spell_cast_name == 'Freeze':
                                frozen = True

                        #if the player has enough mana to cast the spell and it's offensive, it does the damage calcs
                        if spell_status == 'Spell hits':
                            print(f"You attack the {enemy.name} with your {spell_cast_name.lower()}.")
                            damage_calc(enemy, player, 'Spell', spell_cast)
                            attempting_cast = False
                        #if the player misses or casts a healing or support spell, it leaves the loop
                        elif spell_status in ('Healing', 'Spell misses', 'Support'):
                            attempting_cast = False
                        #if the player doesn't have enough mana to cast a spell, it leaves the loop but returns the action
                        elif spell_status == 'Spell fails':
                            if spell_cast_action == 'Bonus':
                                action_turns += 0.5
                            else:
                                action_turns += 1
                        #if the player never picked a valid spell, makes them pick again
                        else:
                            print("Please pick a valid spell!")
                            print("(Type leave to leave)")

        action_turns = 1
        if skip_turn == 0:
            if enemy.health > 0:
                enemy_action = enemy_action_determiner(enemy, player)
                if enemy_action == 'Melee attack': 
                    if (random.randint(1,20) + enemy_melee) >= player_AC:
                        damage_calc(enemy, player, 'Enemy melee', shield_spell)
                        if shield_spell:
                            shield_spell = False
                    else:
                        print(f"The {enemy.name} misses its attack.")
                        input()
                elif enemy_action == 'Ranged attack':
                    if (random.randint(1,20) + enemy_ranged) >= player_AC:
                        damage_calc(enemy, player, 'Enemy ranged', shield_spell)
                        if shield_spell:
                            shield_spell = False
                    else:
                        print(f"The {enemy.name} misses its attack.")
                        input()
                elif enemy_action == 'Special attack':
                    time_taken = reaction_time('Enemy dodge')
                    if shield_spell:
                        print("You feel your shield spell protecting you. The enemy's attack is less effective, but the shield is used up in the process.")
                        time_taken //= 2
                        shield_spell = False
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
        else:
            print(f"The {enemy.name.lower()}'s turn is skipped!")
            skip_turn -= 1
            if skip_turn > 0:
                print(f"It will attack again in {skip_turn} rounds.")
            else:
                print("It will attack again next turn!")
            input()

        #intended sequence of events is that the player casts freeze, the enemy attacks once, and then it's frozen for 2 turns
        if frozen:
            skip_turn = 2
            frozen = False
            print("You manage to freeze the enemy!")

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
