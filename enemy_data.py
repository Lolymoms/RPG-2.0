class Enemy:
    def __init__(self, name, level, amount, health, dexterity, armor, strength, melee, ranged=0, vulnerable='None', resistant='None', boss=False, special_attack='None'):
        self.name = name
        self.level = level
        self.amount = amount
        self.health = health
        self.dexterity = dexterity
        self.max_dexterity = dexterity
        self.armor = armor
        self.strength = strength
        self.melee = melee
        self.ranged = ranged
        self.vulnerable = vulnerable
        self.resistant = resistant
        self.boss = boss
        self.special_attack = special_attack
        #if the enemy has a special attack, makes that attack available
        self.special_attack_available = (special_attack != 'None')

    def stat_modifier(self, stat):
        return (stat - 10)//2
    
    def skill_modifier(self, skill):
        return skill - 2

    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def half_dex(self):
        self.dexterity //= 2
        return (10 + self.stat_modifier(self.dexterity))

    def restore_dex(self):
        self.dexterity = self.max_dexterity
        return (10 + self.stat_modifier(self.dexterity))

feral_dog = Enemy('Feral Dog', 1, 1, 20, 10, 1, 15, 6)
cave_spider = Enemy('Cave Spider', 1, 1, 12, 17, 1, 14, 8)