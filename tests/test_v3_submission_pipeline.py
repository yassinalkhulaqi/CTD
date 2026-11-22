"""Tests for the flag submission pipeline feature."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import ConflictError, NotFoundError, ValidationError
from ctf_team_dashboard.features.submission_pipeline.models import (
    DEFAULT_RULES,
    SubmissionStatus,
    can_transition,
    cipher_flag,
    expected_flag,
    flag_digest,
    normalize_flag,
    validate_flag_format,
)
from ctf_team_dashboard.features.submission_pipeline.service import (
    SubmissionPipelineService,
    is_seeded_answer,
    validate_without_storage,
)
from ctf_team_dashboard.repositories import Repositories

FLAG_PATTERN = r"^flag\{[a-z0-9_]+\}$"


def first_pair(seeded: Repositories) -> tuple[str, str, str]:
    """Return a challenge id, member id and the expected flag for the challenge."""
    challenges = seeded.challenges.list_all()
    members = seeded.members.list_all()
    challenge = challenges[0]
    member = next(m for m in members if m.team_id == challenge.team_id)
    return challenge.id, member.id, expected_flag(challenge.title)


def submit(service: SubmissionPipelineService, challenge: str, member: str, flag: str) -> Any:
    """Submit a flag through the service."""
    return service.submit(challenge_id=challenge, member_id=member, flag=flag)


# ----------------------------------------------------------------------
# Pure domain behaviour
# ----------------------------------------------------------------------
def test_normalize_flag_trims_lowercases_and_strips_quotes() -> None:
    assert normalize_flag("  FLAG{Hello_World}  ") == "flag{hello_world}"
    assert normalize_flag('"flag{abc}"') == "flag{abc}"
    assert normalize_flag("`FLAG{ABC}`") == "flag{abc}"
    assert normalize_flag("flag{ hello world }") == "flag{_hello_world_}"


def test_flag_digest_is_stable_and_case_insensitive() -> None:
    first = flag_digest("challenge-1", "FLAG{AbC}")
    assert first == flag_digest("challenge-1", "flag{abc}")
    assert first != flag_digest("challenge-2", "flag{abc}")
    assert len(first) == 64


def test_cipher_flag_masks_the_answer() -> None:
    masked = cipher_flag("flag{supersecretvalue}")
    assert masked.startswith("flag{")
    assert "supersecret" not in masked
    assert masked.endswith("lue}")


def test_expected_flag_is_deterministic() -> None:
    assert expected_flag("Nonce Reuse") == "flag{nonce_reuse}"
    assert is_seeded_answer("Nonce Reuse", "  FLAG{NONCE_REUSE} ") is True
    assert is_seeded_answer("Nonce Reuse", "flag{wrong}") is False


def test_format_validation_uses_enabled_rules() -> None:
    assert validate_flag_format("flag{abc_123}", DEFAULT_RULES).accepted is True
    bad = validate_flag_format("not-a-flag", DEFAULT_RULES)
    assert bad.accepted is False
    assert bad.code == "format_invalid"
    assert validate_flag_format("", DEFAULT_RULES).code == "format_empty"
    assert validate_without_storage("  FLAG{ABC} ", DEFAULT_RULES).accepted is True


def test_status_transition_rules() -> None:
    assert can_transition(SubmissionStatus.QUEUED, SubmissionStatus.VALIDATING) is True
    assert can_transition(SubmissionStatus.VALIDATING, SubmissionStatus.ACCEPTED) is True
    assert can_transition(SubmissionStatus.REJECTED, SubmissionStatus.RETRYING) is True
    assert can_transition(SubmissionStatus.ACCEPTED, SubmissionStatus.RETRYING) is False
    from ctf_team_dashboard.features.submission_pipeline.models import assert_transition

    with pytest.raises(ValidationError):
        assert_transition(SubmissionStatus.QUEUED, SubmissionStatus.ACCEPTED)


def test_retry_policy_backoff_and_budget() -> None:
    from ctf_team_dashboard.features.submission_pipeline.models import RetryPolicy

    policy = RetryPolicy(max_attempts=3, backoff_seconds=2.0, max_backoff_seconds=10.0)
    assert [policy.delay_for(n) for n in (0, 1, 2, 3, 4)] == [0.0, 2.0, 4.0, 8.0, 10.0]
    assert policy.can_retry(1) is True
    assert policy.can_retry(2) is True
    assert policy.can_retry(3) is False
    scheduled = policy.schedule_after(2, utcnow())
    assert scheduled > utcnow()


# ----------------------------------------------------------------------
# Service behaviour
# ----------------------------------------------------------------------
def test_submit_creates_queued_submission(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submission = submit(service, challenge, member, flag)
    assert submission.status is SubmissionStatus.QUEUED
    assert submission.attempts == 0
    assert submission.accepted is True
    assert submission.flag_digest == flag_digest(challenge, flag)
    assert service.get_submission(submission.id).id == submission.id


def test_submit_validates_challenge_member_and_format(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    with pytest.raises(NotFoundError):
        submit(service, "missing-challenge", member, flag)
    with pytest.raises(NotFoundError):
        submit(service, challenge, "missing-member", flag)
    with pytest.raises(ValidationError) as exc:
        submit(service, challenge, member, "garbage")
    assert exc.value.details["code"] == "format_invalid"


def test_submit_rejects_duplicate_flag(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submit(service, challenge, member, flag)
    with pytest.raises(ConflictError) as exc:
        submit(service, challenge, member, f"  {flag.upper()}  ")
    assert "submission_id" in exc.value.details


def test_process_queue_accepts_correct_flag(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submission = submit(service, challenge, member, flag)
    summary = service.process_queue()
    assert summary.processed == 1
    assert summary.accepted == 1
    assert summary.remaining == 0
    final = service.get_submission(submission.id)
    assert final.status is SubmissionStatus.ACCEPTED
    assert final.attempts == 1
    assert final.completed_at is not None
    assert final.error is None


def test_process_queue_rejects_wrong_flag(seeded: Repositories) -> None:
    challenge, member, _ = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submission = submit(service, challenge, member, "flag{definitely_wrong}")
    summary = service.process_queue()
    assert summary.rejected == 1
    final = service.get_submission(submission.id)
    assert final.status is SubmissionStatus.REJECTED
    assert final.error == "flag_mismatch"


def test_retry_respects_policy_backoff_and_reschedules(seeded: Repositories) -> None:
    challenge, member, _ = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submission = submit(service, challenge, member, "flag{definitely_wrong}")
    service.process_queue()

    now = utcnow()
    retrying = service.retry_submission(submission.id, now=now)
    assert retrying.status is SubmissionStatus.RETRYING
    assert retrying.next_attempt_at is not None
    assert retrying.next_attempt_at > now

    skipped = service.process_queue(now=now + timedelta(seconds=1))
    assert skipped.processed == 0
    assert skipped.skipped == 1

    done = service.process_queue(now=now + timedelta(seconds=10))
    assert done.processed == 1
    assert done.rejected == 1
    assert service.get_submission(submission.id).attempts == 2


def test_retry_with_replacement_flag_can_be_accepted(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submission = submit(service, challenge, member, "flag{definitely_wrong}")
    service.process_queue()
    corrected = service.retry_submission(submission.id, flag=f" {flag.upper()} ")
    assert corrected.accepted is True
    assert corrected.flag_digest == flag_digest(challenge, flag)
    service.process_queue(now=utcnow() + timedelta(seconds=30))
    assert service.get_submission(submission.id).status is SubmissionStatus.ACCEPTED


def test_retry_rejects_invalid_status_and_exhausted_budget(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    accepted = submit(service, challenge, member, flag)
    service.process_queue()
    with pytest.raises(ValidationError):
        service.retry_submission(accepted.id)

    wrong = submit(service, challenge, member, "flag{another_wrong}")
    service.process_queue()
    service.retry_submission(wrong.id)
    service.process_queue(now=utcnow() + timedelta(seconds=30))
    service.retry_submission(wrong.id)
    service.process_queue(now=utcnow() + timedelta(seconds=60))
    assert service.get_submission(wrong.id).attempts == 3
    with pytest.raises(ValidationError) as exc:
        service.retry_submission(wrong.id)
    assert exc.value.details["max_attempts"] == 3


def test_retry_rejects_duplicate_replacement(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    first = submit(service, challenge, member, flag)
    service.process_queue()
    second = submit(service, challenge, member, "flag{a_completely_different_value}")
    service.process_queue()
    with pytest.raises(ConflictError):
        service.retry_submission(second.id, flag=flag)
    assert first.status is SubmissionStatus.QUEUED


def test_list_filters_by_status_challenge_and_member(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submit(service, challenge, member, flag)
    submit(service, challenge, member, "flag{another_guess_here}")
    queued = service.list_submissions(status=SubmissionStatus.QUEUED)
    assert len(queued) == 2
    assert all(item.challenge_id == challenge for item in queued)
    assert len(service.list_submissions(challenge_id="nope")) == 0
    assert len(service.list_submissions(member_id=member)) == 2


def test_stats_aggregate_by_status_and_member(seeded: Repositories) -> None:
    challenge, member, flag = first_pair(seeded)
    service = SubmissionPipelineService(repositories=seeded)
    submit(service, challenge, member, flag)
    submit(service, challenge, member, "flag{not_the_answer}")
    service.process_queue()
    stats = service.stats()
    assert stats.total == 2
    assert stats.by_status["accepted"] == 1
    assert stats.by_status["rejected"] == 1
    assert stats.accepted == 1
    assert stats.acceptance_rate == 0.5
    assert stats.average_attempts == 1.0
    assert stats.by_member[0].member_id == member
    assert stats.by_member[0].acceptance_rate == 0.5


def test_rule_crud_updates_validation(seeded: Repositories) -> None:
    service = SubmissionPipelineService(repositories=seeded)
    assert len(service.list_rules()) >= 2
    rule = service.create_rule(
        name="Suffix check",
        pattern=r"^flag\{[a-z0-9_]+\}$",
        description="Only lower case flags are accepted.",
        priority=5,
    )
    assert service.get_rule(rule.id).name == "Suffix check"
    updated = service.update_rule(rule.id, description="Updated hint", enabled=False)
    assert updated.description == "Updated hint"
    assert updated.enabled is False
    assert service.delete_rule(rule.id) is True
    assert service.delete_rule(rule.id) is False
    with pytest.raises(ValidationError):
        service.create_rule(name="Broken", pattern="[unclosed")


# ----------------------------------------------------------------------
# Router behaviour
# ----------------------------------------------------------------------
def _entities(client: TestClient) -> tuple[str, str, str]:
    challenge = client.get("/api/challenges").json()[0]
    members = client.get("/api/members").json()
    member = next(m for m in members if m["team_id"] == challenge["team_id"])
    return challenge["id"], member["id"], expected_flag(challenge["title"])


def test_router_submission_lifecycle(client: TestClient) -> None:
    challenge, member, flag = _entities(client)
    created = client.post(
        "/api/submissions",
        json={"challenge_id": challenge, "member_id": member, "flag": flag},
    )
    assert created.status_code == 201
    submission = created.json()
    assert submission["status"] == "queued"
    assert submission["accepted"] is True

    listed = client.get("/api/submissions", params={"status": "queued"})
    assert listed.status_code == 200
    assert any(item["id"] == submission["id"] for item in listed.json())

    detail = client.get(f"/api/submissions/{submission['id']}")
    assert detail.status_code == 200
    assert detail.json()["id"] == submission["id"]

    processed = client.post("/api/submissions/process", json={"limit": 10})
    assert processed.status_code == 200
    assert processed.json()["accepted"] == 1

    stats = client.get("/api/submissions/stats")
    assert stats.status_code == 200
    assert stats.json()["by_status"]["accepted"] == 1


def test_router_validation_and_conflict_errors(client: TestClient) -> None:
    challenge, member, flag = _entities(client)
    invalid = client.post(
        "/api/submissions",
        json={"challenge_id": challenge, "member_id": member, "flag": "garbage"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert invalid.json()["error"]["details"]["code"] == "format_invalid"

    client.post(
        "/api/submissions",
        json={"challenge_id": challenge, "member_id": member, "flag": flag},
    )
    duplicate = client.post(
        "/api/submissions",
        json={"challenge_id": challenge, "member_id": member, "flag": flag.upper()},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


def test_router_retry_and_rules_endpoints(client: TestClient) -> None:
    challenge, member, _ = _entities(client)
    created = client.post(
        "/api/submissions",
        json={
            "challenge_id": challenge,
            "member_id": member,
            "flag": "flag{definitely_wrong}",
        },
    ).json()
    client.post("/api/submissions/process", json={})
    retry = client.post(f"/api/submissions/{created['id']}/retry", json={})
    assert retry.status_code == 200
    assert retry.json()["status"] == "retrying"

    rules = client.get("/api/submissions/rules")
    assert rules.status_code == 200
    assert any(rule["id"] == "rule-format" for rule in rules.json())

    created_rule = client.post(
        "/api/submissions/rules",
        json={
            "name": "Custom",
            "pattern": FLAG_PATTERN,
            "description": "Custom hint",
            "priority": 30,
        },
    )
    assert created_rule.status_code == 201
    assert created_rule.json()["name"] == "Custom"


def test_router_not_found(client: TestClient) -> None:
    response = client.get("/api/submissions/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
