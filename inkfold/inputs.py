"""
A report's declared data inputs, each checked for freshness when it loads (roadmap v0.7.0).

A method decorated with :func:`data_input` loads one input and returns it
:class:`Dated`. Read as an attribute, it is the loaded :class:`Dataset`: named,
sourced, dated, and refused before anything renders when it is older than its
``max_age`` at the report's ``as_of`` or dated after it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from inkfold.builder.exceptions import ValidationError
from inkfold.builder.provenance import Dataset, format_date

if TYPE_CHECKING:
    from inkfold.report import Report

T = TypeVar("T")

#: Where a report keeps the inputs it has loaded, in its instance dictionary.
_LOADED = "_inkfold_loaded_inputs"


class FreshnessError(ValidationError):
    """A declared input whose date the report's as-of date does not admit."""


class StaleDataError(FreshnessError):
    """An input older than its ``max_age`` at the report's as-of date."""


class FutureDataError(FreshnessError):
    """An input dated after the report's as-of date: data the report could not have had."""


@dataclass(frozen=True)
class Dated(Generic[T]):
    """What a loader returns: the data, and the date it is as of."""

    value: T
    as_of: date


class Input(Generic[T]):
    """
    One declared input on a :class:`~inkfold.report.Report`, made by :func:`data_input`.

    Read from the class, it is this declaration; read from a report, it is the
    loaded :class:`Dataset`, loaded once per report and checked against the
    report's ``as_of`` before it is returned. A loader's own exception is not
    caught: a failed fetch says why in its own words.
    """

    def __init__(self, loader: Callable[[Any], Dated[T]], source: str, max_age: timedelta):
        self.loader = loader
        self.source = source
        self.max_age = max_age
        self.name = loader.__name__

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @overload
    def __get__(self, report: None, owner: type) -> Input[T]: ...
    @overload
    def __get__(self, report: Report, owner: type) -> Dataset[T]: ...
    def __get__(self, report: Report | None, owner: type) -> Input[T] | Dataset[T]:
        if report is None:
            return self
        loaded: dict[str, Dataset[Any]] = report.__dict__.setdefault(_LOADED, {})
        if self.name not in loaded:
            loaded[self.name] = self.load(report)
        dataset: Dataset[T] = loaded[self.name]
        return dataset

    def load(self, report: Report) -> Dataset[T]:
        """Run the loader and check the date it returns against the report's."""
        dated = self.loader(report)
        if not isinstance(dated, Dated):
            raise ValidationError(
                f"input {self.name!r} returned {type(dated).__name__}; "
                "a loader returns Dated(value, as_of)."
            )
        dataset = Dataset(self.name, self.source, dated.as_of, dated.value)
        report_date: date = report.as_of  # type: ignore[attr-defined]
        age = report_date - dataset.as_of
        if age < timedelta(0):
            raise FutureDataError(
                f"input {self.name!r} is as of {format_date(dataset.as_of)}, after the "
                f"report's {format_date(report_date)}."
            )
        if age > self.max_age:
            raise StaleDataError(
                f"input {self.name!r} is as of {format_date(dataset.as_of)}, {age.days} days "
                f"before the report's {format_date(report_date)}; its max_age is "
                f"{self.max_age.days} days."
            )
        return dataset


def data_input(
    *, source: str, max_age: timedelta
) -> Callable[[Callable[[Any], Dated[T]]], Input[T]]:
    """Declare the decorated method a data input from ``source``, fresh for ``max_age``."""
    if not isinstance(source, str) or not source.strip():
        raise ValidationError(f"a data input's source is non-blank text, got: {source!r}")
    if not isinstance(max_age, timedelta) or max_age < timedelta(0):
        raise ValidationError(
            f"a data input's max_age is a timedelta of 0 or more, got: {max_age!r}"
        )

    def declare(loader: Callable[[Any], Dated[T]]) -> Input[T]:
        return Input(loader, source, max_age)

    return declare


def declared_inputs(cls: type) -> dict[str, Input[Any]]:
    """Every input ``cls`` declares, base classes' first, in the order they were written."""
    found: dict[str, Input[Any]] = {}
    for klass in reversed(cls.__mro__):
        for name, value in vars(klass).items():
            if isinstance(value, Input):
                found[name] = value
    return found


__all__ = [
    "Dated",
    "FreshnessError",
    "FutureDataError",
    "Input",
    "StaleDataError",
    "data_input",
    "declared_inputs",
]
