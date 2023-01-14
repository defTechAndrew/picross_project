"""Purpose: Hold base classes for picross game."""

import dataclasses
from enum import Enum
import random

FILE_EXTENSION = 'json'


class BoardAxis(Enum):
    ROW = 0
    COLUMN = 1


@dataclasses.dataclass
class KeyIsland:
    index: int
    length: int


class BaseBoardMatrix:

    def __init__(self, default_value, dimensions=(5, 5)):

        self._dimensions = dimensions
        self._data = list()
        for _ in range(self._dimensions[0]):
            self._data.append([default_value for _ in range(self._dimensions[1])])

    def __getitem__(self, row_index):

        return self._data[row_index]

    def __setitem__(self, row_index, row_list):

        if len(row_list) == self.dimensions[1]:
            self._data[row_index] = row_list
        else:
            raise ValueError("Passed row does not match object's column dimesion")

    def __iter__(self):

        for row in self._data:
            yield row

    def __len__(self):

        return len(self._data)

    def __eq__(self, other):

        if issubclass(other.__class__, BaseBoardMatrix):
            if len(self) != len(other):
                return False
            for row, other_row in zip(self, other):
                if row != other_row:
                    return False
            return True
        else:
            return False

    @property
    def dimensions(self):

        return self._dimensions


class Board(BaseBoardMatrix):

    def __init__(self, dimensions=(5, 5), palette=None):
        super(Board, self).__init__(0, dimensions=dimensions)

        self.palette = Palette() if palette is None else palette

    def randomize(self):

        for row_index in range(len(self._data)):
            self._data[row_index] = [random.randint(0, self.palette.size) for _ in range(len(self._data[row_index]))]

    def get_axis_key(self, index, axis):

        if axis == BoardAxis.ROW:
            sequence = self[index]
        elif axis == BoardAxis.COLUMN:
            sequence = [self._data[row_index][index] for row_index in range(len(self._data))]
        else:
            raise ValueError('Axis argument is not a valid BoardAxis value.')

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

        return key if key else [KeyIsland(1, 0)]

    def serialize(self):

        return {'dimensions': self.dimensions, 'rows': self._data, 'palette': self.palette.serialize()}

    @classmethod
    def deserialize(cls, data):

        new_palette = Palette.deserialize(data['palette'])
        new_board = cls(dimensions=data['dimensions'], palette=new_palette)
        for row_index, row in enumerate(data['rows']):
            new_board[row_index] = row

        return new_board


class Palette:

    def __init__(self, colors=((40, 40, 40), )):

        self.colors = colors
        self.empty_color = (220, 220, 220)
        self.background_color = (240, 240, 240)
        self.marking_color = (230, 100, 100)

    def __getitem__(self, item):

        return self.empty_color if item == 0 else self.colors[item + 1]

    @property
    def size(self):

        return len(self.colors)

    def serialize(self):

        return self.__dict__

    @classmethod
    def deserialize(cls, data):

        new_palette = cls(data['colors'])
        new_palette.empty_color = data['empty_color']
        new_palette.background_color = data['background_color']
        new_palette.marking_color = data['marking_color']
        return new_palette


class BoardCrossState(BaseBoardMatrix):

    def __init__(self, dimensions=(5, 5)):
        super(BoardCrossState, self).__init__(False, dimensions=dimensions)

    def serialize(self):

        return {'dimensions': self.dimensions, 'crossed': self._data}

    @classmethod
    def deserialize(cls, data):

        new_board = cls(dimensions=data['dimensions'])
        for row_index, row in enumerate(data['rows']):
            new_board[row_index] = row

        return new_board
