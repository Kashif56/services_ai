import random

def generate_id(prefix):
    return prefix + str(random.choices('0123456789', k=6))
