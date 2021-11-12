import abc
from typing import Optional

import numpy as np

from musictools import config
from musictools.daw.midi.notesound import State
from musictools.daw.midi.parse import ParsedMidi
from musictools.util.signal import normalize as normalize_
from contextlib import AbstractContextManager


class Stream(AbstractContextManager):
    def __init__(self):
        self.master = np.zeros(config.chunk_size, dtype='float32')
        self.track: Optional[ParsedMidi] = None

    def render_single(self, track: ParsedMidi, normalize=False):
        self.track = track
        master = np.zeros(track.n_samples, dtype='float32')
        for note in track.notes:
            note.render(master)
        assert np.all(np.abs(master) <= 1)
        if normalize:
            self.write(normalize_(master))
        else:
            self.write(master)
        track.reset()

    def render_chunked(self, track: ParsedMidi, normalize=False):
        self.track = track
        notes = set(track.notes)
        n = 0
        # playing_notes = set()
        self.master[:] = 0
        while n < track.n_samples:
            self.n = n
            chunk_size = min(config.chunk_size, track.n_samples - n)
            samples = np.arange(n, n + chunk_size)
            self.master[:chunk_size] = 0.
            track.playing_notes |= set(note for note in notes if n <= note.sample_on < n + config.chunk_size)
            track.stopped_notes = set()
            for note in track.playing_notes:
                note.render(self.master[:chunk_size], samples)

                if note.state == State.DONE:
                    track.stopped_notes.add(note)

            track.playing_notes -= track.stopped_notes
            notes -= track.stopped_notes
            assert np.all(np.abs(self.master[:chunk_size]) <= 1)
            if normalize:
                self.write(normalize_(self.master[:chunk_size]))
            else:
                self.write(self.master[:chunk_size])
            n += chunk_size
        track.reset()

    @abc.abstractmethod
    def write(self, data: np.ndarray):
        """data.dtype must be float32"""
        ...
