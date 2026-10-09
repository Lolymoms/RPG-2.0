class weapon:
    def __init__(self, damage, damage_type, rarity, type):
        self.damage = damage
        self.damage_type = damage_type
        self.rarity = rarity
        self.type = type

sword = weapon(10, 'Slashing', 'Common', 'Melee')

print(sword.damage)

#chatgpt
for stat, value in sword.__dict__.items():
    print(f"{stat.capitalize()}: {value}")