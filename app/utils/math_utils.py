import math
from typing import Sequence, Tuple


def euclidean_distance(p1: Sequence[float], p2: Sequence[float]) -> float:
    """
    Вычисляет евклидово расстояние между двумя точками одинаковой размерности.

    Args:
        p1: Первая точка (x, y, …).
        p2: Вторая точка (x, y, …).

    Returns:
        Евклидово расстояние.

    Raises:
        ValueError: если размерности точек отличаются.
    """
    if len(p1) != len(p2):
        raise ValueError("Points must have the same dimension")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    «Зажимает» число в указанный диапазон [min_value, max_value].

    Args:
        value: исходное число.
        min_value: минимальное допустимое значение.
        max_value: максимальное допустимое значение.

    Returns:
        value, но не меньше min_value и не больше max_value.
    """
    return max(min_value, min(value, max_value))


def mean(values: Sequence[float]) -> float:
    """
    Вычисляет среднее арифметическое списка чисел.

    Args:
        values: список или кортеж чисел.

    Returns:
        Среднее арифметическое.

    Raises:
        ValueError: если values пуст.
    """
    if not values:
        raise ValueError("Cannot compute mean of empty sequence")
    return sum(values) / len(values)
