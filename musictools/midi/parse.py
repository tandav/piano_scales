from enum import Enum
from enum import auto

import mido
import numpy as np

from .. import config
from ..daw import vst
from ..note import SpecificNote


class State(Enum):
    TODO = auto()
    IN_PROGRESS = auto()
    DONE = auto()


class NoteSound:
    def __init__(
        self,
        absolute_i: int,
        sample_on: int,
        sample_off: int,
        vst: vst.VST,
    ):
        """TODO: maybe remove some variables (which can be expressed via other)"""
        self.note = SpecificNote.from_absolute_i(absolute_i)
        self.sample_on = sample_on
        self.sample_off_wo_release = sample_off  # todo: rename, keep note_off for note off, add with_relase
        self.samples_release = int(vst.adsr.release * config.sample_rate)
        self.sample_off = sample_off + self.samples_release  # actual sample when note is off (including release)

        self.n_samples_wo_release = self.sample_off_wo_release - sample_on
        self.n_samples = sample_off - sample_on  # total samples for playing note sound

        self.samples_attack = min(int(vst.adsr.attack * config.sample_rate), self.n_samples_wo_release)
        self.samples_decay = min(int(vst.adsr.decay * config.sample_rate), self.n_samples_wo_release - self.samples_attack)
        self.samples_sustain = self.n_samples_wo_release - self.samples_attack - self.samples_decay

        self.sample_stop_attack = self.sample_on + self.samples_attack
        self.sample_stop_decay = self.sample_stop_attack + self.samples_decay
        # self.sample_stop_sustain = self.sample_off_wo_release  # do the math
        self.sample_stop_release = self.sample_off_wo_release + self.samples_release

        # todo: use difference, not ranges
        self.range_attack = np.arange(self.sample_on, self.sample_stop_attack)
        self.range_decay = np.arange(self.sample_stop_attack, self.sample_stop_decay)
        self.range_sustain = np.arange(self.sample_stop_decay, self.sample_off_wo_release)
        self.range_release = np.arange(self.sample_off_wo_release, self.sample_off)

        self.attack_envelope = np.linspace(0, 1, self.samples_attack, endpoint=False, dtype='float32')
        # if decay is longer than note then actual sustain is higher than vst.adsr.sustain (do the math)
        print(self.samples_decay)
        s = max((vst.adsr.sustain - 1) * (self.n_samples - self.samples_attack) / self.samples_decay + 1, vst.adsr.sustain)
        self.decay_envelope = np.linspace(1, s, self.samples_decay, endpoint=False, dtype='float32')
        # self.attack_decay_envelope[:self.samples_attack] = np.arange()  # todo: make envelope
        # self.attack_decay_envelope[self.samples_attack:self.samples_decay] = 1.  # todo: make envelope
        self.release_envelope = np.linspace(s, 0, self.samples_release, endpoint=False, dtype='float32')

        self.samples_rendered = 0
        self.vst = vst
        self.key = self.note, self.sample_on, self.sample_off
        self.state = State.TODO

    def render(self, chunk, samples=None):
        self.state = State.IN_PROGRESS
        if samples is None:
            samples = np.arange(len(chunk))
        mask = (self.sample_on <= samples) & (samples < self.sample_off)
        n_samples = np.count_nonzero(mask)

        mask_attack = (self.sample_on <= samples) & (samples < self.sample_stop_attack)
        mask_decay = (self.sample_stop_attack <= samples) & (samples < self.sample_stop_decay)
        mask_sustain = (self.sample_stop_decay <= samples) & (samples < self.sample_off_wo_release)
        mask_release = (self.sample_off_wo_release <= samples) & (samples < self.sample_off)

        t0 = self.samples_rendered / config.sample_rate
        t1 = t0 + n_samples / config.sample_rate
        self.samples_rendered += n_samples
        f = (440 / 32) * (2 ** ((self.note.absolute_i - 9) / 12))
        wave = self.vst(np.linspace(t0, t1, n_samples, endpoint=False), f, a=0.1)
        print(mask_attack.shape, mask.shape, mask_attack, mask, samples, self.sample_on, self.sample_off)

        # q = mask_attack[mask]
        # print('lol')
        wave[mask_attack[mask]] *= self.attack_envelope[(samples[0] <= self.range_attack) & (self.range_attack <= samples[-1])]
        wave[mask_decay[mask]] *= self.decay_envelope[(samples[0] <= self.range_decay) & (self.range_decay <= samples[-1])]
        wave[mask_sustain[mask]] *= self.vst.adsr.sustain
        wave[mask_release[mask]] *= self.release_envelope[(samples[0] <= self.range_release) & (self.range_release <= samples[-1])]
        chunk[mask] += wave
        if samples is None or self.sample_off + self.samples_release <= samples[-1]:
            self.state = State.DONE

    def reset(self):
        self.samples_rendered = 0

    def __hash__(self): return hash(self.key)
    def __eq__(self, other): return self.key == other.key


class MidiTrack:
    def __init__(self, notes, n_samples, numerator=4, vst=None):
        self.notes = notes
        self.n_samples = n_samples
        self.numerator = numerator
        self.vst = vst

    def reset(self):
        for note in self.notes:
            note.reset()

    @classmethod
    def from_file(cls, midi_file, vst):
        ticks, seconds, n_samples = 0, 0., 0
        m = mido.MidiFile(midi_file)
        notes = []
        note_buffer = dict()

        # FAILING BECAUSE OOF RELEASE, CUT LAST NOTE IN A TRACK
        # ADD TESTS FOR DIFFERENT RELEASES
        # crop notes samples which exceeds track.n_samples

        numerator = None

        for message in m.tracks[0]:
            if message.type == 'time_signature':
                assert message.denominator == 4
                numerator = message.numerator
            ticks += message.time
            d_seconds = mido.tick2second(message.time, m.ticks_per_beat, mido.bpm2tempo(config.beats_per_minute))
            seconds += d_seconds
            n_samples += int(config.sample_rate * d_seconds)
            print(message)
            if message.type == 'note_on':
                note_buffer[message.note] = n_samples
            elif message.type == 'note_off':
                notes.append(NoteSound(message.note, note_buffer.pop(message.note), n_samples, vst=vst))

        ticks_per_bar = numerator * m.ticks_per_beat  # todo: support 3/4 and other
        ticks += ticks_per_bar - ticks % ticks_per_bar
        n_samples = int(config.sample_rate * mido.tick2second(ticks, m.ticks_per_beat, mido.bpm2tempo(config.beats_per_minute)))

        return cls(notes, n_samples, numerator)
