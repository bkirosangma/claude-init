"""Unit tests for kb_transform.py — focused on the frontmatter sources path
introduced in MVP-5b. The CLI is invoked as a subprocess so we exercise the
real entry point, not the helper module surface."""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "kb_transform.py"


def run_transform(path: Path, args: list[str] | None = None) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *(args or [])],
        capture_output=True, text=True, check=False,
    )
    return proc.stdout, proc.returncode


def test_legacy_title_only_frontmatter_is_stripped(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("---\ntitle: My Doc\n---\n\nBody text.\n")
    out, rc = run_transform(p)
    assert rc == 0, out
    text = p.read_text()
    # No frontmatter.
    assert not text.startswith("---")
    # Title promoted to H1 since there was no existing H1.
    assert text.startswith("# My Doc")
    assert "Body text." in text


def test_inline_sources_rewritten_to_block_list(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text(
        '---\n'
        'sources: [{url: "https://a.example.com", title: "First"}, {url: "https://b.example.com"}]\n'
        '---\n\n'
        '# Existing H1\n\nBody.\n'
    )
    out, rc = run_transform(p)
    assert rc == 0, out
    text = p.read_text()
    # Frontmatter preserved.
    assert text.startswith("---\n")
    # Sources now in canonical block form.
    assert 'sources:\n' in text
    assert '  - url: "https://a.example.com"\n' in text
    assert '    title: "First"\n' in text
    assert '  - url: "https://b.example.com"\n' in text
    # No more inline `[{` form.
    assert "[{" not in text


def test_block_sources_round_trip_preserves_data(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text(
        '---\n'
        'sources:\n'
        '  - url: "https://a.example.com"\n'
        '    title: "First"\n'
        '  - url: "https://b.example.com"\n'
        '---\n\n'
        '# H1\n\nBody.\n'
    )
    out, rc = run_transform(p)
    assert rc == 0, out
    text = p.read_text()
    assert 'sources:\n' in text
    assert '  - url: "https://a.example.com"\n' in text
    assert '    title: "First"\n' in text
    assert '  - url: "https://b.example.com"\n' in text
    # Title stays absent on the second entry.
    second = text.split('  - url: "https://b.example.com"\n', 1)[1]
    assert not second.lstrip().startswith('title:')


def test_sources_with_bad_urls_are_dropped_during_transform(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text(
        '---\n'
        'sources: [{url: "javascript:alert(1)", title: "JS"}, {url: "https://safe.example.com"}]\n'
        '---\n\n'
        '# H1\n\nBody.\n'
    )
    out, rc = run_transform(p)
    assert rc == 0, out
    text = p.read_text()
    assert 'https://safe.example.com' in text
    assert 'javascript:' not in text


def test_empty_title_in_sources_is_omitted_after_transform(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text(
        '---\n'
        'sources:\n'
        '  - url: "https://a.example.com"\n'
        '    title: ""\n'
        '---\n\n'
        '# H1\n\nBody.\n'
    )
    out, rc = run_transform(p)
    assert rc == 0, out
    text = p.read_text()
    assert 'https://a.example.com' in text
    # Empty title was omitted.
    assert 'title: ""' not in text


def test_frontmatter_with_only_invalid_sources_is_stripped(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text(
        '---\n'
        'title: Tossed\n'
        'sources: [{url: "not-a-url"}]\n'
        '---\n\n'
        'Body.\n'
    )
    out, rc = run_transform(p)
    assert rc == 0, out
    text = p.read_text()
    # Sources were all invalid → no preserved frontmatter.
    assert not text.startswith('---')
    # Title still promoted to H1.
    assert text.startswith('# Tossed')


def test_dry_run_does_not_write_file(tmp_path):
    p = tmp_path / "doc.md"
    original = '---\ntitle: Foo\n---\n\nBody.\n'
    p.write_text(original)
    out, rc = run_transform(p, ["--dry-run"])
    assert rc == 0, out
    assert p.read_text() == original
