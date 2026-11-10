"""
A parameterised report: typed fields in, a renderable document out.

A ``Report`` is a frozen dataclass whose fields are the report's parameters
(as-of date, universe, client, etc.) and whose ``build()`` returns a
document the caller renders, checks or sends. Every parameter is validated
at construction — a bad one raises ``ValidationError`` before ``build()``
is ever called. A parameter is ``str``, ``int``, ``float``, ``bool``,
``date``, ``tuple[X, ...]`` of one of those, or any of them ``| None``.

``build()`` returns ``Renderable``, today an alias for ``Document``. When
the content model lands (roadmap Stage 2) the alias widens to
``Document | ContentModel`` in one line, and every caller typed against
``Renderable`` needs no change. A test pins the alias so the widening is a
conscious act.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from dataclasses import dataclass
from datetime import date
from typing import Any, get_type_hints

from inkfold.builder.document import Document
from inkfold.builder.exceptions import ValidationError
from inkfold.builder.provenance import Dataset
from inkfold.inputs import (
    Dated,
    FreshnessError,
    FutureDataError,
    Input,
    StaleDataError,
    data_input,
    declared_inputs,
    missing_inputs,
    required_input,
)

#: What ``build()`` returns. Today it is ``Document``; the alias widens to
#: ``Document | ContentModel`` when the content model arrives (Stage 2),
#: without a breaking change for callers typed against it.
Renderable = Document

_TRUE = frozenset({"true", "1", "yes"})
_FALSE = frozenset({"false", "0", "no"})


def _parse_bool(text: str) -> bool:
    lowered = text.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ValueError("expected true/false, 1/0 or yes/no")


#: The scalar types a parameter may have, and how the CLI parses each from a string.
_SCALARS: dict[type, Any] = {
    date: date.fromisoformat,
    int: int,
    float: float,
    str: str,
    bool: _parse_bool,
}


@dataclass(frozen=True)
class _ParamType:
    """A parameter's resolved type: a scalar, or a homogeneous tuple of one."""

    scalar: type
    is_tuple: bool = False

    @property
    def name(self) -> str:
        return f"tuple[{self.scalar.__name__}, ...]" if self.is_tuple else self.scalar.__name__


def _strip_optional(annotation: Any) -> Any:
    """``X`` from ``X | None`` or ``Optional[X]``; any other annotation unchanged."""
    if typing.get_origin(annotation) in (typing.Union, types.UnionType):
        non_none = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def _param_type(cls: type, name: str, annotation: Any) -> _ParamType:
    """The resolved type of a parameter, or ``ValidationError`` for one a report cannot take."""
    inner = _strip_optional(annotation)
    if inner in _SCALARS:
        return _ParamType(inner)
    if typing.get_origin(inner) is tuple:
        args = typing.get_args(inner)
        if len(args) == 2 and args[1] is Ellipsis and args[0] in _SCALARS:
            return _ParamType(args[0], is_tuple=True)
    raise ValidationError(
        f"{cls.__name__}.{name} is annotated {annotation!r}; a report parameter is "
        f"str, int, float, bool, date, or tuple[X, ...] of one of those."
    )


def _is_exactly(value: Any, scalar: type) -> bool:
    """``isinstance`` without the subclass leaks that matter for parameters.

    A ``bool`` is an ``int`` and a ``datetime`` is a ``date`` to Python, but
    neither is what a report that declared ``int`` or ``date`` asked for.
    An ``int`` is accepted where ``float`` is declared, as type checkers allow.
    """
    if scalar is float:
        return type(value) in (float, int)
    return type(value) is scalar


def _hints(cls: type) -> dict[str, Any]:
    try:
        return get_type_hints(cls)
    except Exception as exc:
        raise ValidationError(f"{cls.__name__}'s annotations cannot be resolved: {exc}") from exc


def _parse(text: str, scalar: type, name: str) -> Any:
    try:
        return _SCALARS[scalar](text)
    except (ValueError, TypeError) as exc:
        raise ValidationError(
            f"Cannot parse {text!r} as {scalar.__name__} for {name!r}: {exc}"
        ) from exc


