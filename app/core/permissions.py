from __future__ import annotations

"""Roles, ranks and what each may do (planversionalpha.md C.2).

Three separate ideas, deliberately not merged:

* **rank** is the officer's position in the force. The law cares about it:
  IT Act 2000 s.78 reserves investigation of IT Act offences to an officer
  not below the rank of Inspector.
* **role** is what the product lets them do.
* **unit** is what they may see, by jurisdiction.

Every read path must be scoped by unit, or data leaks across districts, so
``scope_filter`` is applied inside the case, link and campaign services rather
than at the endpoint, where it would be easy to forget.
"""

from enum import Enum


class Rank(str, Enum):
    DGP = "DGP"
    ADG = "ADG"
    IG = "IG"
    SP = "SP"
    ADDL_SP = "ADDL_SP"
    DYSP = "DYSP"
    INSPECTOR = "INSPECTOR"
    SI = "SI"
    ASI = "ASI"
    HC = "HC"
    CONSTABLE = "CONSTABLE"


# Seniority order, highest first. Used for the s.78 check, not for permissions.
RANK_ORDER: tuple[Rank, ...] = (
    Rank.DGP, Rank.ADG, Rank.IG, Rank.SP, Rank.ADDL_SP, Rank.DYSP,
    Rank.INSPECTOR, Rank.SI, Rank.ASI, Rank.HC, Rank.CONSTABLE,
)
_RANK_INDEX = {rank: index for index, rank in enumerate(RANK_ORDER)}


class Role(str, Enum):
    OPERATOR = "OPERATOR"
    IO = "IO"
    STATION_HEAD = "STATION_HEAD"
    SUPERVISOR = "SUPERVISOR"
    STATE_VIEWER = "STATE_VIEWER"
    ADMIN = "ADMIN"
    # The single shared account that existed before Phase C. Treated as ADMIN
    # so an existing deployment keeps working after an upgrade.
    OFFICER = "OFFICER"


class Permission(str, Enum):
    CASE_CREATE = "case.create"
    CASE_VIEW = "case.view"
    CASE_ASSIGN = "case.assign"
    CASE_TRANSFER = "case.transfer"
    CASE_UPDATE = "case.update"
    CASE_VERIFY = "case.verify"
    IDENTIFIER_ROLE_CHANGE = "identifier.role_change"
    DOCUMENT_DRAFT = "document.draft"
    APPROVE_STATION = "approve.station"
    APPROVE_SUPERVISOR = "approve.supervisor"
    EXPORT_FULL = "export.full"
    EXPORT_REDACTED = "export.redacted"
    AUDIT_VIEW = "audit.view"
    USER_MANAGE = "user.manage"


P = Permission

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OPERATOR: frozenset({P.CASE_CREATE, P.CASE_VIEW, P.EXPORT_REDACTED}),
    Role.IO: frozenset({
        P.CASE_CREATE, P.CASE_VIEW, P.CASE_UPDATE, P.IDENTIFIER_ROLE_CHANGE,
        P.DOCUMENT_DRAFT, P.EXPORT_FULL, P.EXPORT_REDACTED,
    }),
    Role.STATION_HEAD: frozenset({
        P.CASE_CREATE, P.CASE_VIEW, P.CASE_UPDATE, P.CASE_ASSIGN, P.CASE_TRANSFER,
        P.CASE_VERIFY, P.IDENTIFIER_ROLE_CHANGE, P.DOCUMENT_DRAFT, P.APPROVE_STATION,
        P.EXPORT_FULL, P.EXPORT_REDACTED, P.AUDIT_VIEW,
    }),
    Role.SUPERVISOR: frozenset({
        P.CASE_CREATE, P.CASE_VIEW, P.CASE_UPDATE, P.CASE_ASSIGN, P.CASE_TRANSFER,
        P.CASE_VERIFY, P.IDENTIFIER_ROLE_CHANGE, P.DOCUMENT_DRAFT, P.APPROVE_STATION,
        P.APPROVE_SUPERVISOR, P.EXPORT_FULL, P.EXPORT_REDACTED, P.AUDIT_VIEW,
    }),
    # Read-only across the state: sees everything, changes nothing.
    Role.STATE_VIEWER: frozenset({P.CASE_VIEW, P.EXPORT_REDACTED, P.AUDIT_VIEW}),
    Role.ADMIN: frozenset(Permission),
    Role.OFFICER: frozenset(Permission),
}


class Scope(str, Enum):
    """How much of the case store a role may read."""

    OWN_SUBMISSIONS = "OWN_SUBMISSIONS"
    STATION = "STATION"
    SUBTREE = "SUBTREE"
    ALL = "ALL"


ROLE_SCOPE: dict[Role, Scope] = {
    Role.OPERATOR: Scope.OWN_SUBMISSIONS,
    Role.IO: Scope.STATION,
    Role.STATION_HEAD: Scope.STATION,
    Role.SUPERVISOR: Scope.SUBTREE,
    Role.STATE_VIEWER: Scope.ALL,
    Role.ADMIN: Scope.ALL,
    Role.OFFICER: Scope.ALL,
}

# IT Act 2000 s.78: an offence under the IT Act is investigated by an officer
# not below the rank of Inspector.
MIN_IT_ACT_RANK = Rank.INSPECTOR


def as_role(value: "str | Role | None") -> Role:
    """Parse a role. Unknown or missing values get the least privilege.

    Accepts an enum member as well as a string: ``str(Role.IO)`` renders as
    "Role.IO", so coercing blindly would silently downgrade every caller that
    passes the enum.
    """

    if isinstance(value, Role):
        return value
    try:
        return Role(str(value or "").strip().upper())
    except ValueError:
        return Role.OPERATOR


def as_rank(value: "str | Rank | None") -> Rank | None:
    if isinstance(value, Rank):
        return value
    try:
        return Rank(str(value or "").strip().upper())
    except ValueError:
        return None


def permissions_for(role: "str | Role | None") -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(as_role(role), frozenset())


def has_permission(role: "str | Role | None", permission: Permission) -> bool:
    return permission in permissions_for(role)


def rank_at_least(rank: "str | Rank | None", minimum: Rank) -> bool:
    parsed = as_rank(rank)
    if parsed is None:
        return False
    return _RANK_INDEX[parsed] <= _RANK_INDEX[minimum]


def can_investigate_it_act(rank: "str | Rank | None") -> bool:
    """IT Act s.78 gate, used before a case is assigned."""

    return rank_at_least(rank, MIN_IT_ACT_RANK)


def scope_of(role: "str | Role | None") -> Scope:
    return ROLE_SCOPE.get(as_role(role), Scope.OWN_SUBMISSIONS)


__all__ = [
    "Rank",
    "RANK_ORDER",
    "Role",
    "Permission",
    "Scope",
    "ROLE_PERMISSIONS",
    "ROLE_SCOPE",
    "MIN_IT_ACT_RANK",
    "as_rank",
    "as_role",
    "can_investigate_it_act",
    "has_permission",
    "permissions_for",
    "rank_at_least",
    "scope_of",
]
