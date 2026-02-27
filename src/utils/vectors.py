# ---------------------------------------------------------------------
# Standard library
# ---------------------------------------------------------------------
import math


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum((float(x) ** 2 for x in vector)))
    if norm > 0:
        return [float(x) / norm for x in vector]
    return vector