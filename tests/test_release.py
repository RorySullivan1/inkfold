"""
The release workflow matches the publisher PyPI trusts (roadmap v0.5.0).

PyPI's trusted publisher for ``inkfold`` names a repository, a workflow file and an
environment; an upload from anything else is refused. These hold the workflow, the
metadata, the changelog and the README to what that registration and the policy say.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: The pending publisher registered on PyPI on 2026-11-09. Change these only with it.
PUBLISHER = {
    "project": "inkfold",
    "owner": "RorySullivan1",
    "repository": "inkfold",
    "workflow": "release.yml",
    "environment": "pypi",
}

WORKFLOW = ROOT / ".github" / "workflows" / PUBLISHER["workflow"]


def _project() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def _jobs() -> dict[str, str]:
    """Each job's block of the workflow, by name; the YAML is read as text, needing no parser."""
    text = WORKFLOW.read_text(encoding="utf-8")
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([\w-]+):\n", body, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


class TestTheWorkflow:
    def test_it_is_the_file_the_publisher_names(self):
        assert WORKFLOW.is_file()

    def test_it_runs_on_a_version_tag_and_nothing_else(self):
        trigger = WORKFLOW.read_text(encoding="utf-8").split("\non:\n", 1)[1].split("\n\n")[0]
        assert trigger.split() == ["push:", "tags:", '["v*"]']

    def test_only_the_publish_job_can_mint_a_token_and_it_runs_in_the_environment(self):
        top = WORKFLOW.read_text(encoding="utf-8").split("\njobs:\n", 1)[0]
        assert "id-token" not in top  # a workflow-level grant reaches every job
        jobs = _jobs()
        minting = [name for name, block in jobs.items() if "id-token: write" in block]
        assert minting == ["publish"]
        publish = jobs["publish"]
        assert f"name: {PUBLISHER['environment']}\n" in publish.split("environment:", 1)[1]
        assert "uses: pypa/gh-action-pypi-publish@release/v1" in publish
        assert "needs: build" in publish

    def test_no_secret_is_used(self):
        text = WORKFLOW.read_text(encoding="utf-8").lower()
        for word in ("secrets.", "password", "api-token", "api_token"):
            assert word not in text, word

    def test_the_build_runs_the_artefact_checks_and_a_render(self):
        build = _jobs()["build"]
        for step in (
            'git merge-base --is-ancestor "$GITHUB_SHA" origin/main',
            'GITHUB_REF_NAME"',
            "pytest tests/test_release.py",
            "python -m build",
            "twine check --strict dist/*",
            "python -m qa.distribution dist",
            "python -m inkfold.check draft.py:build",
        ):
            assert step in build, step

    def test_the_release_is_verified_from_pypi_after_the_upload(self):
        verify = _jobs()["verify"]
        assert "needs: publish" in verify and "id-token" not in verify
        assert 'pip install --no-cache-dir $flag "inkfold==$version"' in verify
        assert "python -m inkfold.check draft.py:build" in verify


class TestTheMetadata:
    def test_the_project_and_repository_are_the_publishers(self):
        project = _project()
        assert project["name"] == PUBLISHER["project"]
        repository = f"https://github.com/{PUBLISHER['owner']}/{PUBLISHER['repository']}"
        assert project["urls"]["Repository"] == repository

    def test_the_licence_is_mit(self):
        assert _project()["license"] == "MIT"


class TestTheChangelog:
    def test_the_version_has_a_dated_entry(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        version = re.escape(_project()["version"])
        assert re.search(rf"^## \[{version}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.MULTILINE)
        assert re.search(rf"^\[{version}\]: https://", changelog, re.MULTILINE)

    def test_it_keeps_an_unreleased_section(self):
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert "## [Unreleased]" in changelog and "Keep a Changelog" in changelog


class TestTheReadme:
    def test_it_states_the_open_core_licence_and_the_deprecation_window(self):
        readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
        assert "pip install inkfold" in readme
        assert "licensed separately" in readme
        assert "at least two minor releases and at least 90 days" in readme

    def test_every_link_resolves_on_pypi(self):
        # PyPI renders the README as the project page, where a relative link leads nowhere
        # and a heading has no anchor to jump to.
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        relative = re.findall(r"\]\((?!https?://|mailto:)([^)]+)\)", readme)
        assert relative == []
