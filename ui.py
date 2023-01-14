"""Picross board UI implemented with QT"""

import os
import json
from PySide6 import QtCore, QtWidgets, QtGui
import core as core


class GameWindow(QtWidgets.QMainWindow):
    PUZZLE_DIR = os.path.join(os.getcwd(), 'puzzles')
    PALETTE_DIR = os.path.join(os.getcwd(), 'palettes')

    def __init__(self, parent=None):
        super(GameWindow, self).__init__(parent=parent)

        self.setWindowTitle('Picross')

        file_menu = QtWidgets.QMenu('File')
        self.menuBar().addMenu(file_menu)
        file_menu.addAction('New Game', self.new_game)
        file_menu.addAction('Complete Puzzle', self.complete_puzzle)
        file_menu.addAction('Save Puzzle', self.save_puzzle)
        file_menu.addAction('Load Puzzle', self.load_puzzle)
        create_menu = QtWidgets.QMenu('Create')
        self.menuBar().addMenu(create_menu)
        create_menu.addAction('Create Puzzle', self.create_puzzle)
        create_menu.addAction('Create Palette', self.create_palette)

        self.board_widget = None
        self.init_board(self.generate_random_board((15, 10), 1))

    def new_game(self):

        new_dialog = NewGameDialog(self)
        if new_dialog.exec():
            dimensions, colors = new_dialog.get_values()
            self.init_board(self.generate_random_board(dimensions, colors))

    @staticmethod
    def generate_random_board(dimensions, color_indices):

        if color_indices == 2:
            palette = core.Palette(colors=((230, 80, 80), (160, 220, 220)))
        elif color_indices == 3:
            palette = core.Palette(colors=((132, 45, 106), (38, 111, 97), (174, 151, 60)))
        else:
            palette = core.Palette()

        board = core.Board(dimensions=dimensions, palette=palette)
        board.randomize()

        return board

    def init_board(self, board):

        if self.board_widget is not None:
            self.board_widget.close()

        self.board_widget = BoardWidget(board=board, parent=self)
        self.setCentralWidget(self.board_widget)

    def complete_puzzle(self):

        if self.board_widget:
            self.board_widget.complete_board()

    def create_puzzle(self):

        dialog = CreatePuzzle(parent=self)
        if dialog.exec():
            create_board = core.Board(dialog.dimensions, palette=dialog.palette)
            self.init_board(create_board)
            self.board_widget.complete = True
            save_button = QtWidgets.QPushButton('Save Puzzle')
            self.board_widget.layout().addWidget(save_button)
            save_button.clicked.connect(self.save_puzzle)

    def save_puzzle(self):

        dialog = QtWidgets.QFileDialog(self, 'Save Puzzle', self.PUZZLE_DIR, f'JSON file (*.{core.FILE_EXTENSION})')
        dialog.setDefaultSuffix(f".{core.FILE_EXTENSION}")
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptSave)
        if dialog.exec():
            file_paths = dialog.selectedFiles()
            if file_paths:
                with open(file_paths[0], 'w') as save_file:
                    json.dump(self.board_widget.get_board_state().serialize(), save_file, indent=4)

    def load_puzzle(self):

        dialog = QtWidgets.QFileDialog(self, 'Load Puzzle', self.PUZZLE_DIR, f'JSON file (*.{core.FILE_EXTENSION})')
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptMode.AcceptOpen)
        if dialog.exec():
            file_paths = dialog.selectedFiles()
            if file_paths:
                with open(file_paths[0], 'r') as load_file:
                    puzzle_data = json.load(load_file)
                loaded_board = core.Board.deserialize(puzzle_data)
                self.init_board(loaded_board)

    def create_palette(self):

        dialog = PaletteCreator(name_field=True, parent=self)
        if dialog.exec():
            palette_path = os.path.join((self.PALETTE_DIR, f'{dialog.name}.{core.FILE_EXTENSION}'))
            with open(palette_path, 'w') as save_file:
                json.dump(dialog.palette.serialize(), save_file, indent=4)


