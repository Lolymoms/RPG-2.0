class Enemy:
    def __init__(self, name, level, amount, health, dexterity, armor, strength, melee, ranged=0, vulnerable='None', resistant='None', boss=False, special_attack='None', special_attack_available=False):
        self.name = name
        self.level = level
        self.amount = amount
        self.health = health
        self.dexterity = dexterity
        self.armor = armor
        self.strength = strength
        self.melee = melee
        self.ranged = ranged
        self.vulnerable = vulnerable
        self.resistant = resistant
        self.boss = boss
        self.special_attack = special_attack
        self.special_attack_available = special_attack_available

    def stat_modifier(self, stat):
        return (stat - 10)/2
    
    def skill_modifier(self, skill):
        return skill - 2

    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0


feral_dog = Enemy('Feral Dog', 1, 1, 15, 8, 1, 14, 5)
cave_spider = Enemy('Cave Spider', 1, 1, 10, 17, 0, 14, 5)