from __future__ import annotations

"""Jurisdiction scoping for every case read (planversionalpha.md C.2).

One helper, applied inside the services rather than at each endpoint: an
endpoint that forgets to scope leaks cases across districts, and there is no
way to notice that in review. ``tests/test_scoping.py`` asserts that every
investigate endpoint returns 404 for another unit's case.

The materialised ``unit_path`` makes "everything under my unit" a single
indexed prefix match, identical on SQLite and Postgres.
"""

from sqlalchemy import Select, or_

from app.core.permissions import Scope, scope_of
from app.db.models import CaseRecord, UserRecord

# A case filed by a citizen has no officer and therefore no unit, so it sits
# at the root path. That is the shared intake queue: any officer may see it in
# order to triage and verify it, after which it belongs to their unit. Without
# this, a citizen report would be invisible to everyone and could never be
# verified (planversionalpha.md C.3).
INTAKE_PATH = "/"


def visible_path(user: UserRecord | None) -> str | None:
    """The unit path prefix this user may read, or ``None`` for everything."""

    if user is None:
        return None
    if scope_of(user.role) is Scope.ALL:
        return None
    return getattr(user, "unit_path", None) or "/"


def scope_filter(statement: Select, user: UserRecord | None) -> Select:
    """Restrict a CaseRecord query to what ``user`` may see."""

    if user is None:
        return statement
    scope = scope_of(user.role)
    if scope is Scope.ALL:
        return statement

    if scope is Scope.OWN_SUBMISSIONS:
        # An operator sees only what they submitted, wherever it was filed.
        return statement.where(CaseRecord.created_by == user.id)

    intake = CaseRecord.unit_path == INTAKE_PATH

    path = _unit_path_of(user)
    if path is None:
        # A user with no unit yet can still see their own submissions; they
        # must not silently see the whole state.
        return statement.where(CaseRecord.created_by == user.id)

    if scope is Scope.SUBTREE:
        return statement.where(or_(CaseRecord.unit_path.startswith(path), intake))

    # STATION: this unit exactly, the shared intake queue, plus anything the
    # officer filed themselves.
    return statement.where(
        or_(CaseRecord.unit_path == path, CaseRecord.created_by == user.id, intake)
    )


def can_see_case(user: UserRecord | None, case: CaseRecord) -> bool:
    """Same decision as ``scope_filter``, for a single already-loaded case."""

    if user is None:
        return True
    scope = scope_of(user.role)
    if scope is Scope.ALL:
        return True
    if case.created_by is not None and case.created_by == user.id:
        return True
    if scope is Scope.OWN_SUBMISSIONS:
        return False
    path = _unit_path_of(user)
    if path is None:
        return False
    case_path = case.unit_path or INTAKE_PATH
    if case_path == INTAKE_PATH:
        return True
    if scope is Scope.SUBTREE:
        return case_path.startswith(path)
    return case_path == path


def _unit_path_of(user: UserRecord) -> str | None:
    unit = getattr(user, "unit", None)
    if unit is not None and getattr(unit, "path", None):
        return unit.path
    return getattr(user, "unit_path", None)


__all__ = ["can_see_case", "scope_filter", "visible_path"]
