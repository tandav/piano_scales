from typing import TypeGuard

from musictool.note import Note


def is_frozenset_of_note(s: frozenset[object]) -> TypeGuard[frozenset[Note]]:
    return all(isinstance(x, Note) for x in s)
