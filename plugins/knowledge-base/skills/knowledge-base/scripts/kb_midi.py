#!/usr/bin/env python3
"""
Pure-stdlib MIDI Format-1 writer for kb_svg.py renderers.

Usage (programmatic):
  from kb_midi import MidiFile, MidiTrack, NOTE_ON, NOTE_OFF, write_midi
  mf = MidiFile(ticks_per_beat=480)
  t = MidiTrack()
  t.note(0, 60, 80, 480)   # delta, pitch, velocity, duration_ticks
  mf.add_track(t)
  write_midi(mf, "output.mid")

Usage (CLI):
  kb_midi.py --notes "C4-q D4-q E4-q F4-q" --bpm 120 --out output.mid
  kb_midi.py --notes "C4-q D4-q" --bpm 90 --play

Notes format: <pitch>-<dur> space-separated tokens.
  Duration codes: w=whole, h=half, q=quarter, e=eighth, s=sixteenth
  Pitch: letter A-G + optional # or b + octave number, e.g. C4, F#3, Bb5
"""
import argparse
import struct
import subprocess
import sys
from pathlib import Path


# ── MIDI constants ──────────────────────────────────────────────────────────

NOTE_ON  = 0x90
NOTE_OFF = 0x80
PROGRAM_CHANGE = 0xC0
TEMPO_META = 0x51
END_OF_TRACK = 0x2F

PITCH_NAMES = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11,
}

DUR_FRACTIONS = {
    "w": 4, "h": 2, "q": 1, "e": 0.5, "s": 0.25,
}


# ── Variable-length encoding ─────────────────────────────────────────────────

def _vlq(n: int) -> bytes:
    """Encode a non-negative integer as a MIDI variable-length quantity."""
    if n == 0:
        return b"\x00"
    parts = []
    while n:
        parts.append(n & 0x7F)
        n >>= 7
    parts.reverse()
    result = bytearray()
    for i, b in enumerate(parts):
        result.append(b | (0x80 if i < len(parts) - 1 else 0))
    return bytes(result)


# ── MIDI data structures ──────────────────────────────────────────────────────

class MidiEvent:
    """A single MIDI event with delta time."""
    __slots__ = ("delta", "data")

    def __init__(self, delta: int, data: bytes):
        self.delta = delta
        self.data = data

    def encode(self) -> bytes:
        return _vlq(self.delta) + self.data


class MidiTrack:
    """A single MIDI track (MTrk chunk)."""

    def __init__(self):
        self._events: list[MidiEvent] = []

    def add_event(self, delta: int, data: bytes) -> None:
        self._events.append(MidiEvent(delta, data))

    def note(self, delta_on: int, pitch: int, velocity: int,
             duration_ticks: int, channel: int = 0) -> None:
        """Add a note-on / note-off pair. delta_on is ticks after previous event."""
        self.add_event(delta_on,  bytes([NOTE_ON  | channel, pitch, velocity]))
        self.add_event(duration_ticks, bytes([NOTE_OFF | channel, pitch, 0]))

    def program(self, channel: int, program: int, delta: int = 0) -> None:
        self.add_event(delta, bytes([PROGRAM_CHANGE | channel, program]))

    def encode(self) -> bytes:
        body = bytearray()
        for ev in self._events:
            body += ev.encode()
        body += _vlq(0) + bytes([0xFF, END_OF_TRACK, 0x00])
        header = b"MTrk" + struct.pack(">I", len(body))
        return header + bytes(body)


class MidiFile:
    """A MIDI Format-1 file container."""

    def __init__(self, ticks_per_beat: int = 480, bpm: int = 120):
        self.ticks_per_beat = ticks_per_beat
        self.bpm = bpm
        self._tracks: list[MidiTrack] = []
        self._tempo_track = self._make_tempo_track(bpm)

    def _make_tempo_track(self, bpm: int) -> MidiTrack:
        t = MidiTrack()
        usec = 60_000_000 // bpm
        tempo_data = bytes([0xFF, TEMPO_META, 0x03,
                            (usec >> 16) & 0xFF,
                            (usec >> 8) & 0xFF,
                            usec & 0xFF])
        t.add_event(0, tempo_data)
        return t

    def add_track(self, track: MidiTrack) -> None:
        self._tracks.append(track)

    def encode(self) -> bytes:
        all_tracks = [self._tempo_track] + self._tracks
        n_tracks = len(all_tracks)
        header = (b"MThd"
                  + struct.pack(">I", 6)
                  + struct.pack(">HHH", 1, n_tracks, self.ticks_per_beat))
        body = b"".join(t.encode() for t in all_tracks)
        return header + body