class BoardWidget(QtWidgets.QWidget):

    def __init__(self, board, parent=None):
        super(BoardWidget, self).__init__(parent=parent)

        self.board = board
        self.complete = False
        # Drag operation variables
        self.drag_start = None
        self.drag_start_cell = None
        self.drag_cells = []
        self.drag_initial_state = None

        # Layout Setup
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        grid_container = QtWidgets.QWidget()
        self.layout().addWidget(grid_container)
        grid_layout = QtWidgets.QGridLayout()
        grid_container.setLayout(grid_layout)
        grid_layout.setSpacing(0)
        grid_layout.setVerticalSpacing(0)
        board_palette = QtGui.QPalette()
        board_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(*self.board.palette.background_color))
        self.setAutoFillBackground(True)
        self.setPalette(board_palette)

        # Populate palette switching buttons
        self.palette_buttons = []
        if len(self.board.palette.colors) > 1:
            button_container = QtWidgets.QWidget()
            button_container.setLayout(QtWidgets.QVBoxLayout())
            button_container.layout().setSpacing(0)
            button_container.layout().addStretch()
            grid_layout.addWidget(button_container, 0, 0)
            for index, color in enumerate(self.board.palette.colors):
                self.palette_buttons.append(QtWidgets.QToolButton())
                self.palette_buttons[-1].setCheckable(True)
                pixmap = get_icon_pixmap('circle', QtGui.QColor(*color))
                icon = QtGui.QIcon(pixmap)
                self.palette_buttons[-1].setIcon(icon)
                button_container.layout().addWidget(self.palette_buttons[-1])
                self.palette_buttons[-1].clicked.connect(self.index_selected)

            self.palette_buttons[0].setChecked(True)

        self._index = 1
        key_palettes = get_qt_palettes(self.board.palette)
        key_palettes[0].setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(*self.board.palette.empty_color))

        # Populate board keys
        self.dividers = []
        for axis in (core.BoardAxis.ROW, core.BoardAxis.COLUMN):
            current_index = 1
            is_row = axis is core.BoardAxis.ROW
            additional_length = int(self.board.dimensions[int(is_row)] / 5) - 1
            length = self.board.dimensions[int(is_row)] + additional_length
            axis_dimension = self.board.dimensions[axis.value]
            for axis_index in range(axis_dimension):
                # Add divider every five cells
                if axis_index % 5 == 0 and axis_index != 0:
                    self.dividers.append(get_divider(self.board.palette, horizontal=is_row))
                    if is_row:
                        grid_layout.addWidget(self.dividers[-1], current_index, 1, 1, length)
                    else:
                        grid_layout.addWidget(self.dividers[-1], 1, current_index, length, 1)
                    current_index += 1
                # Add key container
                container = QtWidgets.QWidget()
                container.setAutoFillBackground(True)
                if axis is core.BoardAxis.ROW:
                    layout = QtWidgets.QHBoxLayout()
                    grid_layout.addWidget(container, current_index, 0)
                else:
                    layout = QtWidgets.QVBoxLayout()
                    grid_layout.addWidget(container, 0, current_index)
                layout.setSpacing(0)
                current_index += 1
                container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
                container.setLayout(layout)
                if axis_index % 2 == 1:
                    container.setPalette(key_palettes[0])
                # Add key blocks to containers
                key = self.board.get_axis_key(axis_index, axis)
                layout.addStretch()
                layout.setContentsMargins(0, 0, 0, 0)
                buffer_width = axis is core.BoardAxis.ROW
                for key_island in key:
                    key_block = KeyBlock(
                        key_island.length,
                        key_palettes[key_island.index] if key_island.length else key_palettes[0],
                        buffer_width=buffer_width,
                        parent=self)
                    layout.addWidget(key_block)
                layout.addSpacing(2)

        # Populate board cells
        grid_index = [1, 1]
        self.cells = []
        for row_index, row in enumerate(self.board):
            if row_index % 5 == 0 and row_index != 0:
                grid_index[0] += 1
            self.cells.append([])
            for column_index in range(len(row)):
                if column_index % 5 == 0 and column_index != 0:
                    grid_index[1] += 1
                new_cell = Cell(self.board.palette, self.get_index, (row_index, column_index), parent=self)
                self.cells[row_index].append(new_cell)
                grid_layout.addWidget(self.cells[row_index][-1], *grid_index)
                grid_index[1] += 1
            grid_index[1] = 1
            grid_index[0] += 1

        self.cross_empty_sequences()

        # Add expanding bottom corner to keep puzzle centered
        bottom_corner = QtWidgets.QWidget()
        bottom_corner.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        grid_layout.addWidget(bottom_corner, grid_layout.rowCount(), grid_layout.columnCount())

    def cross_empty_sequences(self):

        for axis in (core.BoardAxis.ROW, core.BoardAxis.COLUMN):
            axis_dimension = self.board.dimensions[axis.value]
            for axis_index in range(axis_dimension):
                key = self.board.get_axis_key(axis_index, axis)
                if key[0].length == 0:
                    if axis is core.BoardAxis.ROW:
                        sequence = self.cells[axis_index]
                    else:
                        sequence = [self.cells[row_index][axis_index] for row_index in range(len(self.cells))]
                    for cell in sequence:
                        cell.cross = True

    def get_board_state(self):

        board = core.Board(self.board.dimensions, self.board.palette)
        for row_index, row in enumerate(board):
            for column_index, _ in enumerate(row):
                row[column_index] = self.cells[row_index][column_index].index
        return board

    def get_cross_state(self):

        cross_board = core.BoardCrossState(self.board.dimensions)
        for row_index, row in enumerate(cross_board):
            for column_index, _ in enumerate(row):
                row[column_index] = self.cells[row_index][column_index].cross
        return cross_board

    def set_board_state(self, board, cross_state=None):

        if cross_state is None:
            cross_state = core.BoardCrossState(board.dimensions)
        for row_index, row in enumerate(board):
            for column_index, row_value in enumerate(row):
                self.cells[row_index][column_index].set_state(row_value, cross_state[row_index][column_index])

    def index_selected(self):

        for index, button in enumerate(self.palette_buttons):
            if button.isChecked() and index + 1 != self._index:
                self.palette_buttons[self._index - 1].setChecked(False)
                self._index = index + 1
                break
            elif not button.isChecked() and index + 1 == self._index:
                self.palette_buttons[self._index - 1].setChecked(True)
                break

    def get_cell_span_to_start(self, position, axis, direction):

        cell_span = [self.get_cell_at_position(position)]
        next_cell = None
        iteration_value = direction * -1  # Flip direction since we walk backwards through the drag
        while next_cell != self.drag_start_cell:
            if next_cell is not None:
                cell_span.insert(0, next_cell)
            grid_index = cell_span[0].grid_index
            if axis == core.BoardAxis.ROW:
                next_cell = self.cells[grid_index[0]][grid_index[1] + iteration_value]
            else:
                next_cell = self.cells[grid_index[0] + iteration_value][grid_index[1]]

        return cell_span

    def get_index(self):

        return self._index

    def check_completion(self):

        return True if self.board == self.get_board_state() else False

    def complete_board(self):

        self.set_board_state(self.board)
        self.complete = True

    def get_cell_at_position(self, position):

        for row in self.cells:
            for cell in row:
                if cell.geometry().contains(position):
                    return cell

    def snap_point_to_cardinal(self, position):

        x_distance = abs(position.x() - self.drag_start.x())
        y_distance = abs(position.y() - self.drag_start.y())
        if x_distance > y_distance:
            direction = 1 if position.x() > self.drag_start.x() else -1
            return QtCore.QPoint(position.x(), self.drag_start.y()), core.BoardAxis.ROW, direction
        else:
            direction = 1 if position.y() > self.drag_start.y() else -1
            return QtCore.QPoint(self.drag_start.x(), position.y()), core.BoardAxis.COLUMN, direction

    def event(self, event):

        if event.type() == QtGui.QMouseEvent.Type.MouseButtonPress:
            position = event.position().toPoint()
            self.drag_start_cell = self.get_cell_at_position(position)
            if self.drag_start_cell:
                self.drag_start = position
                self.drag_cells = []
                self.drag_initial_state = self.get_board_state(), self.get_cross_state()
                start_index = self.drag_start_cell.grid_index
                if QtCore.Qt.MouseButton.LeftButton in event.buttons():
                    self.drag_initial_state[0][start_index[0]][start_index[1]] = self.drag_start_cell.index
                elif QtCore.Qt.MouseButton.RightButton in event.buttons():
                    self.drag_initial_state[1][start_index[0]][start_index[1]] = self.drag_start_cell.cross

        elif self.drag_start_cell is not None and event.type() == QtGui.QMouseEvent.Type.MouseMove:
            end_position, axis, direction = self.snap_point_to_cardinal(event.position().toPoint())
            end_cell = self.get_cell_at_position(end_position)
            last_end_cell = None if len(self.drag_cells) == 0 else self.drag_cells[-1]
            if end_cell is not None and end_cell != self.drag_start_cell and end_cell != last_end_cell:
                current_drag = self.get_cell_span_to_start(end_position, axis, direction)
                if current_drag and self.drag_cells == current_drag[:-1]:  # Drag is one cell longer
                    current_drag[-1].set_state(self.drag_start_cell.index, self.drag_start_cell.cross)
                elif self.drag_cells and self.drag_cells[:-1] == current_drag:  # Drag is one cell shorter
                    reset_cell = self.drag_cells[-1]
                    reset_index = reset_cell.grid_index
                    index = self.drag_initial_state[0][reset_index[0]][reset_index[1]]
                    crossed = self.drag_initial_state[1][reset_index[0]][reset_index[1]]
                    reset_cell.set_state(index, crossed)
                else:
                    self.set_board_state(*self.drag_initial_state)
                    for cell in current_drag:
                        cell.set_state(self.drag_start_cell.index, self.drag_start_cell.cross)
                self.drag_cells = current_drag
            elif self.drag_cells and end_cell == self.drag_start_cell:  # Return to start after a drag operation
                self.set_board_state(*self.drag_initial_state)
                self.drag_cells = []
        elif event.type() == QtGui.QMouseEvent.Type.MouseButtonRelease:
            self.drag_start_cell = None
            if not self.complete:
                if self.check_completion():
                    self.complete_event()

        return super(BoardWidget, self).event(event)

    def complete_event(self):

        self.complete = True
        for row in self.cells:
            for cell in row:
                cell.set_complete_state(True)
        for divider in self.dividers:
            divider.hide()
        CompleteDialog(self).exec()


