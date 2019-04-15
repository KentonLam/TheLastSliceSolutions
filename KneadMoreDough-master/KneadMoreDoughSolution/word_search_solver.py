import json
from collections import namedtuple
import typing
import enum
import math
from sys import float_info
import os
import urllib.request

Position = namedtuple('Position', ['row', 'col'])

def _print(*args, **kwargs):
    return
    print(*args, **kwargs)

class _Pair(typing.NamedTuple):
    row: float
    col: float

def _sign(number):
    if number > float_info.epsilon:
        return 1
    elif number < -float_info.epsilon:
        return -1
    return 0

class GridVector(_Pair):
    _names = {
        (0, -1): 'LEFT',
        (0, 1): 'RIGHT',
        (1, 0): 'DOWN',
        (-1, 0): 'UP'
    }

    _compass_names = {
        (0, -1): 'W',
        (0, 1): 'E',
        (1, 0): 'S',
        (-1, 0): 'N',
    }

    def __neg__(self):
        return self.__class__(*(-x for x in self))

    def __add__(self, other):
        assert len(self) == len(other)
        return self.__class__(*(self[i] + other[i] for i in range(len(self))))

    def __sub__(self, other):
        return self + (-other)

    def sign(self):
        for x in self:
            if x > 0:
                return 1
            elif x < 0:
                return -1
        return 0

    # 0 is DOWN, and positive is ccw.
    def angle(self):
        if self.row == self.col and self.row == 0:
            return 0
        x = self.row
        y = self.col
        return round(math.degrees(math.atan2(y, x)))

    def mag(self):
        return math.sqrt(sum(x**2 for x in self))

    def dim(self):
        dim = None
        for i, x in enumerate(self):
            if x != 0:
                if dim is None:
                    dim = i
                else:
                    raise ValueError('Multi-dimensional vector.')
        if dim is None:
            raise ValueError('Zero vector.')
        return dim

    def round(self):
        return self.__class__(*(round(x) for x in self))

    @classmethod
    def from_polar(cls, magnitude, angle): 
        theta = math.radians(angle)
        return cls(magnitude*math.cos(theta), magnitude*math.sin(theta))

    def rotate(self, rotation_angle):
        return self.__class__.from_polar(
            self.mag(), self.angle()+rotation_angle)

    def rotate_ccw(self):
        return self.rotate(90)

    def rotate_cw(self):
        return self.rotate(-90)

    def set(self, index, value):
        return self.__class__(*(x if i != index else value for i, x in enumerate(self)))

    def as_compass(self, diagonal_left=False):
        if all(x != 0 for x in self):
            return self._compass_names[self[0], 0] + self._compass_names[0, self[1]]
        else:
            return self._compass_names[tuple(self)]
    
    def _get_compass_name(self):
        return self._compass_names[tuple(self)]

    def as_pair(self):
        return repr(self)

    def __str__(self):
        try:
            s = []
            z = self.zeroes(len(self))
            for i, x in enumerate(self):
                if x != 0:
                    s.append(self._names[tuple(z.set(i, x))])
            if s:
                return '+'.join(s)
            else:
                return self.__class__.__name__ + '.zeroes(' + str(len(self)) + ')'
        except KeyError:
            return super().__repr__()
            #return self.__class__.__name__ +'('+ ', '.join(tuple(self)) + ')'

    @classmethod
    def zeroes(cls, dimension):
        return cls(*(dimension*(0, )))

P = GridVector

DOWN = P(1, 0)
RIGHT = P(0, 1)
UP = P(-1, 0)
LEFT = P(0, -1)
repr(UP+DOWN)

DOWN_RIGHT = DOWN + RIGHT
UP_RIGHT = UP + RIGHT
DOWN_LEFT = DOWN + LEFT
UP_LEFT = UP + LEFT

class Adjacent(typing.NamedTuple):
    face: 'CubeFace'
    side: GridVector

