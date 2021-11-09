import itertools
import random
import sys

import joblib
import mido

from musictools import config
from musictools import voice_leading
from musictools.daw.midi.parse import ParsedMidi
from musictools.daw.streams.pcmfile import PCM16File
from musictools.daw.streams.speakers import Speakers
from musictools.daw.streams.video import Video
from musictools.daw.streams.wavfile import WavFile
from musictools.daw.vst.adsr import ADSR
from musictools.daw.vst.organ import Organ
from musictools.daw.vst.sampler import Sampler
from musictools.daw.vst.sine import Sine8
from musictools.note import SpecificNote
from musictools.note import note_range
from musictools.rhythm import Rhythm
from musictools.scale import Scale

memory = joblib.Memory('static/cache', verbose=0)


@memory.cache
def make_rhythms():
    _ = (Rhythm.all_rhythms(n_notes) for n_notes in range(5, 8 + 1))
    _ = itertools.chain.from_iterable(_)
    return tuple(_)


@memory.cache
def make_progressions(note_range_, scale=Scale('C', 'phrygian')):
    progressions = []
    scales = [Scale(note, name) for note, name in scale.note_scales.items()]
    for scale in scales:
        for dist, p in voice_leading.make_progressions(scale, note_range_):
            progressions.append((p, dist, scale))
    return progressions


def render_loop(stream, rhythms, progressions, bass, synth, drum_midi, drumrack):
    progression, dist, scale = random.choice(progressions)
    rhythm = random.choice(rhythms)

    bass_midi = []
    chord_midi = []

    config.tuning = random.randint(430, 600) if random.random() < 0.15 else config.DEFAULT_TUNING

    drumrack.note_mute = {
        SpecificNote('C', 3): random.random() < 0.1,
        SpecificNote('e', 3): random.random() < 0.1,
        SpecificNote('b', 3): random.random() < 0.1,
        SpecificNote('f', 3): random.random() < 0.5,
    }

    for chord_i, chord in enumerate(progression):
        # bass_midi = rhythm.to_midi(note_=chord.notes_ascending[0] + 12)
        # bass_midi = rhythm.to_midi(note_=chord.notes_ascending[0] + -12)

        # bass_midi = rhythm.to_midi(note_=chord.notes_ascending[0])
        bass_midi.append(rhythm.to_midi(note_=chord.notes_ascending[0]))

        # chord_midi = rhythm.to_midi(chord=chord)
        # chord_midi = chord.to_midi(n_bars=1)
        chord_midi.append(chord.to_midi(n_bars=1))

        # render.chunked(stream, ParsedMidi.vstack(
        #     [drum_midi, bass_midi, chord_midi],
        #     [drumrack, bass, synth],
        # ))

    bass._adsr.decay = random.uniform(0.1, 0.5)
    bass_midi = ParsedMidi.hstack(bass_midi)
    chord_midi = ParsedMidi.hstack(chord_midi)

    stream.render_chunked(ParsedMidi.vstack(
        [drum_midi, bass_midi, chord_midi],
        [drumrack, bass, synth],
        meta={
            'bassline': f'bassline {rhythm.bits}',
            'rhythm_score': f'score{rhythm.score:.2f}',
            'bass_decay': f'bass_decay{bass._adsr.decay:.2f}',
            'tuning': f'tuning{config.tuning}Hz',
            'root_scale': f'root scale: {scale.root.name} {scale.name}',
            'progression': progression,
            'dist': f'dist{dist}',
            'scale': scale,
        },
    ), normalize=False)