class Cell(QtWidgets.QFrame):
    SIZE = 18

    def __init__(self, palette, index_call, grid_index, parent=None):
        super(Cell, self).__init__(parent=parent)

        self._index = 0
        self._cross = False
        self._complete = False
        self.index_call = index_call
        self.grid_index = grid_index
        self.color_palette = palette
        self.setFixedSize(self.SIZE, self.SIZE)
        self.fill_palettes = get_qt_palettes(self.color_palette)
        self.setPalette(self.fill_palettes[0])
        self.setAutoFillBackground(True)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.cross_pixmap = get_icon_pixmap('cross', QtGui.QColor(*palette.marking_color), size=self.SIZE - 4)
        self.setFrameShape(QtWidgets.QFrame.Shape.Box)

    def event(self, event):

        if event.type() == QtGui.QMouseEvent.Type.MouseButtonPress and not self._complete:
            if QtCore.Qt.MouseButton.LeftButton in event.buttons():
                self.index = self.index_call()
            elif QtCore.Qt.MouseButton.RightButton in event.buttons():
                self.cross = not self.cross

        return super(Cell, self).event(event)

    def paintEvent(self, event) -> None:

        if self._cross:
            painter = QtGui.QPainter(self)
            painter.drawPixmap(QtCore.QRect(2, 2, self.SIZE - 4, self.SIZE - 4), self.cross_pixmap)
        return super(Cell, self).paintEvent(event)

    def set_state(self, index, crossed):

        self._index = index
        self.setPalette(self.fill_palettes[self._index])
        self._cross = crossed
        self.update()

    def set_complete_state(self, complete):

        self._complete = complete
        if self._complete:
            self.cross = False
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame if self._complete else QtWidgets.QFrame.Shape.Box)

    @property
    def index(self):

        return self._index

    @index.setter
    def index(self, value):

        if not self._complete:
            self._index = 0 if self._index == value else value
            self.setPalette(self.fill_palettes[self._index])
            if self._index:
                self.cross = False

    @property
    def cross(self):

        return self._cross

    @cross.setter
    def cross(self, value):

        self._cross = value
        self.update()
        if value:
            self.index = 0


class CompleteDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(CompleteDialog, self).__init__(parent=parent)

        self.setWindowTitle('Puzzle Complete!')

        self.setLayout(QtWidgets.QVBoxLayout())
        complete_message = QtWidgets.QLabel('Congratulations you have completed the puzzle!')
        self.layout().addWidget(complete_message)
        close_button = QtWidgets.QPushButton('Yay')
        self.layout().addWidget(close_button)
        close_button.clicked.connect(self.close)


class NewGameDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(NewGameDialog, self).__init__(parent=parent)

        self.setWindowTitle('New Game')

        self.setLayout(QtWidgets.QVBoxLayout())
        main_label = QtWidgets.QLabel('Select options for your new game.')
        self.layout().addWidget(main_label)

        dimensions_label = QtWidgets.QLabel('Board Dimensions')
        create_container(self.layout(), (dimensions_label, None))
        row_label = QtWidgets.QLabel('Row:')
        self.row_spin = QtWidgets.QSpinBox()
        column_label = QtWidgets.QLabel('Column:')
        self.column_spin = QtWidgets.QSpinBox()
        for spin in (self.row_spin, self.column_spin):
            spin.setMinimum(5)
            spin.setMaximum(25)
            spin.setSingleStep(5)
            spin.setValue(5)
        create_container(self.layout(), (row_label, self.row_spin, column_label, self.column_spin, None))

        color_label = QtWidgets.QLabel('Colors:')
        self.color_spin = QtWidgets.QSpinBox()
        self.color_spin.setMinimum(1)
        self.color_spin.setMaximum(3)
        self.color_spin.setValue(1)
        create_container(self.layout(), (color_label, self.color_spin, None))

        start_button = QtWidgets.QPushButton('Start')
        start_button.setMinimumWidth(60)
        create_container(self.layout(), (None, start_button, None))

        start_button.clicked.connect(self.accept)

    def get_values(self):

        return (self.row_spin.value(), self.column_spin.value()), self.color_spin.value()


