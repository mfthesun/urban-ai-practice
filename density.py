"""Расчёт плотности населения (пример 3 практического занятия 1).

Плотность населения = число жителей / площадь территории.
Результат выражается в жителях на гектар (чел./га).
"""

POPULATION = 1200  # жителей
AREA_HA = 8.0  # гектаров


def population_density(population: float, area_ha: float) -> float:
    """Возвращает плотность населения в жителях на гектар.

    Parameters
    ----------
    population : float
        Число жителей на территории.
    area_ha : float
        Площадь территории в гектарах.

    Returns
    -------
    float
        Плотность населения, чел./га.
    """
    if area_ha <= 0:
        raise ValueError("Площадь территории должна быть больше нуля")
    return population / area_ha


def main() -> None:
    """Считает и печатает плотность населения для заданных исходных данных."""
    density = population_density(POPULATION, AREA_HA)
    print(f"Население: {POPULATION:.0f} чел.")
    print(f"Площадь территории: {AREA_HA:g} га")
    print(f"Плотность населения: {density:.0f} чел./га")
    print(f"Формула: {POPULATION:.0f} / {AREA_HA:g} = {density:.0f} чел./га")


if __name__ == "__main__":
    main()
