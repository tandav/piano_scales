import operator

import hypothesis.strategies as st
import pytest
from hypothesis import given

from musiclib.interval import AbstractInterval
from musiclib.note import Note
from musiclib.note import SpecificNote


@pytest.mark.parametrize(
    ('i', 'expected'), [
        (0, 'C'),
        (12, 'C'),
        (1, 'd'),
        (13, 'd'),
        (-1, 'B'),
        (-28, 'a'),
    ],
)
def test_from_i(i, expected):
    assert Note.from_i(i) == expected


def test_note_exists():
    with pytest.raises(KeyError):
        Note('Q')
    with pytest.raises(KeyError):
        Note('1')


@pytest.mark.parametrize(
    ('x', 's', 'r'), [
        (Note('C'), 'C', "Note('C')"),
        (SpecificNote('C', 1), 'C1', "SpecificNote('C', 1)"),
    ],
)
def test_str_repr(x, s, r):
    assert str(x) == s
    assert repr(x) == r


@pytest.mark.parametrize(
    ('op', 'a', 'b'), [
        (operator.eq, Note('C'), 'C'),
        (operator.eq, Note('C'), Note('C')),
        (operator.ne, Note('C'), 'D'),
        (operator.ne, Note('C'), Note('D')),
        (operator.lt, Note('C'), 'D'),
        (operator.lt, Note('C'), Note('D')),
        (operator.gt, Note('D'), Note('d')),
        (operator.gt, Note('B'), Note('f')),
        (operator.ne, Note('C'), 1),
        (operator.ne, Note('C'), SpecificNote.from_str('C1')),
        (operator.ne, SpecificNote.from_str('C1'), Note('C')),
        (operator.ne, SpecificNote.from_str('C1'), 'C1'),
    ],
)
def test_ordering(op, a, b):
    assert op(a, b)


def test_ordering_lt():
    assert not Note('C') < Note('C')
    assert not Note('C') > Note('C')
    assert Note('C') <= Note('C')
    assert Note('C') >= Note('C')


def test_note_sub():
    assert Note('C') - Note('C') == AbstractInterval(0)
    assert Note('G') - Note('C') == AbstractInterval(7)
    assert Note('C') - Note('G') == AbstractInterval(5)
    assert Note('G') - 7 == Note('C')
    assert Note('G') - AbstractInterval(7) == Note('C')
    assert Note('C') - 5 == Note('G')
    assert Note('C') - AbstractInterval(5) == Note('G')


@given(st.integers())
def test_specific_note_from_i(i):
    assert SpecificNote.from_i(i).i == i


@pytest.mark.parametrize(
    ('string', 'expected'), [
        ('F1', SpecificNote('F', 1)),
        ('C4', SpecificNote('C', 4)),
        ('C10', SpecificNote('C', 10)),
        ('d456', SpecificNote('d', 456)),
        ('d-456', SpecificNote('d', -456)),
    ],
)
def test_from_str(string, expected):
    assert SpecificNote.from_str(string) == expected


@pytest.mark.parametrize(
    ('note', 'steps', 'expected'), [
        (Note('C'), 4, Note('E')),
        (Note('C'), 15, Note('e')),
        (Note('B'), 2, Note('d')),
        (Note('D'), -2, Note('C')),
        (Note('d'), -2, Note('B')),
    ],
)
def test_note_add(note, steps, expected):
    assert note + steps == expected


@given(st.integers(), st.integers())
def test_specific_note_add(i, to_add):
    note = SpecificNote.from_i(i)
    assert (note + to_add).i == note.i + to_add


@given(st.integers(), st.integers())
def test_specific_note_sub(i, to_sub):
    note = SpecificNote.from_i(i)
    assert note - to_sub == SpecificNote.from_i(note.i - to_sub)


def test_color():
    assert not Note('C').is_black
    assert Note('d').is_black
    assert not SpecificNote('D', 1).is_black
    assert SpecificNote('f', -35).is_black


def test_midi_code():
    A4 = SpecificNote(Note('A'), 4)
    assert A4.i == 69
    assert SpecificNote.from_i(69) == A4


def test_lt_validation():
    with pytest.raises(TypeError):
        assert Note('C') < 1
    with pytest.raises(TypeError):
        assert SpecificNote.from_str('C1') < Note('C')