class PaletteCreator(QtWidgets.QDialog):
    MAX_COLORS = 5
    VALIDATOR = QtGui.QRegularExpressionValidator('^[a-zA-Z0-9_]*$')

    def __init__(self, starting_palette=None, name_field=False, parent=None):
        super(PaletteCreator, self).__init__(parent=parent)

        self.setWindowTitle('Create Palette')
        starting_palette = core.Palette() if starting_palette is None else starting_palette

        self.setLayout(QtWidgets.QVBoxLayout())
        self.main_label = QtWidgets.QLabel('Select colors to make up your palette.')
        self.layout().addWidget(self.main_label)
        self.layout().addWidget(get_divider(starting_palette))

        colors_label = QtWidgets.QLabel('Colors:')
        add_color_button = QtWidgets.QPushButton()
        add_color_button.setIcon(get_icon_pixmap('add', QtGui.QColor(30, 240, 30)))
        add_color_button.clicked.connect(self.add_color)
        subtract_color_button = QtWidgets.QPushButton()
        subtract_color_button.setIcon(get_icon_pixmap('subtract', QtGui.QColor(240, 30, 30)))
        subtract_color_button.clicked.connect(self.subtract_color)
        create_container(self.layout(), widgets=(colors_label, add_color_button, subtract_color_button))

        self.color_container, self.color_layout = create_container(self.layout(), widgets=(), horizontal=False)
        self.color_buttons = []
        self.add_color()

        if name_field:
            name_label = QtWidgets.QLabel('Palette Name:')
            self.name_edit = QtWidgets.QLineEdit('custom_palette_01')
            self.name_edit.setValidator(self.VALIDATOR)
            create_container(self.layout(), widgets=(name_label, self.name_edit))
        else:
            self.name_edit = None

        self.layout().addSpacing(10)
        supplementary_label = QtWidgets.QLabel('Supplementary Colors:')
        self.layout().addWidget(supplementary_label)
        self.secondary_color_buttons = {}
        for color_property in ('empty_color', 'background_color', 'marking_color'):
            button = ColorSwatchButton(color_property.replace('_', ' ').title(), getattr(starting_palette, color_property))
            self.secondary_color_buttons[color_property] = button
            self.layout().addWidget(button)

        self.layout().addStretch()

        self.save_button = QtWidgets.QPushButton('Save')
        self.save_button.clicked.connect(self.accept)
        cancel_button = QtWidgets.QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        create_container(self.layout(), widgets=(None, self.save_button, cancel_button, None))

    def add_color(self):

        color_count = len(self.color_buttons)
        if color_count < self.MAX_COLORS:
            self.color_buttons.append(ColorSwatchButton(f'Color {color_count + 1}'))
            self.color_layout.addWidget(self.color_buttons[-1])

    def subtract_color(self):

        color_count = len(self.color_buttons)
        if color_count > 1:
            self.color_layout.removeWidget(self.color_buttons[-1])
            self.color_buttons[-1].close()
            del self.color_buttons[-1]

    @property
    def name(self):

        if self.name_edit is None:
            return ''
        else:
            return self.name_edit.text().replace(' ', '_')

    @property
    def palette(self):

        new_palette = core.Palette([button.color_rgb for button in self.color_buttons])
        for property_name, button in self.secondary_color_buttons.items():
            setattr(new_palette, property_name, button.color_rgb)
        return new_palette


