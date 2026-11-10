"""
Load and run a :class:`~inkfold.report.Report` from a Python file.

``load_report("report.py", {"as_of": "2026-10-30"})`` imports the module,
finds the first :class:`Report` subclass (or the one named after the colon
in ``report.py:DailyNote``), coerces each CLI string to the field's type,
and returns a constructed instance whose ``build()`` is ready to call.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import ModuleType

from inkfold.builder.exceptions import ValidationError
from inkfold.check.target import TargetError, import_module, split_target
from inkfold.report import Report


def _find_report_class(module: ModuleType, path: Path) -> type[Report]:
    """The first ``Report`` subclass defined in *module*."""
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, Report) and obj is not Report and obj.__module__ == module.__name__:
            return obj
    raise TargetError(
        f"{path} defines no Report subclass. "
        f"Expected a class that inherits from inkfold.report.Report."
    )


def load_report(target: str, overrides: dict[str, str]) -> Report:
    """
    A constructed :class:`Report` from ``path/to/report.py`` or
    ``report.py:ClassName``.

    Without ``:ClassName``, scans the module for the first ``Report``
    subclass defined there.  Each ``--key value`` string in *overrides*
    is coerced to the field's annotated type.

    Raises:
        TargetError: For a missing file, one that cannot be imported,
            or one with no ``Report`` subclass.
        ValidationError: When a parameter fails type or value checking.
    """
    path_text, attribute = split_target(target)

    # split_target returns ("", rest) when there is no colon beyond a
    # Windows drive.  In that case the whole target is the path.
    if not path_text:
        path_text = target
        attribute = ""

    path = Path(path_text)
    if not path.suffix:
        path = path.with_suffix(".py")

    module = import_module(path)

    if attribute:
        cls = getattr(module, attribute, None)
        if cls is None:
            raise TargetError(f"{path} has no attribute {attribute!r}.")
        if not (isinstance(cls, type) and issubclass(cls, Report)):
            raise TargetError(f"{attribute!r} in {path} is not a Report subclass.")
    else:
        cls = _find_report_class(module, path)

    try:
        return cls.from_cli(overrides)
    except ValidationError:
        raise
    except TypeError as exc:
        raise ValidationError(str(exc)) from exc