# ── Note parsing ──────────────────────────────────────────────────────────────

def parse_pitch(token: str) -> int | None:
    """Parse e.g. 'C4', 'F#3', 'Bb5' → MIDI note number, or None."""
    if not token:
        return None
    letter = token[0].upper()
    if letter not in PITCH_NAMES:
        return None
    rest = token[1:]
    accidental = 0
    if rest.startswith("#"):
        accidental = 1
        rest = rest[1:]
    elif rest.startswith("b"):
        accidental = -1
        rest = rest[1:]
    try:
        octave = int(rest)
    except (ValueError, TypeError):
        octave = 4
    return 12 * (octave + 1) + PITCH_NAMES[letter] + accidental


def parse_notes(notes_str: str, ticks_per_beat: int) -> list[tuple[int, int, int]]:
    """
    Parse space-separated '<pitch>-<dur>' tokens.
    Returns list of (delta_ticks, pitch, duration_ticks).
    First note has delta 0; subsequent notes start after the previous note ends.
    """
    result = []
    for tok in notes_str.split():
        pitch_part, _, dur_code = tok.partition("-")
        pitch = parse_pitch(pitch_part)
        if pitch is None:
            continue
        dur_beats = DUR_FRACTIONS.get(dur_code, 1.0)
        dur_ticks = int(dur_beats * ticks_per_beat)
        result.append((0, pitch, dur_ticks))
    return result


# ── Helper: notes_str → MidiTrack ─────────────────────────────────────────────

def notes_to_track(notes_str: str, ticks_per_beat: int,
                   velocity: int = 80, channel: int = 0) -> MidiTrack:
    """Convert a notes string to a MidiTrack with sequential note events."""
    track = MidiTrack()
    for _delta, pitch, dur in parse_notes(notes_str, ticks_per_beat):
        track.note(0, pitch, velocity, dur, channel)
    return track


# ── Write helper ──────────────────────────────────────────────────────────────

def write_midi(mf: MidiFile, path: str) -> None:
    Path(path).write_bytes(mf.encode())


# ── Playback (best-effort) ────────────────────────────────────────────────────

def play_midi(path: str) -> None:
    """Try platform-specific playback. Silent failure if no player found."""
    import platform
    system = platform.system()
    players = {
        "Darwin": ["afplay"],
        "Linux":  ["aplaymidi", "--port=128:0"],
        "Windows": ["wmplayer"],
    }
    cmds = players.get(system, [])
    if not cmds:
        return
    try:
        subprocess.Popen([cmds[0]] + cmds[1:] + [path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="MIDI Format-1 writer for music SVGs")
    ap.add_argument("--notes", default="", help="Space-separated pitch-dur tokens")
    ap.add_argument("--bpm", type=int, default=120)
    ap.add_argument("--velocity", type=int, default=80)
    ap.add_argument("--program", type=int, default=0, help="GM program number (0=piano)")
    ap.add_argument("--out", required=True, help="Output .mid file path")
    ap.add_argument("--play", action="store_true", help="Play after writing")
    args = ap.parse_args()

    tpb = 480
    mf = MidiFile(ticks_per_beat=tpb, bpm=args.bpm)
    track = MidiTrack()
    track.program(0, args.program)
    for _delta, pitch, dur in parse_notes(args.notes, tpb):
        track.note(0, pitch, args.velocity, dur)
    mf.add_track(track)
    write_midi(mf, args.out)

    if args.play:
        play_midi(args.out)


if __name__ == "__main__":
    main()
