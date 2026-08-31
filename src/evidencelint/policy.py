from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

from .models import (
    POLICY_SCHEMA_VERSION,
    AuditReport,
    EvidenceStatus,
    PolicyEvaluation,
    PolicyLevel,
)


BLOCKING_STATUSES = frozenset({EvidenceStatus.FAILED, EvidenceStatus.MISSING})


@dataclass(frozen=True)
class Policy:
    levels: dict[str, PolicyLevel]
    reasons: dict[str, str]
    digest: str
    source: str

    def level_for(self, rule_id: str) -> PolicyLevel:
        return self.levels.get(rule_id, PolicyLevel.REQUIRED)


def default_policy() -> Policy:
    payload = {"schema_version": POLICY_SCHEMA_VERSION, "rules": {}}
    return Policy(
        levels={},
        reasons={},
        digest=_digest(payload),
        source="default",
    )


def load_policy(path: Path, *, rule_ids: Iterable[str]) -> Policy:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except OSError as exc:
        raise ValueError(f"could not read policy: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"policy is not valid JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError("policy must be a JSON object")
    if payload.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ValueError(f"policy schema_version must be {POLICY_SCHEMA_VERSION}")
    rules = payload.get("rules")
    if not isinstance(rules, dict):
        raise ValueError("policy rules must be an object")

    known_rules = set(rule_ids)
    levels: dict[str, PolicyLevel] = {}
    reasons: dict[str, str] = {}
    for rule_id, configuration in rules.items():
        if rule_id not in known_rules:
            raise ValueError(f"policy names unknown rule: {rule_id}")
        if not isinstance(configuration, dict):
            raise ValueError(f"policy rule {rule_id} must be an object")
        level = configuration.get("level")
        try:
            resolved_level = PolicyLevel(level)
        except ValueError as exc:
            raise ValueError(
                f"policy rule {rule_id} level must be required or advisory"
            ) from exc
        reason = configuration.get("reason")
        if resolved_level is PolicyLevel.ADVISORY:
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"policy advisory rule {rule_id} needs a reason")
            reasons[rule_id] = reason.strip()
        elif reason is not None:
            raise ValueError(f"policy required rule {rule_id} must not include a reason")
        levels[rule_id] = resolved_level

    return Policy(
        levels=levels,
        reasons=reasons,
        digest=_digest(payload),
        source="custom",
    )


def apply_policy(report: AuditReport, policy: Policy) -> AuditReport:
    blocking_rule_ids = tuple(
        finding.rule_id
        for finding in report.findings
        if is_blocking(finding.rule_id, finding.status, policy)
    )
    advisory_rules = tuple(
        finding.rule_id
        for finding in report.findings
        if policy.level_for(finding.rule_id) is PolicyLevel.ADVISORY
    )
    evaluation = PolicyEvaluation(
        schema_version=POLICY_SCHEMA_VERSION,
        digest=policy.digest,
        source=policy.source,
        advisory_rules=advisory_rules,
        blocking_rule_ids=blocking_rule_ids,
        reasons=policy.reasons,
    )
    return replace(report, policy=evaluation)


def is_blocking(rule_id: str, status: EvidenceStatus, policy: Policy) -> bool:
    return policy.level_for(rule_id) is PolicyLevel.REQUIRED and status in BLOCKING_STATUSES


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise ValueError(f"policy contains duplicate key: {key}")
        payload[key] = value
    return payload
