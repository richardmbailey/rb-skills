"""Independent P0 toy-artifact checker; not a product gate or adapter."""
import math


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def evaluate(artifact):
    """Compare supplied results with fixed analytical expectations."""
    try:
        case = artifact['case']
        if case == 'O22':
            if artifact['unit'] != 'tonnes' or artifact['kg'] != [0, 1, 1250]:
                return False
            values = artifact['values']
            expected = [0, 0.001, 1.25]
            tolerance = 1e-12
        elif case == 'O23':
            if artifact['unit'] != 'kg' or artifact['initial'] != [10, 2] or artifact['transfer'] != 3:
                return False
            values = artifact['values']
            expected = [7, 5]
            tolerance = 1e-12
            if len(values) != 2 or not all(finite_number(v) for v in values):
                return False
            if abs(sum(values) - 12) > tolerance:
                return False
        elif case == 'O24':
            if artifact['unit'] != 'dimensionless' or artifact['grids'] != [4, 8, 16]:
                return False
            values = artifact['integrals']
            if len(values) != 3 or not all(finite_number(v) for v in values):
                return False
            errors = [abs(v - 1 / 3) for v in values]
            if any(e <= 0 for e in errors):
                return False
            orders = [math.log2(a / b) for a, b in zip(errors, errors[1:])]
            return all(1.9 <= order <= 2.1 for order in orders)
        else:
            return False
        return len(values) == len(expected) and all(
            finite_number(v) and abs(v - e) <= tolerance
            for v, e in zip(values, expected)
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
