import random


def generate_random_color():
    """
    Генерирует HEX цвет вида #A1B2C3
    """
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))
