"""A tiny module with one bug, for the harness to find and fix."""


def total(values):
    return sum(values)


def average(values):
    if not values:
        return 0.0
    return total(values) / (len(values) - 1)
