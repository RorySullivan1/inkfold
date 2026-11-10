"""
Where a figure came from: a dated, named dataset, and the source line it prints.

A :class:`Dataset` is one declared input's data with its source and as-of date
(roadmap v0.7.0). An exhibit or a section given one as ``source=`` prints its
source line from it, and records it, so ``Document.provenance()`` can list
every exhibit and section with the data it was drawn from.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Generic, TypeVar

from .exceptions import ValidationError

T = TypeVar("T")

#: English month names, so a date reads the same under any locale.
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def format_date(day: date) -> str:
    """``8 October 2026``: the house form of an as-of date, independent of locale."""
    return f"{day.day} {_MONTHS[day.month - 1]} {day.year}"


@dataclass(frozen=True)
class Dataset(Generic[T]):
    """
    One declared input's data, with the source and the date it is as of.

    Made by a report's :func:`~inkfold.report.data_input` when the input loads,
    so a dataset always names the input it came from. ``value`` is whatever the
    loader returned: rows, a frame, a mapping.
    """

    name: str
    source: str
    as_of: date
    value: T = field(compare=False)

    def __post_init__(self) -> None:
        for name in ("name", "source"):
            text = getattr(self, name)
            if not isinstance(text, str) or not text.strip():
                raise ValidationError(f"a Dataset's {name} is non-blank text, got: {text!r}")
        if type(self.as_of) is not date:
            kind = "a datetime" if isinstance(self.as_of, datetime) else type(self.as_of).__name__
            raise ValidationError(f"Dataset {self.name!r}'s as_of is a date, got {kind}.")


#: What ``source=`` takes on an exhibit or a section.
SourceArg = str | Dataset | Sequence[Dataset] | None


@dataclass(frozen=True)
class Provenance:
    """One exhibit or section, and a dataset it was drawn from."""

    where: str
    dataset: str
    source: str
    as_of: date


def resolve_source(
    source: SourceArg, as_of: str | None, owner: str, *, dated: bool = True
) -> tuple[str, str, tuple[Dataset, ...]]:
    """
    ``(source, as_of, datasets)`` as an exhibit or section stores them.

    A string passes through with the caller's ``as_of``. Datasets print their
    sources joined by ``; `` and their one date as ``as_of``; when their dates
    differ, each source carries its own and ``as_of`` is empty. ``dated=False``
    is for a holder with no ``as_of`` of its own, which folds the date into the
    source. A dataset's date may not be contradicted by a typed ``as_of``.
    """
    if source is None or isinstance(source, str):
        return source or "", as_of or "", ()
    if isinstance(source, Dataset):
        datasets: tuple[Dataset, ...] = (source,)
    elif isinstance(source, Sequence) and not isinstance(source, str):
        datasets = tuple(source)
    else:
        datasets = ()
    if not datasets or not all(isinstance(d, Dataset) for d in datasets):
        raise ValidationError(f"{owner}'s source is plain text, or Datasets, got: {source!r}")
    if as_of:
        raise ValidationError(
            f"{owner}'s source is a Dataset, which carries its own date; drop as_of={as_of!r}."
        )
    names = list(dict.fromkeys(d.source for d in datasets))
    dates = {d.as_of for d in datasets}
    if len(dates) == 1 and dated:
        return "; ".join(names), format_date(datasets[0].as_of), datasets
    if len(dates) == 1:
        return f"{'; '.join(names)} as of {format_date(datasets[0].as_of)}", "", datasets
    each = dict.fromkeys(f"{d.source} as of {format_date(d.as_of)}" for d in datasets)
    return "; ".join(each), "", datasets


def check_source(source: object, owner: str) -> None:
    """Refuse a ``source=`` that is neither text nor datasets, before anything reads it."""
    if source is None or isinstance(source, str | Dataset):
        return
    if isinstance(source, Sequence) and all(isinstance(d, Dataset) for d in source):
        return
    raise ValidationError(
        f"{owner}'s source is plain text, or Datasets, got: {type(source).__name__}"
    )


__all__ = ["Dataset", "Provenance", "SourceArg", "check_source", "format_date", "resolve_source"]
