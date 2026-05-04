"""Unit tests for kb_archetype meta-archetype dispatch."""
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "kb_archetype.py"


def run(args: list[str]) -> tuple[str, int]:
    """Invoke kb_archetype.py and return (stdout, returncode)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, check=False,
    )
    return proc.stdout.strip(), proc.returncode


def test_single_file_archetype_returns_three_tokens_with_dash_sentinel(write_archetype, archetypes_dir):
    write_archetype("software-architecture", ["api", "microservice"])
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "design a microservice api",
    ])
    assert rc == 0
    parts = out.split(maxsplit=2)
    assert len(parts) == 3, f"expected 3 tokens, got: {out!r}"
    assert parts[0] == "software-architecture"
    assert parts[1] == "-"  # dash sentinel for single-file archetype
    assert parts[2].endswith("software-architecture.md")


def test_no_match_returns_no_match_string(archetypes_dir):
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "anything",
    ])
    assert rc == 0
    assert out == "no-match"


def test_meta_archetype_with_manifest_is_detected(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "description": "music family",
            "domain-indicators": ["music", "song", "scale"],
            "sub-archetypes": {"diagram": "diagram.md"},
        },
        sub_files={"diagram.md": "# music diagram"},
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "C major scale music",
        "--output-type", "diagram",
    ])
    assert rc == 0
    parts = out.split(maxsplit=2)
    assert len(parts) == 3
    assert parts[0] == "music"
    assert parts[1] == "diagram"
    assert parts[2].endswith("music/diagram.md")


def test_meta_document_dispatches_to_biography_on_keyword_hit(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "domain-indicators": ["music", "composer"],
            "sub-archetypes": {
                "document": {
                    "default": "documents/theory-primer.md",
                    "biography": "documents/biography.md",
                }
            },
            "purpose-keywords": {
                "biography": ["biography", "life of"],
            },
        },
        sub_files={
            "documents/theory-primer.md": "# theory primer",
            "documents/biography.md": "# biography",
        },
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "music composer biography of John Coltrane",
        "--output-type", "document",
        "--purpose-hint", "biography of John Coltrane",
    ])
    parts = out.split(maxsplit=2)
    assert parts[1] == "biography"
    assert parts[2].endswith("documents/biography.md")


def test_meta_document_falls_back_to_default_on_no_keyword_match(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "domain-indicators": ["music"],
            "sub-archetypes": {
                "document": {
                    "default": "documents/theory-primer.md",
                    "biography": "documents/biography.md",
                }
            },
            "purpose-keywords": {"biography": ["biography"]},
        },
        sub_files={
            "documents/theory-primer.md": "# primer",
            "documents/biography.md": "# bio",
        },
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "music theory primer",
        "--output-type", "document",
        "--purpose-hint", "what is a perfect fifth",
    ])
    parts = out.split(maxsplit=2)
    assert parts[1] == "default"
    assert parts[2].endswith("documents/theory-primer.md")


def test_meta_unsupported_output_type_returns_no_match(write_meta_archetype, archetypes_dir):
    write_meta_archetype(
        "music",
        {
            "name": "music",
            "domain-indicators": ["music"],
            "sub-archetypes": {"diagram": "diagram.md"},
        },
        sub_files={"diagram.md": "# diagram"},
    )
    out, rc = run([
        "--archetypes-dir", str(archetypes_dir),
        "--topic", "music composition",
        "--output-type", "tabs",  # not in manifest
    ])
    assert out == "no-match"


def test_software_architecture_still_resolves_in_real_archetypes_dir():
    """Phase 1 gate: software-architecture must keep working with no behavior change."""
    real_dir = Path(__file__).resolve().parents[2] / "archetypes"
    out, rc = run([
        "--archetypes-dir", str(real_dir),
        "--topic", "Kubernetes pod lifecycle microservice api",
    ])
    assert rc == 0
    parts = out.split(maxsplit=2)
    assert parts[0] == "software-architecture"
    assert parts[1] == "-"
    assert parts[2].endswith("software-architecture.md")


@pytest.mark.parametrize("topic,expected_subtype", [
    ("music biography of John Coltrane",         "biography"),
    ("composer life of Ravi Shankar",            "biography"),
    ("history of jazz harmony",                  "history-timeline"),
    ("evolution of polyphony chord",             "history-timeline"),
    ("song analysis of Hotel California",        "song-breakdown"),
    ("rhythm anatomy of Giant Steps",            "song-breakdown"),
    ("the sitar instrument",                     "instrument-profile"),
    ("Carnatic music",                           "tradition-overview"),
    ("Gamelan music",                            "tradition-overview"),
    ("Yaman mode vs Aeolian",                    "comparative"),
    ("modes across traditions",                  "comparative"),
    ("perfect fifth scale",                      "default"),  # matches scale domain-indicator
    ("what is a raga",                           "default"),  # matches raga domain-indicator
])
def test_real_music_archetype_dispatches_documents(topic, expected_subtype):
    real_dir = Path(__file__).resolve().parents[2] / "archetypes"
    out, rc = run([
        "--archetypes-dir", str(real_dir),
        "--topic", topic,
        "--output-type", "document",
        "--purpose-hint", topic,
    ])
    assert rc == 0, f"failed for topic {topic!r}: {out!r}"
    parts = out.split(maxsplit=2)
    assert parts[0] == "music", f"expected 'music' for {topic!r}, got {parts[0]!r}"
    assert parts[1] == expected_subtype, (
        f"expected subtype {expected_subtype!r} for topic {topic!r}, got {parts[1]!r}"
    )
