import itertools
from collections.abc import Sequence

import pytest

from musiclib import config
from musiclib.interval import AbstractInterval
from musiclib.note import Note
from musiclib.note import SpecificNote
from musiclib.noteset import NoteSet
from musiclib.scale import Scale


def test_empty():
    NoteSet(frozenset())


@pytest.mark.parametrize(
    ('string', 'expected'), [
        ('CDEFGAB', NoteSet(frozenset(map(Note, 'CDEFGAB')))),
        ('CdeFGab', NoteSet(frozenset(map(Note, 'CdeFGab')))),
        ('CEG', NoteSet(frozenset(map(Note, 'CEG')))),
        ('fa', NoteSet(frozenset(map(Note, 'fa')))),
        ('', NoteSet(frozenset())),
    ],
)
def test_from_str(string, expected):
    assert NoteSet.from_str(string) is expected


@pytest.mark.parametrize(
    ('x', 's', 'r'), [
        (NoteSet.from_str('CEG'), 'CEG', "NoteSet('CEG')"),
    ],
)
def test_str_repr(x, s, r):
    assert str(x) == s
    assert repr(x) == r


@pytest.mark.parametrize(
    ('string', 'expected'), [
        ('fa', {Note('f'): frozenset(map(AbstractInterval, {0, 2})), Note('a'): frozenset(map(AbstractInterval, {0, 10}))}),
        ('', {}),
    ],
)
def test_note_to_intervals(string, expected):
    assert NoteSet.from_str(string).note_to_intervals == expected


@pytest.mark.parametrize(
    'value', [
        'CDE',
        set(map(Note, 'CDE')),
        tuple(map(Note, 'CDE')),
        list(map(Note, 'CDE')),
    ],
)
def test_notes_type_is_frozenset(value):
    with pytest.raises(TypeError):
        NoteSet(value)


def test_contains():
    assert Note('C') in NoteSet.from_str('C')
    assert Note('C') not in NoteSet.from_str('D')
    assert NoteSet.from_str('CD') <= NoteSet.from_str('CDE')
    assert NoteSet.from_str('CDE') <= NoteSet.from_str('CDE')
    assert NoteSet.from_str('CDEF') > NoteSet.from_str('CDE')
    assert NoteSet.from_str('CDE') < NoteSet.from_str('CDEF')
    empty_noteset = NoteSet(frozenset())
    assert Note('C') not in empty_noteset
    assert empty_noteset <= NoteSet.from_str('CDE')
    with pytest.raises(TypeError):
        assert SpecificNote('C', 1) in NoteSet.from_str('CDE')


def test_note_i():
    fs = frozenset(map(Note, 'CDEfGaB'))
    noteset = NoteSet(fs)
    assert fs == noteset._note_i.keys()
    assert noteset._note_i[Note('C')] == 0
    assert noteset._note_i[Note('B')] == 6
    assert noteset._note_i[Note('f')] == 3
    assert noteset._note_i[Note('G')] == 4
    assert NoteSet(frozenset())._note_i == {}


@pytest.mark.parametrize(
    ('noteset', 'note', 'steps', 'result'), [
        (NoteSet.from_str('CDEFGAB'), Note('C'), 3, Note('F')),
        (NoteSet.from_str('CDEFGAB'), Note('C'), -2, Note('A')),
        (NoteSet.from_str('DEFGAbC'), Note('A'), 1, Note('b')),
        (NoteSet.from_str('DEFGAbC'), Note('A'), 0, Note('A')),
        (NoteSet.from_str('CEG'), Note('C'), 1, Note('E')),
        (NoteSet.from_str('CEG'), Note('C'), 2, Note('G')),
        (NoteSet.from_str('CEG'), Note('C'), 3, Note('C')),
        (NoteSet.from_str('CeGb'), Note('e'), 2, Note('b')),
        (NoteSet.from_str('CeGb'), Note('e'), 25, Note('G')),
        (NoteSet.from_str('CEG'), Note('C'), -1, Note('G')),
        (NoteSet.from_str('CEG'), Note('C'), -2, Note('E')),
        (NoteSet.from_str('CEG'), Note('C'), -3, Note('C')),
        (NoteSet.from_str('CeGb'), Note('e'), -15, Note('G')),
    ],
)
def test_add_note_abstract(noteset, note, steps, result):
    assert noteset.add_note(note, steps) == result


