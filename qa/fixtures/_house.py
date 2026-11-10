"""The firm the house-template fixtures speak for, and the close they are as of (v0.8.0)."""

from __future__ import annotations

from datetime import date, timedelta

from inkfold.house import House

#: The close every house fixture's data is as of: a Friday, so the weekly wrap closes a week.
CLOSE = date(2026, 11, 6)

#: Who supplies the fixtures' figures, and how stale they may be.
SOURCE = "Hermes Research; illustrative sample data"
FRESH = timedelta(days=3)

HOUSE = House(
    firm_name="Hermes Research",
    department="Global Equity",
    disclaimer=(
        "<p>Illustrative sample only: the portfolio is fictional and every figure is "
        "invented. Not investment advice.</p>"
    ),
)
