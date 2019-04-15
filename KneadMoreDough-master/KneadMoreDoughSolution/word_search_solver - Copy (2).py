import json
from collections import namedtuple
import typing
import enum
import math
from sys import float_info

Position = namedtuple('Position', ['row', 'col'])

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

    def __rsub__(self, other):
        return self.__class__(*(other[i] - self[i] for i in range(len(self))))

    def __sub__(self, other):
        return self + (-other)

    def sign(self):
        for x in self:
            if x > 0:
                return 1
            elif x < 0:
                return -1
        return 0

    def angle(self):
        if self.row == self.col and self.row == 0:
            return 0
        x = self.row
        y = self.col
        return round(math.degrees(math.atan2(y, x)))

    def magnitude(self):
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

    def is_horizontal(self):
        return all(self[i] == 0 for i in range(len(self)) if i != 1)

    def is_vertical(self):
        return all(self[i] == 0 for i in range(len(self)) if i != 0)

    def rotate(self, rotation_angle):
        return self.__class__.from_polar(
            self.magnitude(), self.angle()+rotation_angle)

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
    def __init__(self, letters):
        self._letters = letters
        self._bound = len(letters) - 1
        self._adjacents: typing.Dict[tuple, Adjacent] = {}

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
            self._pos += self._dir
            return self
        else:
            return self.exit_face()

    def leaving_bounds(self):
        return [i for i in range(len(self._pos)) 
                    if (not 0 <= self._pos[i] + self._dir[i] <= self._bound) ]

    def _exit_face_normal(self):
        transition = self._adjacents[self._dir]

        if self._dir.is_vertical():
            index = self._pos.col
        elif self._dir.is_horizontal():
            index = self._pos.row
        
        if self._dir.sign() != -transition.side.sign():
            index = self._bound - index

        if transition.side.is_vertical():
            new_r = ((transition.side[0] + 1)//2) * self._bound
            new_c = index
        elif transition.side.is_horizontal():
            new_c = ((transition.side[1] + 1)//2) * self._bound
            new_r = index

        new_face: CubeFace = transition.face
        new_face.start(new_r, new_c, -(transition.side))
        return new_face

    def _exit_face_diagonal(self):
        if len(self.leaving_bounds()) > 1:
            raise Exception('Ambiguous corner')
        
        # the index of the out of bound dimension. 0 = row, 1 = col
        i = self.leaving_bounds()[0]
        
        exit_edge = GridVector.zeroes(2).set(i, self._dir[i])

        # exit position vector. one dimension of this will be invalid at the moment.
        exit_index = self._pos[1-i]

        new_face: CubeFace = self._adjacents[exit_edge].face
        new_side: GridVector = self._adjacents[exit_edge].side

        new_dir: GridVector = self._dir.rotate(
            (-new_side).angle() - exit_edge.angle()).round()

        new_index = exit_index
        if self._dir.sign() != -new_side.sign():
            new_index = self._bound - exit_index
        
        new_pos = [None, None]
        # [row, col]
        new_pos[i] = (new_side[new_side.dim()]+1)//2*self._bound
        new_pos[1-i] = new_index

        print('We have arrived on', new_face, 'at', GridVector(*new_pos), 'facing', new_dir)

        return new_face.start(GridVector(*new_pos), new_dir)

    def exit_face(self):
        return self._exit_face_diagonal()

    def __str__(self):
        return 'CubeFace('+str(self._letters)+')'

    def __repr__(self):
        return 'CubeFace('+repr(self._letters)+')'

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
        faces.append(CubeFace(lines[:size]))
        middle = [ [l[i:i+size] for i in range(0, len(l), size)] for l in lines[size:2*size] ]
        for i in range(len(middle[0])):
            faces.append(CubeFace([middle[j][i] for j in range(len(middle))]))
        faces.append(CubeFace(lines[2*size:3*size]))
        self._faces = faces
        self._set_cube_adjacents()
        faces[2].start(GridVector(0, 2), UP+LEFT).move_one()
        print(faces)

    def find_words(self, words):
        self._words = words
        for word in self._words:
            #print('Searching for', word)
            for face, start in self._find_letter(word[0]):
                #print(' Testing for', word, 'on', self._face_str(face), 'at', start.as_pair())
                self._test_starting_pos(word, face, GridVector(*start))

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
        for direction in (UP, DOWN, LEFT, RIGHT):
            #if True:
            for move_name, move_func in {'NORMAL': self._move_normal, 'DIAGONAL': self._move_diag_left}.items():
                #print('    '+str(start), str(direction), move_name, end='... ')
                current = face.start(start, direction)
                matched = True
                for i, letter in enumerate(word):
                    if i == 0: 
                        continue
                    current = move_func(current)
                    if current.get() != letter:
                        matched = False
                        break
                #print('"' + word[:(i)] + '" found')
                if matched:
                    print('''MATCH:
    word: {word}
    start: {n}, {start}
    direction: {direction}
    move: {move_name}
    compass: {c}
    grid: {grid}'''.format(
        word=word, face=face, start=start, 
        direction=direction, move_name=move_name, n=self._face_str(face),
        c=direction.as_compass(move_name != 'NORMAL'), grid=self._face_to_rowcol(face, *start)))
                    print()

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


def main():
    with open('puzzles.json') as f:
        decoder = json.decoder.JSONDecoder()
        puzzles = decoder.decode(f.read())
    words_no_s = [
        "Anchovy",
        "Bacon",
        "Cheese",
        "Garlic",
        "GreenPepper",
        "Habenero",
        "Jalapeno",
        "Mushroom",
        "Olive",
        "Onion",
        "Pineapple",
        "Pepperoni",
        "Sausage",
        "Tomato"
    ]
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
    w = WordCubeSolver(5)

    # 11: edge case
    puzzle = puzzles[2]['Puzzle']['Lines']
    puzzle = [p.replace(' ', '') for p in puzzle]
    print('PUZZLE:\n')
    for line in puzzle:
        print(line)
    print()

    w.create_cube(puzzle)
    w.find_words(words)

if __name__ == '__main__':
    main()
