"""
The artefact checks catch what they exist to catch (#237).

The real wheel and sdist are built and checked in CI's ``wheel`` job; these
build small stand-ins so each check is proven to fail without a build backend.
"""

from __future__ import annotations

import io
import re
import tarfile
import zipfile
from pathlib import Path

import pytest

from qa.distribution import PACKAGE, main, sdist_problems, wheel_problems

ROOT = Path(__file__).resolve().parent.parent


def _wheel(path: Path, names: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as wheel:
        for name in names:
            wheel.writestr(name, "")
    return path


def _sdist(path: Path, names: list[str]) -> Path:
    with tarfile.open(path, "w:gz") as sdist:
        for name in names:
            info = tarfile.TarInfo(f"inkfold-0.1.0/{name}")
            sdist.addfile(info, io.BytesIO(b""))
    return path


LIBRARY = [
    "pyproject.toml",
    "README.md",
    "LICENSE",
    "PKG-INFO",
    f"{PACKAGE}/__init__.py",
]
WHEEL = [f"{PACKAGE}/__init__.py", f"{PACKAGE}/py.typed", "inkfold-0.1.0.dist-info/METADATA"]


class TestTheWheel:
    def test_the_marker_is_in_the_source_package(self):
        marker = ROOT / PACKAGE / "py.typed"
        assert marker.is_file() and marker.read_bytes() == b""

    def test_a_wheel_with_the_marker_passes(self, tmp_path):
        assert wheel_problems(_wheel(tmp_path / "p.whl", WHEEL)) == []

    def test_a_wheel_without_it_is_named(self, tmp_path):
        wheel = _wheel(tmp_path / "p.whl", [name for name in WHEEL if "py.typed" not in name])
        assert wheel_problems(wheel) == [f"p.whl is missing {PACKAGE}/py.typed"]

    def test_a_second_import_root_is_named(self, tmp_path):
        # The retired svc shim is the case this exists for (#255).
        wheel = _wheel(tmp_path / "p.whl", [*WHEEL, "svc/__init__.py"])
        assert wheel_problems(wheel) == [f"p.whl installs svc, beside {PACKAGE}"]

    def test_the_command_fails_on_it(self, tmp_path, capsys):
        _wheel(tmp_path / "p.whl", [f"{PACKAGE}/__init__.py"])
        assert main([str(tmp_path)]) == 1
        assert "missing" in capsys.readouterr().err

    def test_the_command_fails_on_an_empty_directory(self, tmp_path):
        assert main([str(tmp_path)]) == 1


class TestTheSdist:
    def test_the_library_alone_passes(self, tmp_path):
        assert sdist_problems(_sdist(tmp_path / "p.tar.gz", [*LIBRARY, ".gitignore"])) == []

    def test_every_stray_root_is_named(self, tmp_path):
        extra = [".claude/memory/INDEX.md", "tests/test_x.py", "qa/lint.py", "svc/__init__.py"]
        problems = sdist_problems(_sdist(tmp_path / "p.tar.gz", [*LIBRARY, *extra]))
        assert [p.split(" carries ")[1].split(",")[0] for p in problems] == [
            ".claude",
            "qa",
            "svc",
            "tests",
        ]

    def test_a_missing_licence_or_readme_is_named(self, tmp_path):
        sdist = _sdist(
            tmp_path / "p.tar.gz",
            ["pyproject.toml", f"{PACKAGE}/__init__.py"],
        )
        assert sdist_problems(sdist) == [
            "p.tar.gz is missing README.md",
            "p.tar.gz is missing LICENSE",
        ]

    def test_the_repository_config_matches_the_check(self):
        import tomllib

        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        included = set(config["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"])
        assert included <= {PACKAGE, "pyproject.toml", "README.md", "LICENSE"}
        assert config["project"]["license-files"] == ["LICENSE"]
        assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_nothing_in_the_repository_imports_the_retired_name():
    """``svc`` was the import root until #248 and its shim was removed in #255."""
    offenders = [
        str(path.relative_to(ROOT))
        for top in (PACKAGE, "qa", "tests", "examples", "drafts")
        for path in (ROOT / top).rglob("*.py")
        if any(
            line.lstrip().startswith(("import svc", "from svc"))
            for line in path.read_text(encoding="utf-8").splitlines()
        )
    ]
    assert offenders == []


#: The project's former names (before v0.4.0, and v0.4.0's, which PyPI prohibits), spelled so this
#: file does not match itself.
OLD_NAME = "py" + "hermes"
OLD_NAMES = (OLD_NAME, "oct" + "avo")

#: Files that are history in full: the memory's session logs and archive, and a dated review ledger.
HISTORY = (".claude/memory/sessions/", ".claude/skills/claim-grounding/reviews/ledger.jsonl")

#: The cards that record a rename, wherever they sit.
RENAME_CARDS = ("# version: v0.4.0\n", "# version: v0.4.1\n")

#: An old name as code: an import, a module path or an environment variable, never history.
CODE = re.compile(
    rf"(?i)\b(?:{'|'.join(OLD_NAMES)})(?:[./]|_[A-Z])|import (?:{'|'.join(OLD_NAMES)})"
)

#: The one name that stays: the session branch that built the roadmap.
KEPT = (f"integrate-claude-assets-{OLD_NAME}",)


def _current_lines(name: str, text: str) -> list[tuple[int, str]]:
    """The lines of ``name`` that state current truth, which must not use the old name."""
    lines = list(enumerate(text.splitlines(), 1))
    if name == ".claude/memory/INDEX.md":
        # State and Threads are current truth; Decisions and Log are history.
        section, current = "", []
        for n, line in lines:
            section = line[3:].split()[0] if line.startswith("## ") else section
            if section in ("State", "Threads"):
                current.append((n, line))
        lines = current
    if name == ".meta/roadmap/INDEX.md":
        # Its dated Decisions and a shipped version's row are records; the rest is the plan.
        section, current = "", []
        for n, line in lines:
            section = line[3:].split()[0] if line.startswith("## ") else section
            if section != "Decisions" and "| shipped" not in line:
                current.append((n, line))
        lines = current
    shipped = re.search(r"^status: shipped$", text, re.MULTILINE)
    if name.startswith(".meta/") and (shipped or text.startswith(RENAME_CARDS)):
        return []  # a shipped card, or a rename's own, is a record
    if name.startswith((".claude/memory/", ".meta/")):  # a rename line may name both, not as code
        lines = [
            (n, line) for n, line in lines if "inkfold" not in line.lower() or CODE.search(line)
        ]
    return lines


def test_the_old_names_survive_only_in_history():
    """Allegro's Hermes client owns the first name (v0.4.0); PyPI prohibits the second (v0.4.1)."""
    import re
    import subprocess

    listing = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    if listing.returncode != 0:
        pytest.skip("needs a git checkout to list the tracked files")
    pattern = re.compile("|".join(OLD_NAMES), re.IGNORECASE)
    offenders = []
    for name in filter(None, listing.stdout.decode("utf-8").split("\0")):
        if name.startswith(HISTORY):
            continue
        if pattern.search(name):
            offenders.append(name)
        path = ROOT / name
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue  # a binary file, or one deleted but not yet staged
        for n, line in _current_lines(name, text):
            for kept in KEPT:
                line = re.sub(re.escape(kept), "", line, flags=re.IGNORECASE)
            if pattern.search(line):
                offenders.append(f"{name}:{n}")
    assert offenders == []
