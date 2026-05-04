"""Shared pytest fixtures for kb_* tests."""
from pathlib import Path
import json
import textwrap
import pytest


@pytest.fixture
def archetypes_dir(tmp_path):
    """Empty archetypes directory; tests add their own files."""
    d = tmp_path / "archetypes"
    d.mkdir()
    return d


@pytest.fixture
def write_archetype(archetypes_dir):
    """Helper that writes a single-file archetype with frontmatter."""
    def _write(name: str, indicators: list[str]) -> Path:
        p = archetypes_dir / f"{name}.md"
        body = textwrap.dedent(f"""\
            ---
            name: {name}
            description: test archetype
            domain-indicators: [{', '.join(indicators)}]
            ---

            # {name}
            """)
        p.write_text(body)
        return p
    return _write


@pytest.fixture
def write_meta_archetype(archetypes_dir):
    """Helper that writes a meta-archetype directory with manifest.json."""
    def _write(name: str, manifest: dict, sub_files: dict[str, str] | None = None) -> Path:
        d = archetypes_dir / name
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps(manifest, indent=2))
        if sub_files:
            for rel, content in sub_files.items():
                target = d / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
        return d
    return _write
