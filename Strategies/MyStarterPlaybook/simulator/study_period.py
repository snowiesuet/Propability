"""Inclusive filters for historical account studies, keyed by session date."""

from datetime import date

from account_engine import CompletedTrade


def _parse(value: str | None, label: str) -> date | None:
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD")
    return parsed


def select_period(events, start_date: str | None = None, end_date: str | None = None):
    """Return events within inclusive session-date bounds and period metadata.

    Session IDs are ISO dates assigned by the existing Eastern session-reset
    function. A SessionClose is included according to the session it closes,
    even though its observation timestamp may be on the following calendar day.
    """
    start = _parse(start_date, "--start-date")
    end = _parse(end_date, "--end-date")
    if start is not None and end is not None and start > end:
        raise ValueError("--start-date must be on or before --end-date")
    selected = tuple(event for event in events
                     if (start is None or date.fromisoformat(event.session_id) >= start)
                     and (end is None or date.fromisoformat(event.session_id) <= end))
    if not selected:
        raise ValueError("Selected date range contains no observed account events")
    sessions = sorted({event.session_id for event in selected})
    trade_count = sum(isinstance(event, CompletedTrade) for event in selected)
    return selected, {
        "start_date_inclusive": start.isoformat() if start else None,
        "end_date_inclusive": end.isoformat() if end else None,
        "session_date_basis": "session_id, assigned by the configured Eastern session reset",
        "observed_session_count": len(sessions),
        "first_observed_session": sessions[0],
        "last_observed_session": sessions[-1],
        "trade_count": trade_count,
    }
