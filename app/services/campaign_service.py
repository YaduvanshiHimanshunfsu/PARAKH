from __future__ import annotations

"""Campaign detection: group cases that come from one operation.

Linking (``link_service``) answers "what is connected to *this* case?". A
campaign is the transitive answer: every case reachable from every other through
a shared payment account, phone number, server, app signature — or through a
reworded copy of the same message template. Cases are the nodes, those shared
traces are the edges, and each connected component is one campaign.

Two rules keep components honest:

* Only identifiers that point at an operator link cases. A full URL is too
  specific to add anything its domain does not, an IFSC names a bank branch
  rather than an account, and platform hosts such as ``t.me`` or ``bit.ly``
  are shared by thousands of unrelated messages.
* Template similarity only links cases of the same artifact type, using the
  same SimHash threshold as the per-case similarity panel.
"""

import difflib
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CaseRecord
from app.schemas import (
    ArtifactType,
    Campaign,
    CampaignEdge,
    CampaignGraph,
    CampaignIdentifier,
    CampaignNode,
    CampaignTextChange,
    CampaignTimelineEntry,
    IdentifierType,
    RiskLevel,
)
from app.services.case_service import to_summary
from app.services.link_service import identifier_weight, links_cases
from app.utils.fingerprint import NEAR_DUPLICATE_THRESHOLD, hamming_distance

# Pairwise template comparison is quadratic, so it only looks at recent cases.
_SIMILARITY_WINDOW = 600
_MAX_GRAPH_IDENTIFIERS = 30
_MAX_CHANGES = 6
_MAX_DIFF_CHARS = 4_000

_RISK_ORDER = {RiskLevel.HIGH: 0, RiskLevel.MEDIUM: 1, RiskLevel.LOW: 2}
_TYPE_LABEL = {
    IdentifierType.UPI: "UPI",
    IdentifierType.PHONE: "Phone",
    IdentifierType.BANK_ACCOUNT: "Account",
    IdentifierType.CRYPTO_BTC: "BTC wallet",
    IdentifierType.CRYPTO_ETH: "ETH wallet",
    IdentifierType.CERT_SHA256: "Signing cert",
    IdentifierType.ICON_PHASH: "App icon",
    IdentifierType.PACKAGE: "App",
    IdentifierType.TELEGRAM: "Telegram",
    IdentifierType.IP: "Server",
    IdentifierType.EMAIL: "Email",
    IdentifierType.DOMAIN: "Domain",
}


def _utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def text_changes(before: str, after: str) -> list[CampaignTextChange]:
    """Word-level differences between a message and its earlier variant."""

    old = before[:_MAX_DIFF_CHARS].split()
    new = after[:_MAX_DIFF_CHARS].split()
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    changes: list[CampaignTextChange] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        removed = " ".join(old[i1:i2]).strip(".,;:!?")
        added = " ".join(new[j1:j2]).strip(".,;:!?")
        if not removed and not added:
            continue
        changes.append(CampaignTextChange(before=_clip(removed, 80), after=_clip(added, 80)))
        if len(changes) >= _MAX_CHANGES:
            break
    return changes


def _case_label(case: CaseRecord) -> str:
    details = case.details or {}
    if case.artifact_type == ArtifactType.APK.value:
        label = details.get("app_label") or details.get("package") or "Android app"
    elif case.artifact_type == ArtifactType.WEBSITE.value:
        label = (case.summary or "Website").split(" — ")[0]
    else:
        # Variants of one template start with identical words, so the text
        # cannot tell them apart; kind and date can.
        kind = {"MESSAGE": "Message", "EMAIL": "Email", "URL": "Link"}.get(case.artifact_type, "Case")
        label = f"{kind} · {_utc(case.created_at):%d %b}"
    return _clip(label or case.case_id, 28)


def _similarity(distance: int) -> int:
    return max(0, 100 - round(distance * 100 / (NEAR_DUPLICATE_THRESHOLD * 2)))


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            # The earliest case stays the root, so a campaign's ID is stable.
            self.parent[max(a, b)] = min(a, b)


