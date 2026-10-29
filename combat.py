import random
import time
import player_data

class Combat:
    def __init__(self, player, enemy):
        self.player = player
        self.enemy = enemy
        self.defending = False
        self.rage_rounds = -1
        self.hunter_net = -1
        self.freeze = -1
        self.poison = -1
        self.shield = False
        self.searing_smite = 0
        self.ranger_class_action = False
        self.player_turn_action = True
        self.player_bonus_action = True

        self.enemy_special_attack = False

    def player_turn(self):
        player_options = ['Attack', 'Run', 'Defend', 'Use consumable']
        player_turn = True
        self.player_turn_action = True
        self.player_bonus_action = True

        if self.player.class_action_available:
            player_options.append('Class action')
        if self.enemy.boss:
            player_options.remove('Run')

        if self.rage_rounds > 0:
            self.rage_rounds -= 1
            print(f"You have {self.rage_rounds} of rage left.")
        elif self.rage_rounds == 0:
            self.player.rage_end()
            self.rage_rounds -= 1

        if self.hunter_net > 0:
            self.hunter_net -= 1
        elif self.hunter_net == 0:
            print(f"The {self.enemy.name} escapes from your net!")
            self.enemy.restore_dex()
            self.hunter_net -= 1

        while player_turn:
            if self.enemy.health <= 0:
                return 'Victory'
            else:
                print(f"The {self.enemy.name} has {self.enemy.health} health remaining.")
            #if the player has no turns left, ends their turn
            if self.player_turn_action == False and self.player_bonus_action == False:
                player_turn = False
                break
            
            player_action = self.get_player_action(f"What would you like to do? (Attack/Defend/Use consumable{'/Run' if 'Run' in player_options else ''}{'/Class action' if 'Class action' in player_options else ''}) ", player_options)

            #the function checks for player actions inside the function
            if player_action == 'Attack': #both
                self.attack()
            
            elif player_action == 'Run' and self.player_turn_action:
                if self.attempt_run() == 'Run':
                    return 'Run'
            elif player_action == 'Run' and self.player_turn_action == False:
                print("You have no actions remaining.")

            elif player_action in ('Use consumable', 'Class action', 'Defend') and self.player_bonus_action:
                if player_action == 'Use consumable': #bonus
                    self.use_consumable()
                elif player_action == 'Class action': #bonus
                    self.class_action()
                    player_options.remove('Class action')
                elif player_action == 'Defend': #bonus
                    self.defend()
            elif self.player_turn_action and player_action in ('Use consumable', 'Class action'):
                if input("Would you like to convert your action into one bonus action? (Yes/No) ").capitalize() == 'Yes':
                    self.player_turn_action = False
                    self.player_bonus_action = True
            else:
                print("You have no bonus actions remaining!")

    def get_player_action(self, text, options):
        while True:
            choice = input(text).capitalize()
            if choice in options:
                return choice
            else:
                print("Invalid choice!")

    def attempt_run(self):
        self.player_turn_action = False
        player_bonus = (self.player.stat_modifier(self.player.dexterity) + random.randint(1, 10))
        enemy_bonus = (self.enemy.stat_modifier(self.enemy.dexterity) + random.randint(1, 10))

        if self.player.level < self.enemy.level:
            if (player_bonus * (self.enemy.level - self.player.level)) > enemy_bonus:
                return 'Run'
        else:
            if player_bonus > enemy_bonus:
                return 'Run'

        print("You attempt to run, but fail.")

    def defend(self):
        self.player_bonus_action = False
        print("You defend yourself! You will have a chance to dodge the enemy's next attack.")
        self.defending = True

    def use_consumable(self):
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

        while accessing_consumables:
            inventory_selection_2 = input("What would you like to use? ").capitalize()
            if inventory_selection_2 == 'Leave':
                accessing_consumables = False
            else:
                for item in consumables:
                    if item.name == inventory_selection_2:
                        print(f"You use a {inventory_selection_2}.")
                        healing = item.amount_healing()
                        self.player.heal(healing)
                        item.use_item(1)
                        print(f"You heal {healing} HP! You now have {self.player.health} HP.")
                        accessing_consumables = False
                        self.player_bonus_action = False
                        input()

                if accessing_consumables:
                    print("Please enter a valid consumable! Type leave to leave.")

    #make this work!!
    def class_action(self):
        self.player_bonus_action = False
        self.player.class_action_available = False
        if self.player.class_action == 'Basic':
            if self.player.class_name == 'Barbarian':
                print(f"You are enraged! Your strength increases, but your dexterity decreases for 2 turns.")
                self.player.rage()
                self.rage_rounds = 2
                input()
            elif self.player.class_name == 'Ranger':
                print("You now have a multiattack! You can now shoot an extra arrow per turn.")
                self.ranger_class_action = True
                input()
            elif self.player.class_name == 'Rogue':
                print("You inspect your enemy to take advantage of its vulnerabilities and spot its resistances.")
                print(f"The {self.enemy.name} is vulnerable to {(self.enemy.vulnerable).lower()} attacks.")
                print(f"The {self.enemy.name} is resistant to {(self.enemy.resistant).lower()} attacks.")
                input()
                if self.player.level > 2:
                    print("You can also glean some more information about the enemy's statistics.")
                    print(f"The enemy has a dexterity of {self.enemy.dexterity} and a strength of {self.enemy.strength}.")
            elif self.player.class_name == 'Hunter':
                print("You deploy a net on your enemy. Their dexterity is halved for two rounds.")
                self.hunter_net += 2
                self.enemy.half_dex()
                input()

    def attack(self):
        attack_options = ['Melee', 'Ranged', 'Spell']
        spell_cast = None
        attack_lands = False
        melee_bonus_turns = 1
        ranged_bonus_turns = 1

        if self.player.class_name == 'Rogue' and self.player.melee.attack_type == 'Light':
            attack_options.append('Sneak attack')
        if self.player.special_attack_available:
            attack_options.append('Special attack')

        if self.player_turn_action:
            attack_type = self.get_player_action(f"How do you want to attack? (Melee/Ranged/Spell{'/Sneak attack' if 'Sneak attack' in attack_options else ''}{'/Special attack' if 'Special attack' in attack_options else ''})", attack_options)
        elif self.player_bonus_action:
            attack_type = self.get_player_action("How do you want to attack? (Spell/Leave) ", ('Spell', 'Leave'))

        if attack_type == 'Leave':
            return
        elif attack_type == 'Special attack':
            self.player_turn_action = False
            self.special_attack()
            return
        elif attack_type == 'Spell':
            #returns the spell cast by the player if it succeeds
            spell_cast = self.spell()
        elif attack_type in ('Melee', 'Sneak attack'):
            self.player_turn_action = False
            weapon_damage = self.player.melee.damage
            weapon_damage_type = self.player.melee.damage_type
            modifier = self.player.stat_modifier(self.player.strength)
            to_hit = self.modifier('Melee')
        elif attack_type == 'Ranged':
            self.player_turn_action = False
            weapon_damage = self.player.ranged.damage
            weapon_damage_type = self.player.ranged.damage_type
            modifier = self.player.stat_modifier(self.player.dexterity)
            to_hit = self.modifier('Ranged')

        if spell_cast == None and attack_type == 'Spell':
            return

        enemy_ac = self.modifier('Enemy ac')

        if self.player.ranged_skill >= 5:
            ranged_bonus_turns += 1
        if self.player.melee_skill >= 5:
            melee_bonus_turns += 1

        if self.ranger_class_action:
            ranged_bonus_turns += 1
            self.ranger_class_action = False
            print("You use your multiattack!")
        if self.player.melee.attack_type == 'Light':
            melee_bonus_turns += 1

        player_attacking_turn = True
        while player_attacking_turn:
            if self.enemy.health <= 0:
                return 'Victory'
            attack_lands = False
            if attack_type == 'Ranged':
                to_hit = self.modifier('Ranged')
            elif attack_type == 'Melee':
                to_hit = self.modifier('Melee')

            if spell_cast != None:
                print(f"You attack the {self.enemy.name} with your {spell_cast.name.lower()}!")
                weapon_damage = spell_cast.damage
                weapon_damage_type = spell_cast.damage_type
                modifier = self.player.stat_modifier(self.player.intelligence)
                attack_lands = True
            elif attack_type in ('Melee', 'Ranged') and to_hit >= enemy_ac:
                attack_lands = True
            elif attack_type == 'Sneak attack' and (random.randint(1,20) + self.player.stat_modifier(self.player.dexterity)) >= (enemy_ac + self.enemy.level):
                attack_lands = True
                print(f"You manage to sneak up on the {self.enemy.name}!")

            if attack_lands:
                if spell_cast == None:
                    damage = max(1,((random.randint(int(weapon_damage * 0.7),int(weapon_damage * 1.3)) + modifier) - self.enemy.armor))
                else:
                    damage = max(1,((random.randint(weapon_damage, int(weapon_damage * 1.3)) + modifier) - self.enemy.armor))

                if self.enemy.vulnerable == weapon_damage_type:
                    damage *= 2
                    print("This attack does especially well!")
                elif self.enemy.resistant == weapon_damage_type:
                    damage //= 2
                    print("This attack seems less impactful.")

                if attack_type == 'Sneak attack':
                    damage *= 3

                if self.searing_smite > 0 and attack_type == 'Melee':
                    damage = int(damage * 1.5)
                    self.searing_smite -= 1
                    print("Your searing smite increases your melee weapon damage this turn!")

                self.enemy.take_damage(damage)
                print(f"You hit the {self.enemy.name} and deal {damage} damage!")
                input()
            else:
                if attack_type == 'Sneak attack':
                    print("You don't manage to sneak up on the enemy!")
                else:
                    print("You miss the attack!")
                input()

            if attack_type == 'Melee':
                melee_bonus_turns -= 1
            elif attack_type == 'Ranged':
                ranged_bonus_turns -= 1
            elif attack_type == 'Sneak attack':
                melee_bonus_turns -= 1
                attack_type = 'Melee'

            if attack_type == 'Melee' and melee_bonus_turns <= 0:
                player_attacking_turn = False
            elif attack_type == 'Ranged' and ranged_bonus_turns <= 0:
                player_attacking_turn = False
            elif attack_type == 'Spell':
                player_attacking_turn = False

    def special_attack(self):
        self.player_turn_action = False
        score = self.reaction_time('Special attack')
        if score <= 35:
            multiplier = 1.25
            print("You hit dead center! 25% more damage.")
        elif score <= 60:
            multiplier = 1
            print("You hit near the chest! Regular hit.")
        elif score <= 80:
            multiplier = 0.75
            print("You hit an arm! -25% damage")
        else:
            multiplier = 0.5
            print("You barely hit! -50% damage")
        damage = int(max(1,((self.player.melee.damage * 2) * multiplier) - self.enemy.armor))
        self.enemy.take_damage(damage)
        print(f"You deal {damage} damage!")
        self.player.special_attack_available = False

    def spell(self):
        print(f"Current mana - {self.player.mana}")
        print("")
        for spell in self.player.known_spells:
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
            for spell in self.player.known_spells:
                if spell.name == player_spell:
                    if spell.action == 'Action' and self.player_turn_action == False:
                        print("You don't have an action available!")
                        return
                    elif spell.action == 'Bonus action' and self.player_bonus_action == False:
                        print("You don't have a bonus action available!")
                        if self.player_turn_action:
                            if input("Do you want to turn your action into a bonus action?").capitalize() == 'Yes':
                                self.player_turn_action = False
                                self.player_bonus_action = True
                            else:
                                return
                        else:
                            return
                        
                    spell_cast = spell
                    #attempts to cast the spell, if the player doesn't have enough mana it fails. If it's a healing spell it heals directly
                    spell_status = spell.cast_spell(self.player, self.modifier('Spell'), self.modifier('Enemy ac'))
                    attempting_cast = False
            if spell_cast == None:
                print("Please input a valid spell!")

        if spell_cast != None and spell_status != 'Spell fails':
            if spell_cast.action == 'Action':
                self.player_turn_action = False
            else:
                self.player_bonus_action = False

        #damage logic is handled in the attack method
        if spell_status == 'Spell hits':
            if spell_cast.name in ('Poison', 'Freeze'):
                self.support_spell(spell_cast)
                if spell_cast.name == 'Freeze':
                    return spell_cast
            else:
                return spell_cast
        elif spell_status == 'Support':
            self.support_spell(spell_cast)
        else:
            return

    def support_spell(self, spell_cast):
        if spell_cast.name == 'Freeze':
            self.freeze = 2
            return
        elif spell_cast.name == 'Shield':
            self.shield = True
            return
        elif spell_cast.name == 'Searing smite':
            self.searing_smite = 2
            return
        elif spell_cast.name == 'Poison':
            self.poison = 3
            return

    def modifier(self, type):
        if type == 'Melee':
            return (random.randint(1,20) + (self.player.stat_modifier(self.player.strength)) + (self.player.level // 2))
        elif type == 'Ranged':
            return (random.randint(1,20) + (self.player.stat_modifier(self.player.dexterity)) + (self.player.level // 2))
        elif type == 'Spell':
            return (random.randint(1,20) + (self.player.stat_modifier(self.player.intelligence)) + (self.player.level // 2))
        elif type == 'Player ac':
            return (10 + (self.player.stat_modifier(self.player.dexterity)))
        elif type == 'Enemy ac':
            return (10 + (self.enemy.stat_modifier(self.enemy.dexterity)))
        elif type == 'Enemy melee':
            return (random.randint(1,20) + (self.enemy.stat_modifier(self.enemy.strength)) + (self.enemy.level // 2))
        elif type == 'Enemy ranged':
            return (random.randint(1,20) + (self.enemy.stat_modifier(self.enemy.dexterity)) + (self.enemy.level // 2))

    #function that returns a value 1-100 based on how fast the player reacted to a prompt
    def reaction_time(self, type):
        #gets a random number and divides by 10. This is used as the random amount of time waited
        time_waiting = random.randint(5,30)
        time_waiting = time_waiting / 10
        if type == 'Dodge':
            print("You are prepared for the enemy's attack, and can dodge!")
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

    def enemy_turn(self):
        enemy_action = None
        if self.poison > 0:
            self.enemy.take_damage(4)
            self.poison -= 1
            print("The poison spell does 4 damage!")
        if self.enemy.health <= 0:
            return 'Victory'

        if self.enemy_special_attack:
            time_taken = self.reaction_time('Enemy dodge')
            if time_taken <= 35:
                multiplier = 0.5
                print("You manage to dodge well! -50% damage")
            elif time_taken <= 60:
                multiplier = 0.75
                print("You manage to dodge slightly. -25% damage")
            else:
                multiplier = 1
                print("You don't manage to dodge well. 100% damage")

            damage = int(max(1,(((self.enemy.melee * 2)* multiplier) - self.player.armor)))
            if self.shield:
                damage = int(damage * 0.75)
                print("You feel your shield protecting you! It reduces the damage you take this turn, but is no longer active.")
                self.shield = False
            self.player.take_damage(damage)
            print(f"You take {damage} damage. You have {self.player.health} health left.")
            input()
            self.enemy.special_attack_available = False
            self.enemy_special_attack = False
            enemy_action = 'Skip'

        if enemy_action == 'Skip':
            return
        else:
            enemy_action = self.enemy_action_determiner()

        if enemy_action == 'Melee attack':
            weapon_damage = self.enemy.melee
            modifier = self.enemy.stat_modifier(self.enemy.strength)
            to_hit = self.modifier('Enemy melee')
        elif enemy_action == 'Ranged attack':
            weapon_damage = self.enemy.ranged
            modifier = self.enemy.stat_modifier(self.enemy.dexterity)
            to_hit = self.modifier('Enemy ranged')
        elif enemy_action == 'Special attack':
            self.enemy_special_attack = True
            print("The enemy is preparing a special attack!")
            input()
            return

        player_ac = self.modifier('Player ac')

        if to_hit >= player_ac:
            damage = max(1,((random.randint(int(weapon_damage * 0.7),int(weapon_damage * 1.3)) + modifier) - self.player.armor))
            if self.defending:
                time_taken_dodging = self.reaction_time('Dodge')
                self.defending = False
                if time_taken_dodging <= 15:
                    print("You fully dodge the enemy's attack!")
                    damage = 0
                elif time_taken_dodging <= 35:
                    print("You dodge the enemy's attack partially. 25% reduced damage.")
                    damage = int(damage * 0.75)
                elif time_taken_dodging <= 60:
                    print("You try to dodge the enemy's attack, but don't manage to do it well. Normal damage")
                else:
                    print("While trying to dodge, you slip! 25% more damage.")
                    damage = int(damage * 1.25)
            elif self.shield:
                damage = int(damage * 0.75)
                print("You feel your shield protecting you! It reduces the damage you take this turn, but is no longer active.")
                self.shield = False
            print(f"The {self.enemy.name} hits you with a {enemy_action.lower()} for {damage} damage.")
            self.player.take_damage(damage)
            print(f"You have {self.player.health} health left.")
            input()
        else:
            print("The enemy misses its attack.")
            input()

    def enemy_action_determiner(self):
        if self.enemy.boss and self.enemy.special_attack_available:
            return 'Special attack'
        elif self.enemy.boss and self.enemy.ranged > 0:
            return 'Ranged attack'
        elif self.enemy.boss:
            return 'Melee attack'
    
        if self.enemy.health < self.player.health and self.enemy.ranged > 0:
            return 'Ranged attack'
        else:
            return 'Melee attack'

    def enemy_death(self):
        print(f"The {self.enemy.name} has died!")
        gold = random.randint(self.enemy.level,(self.enemy.level * 5))
        print(f"Encounter over. You get {gold} gold")
        self.player.add_gold(gold)
        print(f"You have {self.player.gold} gold.")
        input()
        experience = (self.enemy.level * 50)
        print(f"You also gain {experience} experience!")
        self.player.add_experience(experience)
        print(f"You have {self.player.experience} experience.")
        input()
        return 'Victory'

##player
#attack
    #melee
        #light weapons have double attack
        #skill level >= 5 have double attack
    #ranged
        #skill level >= 5 have double attack
    #spell
    #sneak attack (rogue)
    #special attack
#use consumable
#class action
#run
    #can't run from a boss
    #running while underleveled is easier
#dodge/defend 


##enemy
#attack
    #melee
    #ranged
    #special attack


##numbers
#AC - 10 + dex
#melee - 10 + str + (level // 2)
#ranged - 10 + dex + (level // 2)
#spell - 10 + int + (level // 2)

#to hit - (d20 + melee/ranged/spell) >= enemy/player AC
#damage - ((70% damage - 130% damage) + str/dex/int) - armor
#sneak attack - ^damage^ * 3


def encounter(player, enemy):
    fight = Combat(player, enemy)
    fight_condition = None
    skip_enemy_turn = False
    print(f"You are fighting a {enemy.name.lower()}! It's your turn.")
    if player.level < enemy.level:
        print("You are underleveled! Running will be easier.")
    while True:
        if fight_condition == None:
            fight_condition = fight.player_turn()

        if fight_condition == 'Run':
            player.rage_end()
            return 'Run'
        elif fight_condition == 'Victory':
            player.rage_end()
            fight.enemy_death()
            return 'Victory'

        if skip_enemy_turn == False:
            fight_condition = fight.enemy_turn()

        if fight.freeze > 0:
            skip_enemy_turn = True
            fight.freeze -= 1
            print("The enemy's turn is skipped due to the freeze spell!")
            input()
        elif fight.freeze == 0:
            fight.freeze -= 1
            skip_enemy_turn = False