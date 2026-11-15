def transfer(source, target, amount):
    return source - amount, target + amount


def kilograms_to_tonnes(value):
    return value / 100  # Deliberate evaluation defect.
