"""Golden-master tests for kb_svg.py. Each renderer has one canonical invocation."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "kb_svg.py"
GOLDEN = Path(__file__).resolve().parent / "fixtures" / "svg_golden"


def run_svg(*args: str) -> str:
    """Invoke kb_svg.py and return stdout SVG (stripped of timestamps)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, check=True,
    )
    return _strip_volatile(proc.stdout)


def _strip_volatile(svg: str) -> str:
    """Remove any volatile bytes (timestamps, UUIDs) before comparison."""
    svg = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", "TIMESTAMP", svg)
    svg = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "UUID", svg)
    return svg.strip()


def assert_golden(name: str, actual: str):
    GOLDEN.mkdir(parents=True, exist_ok=True)
    path = GOLDEN / f"{name}.svg"
    if not path.exists():
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"wrote new golden: {path}")
    expected = _strip_volatile(path.read_text(encoding="utf-8"))
    assert actual == expected, f"{name} differs from golden {path}"


def test_staff_basic_treble_c_major():
    actual = run_svg(
        "--type", "staff",
        "--clef", "treble",
        "--key", "C major",
        "--time-sig", "4/4",
        "--notes", "C4-q D4-q E4-q F4-q",
        "--width", "600",
        "--height", "200",
    )
    assert "<line" in actual  # 5 staff lines drawn
    assert actual.count("<line") >= 5
    assert_golden("staff_basic", actual)


def test_fretboard_guitar_standard_tuning():
    actual = run_svg(
        "--type", "fretboard",
        "--strings", "6",
        "--tuning", "EADGBE",
        "--notes", "0,2,3",
        "--width", "700", "--height", "240",
    )
    assert "<line" in actual
    assert "E" in actual
    assert_golden("fretboard_guitar_eadgbe", actual)


def test_circle_of_fifths_basic():
    actual = run_svg(
        "--type", "circle-of-fifths",
        "--highlight", "C,G,D",
        "--width", "500", "--height", "500",
    )
    for k in ["C", "G", "D", "A", "E", "B", "F"]:
        assert f">{k}<" in actual
    assert_golden("circle_basic", actual)


def test_raga_clock_yaman():
    actual = run_svg(
        "--type", "raga-clock",
        "--raga", "Yaman",
        "--shrutis", "12",
        "--width", "500", "--height", "500",
    )
    for s in ["Sa", "Re", "Ga", "Ma", "Pa", "Dha", "Ni"]:
        assert f">{s}<" in actual
    assert_golden("raga_yaman", actual)


def test_maqam_jins_hijaz():
    actual = run_svg(
        "--type", "maqam-jins",
        "--jins", "Hijaz",
        "--root", "D",
        "--show-cents",
        "--width", "600", "--height", "260",
    )
    assert "Hijaz" in actual
    assert "D" in actual
    assert_golden("maqam_hijaz", actual)


def test_gamelan_cipher_slendro():
    actual = run_svg(
        "--type", "gamelan-cipher",
        "--tuning", "slendro",
        "--pattern", "1 2 3 5 6 1",
        "--width", "600", "--height", "200",
    )
    assert "1" in actual and "2" in actual
    assert_golden("gamelan_slendro", actual)


def test_chord_box_dm7_guitar():
    actual = run_svg(
        "--type", "chord-box",
        "--instrument", "guitar",
        "--chord", "Dm7",
        "--fingering", "x x 0 2 1 1",
        "--width", "200", "--height", "240",
    )
    assert "Dm7" in actual
    assert_golden("chord_dm7", actual)


def test_neume_basic():
    actual = run_svg(
        "--type", "neume",
        "--neumes", "punctum climacus torculus",
        "--text", "Ky-ri-e",
        "--mode", "I",
        "--width", "600", "--height", "200",
    )
    assert "<rect" in actual
    assert_golden("neume_basic", actual)


def test_sargam_yaman_ascending():
    actual = run_svg(
        "--type", "sargam",
        "--notes", "Sa Re Ga Ma Pa Dha Ni",
        "--tradition", "hindustani",
        "--width", "600", "--height", "200",
    )
    assert "Sa" in actual
    assert "Ni" in actual
    assert_golden("sargam_yaman_aro", actual)


def test_jianpu_c_major_scale():
    actual = run_svg(
        "--type", "jianpu",
        "--notes", "1 2 3 4 5 6 7 1",
        "--key", "1=C",
        "--time-sig", "4/4",
        "--width", "600", "--height", "200",
    )
    assert "1=C" in actual
    assert_golden("jianpu_c_major", actual)


def test_gongche_pentatonic():
    actual = run_svg(
        "--type", "gongche",
        "--notes", "上 尺 工 六 五",
        "--width", "600", "--height", "200",
    )
    assert "<text" in actual
    assert_golden("gongche_penta", actual)


def test_rhythm_grid_funk():
    actual = run_svg(
        "--type", "rhythm-grid",
        "--steps", "16",
        "--tracks", "Kick:x...x...x...x.;Snare:....x.......x...;HiHat:x.x.x.x.x.x.x.x.",
        "--width", "700", "--height", "200",
    )
    assert "Kick" in actual
    assert_golden("rhythm_funk", actual)


def test_clave_son_3_2():
    actual = run_svg(
        "--type", "clave",
        "--pattern", "1 0 0 1 0 0 1 0 1 0 0 0 1 0 0 0",
        "--style", "3-2",
        "--tradition", "latin",
        "--width", "700", "--height", "260",
    )
    assert "<circle" in actual
    assert_golden("clave_son_3_2", actual)


def test_tala_teentaal():
    actual = run_svg(
        "--type", "tala",
        "--tala", "teentaal",
        "--tradition", "hindustani",
        "--width", "500", "--height", "500",
    )
    assert "Teentaal" in actual
    assert_golden("tala_teentaal", actual)
