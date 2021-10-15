import abc
from pathlib import Path
from typing import Union

import numpy as np
from scipy.io import wavfile

from ... import config
from ...note import SpecificNote


class ADSR:
    def __init__(
        self,
        attack: float = 0.,
        decay: float = 1e-3,
        sustain: float = 1.,
        release: float = 1e-3,
    ):
        # ranges like in Ableton Live Operator, Wavetable
        if not (0. <= attack <= 20.): raise ValueError('wrong attack value')
        if not (1e-3 <= decay <= 20.): raise ValueError('wrong decay value')
        if not (0. <= sustain <= 1.): raise ValueError('wrong sustain value')
        if not (1e-3 <= release <= 20.): raise ValueError('wrong release value')

        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release


class VST(abc.ABC):
    def __init__(self, adsr=ADSR()):
        self.adsr = adsr

    def note_to_freq(self, note: SpecificNote):
        return (440 / 32) * (2 ** ((note.absolute_i - 9) / 12))

    def samples_to_t(self, ns_rendered: int, ns_to_render: int):
        t0 = ns_rendered / config.sample_rate
        t1 = t0 + ns_to_render / config.sample_rate
        return np.linspace(t0, t1, ns_to_render, endpoint=False)

    @abc.abstractmethod
    def __call__(self, *args, **kwargs): ...


class Sine(VST):
    def __call__(self, ns_rendered: int, ns_to_render: int, note: SpecificNote, a=0.1, p=0.):
        t = self.samples_to_t(ns_rendered, ns_to_render)
        f = self.note_to_freq(note)
        return a * np.sin(2 * np.pi * f * t + p)


class Organ(VST):
    def __call__(self, ns_rendered: int, ns_to_render: int, note: SpecificNote, a=0.1, p=0.):
        t = self.samples_to_t(ns_rendered, ns_to_render)
        f0 = self.note_to_freq(note)
        f1 = self.note_to_freq(note + 7)
        f2 = self.note_to_freq(note + 19)

        return (
            a * np.sin(2 * np.pi * f0 * t + p) +
            a * np.sin(2 * np.pi * f1 * t + p) +
            a * np.sin(2 * np.pi * f2 * t + p)
        )


class Sampler(VST):
    DEFAULT_NOTE_TO_SAMPLE_PATH = note_to_sample_path = (
        (SpecificNote('C', 3), config.kick),
        (SpecificNote('e', 3), config.clap),
        (SpecificNote('b', 3), config.hat),
    )

    # todo: add note to sample mapping support (kinda easy)\
    def __init__(self, note_to_sample_path=DEFAULT_NOTE_TO_SAMPLE_PATH, adsr=ADSR()):
        super().__init__(adsr)
        self.note_to_sample = dict()
        for note, sample_path in note_to_sample_path:
            self.note_to_sample[note] = self.load_sample(sample_path)

    def load_sample(self, sample_path: Union[str, Path]):
        sample_rate, sample = wavfile.read(sample_path)
        if sample.dtype != 'float32':
            raise ValueError(f'Sample {sample_path} should be in float32 format')
        if sample_rate != config.sample_rate:
            raise NotImplementedError(
                f'resampling is not supported yet, please save sample {sample_path} with sample rate {config.sample_rate}')
        return sample

    def __call__(self, ns_rendered: int, ns_to_render: int, note: SpecificNote, a=0.1):
        sample = a * self.note_to_sample[note][ns_rendered: ns_rendered + ns_to_render]
        out = np.zeros(ns_to_render, dtype='float32')  # handle cases when samples ends earlier than note_off, render zeros till note_off (and maybe release? idk lol)
        out[:len(sample)] = sample
        return out