class CubeFace:
    def __init__(self, letters, number=None):
        self._letters = letters
        self._bound = len(letters) - 1
        self._adjacents: typing.Dict[tuple, Adjacent] = {}
        self._number = number

    def has_adj(self, direction):
        return direction in self._adjacents

    def set_one_adj(self, direction, adj):
        self._adjacents[direction] = adj
        if not adj.face.has_adj(adj.side):
            adj.face.set_one_adj(adj.side, Adjacent(self, direction))

    def set_many_adj(self, adj_dict):
        for k, v in adj_dict.items():
            self.set_one_adj(k, v)

    def start(self, start_vector, direction_vector):
        self._pos = start_vector

        self._dir = direction_vector
        return self

    def get(self):
        current = self._letters
        for x in self._pos:
            current = current[x]
        return current

    def rotate_cw(self):
        self._dir = self._dir.rotate_cw().round()
        return self

    def rotate_ccw(self):
        self._dir = self._dir.rotate_ccw().round()
        return self

    def move_one(self):
        if not self.leaving_bounds():
            _print('Normal transition from', repr(self._pos), 'to', repr(self._pos + self._dir))
            self._pos += self._dir
            return self
        else:
            return self.exit_face()

    def leaving_bounds(self):
        return [i for i in range(len(self._pos)) 
                    if (not 0 <= self._pos[i] + self._dir[i] <= self._bound) ]

    def _exit_face_diagonal(self):
        if len(self.leaving_bounds()) > 1:
            raise Exception('Ambiguous corner')
        
        # the index of the out of bound dimension. 0 = row, 1 = col
        i = self.leaving_bounds()[0]
        
        exit_side = GridVector.zeroes(2).set(i, self._dir[i])

        # exit position vector. one dimension of this will be invalid at the moment.
        exit_index = self._pos[1-i]

        new_face: CubeFace = self._adjacents[exit_side].face
        new_side: GridVector = self._adjacents[exit_side].side

        new_dir: GridVector = self._dir.rotate(
            (-new_side).angle() - exit_side.angle()).round()

        new_index = exit_index
        # if the signs of the 90 degree ccw rotations are equal, we need to 
        # invert the index.
        if exit_side.rotate(90).round().sign() == new_side.rotate(90).round().sign():
            new_index = self._bound - new_index
        
        new_pair = [None, None]
        # [row, col]
        new_pair[i] = (new_side[new_side.dim()]+1)//2*self._bound
        new_pair[1-i] = new_index

        if new_side.dim() != i:
            new_pair = new_pair[::-1]

        new_pos = GridVector(*new_pair) + new_dir + new_side

        _print('Diagonal edge transition in dimension', self.leaving_bounds())
        _print('  Previously on', self, 'at', repr(self._pos), 'facing', self._dir)
        _print('  Moved onto', new_face, 'at', repr(new_pos), 'facing', new_dir)

        return new_face.start(new_pos, new_dir)

    def exit_face(self):
        return self._exit_face_diagonal()

    def __str__(self):
        return repr(self)

    def __repr__(self):
        number_str = ''
        if self._number is not None:
            number_str = ', number=' + str(self._number)
        return 'CubeFace('+repr(self._letters)+number_str+')'

