"""Python model of the Euclidean rhythm (features/chord/euclid_math.c): bit i = a hit on step i (0 <= i < n) when
((i + r) * k) mod n < k; k >= n fills every step."""


def mask(k: int, n: int, r: int) -> int:
    if k >= n:
        return (1 << n) - 1
    return sum(1 << i for i in range(n) if ((i + r) * k) % n < k)