@pytest.mark.parametrize(
    ('noteset', 'note', 'steps'), [
        (NoteSet(frozenset()), 'A', 1),
        (NoteSet(frozenset()), 'A1', 1),
    ],
)
def test_add_note_empty_noteset(noteset, note, steps):
    with pytest.raises(NotImplementedError):
        noteset.add_note(note, steps)


def _make_keyboard(notes: Sequence[Note], octaves: Sequence[int]) -> tuple[SpecificNote, ...]:
    return tuple(sorted(SpecificNote(note, octave) for octave, note in itertools.product(octaves, notes)))


def _add_note_specific_generator():
    natural = [Scale.from_name(root, name) for root, name in itertools.product(config.chromatic_notes, config.scale_order['natural'])]
    notesets = [NoteSet.from_str('CDEFGAB'), NoteSet.from_str('DEFGAbC')]
    notesets += [s.noteset for s in natural]
    notesets += [
        Scale.from_name('C', 'h_minor_1').noteset,
        Scale.from_name('C', 'h_major_1').noteset,
        Scale.from_name('E', 'h_minor_1').noteset,
        Scale.from_name('d', 'm_minor_1').noteset,
        Scale.from_name('b', 'p_minor').noteset,
    ]
    for noteset in notesets:
        yield pytest.param(noteset, id=f'NoteSet({noteset})')


@pytest.mark.parametrize('noteset', _add_note_specific_generator())
def test_add_note_specific(noteset):
    keyboard = _make_keyboard(notes=noteset.notes_ascending, octaves=range(-10, 10))
    for _note, octave, steps in itertools.product(
        [noteset.notes_ascending[0], noteset.notes_ascending[1], noteset.notes_ascending[2], noteset.notes_ascending[-1]],
        [-2, -1, 0, 1, 2],
        [-29, -13, -8, -7, -6, -2, -1, 0, 1, 2, 6, 7, 8, 13, 29],
    ):
        note = SpecificNote(_note, octave)
        result = keyboard[keyboard.index(note) + steps]
        assert noteset.add_note(note, steps) == result