def main() -> int:
    # todo: argparse
    # parser = argparse.ArgumentParser(description='Run streaming, pass output stream')
    # parser.add_argument('--output', action='store_const', const=streams.Speakers , default=streams.Speakers)
    # parser.add_argument('--speakers', dest='output_stream', action='store_const', const=streams.Speakers , help='stream to speakers')
    # parser.add_argument('--youtube' , dest='output_stream', action='store_const', const=streams.YouTube  , help='stream to youtube')
    # parser.add_argument('--wav'     , dest='output_stream', action='store_const', const=streams.WavFile  , help='save to wave/riff file')
    # parser.add_argument('--pcm'     , dest='output_stream', action='store_const', const=streams.PCM16File, help='save to pcm16 file')
    # args = parser.parse_args()
    # print(args, args.output_stream)
    # print(args)
    # raise
    # synth = vst.Sampler(adsr=ADSR(attack=0.001, decay=0.15, sustain=0, release=0.1))
    # synth = vst.Sine(adsr=ADSR(attack=0.001, decay=0.05, sustain=1, release=1))
    # synth = vst.Organ(adsr=ADSR(attack=0.001, decay=0.15, sustain=0, release=0.1))
    # midi = ParsedMidi.from_file(config.midi_file, vst=synth)
    # midi = ParsedMidi.from_file('drumloop.mid', vst=synth)
    # midi = ParsedMidi.from_file('bassline.mid', vst=synth)
    # midi = ParsedMidi.from_file('4-4-8.mid', vst=synth)
    # midi = ParsedMidi.from_files(['4-4-8.mid', '4-4-8-offbeat.mid'], vst=(

    is_test = False
    if len(sys.argv) == 1:
        output = Speakers
    else:
        if sys.argv[1] == 'video_test':
            output = Video
            config.OUTPUT_VIDEO = '/dev/null'
            # config.OUTPUT_VIDEO = '/tmp/output.flv'
            config.beats_per_minute = 480
            # config.frame_width = 426
            # config.frame_width = 240
            is_test = True
            n_loops = 2
        elif sys.argv[1] == 'video_file':
            output = Video
            config.OUTPUT_VIDEO = '/tmp/output.flv'
            is_test = True
            n_loops = int(sys.argv[2]) if len(sys.argv) == 3 else 4
        else:
            output = {
                'speakers': Speakers,
                'video': Video,
                'wav': WavFile,
                'pcm': PCM16File,
            }[sys.argv[1]]

    # C = make_rhythms(SpecificNote('C', 4))
    #
    # notes_rhythms = [
    #     make_rhythms(SpecificNote('b', 3)),
    #     make_rhythms(SpecificNote('a', 3)),
    #     make_rhythms(SpecificNote('G', 3)),
    #     make_rhythms(SpecificNote('F', 3)),
    # ]

    config.note_range = note_range(SpecificNote('C', 3), SpecificNote('G', 6))

    rhythms = make_rhythms()
    progressions = make_progressions(config.note_range)

    # n = len(notes_rhythms[0])

    # drum_midi = mido.MidiFile(config.midi_folder + 'drumloop.mid')
    # drum_midi = ParsedMidi.hstack([mido.MidiFile(config.midi_folder + 'drumloop.mid')] * 4)
    drum_midi = ParsedMidi.hstack([mido.MidiFile(config.midi_folder + 'drumloop-with-closed-hat.mid')] * 4)

    # m1 = mido.MidiFile(config.midi_folder + '153_0101000101010010.mid')
    bass = Organ(adsr=ADSR(attack=0.001, decay=0.15, sustain=0, release=0.1), amplitude=0.05)
    drumrack = Sampler()
    # synth = Sine(adsr=ADSR(attack=0.05, decay=0.1, sustain=1, release=0.1), amplitude=0.025)
    synth = Sine8(adsr=ADSR(attack=0.05, decay=0.1, sustain=1, release=0.1), amplitude=0.003)
    # midi = ParsedMidi.from_files(['153_0101000101010010.mid'z, '153_0101000101010010.mid'], vst=(
    # midi = ParsedMidi.from_files(['drumloop.mid', '153_0101000101010010.mid'], vst=(
    # midi = ParsedMidi.from_files(['drumloop.mid', 'bassline.mid'], vst=(
    # # midi = ParsedMidi.vstack([m0, m1], vst=(
    #     vst.Sampler(),
    #     bass,
    # ))

    # with streams.WavFile(config.wav_output_file, dtype='float32') as stream:
    # with streams.WavFile(config.wav_output_file, dtype='int16') as stream:
    # with streams.WavFile(config.wav_output_file, dtype='int16') as stream:
    # with streams.PCM16File(config.audio_pipe) as stream:
    # with streams.Speakers() as stream:
    with output() as stream:
        # for _ in range(4): render.chunked(stream, midi)
        # for _ in range(4): render.single(stream, midi)
        # for _ in range(1): render.chunked(stream, midi)
        # for _ in range(4): render.single(stream, ParsedMidi.from_file('weird.mid', vst=synth))
        #     for _ in range(4): render.chunked(stream, ParsedMidi.from_file('dots.mid', vst=synth))

        # midi.rhythm_to_midi(r, Path.home() / f"Desktop/midi/prog.mid",  progression=p)

        if is_test:
            for _ in range(n_loops):
                render_loop(stream, rhythms, progressions, bass, synth, drum_midi, drumrack)
        else:
            while True:
                render_loop(stream, rhythms, progressions, bass, synth, drum_midi, drumrack)

        # for _ in range(1):
        #     i = random.randrange(0, n)
        #     for _ in range(1):
        #         midi = ParsedMidi.vstack([drum_midi, C[i]], vst=(vst.Sampler(), bass))
        #         render.chunked(stream, midi)
        #     for _ in range(3):
        #         midi = ParsedMidi.vstack([drum_midi, random.choice(notes_rhythms)[i]], vst=(vst.Sampler(), bass))
        #         render.chunked(stream, midi)

    print('exit main')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