class CreatePuzzle(PaletteCreator):

    def __init__(self, parent=None):
        super(CreatePuzzle, self).__init__(name_field=False, parent=parent)

        self.setWindowTitle('Create Puzzle')
        self.main_label.setText('Set palette colors and choose the dimensions of your new puzzle.')
        self.save_button.setText('Create')

        dimensions_label = QtWidgets.QLabel('Board Dimensions')
        title_container, _ = create_container(None, (dimensions_label, None))
        self.layout().insertWidget(2, title_container)
        row_label = QtWidgets.QLabel('Row:')
        self.row_spin = QtWidgets.QSpinBox()
        column_label = QtWidgets.QLabel('Column:')
        self.column_spin = QtWidgets.QSpinBox()
        for spin in (self.row_spin, self.column_spin):
            spin.setMinimum(5)
            spin.setMaximum(25)
            spin.setSingleStep(5)
            spin.setValue(5)
        container, _ = create_container(None, widgets=(row_label, self.row_spin, column_label, self.column_spin, None))
        self.layout().insertWidget(3, container)

        self.layout().insertWidget(4, get_divider())

    @property
    def dimensions(self):

        return self.row_spin.value(), self.column_spin.value()


class ColorSwatchButton(QtWidgets.QPushButton):

    def __init__(self, label, color=(20, 20, 20), parent=None):
        super(ColorSwatchButton, self).__init__(parent=parent)

        self.setText(label)
        self.setAutoFillBackground(True)
        self.setFlat(True)
        palette = self.palette()
        palette.setColor(QtWidgets.QPushButton.backgroundRole(self), QtGui.QColor(*color))
        if sum(color) < 400:
            palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor('white'))
        self.setPalette(palette)

        self.clicked.connect(self.change_color)

    def change_color(self):

        color = QtWidgets.QColorDialog.getColor(self.color)
        if color.isValid():
            palette = self.palette()
            palette.setColor(QtWidgets.QPushButton.backgroundRole(self), color)
            if sum((color.red(), color.green(), color.blue())) < 400:
                palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor('white'))
            else:
                palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor('black'))
            self.setPalette(palette)

    @property
    def color(self):

        return self.palette().color(QtWidgets.QPushButton.backgroundRole(self))

    @property
    def color_rgb(self):

        color = self.color
        return color.red(), color.green(), color.blue()


