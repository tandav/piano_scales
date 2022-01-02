import itertools
from collections.abc import Sequence
from collections.abc import Iterable

from musictools import config
from musictools.note import Note
from musictools.note import SpecificNote


def iterate(
    start_note: str | Note | SpecificNote = config.chromatic_notes[0],
    take_n: int | None = None,
) -> Iterable[Note | SpecificNote]:
    names = itertools.cycle(config.chromatic_notes)

    if isinstance(start_note, SpecificNote):
        octaves = itertools.chain.from_iterable(
            itertools.repeat(octave, 12)
            for octave in itertools.count(start=start_note.octave)
        )
        notes = (SpecificNote(name, octave) for name, octave in zip(names, octaves))
    else:
        if isinstance(start_note, str):
            start_note = Note(start_note)
        notes = (Note(name) for name in names)

    notes = itertools.dropwhile(lambda note: note.name != start_note.name, notes)

    if take_n is not None:
        notes = itertools.islice(notes, take_n)

    yield from notes


def sort_notes(it: Iterable[str | Note | SpecificNote]):
    first = next(iter(it))
    if isinstance(first, str): return sorted(it, key=config.note_i.__getitem__)
    elif type(first) is Note: return sorted(it, key=lambda note: note.i)
    elif type(first) is SpecificNote: return sorted(it, key=lambda note: note.absolute_i)
    else: raise TypeError