@pytest.mark.parametrize(
    ('notes', 'left', 'right', 'distance'), [
        ('CDEFGAB', Note('E'), Note('C'), 2),
        ('CDEFGAB', Note('C'), Note('E'), 5),
        ('CDEFGAB', Note('B'), Note('C'), 6),
        ('CDEFGAB', Note('C'), Note('C'), 0),
        ('CDEFGAB', Note('E'), Note('A'), 4),
        ('CDE', Note('D'), Note('D'), 0),
        ('CDE', Note('E'), Note('D'), 1),
        ('CDE', Note('E'), Note('C'), 2),
        ('CDE', Note('C'), Note('D'), 2),
        ('CDE', Note('C'), Note('E'), 1),
        ('ab', Note('a'), Note('a'), 0),
        ('ab', Note('a'), Note('b'), 1),
        ('ab', Note('b'), Note('a'), 1),
        ('f', Note('f'), Note('f'), 0),
        ('CdDeEFfGaAbB', Note('b'), Note('b'), 0),
        ('CdDeEFfGaAbB', Note('G'), Note('C'), 7),
        ('CdDeEFfGaAbB', Note('C'), Note('d'), 11),
        ('CdDeEFfGaAbB', Note('C'), Note('G'), 5),

        ('CDEFGAB', SpecificNote('E', 1), SpecificNote('C', 1), 2),
        ('CDEFGAB', SpecificNote('E', 3), SpecificNote('C', 1), 16),
        ('CDEFGAB', SpecificNote('C', 1), SpecificNote('E', 3), -16),
        ('CDEFGAB', SpecificNote('C', 2), SpecificNote('E', -1), 19),
        ('CDEFGAB', SpecificNote('E', -1), SpecificNote('C', 2), -19),
        ('CDEFGAB', SpecificNote('C', 2), SpecificNote('E', -3), 33),
        ('CDEFGAB', SpecificNote('E', -3), SpecificNote('C', 2), -33),
        ('CDEFGAB', SpecificNote('C', -2), SpecificNote('E', -3), 5),
        ('CDEFGAB', SpecificNote('E', -3), SpecificNote('C', -2), -5),
        ('CDEFGAB', SpecificNote('B', 1), SpecificNote('C', 1), 6),
        ('CDEFGAB', SpecificNote('C', 1), SpecificNote('B', 1), -6),
        ('CDEFGAB', SpecificNote('B', 10), SpecificNote('C', 1), 69),
        ('CDEFGAB', SpecificNote('C', 1), SpecificNote('B', 10), -69),
        ('CDEFGAB', SpecificNote('C', 0), SpecificNote('C', 0), 0),
        ('CDEFGAB', SpecificNote('F', 34), SpecificNote('F', 34), 0),
        ('CDEFGAB', SpecificNote('E', 4), SpecificNote('A', 2), 11),
        ('CDEFGAB', SpecificNote('A', 2), SpecificNote('E', 4), -11),
        ('CDE', SpecificNote('D', 2), SpecificNote('D', 2), 0),
        ('CDE', SpecificNote('D', 2), SpecificNote('D', 3), -3),
        ('CDE', SpecificNote('E', 5), SpecificNote('D', 4), 4),
        ('CDE', SpecificNote('D', 4), SpecificNote('E', 5), -4),
        ('CDE', SpecificNote('E', 5), SpecificNote('C', 4), 5),
        ('CDE', SpecificNote('C', 4), SpecificNote('E', 5), -5),
        ('ab', SpecificNote('a', 3), SpecificNote('a', 3), 0),
        ('ab', SpecificNote('b', 3), SpecificNote('a', 3), 1),
        ('ab', SpecificNote('a', 3), SpecificNote('b', 3), -1),
        ('ab', SpecificNote('b', 4), SpecificNote('a', 3), 3),
        ('ab', SpecificNote('a', 3), SpecificNote('b', 4), -3),
        ('f', SpecificNote('f', 0), SpecificNote('f', 0), 0),
        ('f', SpecificNote('f', 1), SpecificNote('f', 0), 1),
        ('f', SpecificNote('f', 0), SpecificNote('f', 1), -1),
        ('f', SpecificNote('f', 2), SpecificNote('f', 0), 2),
        ('f', SpecificNote('f', 0), SpecificNote('f', 2), -2),
        ('f', SpecificNote('f', 40), SpecificNote('f', 1), 39),
        ('f', SpecificNote('f', 1), SpecificNote('f', 40), -39),
        ('f', SpecificNote('f', 1), SpecificNote('f', -2), 3),
        ('f', SpecificNote('f', -2), SpecificNote('f', 1), -3),
        ('f', SpecificNote('f', -4), SpecificNote('f', -7), 3),
        ('f', SpecificNote('f', -7), SpecificNote('f', -4), -3),
        ('CdDeEFfGaAbB', SpecificNote('b', 2), SpecificNote('b', 2), 0),
        ('CdDeEFfGaAbB', SpecificNote('G', 5), SpecificNote('C', 3), 31),
        ('CdDeEFfGaAbB', SpecificNote('C', 3), SpecificNote('G', 5), -31),
        ('CdDeEFfGaAbB', SpecificNote('C', 2), SpecificNote('d', -1), 35),
        ('CdDeEFfGaAbB', SpecificNote('d', -1), SpecificNote('C', 2), -35),
        ('CdDeEFfGaAbB', SpecificNote('C', -2), SpecificNote('C', -3), 12),
        ('CdDeEFfGaAbB', SpecificNote('C', -3), SpecificNote('C', -2), -12),
        ('CdDeEFfGaAbB', SpecificNote('C', -3), SpecificNote('C', -8), 60),
        ('CdDeEFfGaAbB', SpecificNote('C', -8), SpecificNote('C', -3), -60),
        ('CdDeEFfGaAbB', SpecificNote('d', -3), SpecificNote('G', -8), 54),
        ('CdDeEFfGaAbB', SpecificNote('G', -8), SpecificNote('d', -3), -54),
    ],
)
def test_subtract(notes, left, right, distance):
    assert NoteSet.from_str(notes).subtract(left, right) == distance


def test_subtract_types():
    noteset = NoteSet.from_str('CDEFGAB')
    with pytest.raises(TypeError):
        noteset.subtract(Note('C'), SpecificNote('D', 1))
    with pytest.raises(TypeError):
        noteset.subtract(SpecificNote('D', 1), Note('C'))
    with pytest.raises(TypeError):
        noteset.subtract('C', SpecificNote('D', 1))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        noteset.subtract('D1', Note('C'))  # type: ignore[arg-type]
