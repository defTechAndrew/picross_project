"""Purpose: Hold base classes for picross game."""

import dataclasses
from enum import Enum
import random


class BoardAxis(Enum):
    ROW = 0
    COLUMN = 1


@dataclasses.dataclass
class KeyIsland:
    index: int
    length: int


class Board:

    def __init__(self, dimensions=(5, 5), palette=None):

        self.dimensions = dimensions
        self.palette = Palette() if palette is None else palette
        self._rows = list()
        for _ in range(dimensions[0]):
            self._rows.append([0 for _ in range(dimensions[1])])

    def __getitem__(self, item):

        return self._rows[item]

    def __setitem__(self, key, value):

        self._rows[key] = value

    def __iter__(self):

        for row in self._rows:
            yield row

    def __eq__(self, other):

        if isinstance(other, Board):
            if len(self._rows) != len(other._rows):
                return False
            for row, other_row in zip(self._rows, other._rows):
                if row != other_row:
                    return False
            return True
        else:
            return False

    def randomize(self):

        for row_index in range(len(self._rows)):
            self._rows[row_index] = [random.randint(0, self.palette.size) for _ in range(len(self._rows[row_index]))]

    def _get_axis_index(self, index, axis):

        if axis == BoardAxis.ROW:
            return self[index]
        elif axis == BoardAxis.COLUMN:
            return [self._rows[index] for index in range(len(self._rows))]

    def get_axis_key(self, index, axis):

        sequence = self._get_axis_index(index, axis)
        key = list()
        last_value = sequence[0]
        current_length = 0
        for value in sequence:
            if value == last_value:
                current_length += 1
            else:
                if last_value != 0:
                    key.append(KeyIsland(last_value, current_length))
                current_length = 1
            last_value = value

        if last_value != 0:  # Capture final island after iteration
            key.append(KeyIsland(last_value, current_length))

        return key


class Palette:

    def __init__(self, colors=((0, 0, 0), )):

        self.colors = colors

    @property
    def size(self):

        return len(self.colors)


def test():
    y = Palette(colors=((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    x = Board(dimensions=(15, 20), palette=y)
    x.randomize()
    return x
