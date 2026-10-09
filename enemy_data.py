class Enemy:
    def __init__(self, name, level, amount, health, dexterity, armor, strength, damage, damage_ranged=0, vulnerable='None', resistant='None', boss='False'):
        self.name = name
        self.level = level
        self.amount = amount
        self.health = health
        self.dexterity = dexterity
        self.armor = armor
        self.strength = strength
        self.damage = damage
        self.damage_ranged = damage_ranged
        self.vulnerable = vulnerable
        self.resistant = resistant
        self.boss = boss

    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0


goblins = Enemy('Goblins', 1, 3, 5, 5, 1, 5, 7, 6)