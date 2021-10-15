import io

import numpy as np
import pytest

from musictools.daw import render
from musictools.daw.vst import ADSR
from musictools.daw.vst import Sine
from musictools.midi.parse import MidiTrack


@pytest.mark.parametrize('vst', (
    Sine(adsr=ADSR(attack=0.05, decay=0.3, sustain=0.1, release=0.001)),
    Sine(adsr=ADSR(attack=0.001, decay=0.3, sustain=1, release=1))
))
@pytest.mark.parametrize('midi_file', (
    'static/midi/overlap.mid',
    'static/midi/4.mid',
    'static/midi/4-2.mid',
    'static/midi/4-3.mid',
    'static/midi/4-4.mid',
    'static/midi/chord.mid',
    'static/midi/weird.mid',
))
def test_chunks(midi_file, vst):

    track = MidiTrack.from_file(midi_file, vst)

    single = io.BytesIO()
    chunked = io.BytesIO()

    render.single(single, track)
    render.chunked(chunked, track)

    single = np.frombuffer(single.getvalue(), dtype='float32')
    chunked = np.frombuffer(chunked.getvalue(), dtype='float32')

    assert np.allclose(single, chunked, atol=1e-7)
