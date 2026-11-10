"""
``python -m inkfold.run report.py --as-of 2026-10-30``: build, save and check a report.

Loads a :class:`~inkfold.report.Report` subclass from the target module,
constructs it with the CLI parameters, calls ``build()``, and writes the
rendered document to ``output/``. With no ``--out`` flag the default is
``output/<stem>.html`` (and ``.txt``).

Exit codes match ``python -m inkfold.check``: 0 clean, 1 lint errors,
2 build failed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from inkfold.builder.document import Document
from inkfold.builder.exceptions import EmailBuilderError, ValidationError
from inkfold.check.lint import (
    Severity,
    format_findings,
    layout_findings,
    lint_html,
    render_for_check,
)
from inkfold.check.target import TargetError, split_target
from inkfold.data.exceptions import DataError

from . import load_report

EXIT_OK = 0
EXIT_LINT_ERRORS = 1
EXIT_BUILD_FAILED = 2

#: Where the two parts land unless ``--out`` says otherwise.
DEFAULT_OUT_DIR = Path("output")


def _parse_args(argv: list[str]) -> tuple[str, Path, dict[str, str]]:
    """``(target, out_dir, overrides)`` from the raw argv.

    The first positional argument is the target. Every ``--key value``
    pair after it is a report parameter. ``--out DIR`` is consumed here.
    """
    if not argv:
        print("usage: python -m inkfold.run TARGET [--key value ...]", file=sys.stderr)
        raise SystemExit(2)

    target = argv[0]
    overrides: dict[str, str] = {}
    out_dir = DEFAULT_OUT_DIR
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--out" and i + 1 < len(argv):
            out_dir = Path(argv[i + 1])
            i += 2
            continue
        if arg.startswith("--") and i + 1 < len(argv):
            key = arg[2:].replace("-", "_")
            overrides[key] = argv[i + 1]
            i += 2
        else:
            print(f"error: unexpected argument {arg!r}", file=sys.stderr)
            raise SystemExit(2)
    return target, out_dir, overrides


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    try:
        target, out_dir, overrides = _parse_args(argv)
    except SystemExit:
        return EXIT_BUILD_FAILED

    try:
        report = load_report(target, overrides)
        result = report.build()
    except (TargetError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED
    except (EmailBuilderError, DataError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED

    if not isinstance(result, Document):
        print(
            f"error: build() returned {type(result).__name__}, expected a Document.",
            file=sys.stderr,
        )
        return EXIT_BUILD_FAILED

    document = result
    try:
        html = render_for_check(document)
        text = document.text()
    except EmailBuilderError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED

    # Strip a :ClassName suffix but keep a Windows drive letter.
    path_part, _attribute = split_target(target)
    if not path_part:
        path_part = target
    stem = Path(path_part).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    for suffix, part in (("html", html), ("txt", text)):
        destination = out_dir / f"{stem}.{suffix}"
        destination.write_text(part, encoding="utf-8")
        print(f"{destination}  ({len(part.encode('utf-8')) / 1024:.1f} KB)")

    findings = lint_html(html, document.medium.name, document.rendered_sections())
    findings += layout_findings(document)
    print(format_findings(findings))
    failed = any(finding.severity is Severity.ERROR for finding in findings)
    return EXIT_LINT_ERRORS if failed else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