class WordCubeSolver:

    def __init__(self, cube_length=5):
        self._length = cube_length

    def create_cube(self, lines):
        self._lines = lines
        # 0
        # 1 2 3 4
        # 5
        
        faces = []
        size = self._length
        faces.append(CubeFace(lines[:size], 0))
        middle = [ [l[i:i+size] for i in range(0, len(l), size)] for l in lines[size:2*size] ]
        for i in range(len(middle[0])):
            faces.append(CubeFace([middle[j][i] for j in range(len(middle))], 1+i))
        faces.append(CubeFace(lines[2*size:3*size], 5))
        self._faces = faces
        self._set_cube_adjacents()
        '''f = faces[2].start(GridVector(0, 1), UP)
        while True:
            f = f.move_one()'''
        _print(faces)

    def find_words(self, words):
        self._words = words
        self._matches = []
        for word in self._words:
            _print('Searching for', word)
            for face, start in self._find_letter(word[0]):
                #print(' Testing for', word, 'on', self._face_str(face), 'at', start.as_pair())
                self._test_starting_pos(word, face, GridVector(*start))
        return self._matches

    def _set_cube_adjacents(self):
        faces = self._faces
        faces[1].set_many_adj({
            UP: Adjacent(faces[0], DOWN),
            LEFT: Adjacent(faces[4], RIGHT),
            RIGHT: Adjacent(faces[2], LEFT),
            DOWN: Adjacent(faces[5], UP)
        })

        faces[2].set_many_adj({
            UP: Adjacent(faces[0], RIGHT),
            RIGHT: Adjacent(faces[3], LEFT),
            DOWN: Adjacent(faces[5], RIGHT)
        })

        faces[3].set_many_adj({
            UP: Adjacent(faces[0], UP),
            DOWN: Adjacent(faces[5], DOWN),
            RIGHT: Adjacent(faces[4], LEFT)
        })

        faces[4].set_many_adj({
            UP: Adjacent(faces[0], LEFT),
            DOWN: Adjacent(faces[5], LEFT)
        })

    def _move_normal(self, face: CubeFace) -> CubeFace:
        return face.move_one()

    def _move_diag_left(self, face: CubeFace) -> CubeFace:
        return face.rotate_ccw().move_one().rotate_cw().move_one()

    def _test_starting_pos(self, word: str, face: CubeFace, start: GridVector):
        for direction in (UP, DOWN, LEFT, RIGHT, UP+LEFT, UP+RIGHT, DOWN+LEFT, DOWN+RIGHT):
            if True:
                #print('\nTesting direction', direction)
                move_name = '-'
                #for move_name, move_func in {'NORMAL': self._move_normal, 'DIAGONAL': self._move_diag_left}.items():
                #_print('    '+str(start), str(direction), move_name, end='... ')
                current = face.start(start, direction)
                matched = True
                for i, letter in enumerate(word):
                    if i == 0: 
                        continue
                    try:
                        current = current.move_one()
                    except Exception:
                        matched = False
                        break
                    if current.get() != letter:
                        matched = False
                        break
                #_print('"' + word[:(i)] + '" found')
                if matched:
                    _print('''MATCH:
    word: {word}
    start: {n}, {start}
    direction: {direction}
    compass: {c}
    grid: {grid}'''.format(
        word=word, face=face, start=repr(start), 
        direction=direction, n=self._face_str(face),
        c=direction.as_compass(), grid=self._face_to_rowcol(face, *start)))
                    _print()
                    self._matches.append(FoundWord(word=word, start_face=face,
                        start_pos=start, grid_pos=self._face_to_rowcol(face, *start),
                        direction=direction))

    def _face_str(self, face: CubeFace):
        return 'Faces['+str(self._faces.index(face))+']'

    def _rowcol_to_face(self, row, col):
        if row < self._length:
            face = self._faces[0]
        elif row >= self._length*2:
            face = self._faces[5]
        else:
            face = self._faces[1 + col//self._length]

        r = row % self._length
        c = col % self._length
        return (face, GridVector(r, c))

    def _face_to_rowcol(self, face, r, c):
        if not isinstance(face, int):
            face = self._faces.index(face)
        
        row, col = r, c
        if face >= 5:
            row += 10
        elif face >= 1:
            row += 5
        
        if 2 <= face <= 4:
            col += (face-1)*self._length

        return (row, col)

    def _find_letter(self, target):
        out = []

        for row, row_text in enumerate(self._lines):
            for col, letter in enumerate(row_text):
                if target == letter:
                    out.append(self._rowcol_to_face(row, col))
        return out

        concat = ''.join(self._lines)
        size = self._length
        faces = self._faces

        indexes = [i for i, c in enumerate(concat) if c == letter]
        for i in indexes:
            if i <= size**2:
                out.append((faces[0], (i // size, i % size) ))
            elif i <= 5*size**2:
                n = 1+(i-size**2)%(4*size)//size
                out.append((faces[n], ( (i-size**2)//(4*size), i % size )))
            else:
                out.append((faces[5], ((i-5*size**2)//size, i % size) ))
        return out

class FoundWord(typing.NamedTuple):
    word: str
    start_face: CubeFace
    start_pos: GridVector
    grid_pos: tuple
    direction: GridVector

def test_main():

    with open('puzzles2.json') as f:
        decoder = json.decoder.JSONDecoder()
        puzzles = decoder.decode(f.read())
    words_with_s = [
        "Anchovy",
        "Bacon",
        "Cheese",
        "Garlic",
        "GreenPeppers",
        "Habenero",
        "Jalapenos",
        "Mushrooms",
        "Olives",
        "Onions",
        "Pineapple",
        "Pepperoni",
        "Sausage",
        "Tomatoes"
    ]
    words = words_with_s
    words = [x.upper() for x in words]
    w = WordCubeSolver(5)

    # 11: edge case
    for i, puzzle_object in enumerate(puzzles):
        puzzle = puzzle_object['Puzzle']['Lines']
        puzzle = [p.replace(' ', '') for p in puzzle]
        print('Solving puzzle {} of {}: '.format(i+1, len(puzzles)) + puzzle_object['Id'])
        for line in puzzle:
            print(line)
        print()

        w.create_cube(puzzle)
        matches = w.find_words(words)

        found_words = set(x.word for x in matches)
        assert found_words == {'JALAPENOS', 'MUSHROOMS', 'PEPPERONI', 'SAUSAGE'}

    print('No errors.')

def challenge_main():
    puzzle_input = json.decoder.JSONDecoder().decode(input('Enter puzzle: '))
    words_with_s = [
        "Anchovy",
        "Bacon",
        "Cheese",
        "Garlic",
        "GreenPeppers",
        "Habenero",
        "Jalapeno",
        "Mushrooms",
        "Olives",
        "Onions",
        "Pineapple",
        "Pepperoni",
        "Sausage",
        "Tomatoes"
    ]
    words = words_with_s
    words = [x.upper() for x in words]
    solver = WordCubeSolver(5)
    solver.create_cube([l.replace(' ', '') for l in puzzle_input['Puzzle']['Lines']])
    found_words: typing.List[FoundWord] = solver.find_words(words)

    response = {
        'PuzzleId': puzzle_input['Id'],
        'Initials': 'KYL',
        'Words': []
    }

    for found in found_words:
        response['Words'].append({
            'word': found.word,
            'x': found.grid_pos[1],
            'y': found.grid_pos[0],
            'direction': found.direction.as_compass()
        })
    
    print()
    print()
    print(json.encoder.JSONEncoder(indent=None).encode(response))

if __name__ == '__main__':
    test_main()