class KeyBlock(QtWidgets.QFrame):
    PADDING = 6

    def __init__(self, length, palette, buffer_width=False, parent=None):
        super(KeyBlock, self).__init__(parent=parent)

        self.setFrameStyle(QtWidgets.QFrame.Shape.Box)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(str(length))
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        label_palette = QtGui.QPalette()
        label_palette.setColor(QtGui.QPalette.ColorRole.WindowText, get_readable_text_color(palette))
        label.setPalette(label_palette)
        self.layout().addWidget(label)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        if buffer_width:
            self.setMinimumWidth(label.sizeHint().width() + self.PADDING)


def get_icon_pixmap(name, color, size=Cell.SIZE):

    size = QtCore.QSize(size, size)
    icon = QtGui.QIcon(os.path.join(os.getcwd(), 'icons', f"{name}.svg"))
    pixmap = icon.pixmap(size)

    painter = QtGui.QPainter()
    painter.begin(pixmap)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.setBrush(color)
    painter.setPen(color)
    painter.fillRect(pixmap.rect(), color)
    painter.end()

    return pixmap


def get_qt_palettes(palette):

    background_color = QtGui.QColor(*palette.background_color)
    qt_palettes = [QtGui.QPalette()]
    qt_palettes[-1].setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(*palette.empty_color))
    qt_palettes[-1].setColor(QtGui.QPalette.ColorRole.WindowText, background_color)
    for color_rgb in palette.colors:
        qt_palettes.append(QtGui.QPalette())
        color = QtGui.QColor(*color_rgb)
        qt_palettes[-1].setColor(QtGui.QPalette.ColorRole.Window, color)
        qt_palettes[-1].setColor(QtGui.QPalette.ColorRole.WindowText, background_color)
        qt_palettes[-1].setColor(QtGui.QPalette.ColorRole.WindowText, background_color)

    return qt_palettes


def get_readable_text_color(palette):

    color = palette.color(QtGui.QPalette.ColorRole.Window)
    if sum((color.red(), color.green(), color.blue())) < 400:
        return QtGui.QColor('white')
    else:
        return QtGui.QColor('black')


def create_container(parent_layout, widgets, horizontal=True):

    container = QtWidgets.QWidget()
    if parent_layout is not None:
        parent_layout.addWidget(container)
    layout = QtWidgets.QHBoxLayout() if horizontal else QtWidgets.QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    container.setLayout(layout)

    for widget in widgets:
        if widget is None:
            layout.addStretch()
        elif isinstance(widget, int):
            layout.addSpacing(widget)
        else:
            layout.addWidget(widget)

    return container, layout


def get_divider(palette=None, horizontal=True):

    divider = QtWidgets.QWidget()
    divider.setAutoFillBackground(True)
    if horizontal:
        divider.setFixedHeight(2)
    else:
        divider.setFixedWidth(2)
    empty_palette = QtGui.QPalette()
    palette = core.Palette() if palette is None else palette
    empty_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(*palette.marking_color))
    divider.setPalette(empty_palette)

    return divider