async def build_campaign_graph(
    session: AsyncSession, *, max_cases: int = 1_000, min_cases: int = 2
) -> CampaignGraph:
    """Group the most recent cases into campaigns and lay them out as a graph."""

    recent = (
        (
            await session.execute(
                select(CaseRecord)
                .order_by(CaseRecord.created_at.desc(), CaseRecord.id.desc())
                .limit(max(1, min(max_cases, 2_000)))
            )
        )
        .scalars()
        .unique()
        .all()
    )
    cases = sorted(recent, key=lambda case: (_utc(case.created_at), case.id))
    groups = _UnionFind(len(cases))

    holders: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, case in enumerate(cases):
        for row in case.identifiers:
            if links_cases(row.type, row.value):
                holders[(row.type, row.value)].append(index)
    shared = {key: indexes for key, indexes in holders.items() if len(indexes) >= 2}
    for indexes in shared.values():
        for other in indexes[1:]:
            groups.union(indexes[0], other)

    # (earlier, later) -> similarity percentage
    similar: dict[tuple[int, int], int] = {}
    by_type: dict[str, list[int]] = defaultdict(list)
    window_start = max(0, len(cases) - _SIMILARITY_WINDOW)
    for index in range(window_start, len(cases)):
        if cases[index].simhash:
            by_type[cases[index].artifact_type].append(index)
    for indexes in by_type.values():
        for position, left in enumerate(indexes):
            for right in indexes[position + 1 :]:
                a, b = cases[left], cases[right]
                if a.content_sha256 and a.content_sha256 == b.content_sha256:
                    distance = 0
                else:
                    distance = hamming_distance(a.simhash, b.simhash)
                if distance <= NEAR_DUPLICATE_THRESHOLD:
                    similar[(left, right)] = _similarity(distance)
                    groups.union(left, right)

    components: dict[int, list[int]] = defaultdict(list)
    for index in range(len(cases)):
        components[groups.find(index)].append(index)

    campaigns: list[Campaign] = []
    nodes: list[CampaignNode] = []
    edges: list[CampaignEdge] = []
    for root, members in components.items():
        if len(members) < min_cases:
            continue
        member_set = set(members)
        campaign_id = f"CMP-{cases[root].case_id.split('-', 1)[-1]}"
        keys = sorted(
            (key for key, indexes in shared.items() if indexes[0] in member_set),
            key=lambda key: (
                -identifier_weight(IdentifierType(key[0])) * len(shared[key]),
                key[1],
            ),
        )
        key_identifiers = [
            CampaignIdentifier(type=IdentifierType(t), value=v, case_count=len(shared[(t, v)]))
            for t, v in keys
        ]
        campaigns.append(
            _campaign(campaign_id, [cases[i] for i in members], members, key_identifiers, similar)
        )

        for index in members:
            case = cases[index]
            nodes.append(
                CampaignNode(
                    id=f"c:{case.case_id}",
                    kind="case",
                    label=_case_label(case),
                    campaign_id=campaign_id,
                    case_id=case.case_id,
                    artifact_type=ArtifactType(case.artifact_type),
                    risk_level=RiskLevel(case.risk_level),
                )
            )
        for type_value, value in keys[:_MAX_GRAPH_IDENTIFIERS]:
            identifier_type = IdentifierType(type_value)
            node_id = f"i:{type_value}:{value}"
            nodes.append(
                CampaignNode(
                    id=node_id,
                    kind="identifier",
                    label=_clip(value, 40),
                    campaign_id=campaign_id,
                    identifier_type=identifier_type,
                    value=value,
                    case_count=len(shared[(type_value, value)]),
                )
            )
            for index in shared[(type_value, value)]:
                edges.append(
                    CampaignEdge(
                        source=f"c:{cases[index].case_id}",
                        target=node_id,
                        kind="identifier",
                        weight=min(100, identifier_weight(identifier_type) * 10),
                    )
                )
        for (left, right), score in similar.items():
            if left in member_set:
                edges.append(
                    CampaignEdge(
                        source=f"c:{cases[left].case_id}",
                        target=f"c:{cases[right].case_id}",
                        kind="similar",
                        weight=score,
                    )
                )

    campaigns.sort(key=lambda item: item.last_seen, reverse=True)
    campaigns.sort(key=lambda item: (-item.case_count, _RISK_ORDER[item.risk_level]))
    return CampaignGraph(
        campaigns=campaigns,
        nodes=nodes,
        edges=edges,
        cases_scanned=len(cases),
        linked_case_count=sum(item.case_count for item in campaigns),
    )


def _campaign(
    campaign_id: str,
    members: list[CaseRecord],
    indexes: list[int],
    key_identifiers: list[CampaignIdentifier],
    similar: dict[tuple[int, int], int],
) -> Campaign:
    if key_identifiers:
        top = key_identifiers[0]
        name = f"{_TYPE_LABEL.get(top.type, top.type.value)} {top.value}"
    else:
        name = f"Repeated template: “{_clip(' '.join((members[0].content_text or '').split()), 48)}”"

    timeline: list[CampaignTimelineEntry] = []
    seen_identifiers: set[tuple[str, str]] = set()
    position_of = {index: position for position, index in enumerate(indexes)}
    for position, case in enumerate(members):
        index = indexes[position]
        parent = max(
            (
                (score, earlier)
                for (earlier, later), score in similar.items()
                if later == index and earlier in position_of
            ),
            default=None,
        )
        variant_of = similarity = None
        changes: list[CampaignTextChange] = []
        if parent is not None:
            similarity, earlier = parent
            source = members[position_of[earlier]]
            variant_of = source.case_id
            changes = text_changes(source.content_text or "", case.content_text or "")

        own = sorted(
            (
                (row.type, row.value)
                for row in case.identifiers
                if links_cases(row.type, row.value)
            ),
            key=lambda key: -identifier_weight(IdentifierType(key[0])),
        )
        fresh = [key for key in own if key not in seen_identifiers]
        seen_identifiers.update(own)

        summary = to_summary(case)
        timeline.append(
            CampaignTimelineEntry(
                case_id=case.case_id,
                created_at=summary.created_at,
                artifact_type=summary.artifact_type,
                risk_level=summary.risk_level,
                summary=summary.summary,
                preview=_clip(summary.preview, 300),
                variant_of=variant_of,
                similarity=similarity,
                changes=changes,
                new_identifiers=[f"{t}: {v}" for t, v in fresh[:8]] if position else [],
            )
        )

    return Campaign(
        campaign_id=campaign_id,
        name=_clip(name, 200),
        case_count=len(members),
        risk_level=min((RiskLevel(case.risk_level) for case in members), key=_RISK_ORDER.__getitem__),
        artifact_mix=dict(Counter(case.artifact_type for case in members)),
        first_seen=timeline[0].created_at,
        last_seen=timeline[-1].created_at,
        key_identifiers=key_identifiers[:12],
        timeline=timeline,
    )


__all__ = ["build_campaign_graph", "text_changes"]
