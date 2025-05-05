from typing import List, Tuple

from app.utils.math_utils import euclidean_distance


Point = Tuple[float, float]
Polygon = List[Point]


def is_point_in_polygon(point: Point, polygon: Polygon) -> bool:
    """
    Определяет, находится ли точка внутри многоугольника (включая границу)
    методом ray-casting (прямо-лево пересечения).

    Args:
        point: кортеж (x, y) — проверяемая точка.
        polygon: список вершин [(x1,y1), (x2,y2), ...] в порядке обхода.

    Returns:
        True, если точка внутри или на границе, иначе False.
    """
    x, y = point
    inside = False
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        # проверяем, пересекает ли луч вправо от точки ребро [i,i+1]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
            inside = not inside
    # Если точка лежит точно на одном из отрезков, считать внутри
    # (дополнительная проверка)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        # проекция точки на отрезок
        dx, dy = x2 - x1, y2 - y1
        # если точка коллинеарна и лежит между концами отрезка
        if abs(dy * (x - x1) - dx * (y - y1)) < 1e-9:
            dot = (x - x1) * dx + (y - y1) * dy
            if 0 <= dot <= dx*dx + dy*dy:
                return True
    return inside


def polygon_area(polygon: Polygon) -> float:
    """
    Вычисляет ориентированную площадь многоугольника по формуле
    Гаусса (shoelace). Возвращает абсолютное значение.

    Args:
        polygon: список вершин [(x1,y1), ...] в порядке обхода.

    Returns:
        Площадь (в тех же единицах, что координаты).
    """
    area = 0.0
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def polygon_centroid(polygon: Polygon) -> Point:
    """
    Вычисляет центр тяжести (геометрический центр) многоугольника.

    Args:
        polygon: список вершин [(x1,y1), ...] в порядке обхода.

    Returns:
        Кортеж (cx, cy).
    """
    n = len(polygon)
    if n == 0:
        raise ValueError("Polygon must have at least one vertex")
    if n == 1:
        return polygon[0]
    # для линии (2 точки) вернём середину
    if n == 2:
        (x1, y1), (x2, y2) = polygon
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    # формулы с учётом ориентированной площади
    signed_area = 0.0
    cx = cy = 0.0
    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i + 1) % n]
        a = x0 * y1 - x1 * y0
        signed_area += a
        cx += (x0 + x1) * a
        cy += (y0 + y1) * a

    if abs(signed_area) < 1e-9:
        # вырожденный полигон — вернём среднее по точкам
        xs, ys = zip(*polygon)
        return (sum(xs) / n, sum(ys) / n)

    signed_area *= 0.5
    factor = 1 / (6 * signed_area)
    return (cx * factor, cy * factor)


def nearest_point_on_polygon(point: Point, polygon: Polygon) -> Point:
    """
    Находит ближайшую точку на границе многоугольника к заданной точке.

    Args:
        point: (x, y).
        polygon: список вершин.

    Returns:
        Кортеж координат ближайшей точки на границе.
    """
    best_point: Point = polygon[0]
    best_dist = float("inf")
    # проходим по всем отрезкам
    for i in range(len(polygon)):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % len(polygon)]
        # проекция точки на бесконечную прямую
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            proj = (x1, y1)
        else:
            t = ((point[0] - x1) * dx + (point[1] - y1) * dy) / (dx*dx + dy*dy)
            t_clamped = max(0.0, min(1.0, t))
            proj = (x1 + t_clamped * dx, y1 + t_clamped * dy)
        dist = euclidean_distance(point, proj)
        if dist < best_dist:
            best_dist = dist
            best_point = proj
    return best_point