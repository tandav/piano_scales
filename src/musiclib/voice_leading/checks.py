from __future__ import annotations

import functools
import itertools
from typing import TYPE_CHECKING
from typing import Any

from musiclib.progression import Progression

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Hashable

    from musiclib.note import SpecificNote
    from musiclib.noteset import SpecificNoteSet
    from musiclib.scale import Scale


def chord_pair_check_cache(f: Callable[..., bool]) -> Callable[..., bool]:
    cache: dict[Hashable, bool] = {}
    cache_info = {'hits': 0, 'misses': 0, 'currsize': 0}

    @functools.wraps(f)
    def is_check_passed(a: SpecificNoteSet, b: SpecificNoteSet, *args: Any) -> bool:
        a, b = Progression((a, b)).transposed_to_C0
        key = a, b, *args
        cached = cache.get(key)
        if cached is not None:
            cache_info['hits'] += 1
            return cached
        cache_info['misses'] += 1
        cache_info['currsize'] += 1
        computed = f(a, b, *args)
        cache[key] = computed
        return computed
    is_check_passed._cache = cache  # type: ignore[attr-defined]
    is_check_passed._cache_info = cache_info  # type: ignore[attr-defined]
    return is_check_passed


@chord_pair_check_cache
def is_parallel_interval(a: SpecificNoteSet, b: SpecificNoteSet, interval: int, /) -> bool:
    """
    parallel in same voices!
    if there'are eg fifth in 1st and fifth in 2nd chord but not from same voices
    - then it allowed (aint considered parallel) (test it)

    a1 - b1
    a0 - b0
    todo: what about fifths + octave (eg C5 G6 -> F5 C6)
    """
    voice_transitions = tuple(zip(a, b, strict=True))
    for (a0, b0), (a1, b1) in itertools.combinations(voice_transitions, 2):
        if abs(a0 - a1) % 12 == interval == abs(b0 - b1) % 12:
            return True
    return False


@chord_pair_check_cache
def is_hidden_parallel(a: SpecificNoteSet, b: SpecificNoteSet, interval: int, /) -> bool:
    """
    hidden/direct parallel/consecutive interval is when:
        1. outer voices (lower and higher) go in same direction (instead of oblique or contrary motion)
        2. they approach param:interval
    voice leading rules often forbid hidden fifths and octaves (param:interval = 7, 0) (explanation: 12 % 12 == 0 octave equal to unison)
    """
    a_low, a_high = a[0], a[-1]
    b_low, b_high = b[0], b[-1]

    is_same_direction = (a_low < b_low and a_high < b_high) or (a_low > b_low and a_high > b_high)
    return is_same_direction and (b_high - b_low) % 12 == interval


@chord_pair_check_cache
def is_voice_crossing(a: SpecificNoteSet, b: SpecificNoteSet, /) -> bool:
    n = len(b)
    for i in range(n):
        upper = i < n - 1 and b[i] > a[i + 1]
        lower = i > 0 and b[i] < a[i - 1]
        if upper or lower:
            return True
    return False


@chord_pair_check_cache
def is_large_leaps(a: SpecificNoteSet, b: SpecificNoteSet, interval: int, /) -> bool:
    return any(abs(an - bn) > interval for an, bn in zip(a, b, strict=True))


@chord_pair_check_cache
def is_make_major_scale_leading_tone_resolving_semitone_up(
    a: SpecificNoteSet,
    b: SpecificNoteSet,
    s: Scale,
    /,
) -> bool:
    if s.intervalset.names != frozenset({'major'}):
        raise ValueError('pass major scale')
    leading_tone = next(note for note in a.notes if note.abstract == s.notes_ascending[-1])
    tonic = next(note for note in b.notes if note.abstract == s.root)
    return tonic - leading_tone == 1


def is_large_spacing_intervals(c: tuple[int, ...], max_interval: int = 12, /) -> bool:
    return any(b - a > max_interval for a, b in itertools.pairwise(c))


def is_small_spacing_intervals(c: tuple[int, ...], min_interval: int = 3, /) -> bool:
    return any(b - a < min_interval for a, b in itertools.pairwise(c))


def is_large_spacing(c: SpecificNoteSet, max_interval: int = 12, /) -> bool:
    return is_large_spacing_intervals(c.intervals, max_interval)


def is_small_spacing(c: SpecificNoteSet, min_interval: int = 3, /) -> bool:
    return is_small_spacing_intervals(c.intervals, min_interval)


def find_paused_voices(a: SpecificNoteSet, b: SpecificNoteSet, n_notes: int) -> tuple[int, ...] | tuple[()]:
    if n_notes == 0 or len(a) == len(b) == 0:
        return ()
    if max(len(a), len(b)) > n_notes:
        raise ValueError('both chords should hava number of notes <= n_notes')
    less_notes, more_notes = sorted((a, b), key=len)
    used = set()

    def _key(note0: SpecificNote, note1: SpecificNote) -> int:
        return abs(note0 - note1)

    for note in less_notes:
        nearest = min(more_notes, key=functools.partial(_key, note1=note))
        used.add(nearest)
    paused = tuple(i for i, note in enumerate(more_notes) if note not in used)
    return paused  # noqa: RET504