@dataclass(frozen=True)
class Report:
    """
    A parameterised report whose ``build()`` returns a renderable document.

    Subclass with ``@dataclass(frozen=True)``, declare typed fields (as-of
    date, universe, client, etc.), and implement ``build()``. Every field is
    validated at construction — a bad parameter raises ``ValidationError``
    before ``build()`` is ever called. Override ``_validate()`` for checks
    that span fields.

    ``build()`` returns :data:`Renderable`, today a :class:`Document`.
    This type alias will widen to ``Document | ContentModel`` in a future
    release without a breaking change, so callers should handle the union
    or use ``isinstance``.
    """

    def __post_init__(self) -> None:
        missing = missing_inputs(type(self))
        if missing:
            listed = "; ".join(f"{name} ({inp.what})" for name, inp in missing.items())
            raise ValidationError(
                f"{type(self).__name__} must load each input its template reads with "
                f"@data_input: {listed}."
            )
        self._validate_fields()
        if self.inputs() and type(getattr(self, "as_of", None)) is not date:
            raise ValidationError(
                f"{type(self).__name__} declares data inputs, so it needs an `as_of: date` "
                "parameter to judge their freshness against."
            )
        self._validate()

    def _validate_fields(self) -> None:
        """Check each field's value against its annotation, exactly."""
        cls = type(self)
        hints = _hints(cls)
        for f in dataclasses.fields(self):
            value = getattr(self, f.name)
            annotation = hints[f.name]
            kind = _param_type(cls, f.name, annotation)
            if value is None:
                if _strip_optional(annotation) is not annotation:
                    continue
                raise ValidationError(f"{f.name!r} is required and cannot be None.")
            if kind.is_tuple:
                if type(value) is not tuple:
                    raise ValidationError(
                        f"{f.name!r} must be {kind.name}, got {type(value).__name__}."
                    )
                for item in value:
                    if not _is_exactly(item, kind.scalar):
                        raise ValidationError(
                            f"{f.name!r} must be {kind.name}; it holds "
                            f"{item!r}, a {type(item).__name__}."
                        )
            elif not _is_exactly(value, kind.scalar):
                raise ValidationError(
                    f"{f.name!r} must be {kind.name}, got {type(value).__name__}."
                )

    def _validate(self) -> None:
        """Override for cross-field validation. Called after field checks."""

    def build(self) -> Renderable:
        """Build the report. Must be implemented by every subclass."""
        raise NotImplementedError(f"{type(self).__name__} must implement build() -> Renderable")

    @classmethod
    def inputs(cls) -> dict[str, Input[Any]]:
        """The data inputs this report declares with ``@data_input``, by name."""
        return declared_inputs(cls)

    def load(self) -> tuple[Dataset[Any], ...]:
        """Load every declared input, in declaration order, raising on the first stale one."""
        return tuple(getattr(self, name) for name in self.inputs())

    @classmethod
    def params(cls) -> list[dataclasses.Field[Any]]:
        """The report's declared parameter fields."""
        return list(dataclasses.fields(cls))

    @classmethod
    def from_cli(cls, overrides: dict[str, str]) -> Report:
        """Construct from CLI ``--key value`` strings, parsing each to its type.

        A tuple parameter is given comma-separated (``--universe AAPL,MSFT``).
        An unknown key, a missing required one, or a value that does not
        parse raises ``ValidationError``.
        """
        hints = _hints(cls)
        fields = {f.name: f for f in dataclasses.fields(cls)}
        unknown = sorted(set(overrides) - set(fields))
        if unknown:
            known = ", ".join(f"--{name.replace('_', '-')}" for name in fields) or "none"
            names = ", ".join(f"--{name.replace('_', '-')}" for name in unknown)
            raise ValidationError(f"{cls.__name__} takes no {names}; its parameters are {known}.")

        kwargs: dict[str, Any] = {}
        for name, text in overrides.items():
            kind = _param_type(cls, name, hints[name])
            if kind.is_tuple:
                items = [part.strip() for part in text.split(",") if part.strip()]
                kwargs[name] = tuple(_parse(item, kind.scalar, name) for item in items)
            else:
                kwargs[name] = _parse(text, kind.scalar, name)

        missing = [
            name
            for name, f in fields.items()
            if name not in kwargs
            and f.default is dataclasses.MISSING
            and f.default_factory is dataclasses.MISSING
        ]
        if missing:
            names = ", ".join(f"--{name.replace('_', '-')}" for name in missing)
            raise ValidationError(f"{cls.__name__} requires {names}.")
        return cls(**kwargs)


__all__ = [
    "Dataset",
    "Dated",
    "FreshnessError",
    "FutureDataError",
    "Renderable",
    "Report",
    "StaleDataError",
    "data_input",
    "required_input",
]
