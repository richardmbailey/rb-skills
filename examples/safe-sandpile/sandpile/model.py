"""Open-boundary BTW and slope-relaxation sandpile models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import random
from typing import Literal


DropMode = Literal["random", "center"]
ModelType = Literal["btw", "slope"]


@dataclass(frozen=True, slots=True)
class Avalanche:
    """Measurements for the relaxation caused by one added grain."""

    grain_index: int
    size: int
    area: int
    duration: int
    lost: int
    row: int
    column: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class SandpileModel:
    """A square integer lattice with selectable BTW or slope relaxation."""

    MIN_SIZE = 3
    MAX_SIZE = 128
    MAX_CENTRAL_NOISE_RADIUS = 32
    MIN_REPOSE_ANGLE_DEGREES = 10.0
    MAX_REPOSE_ANGLE_DEGREES = 60.0
    LAYER_HEIGHT_CELLS = 0.1
    _SLOPE_EPSILON = 1e-12
    _NEIGHBOURS = (
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1), (0, 1),
        (1, -1), (1, 0), (1, 1),
    )

    def __init__(
        self,
        size: int = 32,
        seed: int = 1,
        drop_mode: DropMode = "random",
        central_noise_radius: int = 0,
        model_type: ModelType = "btw",
        angle_of_repose_degrees: float = 40.0,
    ) -> None:
        self._validate_configuration(
            size,
            seed,
            drop_mode,
            central_noise_radius,
            model_type,
            angle_of_repose_degrees,
        )
        self.size = size
        self.seed = seed
        self.drop_mode = drop_mode
        self.central_noise_radius = central_noise_radius
        self.model_type = model_type
        self.angle_of_repose_degrees = float(angle_of_repose_degrees)
        self._critical_slope = math.tan(math.radians(self.angle_of_repose_degrees))
        self._random = random.Random(seed)
        self._central_candidates: list[tuple[int, int]] = []
        self._central_weights: list[float] = []
        self._prepare_central_distribution()
        self.grid = [[0 for _ in range(size)] for _ in range(size)]
        self.total_added = 0
        self.total_lost = 0
        self.avalanches: list[Avalanche] = []

    @classmethod
    def _validate_configuration(
        cls,
        size: int,
        seed: int,
        drop_mode: str,
        central_noise_radius: int,
        model_type: str,
        angle_of_repose_degrees: float,
    ) -> None:
        if isinstance(size, bool) or not isinstance(size, int):
            raise TypeError("size must be an integer")
        if not cls.MIN_SIZE <= size <= cls.MAX_SIZE:
            raise ValueError(f"size must be between {cls.MIN_SIZE} and {cls.MAX_SIZE}")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        if drop_mode not in {"random", "center"}:
            raise ValueError("drop_mode must be 'random' or 'center'")
        cls._validate_central_noise_radius(central_noise_radius)
        if model_type not in {"btw", "slope"}:
            raise ValueError("model_type must be 'btw' or 'slope'")
        if isinstance(angle_of_repose_degrees, bool) or not isinstance(
            angle_of_repose_degrees,
            (int, float),
        ):
            raise TypeError("angle_of_repose_degrees must be a number")
        if not math.isfinite(angle_of_repose_degrees):
            raise ValueError("angle_of_repose_degrees must be finite")
        if not (
            cls.MIN_REPOSE_ANGLE_DEGREES
            <= angle_of_repose_degrees
            <= cls.MAX_REPOSE_ANGLE_DEGREES
        ):
            raise ValueError(
                "angle_of_repose_degrees must be between "
                f"{cls.MIN_REPOSE_ANGLE_DEGREES:g} and "
                f"{cls.MAX_REPOSE_ANGLE_DEGREES:g}"
            )

    @classmethod
    def _validate_central_noise_radius(cls, radius: int) -> None:
        if isinstance(radius, bool) or not isinstance(radius, int):
            raise TypeError("central_noise_radius must be an integer")
        if not 0 <= radius <= cls.MAX_CENTRAL_NOISE_RADIUS:
            raise ValueError(
                "central_noise_radius must be between "
                f"0 and {cls.MAX_CENTRAL_NOISE_RADIUS}"
            )

    def _prepare_central_distribution(self) -> None:
        """Cache a truncated discrete Gaussian around the central lattice site."""

        centre = self.size // 2
        radius = self.central_noise_radius
        if radius == 0:
            self._central_candidates = [(centre, centre)]
            self._central_weights = [1.0]
            return

        sigma = max(radius / 2, 0.5)
        radius_squared = radius * radius
        candidates: list[tuple[int, int]] = []
        weights: list[float] = []
        for row in range(max(0, centre - radius), min(self.size, centre + radius + 1)):
            for column in range(max(0, centre - radius), min(self.size, centre + radius + 1)):
                distance_squared = (row - centre) ** 2 + (column - centre) ** 2
                if distance_squared <= radius_squared:
                    candidates.append((row, column))
                    weights.append(math.exp(-distance_squared / (2 * sigma * sigma)))
        self._central_candidates = candidates
        self._central_weights = weights

    def set_source(self, drop_mode: DropMode, central_noise_radius: int) -> None:
        """Change subsequent drop placement without clearing physical state or history."""

        if drop_mode not in {"random", "center"}:
            raise ValueError("drop_mode must be 'random' or 'center'")
        self._validate_central_noise_radius(central_noise_radius)
        self.drop_mode = drop_mode
        self.central_noise_radius = central_noise_radius
        self._prepare_central_distribution()

    def set_drop_mode(self, drop_mode: DropMode) -> None:
        """Change the source used by subsequent additions without clearing state."""

        self.set_source(drop_mode, self.central_noise_radius)

    @property
    def retained_mass(self) -> int:
        return sum(sum(row) for row in self.grid)

    @property
    def mass_balance_residual(self) -> int:
        """Return zero when added mass equals retained plus boundary loss."""

        return self.total_added - self.retained_mass - self.total_lost

    @property
    def maximum_height_layers(self) -> int:
        return max((max(row, default=0) for row in self.grid), default=0)

    @property
    def maximum_height_cells(self) -> float:
        return round(self.maximum_height_layers * self.LAYER_HEIGHT_CELLS, 10)

    def _height_at_or_outside(self, row: int, column: int) -> int:
        if 0 <= row < self.size and 0 <= column < self.size:
            return self.grid[row][column]
        return 0

    @property
    def maximum_slope_degrees(self) -> float:
        if self.model_type != "slope":
            return 0.0
        maximum_slope = 0.0
        for row in range(self.size):
            for column in range(self.size):
                height = self.grid[row][column]
                for row_delta, column_delta in self._NEIGHBOURS:
                    neighbour_height = self._height_at_or_outside(
                        row + row_delta,
                        column + column_delta,
                    )
                    if height <= neighbour_height:
                        continue
                    distance = math.hypot(row_delta, column_delta)
                    slope = (
                        (height - neighbour_height)
                        * self.LAYER_HEIGHT_CELLS
                        / distance
                    )
                    maximum_slope = max(maximum_slope, slope)
        return math.degrees(math.atan(maximum_slope))

    def _drop_location(self) -> tuple[int, int]:
        if self.drop_mode == "center":
            if self.central_noise_radius == 0:
                return self._central_candidates[0]
            return self._random.choices(
                self._central_candidates,
                weights=self._central_weights,
                k=1,
            )[0]
        return self._random.randrange(self.size), self._random.randrange(self.size)

    def add_grain(self, row: int | None = None, column: int | None = None) -> Avalanche:
        """Add one grain and fully relax the lattice before returning."""

        if (row is None) != (column is None):
            raise ValueError("row and column must be supplied together")
        if row is None:
            row, column = self._drop_location()
        else:
            if isinstance(row, bool) or isinstance(column, bool):
                raise TypeError("row and column must be integers")
            if not isinstance(row, int) or not isinstance(column, int):
                raise TypeError("row and column must be integers")
            if not (0 <= row < self.size and 0 <= column < self.size):
                raise ValueError("row and column must be inside the lattice")

        self.grid[row][column] += 1
        self.total_added += 1
        avalanche = (
            self._stabilize_slope(row, column)
            if self.model_type == "slope"
            else self._stabilize_btw(row, column)
        )
        self.avalanches.append(avalanche)
        return avalanche

    def add_grains(self, count: int) -> list[Avalanche]:
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer")
        if count < 1:
            raise ValueError("count must be positive")
        return [self.add_grain() for _ in range(count)]

    def _stabilize_btw(self, drop_row: int, drop_column: int) -> Avalanche:
        size = 0
        duration = 0
        lost = 0
        toppled_sites: set[tuple[int, int]] = set()

        while True:
            unstable: list[tuple[int, int, int]] = []
            for row_index, row_values in enumerate(self.grid):
                for column_index, height in enumerate(row_values):
                    if height >= 4:
                        unstable.append((row_index, column_index, height // 4))
            if not unstable:
                break

            duration += 1
            for row_index, column_index, topplings in unstable:
                self.grid[row_index][column_index] -= 4 * topplings
                size += topplings
                toppled_sites.add((row_index, column_index))
                for row_delta, column_delta in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    neighbour_row = row_index + row_delta
                    neighbour_column = column_index + column_delta
                    if 0 <= neighbour_row < self.size and 0 <= neighbour_column < self.size:
                        self.grid[neighbour_row][neighbour_column] += topplings
                    else:
                        lost += topplings

        self.total_lost += lost
        return Avalanche(
            grain_index=self.total_added,
            size=size,
            area=len(toppled_sites),
            duration=duration,
            lost=lost,
            row=drop_row,
            column=drop_column,
        )

    def _stabilize_slope(self, drop_row: int, drop_column: int) -> Avalanche:
        """Relax one added layer using synchronous, distance-corrected downhill moves."""

        size = 0
        duration = 0
        lost = 0
        moved_sites: set[tuple[int, int]] = set()

        while True:
            moves: list[tuple[int, int, int, int]] = []
            for row in range(self.size):
                for column in range(self.size):
                    height = self.grid[row][column]
                    if height == 0:
                        continue
                    steepest = self._critical_slope
                    destinations: list[tuple[int, int]] = []
                    for row_delta, column_delta in self._NEIGHBOURS:
                        neighbour_row = row + row_delta
                        neighbour_column = column + column_delta
                        neighbour_height = self._height_at_or_outside(
                            neighbour_row,
                            neighbour_column,
                        )
                        if height <= neighbour_height:
                            continue
                        distance = math.hypot(row_delta, column_delta)
                        slope = (
                            (height - neighbour_height)
                            * self.LAYER_HEIGHT_CELLS
                            / distance
                        )
                        if slope > steepest + self._SLOPE_EPSILON:
                            steepest = slope
                            destinations = [(neighbour_row, neighbour_column)]
                        elif (
                            destinations
                            and abs(slope - steepest) <= self._SLOPE_EPSILON
                        ):
                            destinations.append((neighbour_row, neighbour_column))
                    if destinations:
                        destination = self._random.choice(destinations)
                        moves.append((row, column, destination[0], destination[1]))

            if not moves:
                break

            duration += 1
            size += len(moves)
            for row, column, neighbour_row, neighbour_column in moves:
                self.grid[row][column] -= 1
                moved_sites.add((row, column))
                if 0 <= neighbour_row < self.size and 0 <= neighbour_column < self.size:
                    self.grid[neighbour_row][neighbour_column] += 1
                else:
                    lost += 1

        self.total_lost += lost
        return Avalanche(
            grain_index=self.total_added,
            size=size,
            area=len(moved_sites),
            duration=duration,
            lost=lost,
            row=drop_row,
            column=drop_column,
        )

    def clear_avalanche_history(self) -> None:
        """Discard measurements while preserving the current physical state."""

        self.avalanches.clear()

    def snapshot(self, recent: int = 40) -> dict[str, object]:
        if isinstance(recent, bool) or not isinstance(recent, int) or recent < 0:
            raise ValueError("recent must be a non-negative integer")
        positive = sum(event.size > 0 for event in self.avalanches)
        return {
            "size": self.size,
            "seed": self.seed,
            "drop_mode": self.drop_mode,
            "central_noise_radius": self.central_noise_radius,
            "model_type": self.model_type,
            "angle_of_repose_degrees": self.angle_of_repose_degrees,
            "layer_height_cells": self.LAYER_HEIGHT_CELLS,
            "maximum_height_layers": self.maximum_height_layers,
            "maximum_height_cells": self.maximum_height_cells,
            "maximum_slope_degrees": self.maximum_slope_degrees,
            "grid": [row[:] for row in self.grid],
            "total_added": self.total_added,
            "retained_mass": self.retained_mass,
            "total_lost": self.total_lost,
            "mass_balance_residual": self.mass_balance_residual,
            "recorded_avalanches": len(self.avalanches),
            "positive_avalanches": positive,
            "largest_avalanche": max((event.size for event in self.avalanches), default=0),
            "recent_avalanches": [event.as_dict() for event in self.avalanches[-recent:]],
        }
