"""Tests for the writeups library feature."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from ctf_team_dashboard.domain.enums import ChallengeCategory, Difficulty
from ctf_team_dashboard.domain.models import utcnow
from ctf_team_dashboard.errors import NotFoundError, ValidationError
from ctf_team_dashboard.features.writeups_library.errors import (
    ApprovalRequiredError,
    DuplicateReviewError,
    DuplicateWriteupError,
    InvalidTransitionError,
    RatingOutOfRangeError,
    ReviewNotAllowedError,
)
from ctf_team_dashboard.features.writeups_library.models import (
    PRIOR_MEAN,
    ReviewVerdict,
    Writeup,
    WriteupBookmark,
    WriteupReview,
    WriteupStatus,
    bayesian_score,
    build_toc,
    count_words,
    excerpt,
    is_submittable,
    is_valid_rating,
    normalise_tags,
    reading_time,
    slugify,
    split_sections,
)
from ctf_team_dashboard.features.writeups_library.service import WriteupService
from ctf_team_dashboard.features.writeups_library.store import (
    WriteupBookmarkRepository,
    WriteupRepository,
    WriteupReviewRepository,
)

BODY = """# Reconstructing the stream

## Recovering the nonce

The server reused a nonce across two messages. That is a serious mistake.

```python
def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))
```

## Forging a ciphertext

With both plaintexts we can recover the keystream and craft any message we want.

### Verification

Submit the forged token and collect the flag.
"""


def make_writeup(**overrides: object) -> Writeup:
    """Build a deterministic writeup for domain and store tests."""
    values: dict[str, object] = {
        "id": "wu_test0000000001",
        "challenge_id": "challenge-1",
        "author_id": "member-1",
        "title": "Recovering the keystream",
        "summary": "A detailed walkthrough of the nonce reuse vulnerability.",
        "body": BODY,
        "category": ChallengeCategory.CRYPTO,
        "difficulty": Difficulty.HARD,
        "tags": ("crypto", "aes"),
        "status": WriteupStatus.DRAFT,
    }
    values.update(overrides)
    return Writeup(**values)  # type: ignore[arg-type]


def service_writeup(
    service: WriteupService,
    *,
    title: str = "Breaking the cipher",
    challenge_id: str = "challenge-1",
    author_id: str = "member-1",
    category: ChallengeCategory = ChallengeCategory.CRYPTO,
    status: WriteupStatus = WriteupStatus.DRAFT,
) -> Writeup:
    """Create a long writeup through the service layer."""
    writeup = service.create(
        challenge_id=challenge_id,
        author_id=author_id,
        title=title,
        summary="A complete and careful walkthrough of the solution.",
        body=BODY,
        category=category,
        difficulty=Difficulty.MEDIUM,
        tags=["crypto", "AES", "stream-cipher"],
    )
    if status is not WriteupStatus.DRAFT:
        writeup = service.submit(writeup.id)
    if status is WriteupStatus.PUBLISHED:
        service.add_review(
            writeup.id, "reviewer-1", ReviewVerdict.APPROVE, "Clear and accurate explanation."
        )
        writeup = service.publish(writeup.id)
    return writeup


def post_writeup(client: TestClient, **overrides: object) -> dict[str, object]:
    """Create a writeup through the HTTP API."""
    payload: dict[str, object] = {
        "challenge_id": "challenge-1",
        "author_id": "member-1",
        "title": "Breaking the cipher",
        "summary": "A complete and careful walkthrough of the solution.",
        "body": BODY,
        "category": "crypto",
        "difficulty": "medium",
        "tags": ["crypto", "AES"],
    }
    payload.update(overrides)
    response = client.post("/api/writeups", json=payload)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


class TestPureModels:
    def test_slugify_normalises_punctuation(self) -> None:
        assert slugify("  Hello, World!  ") == "hello-world"
        assert slugify("AES-GCM / Nonce Reuse") == "aes-gcm-nonce-reuse"
        assert slugify("***") == "writeup"

    def test_normalise_tags_cleans_and_caps(self) -> None:
        tags = normalise_tags(
            [
                "  #Crypto ",
                "crypto",
                "",
                "AES-GCM",
                "web",
                "pwn",
                " reversing ",
                "osint",
                "misc",
                "forensics",
            ]
        )
        assert tags[:3] == ("crypto", "aes-gcm", "web")
        assert len(tags) == 8
        assert len(set(tags)) == len(tags)

    def test_word_count_and_reading_time(self) -> None:
        assert count_words("one two three") == 3
        assert reading_time("") == 0
        assert reading_time("word " * 10, words_per_minute=200) == 1
        assert reading_time("word " * 401, words_per_minute=200) == 3

    def test_excerpt_strips_markdown_and_truncates(self) -> None:
        assert excerpt("# Title\nA `code` and [link](url) here.") == "Title A code and link here."
        long = excerpt("word " * 100, limit=40)
        assert long.endswith("…")
        assert len(long) <= 41

    def test_bayesian_score_uses_prior_and_bounds(self) -> None:
        assert bayesian_score(0, 0) == PRIOR_MEAN
        assert bayesian_score(5, 1) < 5.0
        assert bayesian_score(500, 100) > bayesian_score(5, 1)
        assert bayesian_score(-20, 1) == 1.0

    def test_build_toc_extracts_headings_and_dedupes(self) -> None:
        toc = build_toc(BODY)
        anchors = [entry.anchor for entry in toc]
        assert anchors == ["recovering-the-nonce", "forging-a-ciphertext", "verification"]
        assert toc[0].level == 2
        assert toc[1].indent == 0
        assert toc[2].indent == 1
        assert len(set(anchors)) == len(anchors)
        assert all(entry.level >= 2 for entry in toc)

    def test_build_toc_handles_duplicate_titles(self) -> None:
        toc = build_toc("## Steps\n\n## Steps\n\n### Steps")
        assert [entry.anchor for entry in toc] == ["steps", "steps-1", "steps-2"]

    def test_split_sections_keeps_content(self) -> None:
        sections = split_sections("Intro text\n\n## Alpha\nFirst.\n\n## Beta\nSecond.")
        assert [section.title for section in sections] == ["Introduction", "Alpha", "Beta"]
        assert "First." in sections[1].content
        assert sections[1].word_count == 1

    def test_status_transition_rules(self) -> None:
        assert WriteupStatus.DRAFT.allows(WriteupStatus.REVIEW)
        assert not WriteupStatus.DRAFT.allows(WriteupStatus.PUBLISHED)
        assert WriteupStatus.REVIEW.allows(WriteupStatus.PUBLISHED)
        assert WriteupStatus.REVIEW.allows(WriteupStatus.DRAFT)
        assert WriteupStatus.PUBLISHED.allows(WriteupStatus.DRAFT)
        assert not WriteupStatus.PUBLISHED.allows(WriteupStatus.REVIEW)

    def test_writeup_derived_properties(self) -> None:
        writeup = make_writeup(
            rating_sum=12, rating_count=3, ratings=(("a", 5), ("b", 4), ("c", 3))
        )
        assert writeup.slug == "recovering-the-keystream"
        assert writeup.reading_minutes >= 1
        assert writeup.average_rating == 4.0
        assert 3.5 < writeup.bayesian_score < 4.0
        assert writeup.star_distribution == (0, 0, 1, 1, 1)
        assert writeup.rating_by("b") == 4
        assert writeup.rating_by("missing") is None
        assert len(writeup.toc) == 3
        assert writeup.can_transition_to(WriteupStatus.REVIEW)

    def test_writeup_immutable_updates(self) -> None:
        original = make_writeup()
        published = original.with_status(WriteupStatus.PUBLISHED)
        assert published.published_at is not None
        assert original.published_at is None
        assert original.status is WriteupStatus.DRAFT
        drafted = published.with_status(WriteupStatus.DRAFT)
        assert drafted.published_at is None
        rated = original.with_ratings([("a", 5), ("a", 2)])
        assert rated.rating_count == 1
        assert rated.rating_sum == 2
        assert original.with_view().views == original.views + 1

    def test_submit_gate_and_rating_bounds(self) -> None:
        assert is_submittable(make_writeup())
        assert not is_submittable(make_writeup(summary="", body="too short"))
        assert is_valid_rating(1)
        assert is_valid_rating(5)
        assert not is_valid_rating(0)
        assert not is_valid_rating(6)

    def test_review_and_stats_helpers(self, database: object) -> None:
        review = WriteupReview(
            id="rv_1",
            writeup_id="wu_1",
            reviewer_id="r1",
            verdict=ReviewVerdict.APPROVE,
            comment="Excellent detail throughout.",
        )
        assert review.approved
        assert review.is_substantive
        assert not review.requests_changes
        assert ReviewVerdict.REQUEST_CHANGES.label == "Changes requested"
        bookmark = WriteupBookmark(id="bm_1", writeup_id="wu_1", member_id="m1")
        assert bookmark.member_id == "m1"
        service = WriteupService()
        stats = service.stats()
        assert stats.total == 0
        assert stats.publication_rate == 0.0
        assert stats.status_count(WriteupStatus.DRAFT) == 0


class TestStore:
    def test_writeup_crud_roundtrip(self, database: object) -> None:
        repo = WriteupRepository()
        writeup = repo.create(make_writeup())
        assert repo.get(writeup.id) == writeup
        updated = repo.update(replace(writeup, title="A new title", status=WriteupStatus.REVIEW))
        assert repo.get(writeup.id).title == updated.title  # type: ignore[union-attr]
        assert repo.exists_for_pair("member-1", "challenge-1")
        assert not repo.exists_for_pair("member-1", "other")
        assert repo.delete(writeup.id)
        assert repo.get(writeup.id) is None

    def test_filtering_search_and_sorting(self, database: object) -> None:
        repo = WriteupRepository()
        repo.create(
            make_writeup(
                id="wu_a",
                title="Alpha crypto",
                category=ChallengeCategory.CRYPTO,
                tags=("crypto", "aes"),
            )
        )
        repo.create(
            make_writeup(
                id="wu_b",
                title="Beta web",
                category=ChallengeCategory.WEB,
                status=WriteupStatus.PUBLISHED,
                tags=("web",),
            )
        )
        repo.create(
            make_writeup(
                id="wu_c",
                title="Gamma crypto",
                category=ChallengeCategory.CRYPTO,
                author_id="member-2",
                rating_sum=15,
                rating_count=3,
                tags=("crypto",),
            )
        )
        assert len(repo.list_writeups()) == 3
        assert len(repo.list_writeups(status=WriteupStatus.PUBLISHED)) == 1
        assert len(repo.list_writeups(category=ChallengeCategory.CRYPTO)) == 2
        assert len(repo.list_writeups(tag="aes")) == 1
        assert len(repo.list_writeups(author_id="member-2")) == 1
        assert len(repo.list_writeups(search="gamma")) == 1
        assert len(repo.list_writeups(search="alpha beta")) == 0
        assert repo.list_writeups(sort="rating")[0].id == "wu_c"
        assert repo.list_writeups(limit=2, offset=1)[0].id in {"wu_b", "wu_a"}
        assert repo.count_matching(category=ChallengeCategory.CRYPTO) == 2

    def test_review_repository(self, database: object) -> None:
        repo = WriteupReviewRepository()
        review = repo.create(
            WriteupReview(
                id="rv_1", writeup_id="wu_1", reviewer_id="r1", verdict=ReviewVerdict.APPROVE
            )
        )
        assert repo.get_pair("wu_1", "r1") == review
        assert repo.has_approval("wu_1")
        assert repo.for_writeup("wu_1") == [review]
        assert repo.for_reviewer("r1") == [review]
        assert repo.count_pending_reviews() == 1
        assert repo.delete_for_writeup("wu_1") == 1
        assert not repo.has_approval("wu_1")

    def test_bookmark_repository(self, database: object) -> None:
        repo = WriteupBookmarkRepository()
        repo.create(WriteupBookmark(id="bm_1", writeup_id="wu_1", member_id="m1"))
        assert repo.is_bookmarked("wu_1", "m1")
        assert repo.count_all() == 1
        assert [item.writeup_id for item in repo.for_member("m1")] == ["wu_1"]
        assert [item.member_id for item in repo.for_writeup("wu_1")] == ["m1"]
        assert repo.remove("wu_1", "m1")
        assert not repo.is_bookmarked("wu_1", "m1")


class TestService:
    def test_create_normalises_tags_and_rejects_duplicates(self, database: object) -> None:
        service = WriteupService()
        created = service_writeup(service)
        assert created.tags == ("crypto", "aes", "stream-cipher")
        assert created.status is WriteupStatus.DRAFT
        with pytest.raises(DuplicateWriteupError):
            service_writeup(service, title="Another take")

    def test_create_rejects_empty_fields(self, database: object) -> None:
        service = WriteupService()
        with pytest.raises(ValidationError):
            service.create(
                challenge_id="c",
                author_id="a",
                title="",
                summary="long enough summary",
                body="body",
                category=ChallengeCategory.WEB,
                difficulty=Difficulty.EASY,
            )
        with pytest.raises(ValidationError):
            service.create(
                challenge_id="c",
                author_id="a",
                title="Title",
                summary="",
                body="body",
                category=ChallengeCategory.WEB,
                difficulty=Difficulty.EASY,
            )

    def test_update_fields_and_conflicts(self, database: object) -> None:
        service = WriteupService()
        first = service_writeup(service)
        second = service_writeup(service, title="Second writeup", challenge_id="challenge-2")
        assert service.update(first.id) == first
        edited = service.update(
            first.id, title="  Renamed title ", tags=["#Web", "web"], category=ChallengeCategory.WEB
        )
        assert edited.title == "Renamed title"
        assert edited.tags == ("web",)
        assert edited.category is ChallengeCategory.WEB
        with pytest.raises(DuplicateWriteupError):
            service.update(first.id, challenge_id=second.challenge_id)
        with pytest.raises(ValidationError):
            service.update(first.id, summary="")
        assert service.get(first.id).title == "Renamed title"

    def test_submit_and_transition_validation(self, database: object) -> None:
        service = WriteupService()
        short = service.create(
            challenge_id="c2",
            author_id="m2",
            title="Short one",
            summary="A reasonable summary here.",
            body="tiny",
            category=ChallengeCategory.WEB,
            difficulty=Difficulty.EASY,
        )
        with pytest.raises(ValidationError):
            service.submit(short.id)
        writeup = service.submit(service_writeup(service).id)
        assert writeup.status is WriteupStatus.REVIEW
        with pytest.raises(InvalidTransitionError):
            service.submit(writeup.id)
        with pytest.raises(ApprovalRequiredError):
            service.publish(writeup.id)

    def test_review_workflow(self, database: object) -> None:
        service = WriteupService()
        draft = service_writeup(service)
        with pytest.raises(ReviewNotAllowedError):
            service.add_review(draft.id, "reviewer-1", ReviewVerdict.APPROVE, "Looks good")
        writeup = service.submit(draft.id)
        with pytest.raises(ValidationError):
            service.add_review(writeup.id, "member-1", ReviewVerdict.APPROVE, "Self review")
        change = service.add_review(
            writeup.id, "reviewer-2", ReviewVerdict.REQUEST_CHANGES, "Add more detail here"
        )
        assert change.requests_changes
        assert service.get(writeup.id).status is WriteupStatus.DRAFT
        writeup = service.submit(writeup.id)
        service.add_review(writeup.id, "reviewer-1", ReviewVerdict.APPROVE, "Nice work")
        with pytest.raises(DuplicateReviewError):
            service.add_review(writeup.id, "reviewer-1", ReviewVerdict.APPROVE, "Again")
        published = service.publish(writeup.id)
        assert published.status is WriteupStatus.PUBLISHED
        assert published.published_at is not None
        assert len(service.reviews_for(published.id)) == 2
        withdrawn = service.withdraw(published.id)
        assert withdrawn.status is WriteupStatus.DRAFT
        assert withdrawn.published_at is None

    def test_rating_bounds_and_recompute(self, database: object) -> None:
        service = WriteupService()
        writeup = service_writeup(service)
        with pytest.raises(RatingOutOfRangeError):
            service.rate(writeup.id, "member-2", 0)
        with pytest.raises(RatingOutOfRangeError):
            service.rate(writeup.id, "member-2", 6)
        rated = service.rate(writeup.id, "member-2", 5)
        updated = service.rate(writeup.id, "member-2", 2)
        assert rated.rating_count == 1
        assert rated.rating_sum == 5
        assert updated.rating_count == 1
        assert updated.rating_sum == 2
        other = service.rate(writeup.id, "member-3", 4)
        assert other.rating_count == 2
        assert other.rating_sum == 6
        assert other.star_distribution == (0, 1, 0, 1, 0)
        assert other.bayesian_score > 2.0

    def test_bookmarks_and_stats(self, database: object) -> None:
        service = WriteupService()
        first = service_writeup(service, status=WriteupStatus.PUBLISHED)
        service_writeup(
            service,
            title="Second",
            challenge_id="c2",
            category=ChallengeCategory.WEB,
            status=WriteupStatus.PUBLISHED,
        )
        assert service.toggle_bookmark(first.id, "member-9")
        assert service.is_bookmarked(first.id, "member-9")
        assert first.id in service.bookmark_ids("member-9")
        assert service.bookmark_count(first.id) == 1
        assert not service.toggle_bookmark(first.id, "member-9")
        service.rate(first.id, "member-7", 5)
        stats = service.stats()
        assert stats.total == 2
        assert stats.published == 2
        assert stats.total_views >= 0
        assert stats.total_ratings == 1
        assert stats.bookmarks == 0
        assert stats.publication_rate == 1.0
        assert stats.status_count(WriteupStatus.DRAFT) == 0
        assert stats.top_rated[0].id == first.id
        assert len(stats.by_category) == len(ChallengeCategory)
        assert stats.by_category[1].published == 1

    def test_views_search_and_mine(self, database: object) -> None:
        service = WriteupService()
        writeup = service_writeup(service, status=WriteupStatus.PUBLISHED)
        assert service.record_view(writeup.id).views == 1
        assert service.record_view(writeup.id).views == 2
        assert [item.id for item in service.mine("member-1")] == [writeup.id]
        assert [item.id for item in service.search("cipher")] == [writeup.id]
        assert service.search("nonexistent-term") == []
        assert [item.id for item in service.top_rated()] == []
        now = utcnow()
        assert len(service.created_between(now - timedelta(days=1), now + timedelta(days=1))) == 1
        assert service.created_between(now + timedelta(days=1), now + timedelta(days=2)) == []

    def test_delete_removes_related_records(self, database: object) -> None:
        service = WriteupService()
        writeup = service_writeup(service, status=WriteupStatus.PUBLISHED)
        service.toggle_bookmark(writeup.id, "member-9")
        assert len(service.reviews_for(writeup.id)) == 1
        service.delete(writeup.id)
        with pytest.raises(NotFoundError):
            service.get(writeup.id)
        assert service.bookmark_ids("member-9") == []


class TestRouter:
    def test_create_list_get_patch_delete(self, client: TestClient) -> None:
        created = post_writeup(client)
        assert created["status"] == "draft"
        assert created["slug"] == "breaking-the-cipher"
        assert len(created["toc"]) == 3
        listed = client.get("/api/writeups").json()
        assert listed["total"] == 1
        assert len(listed["items"]) == 1
        detail = client.get(f"/api/writeups/{created['id']}").json()
        assert detail["views"] == 1
        patched = client.patch(
            f"/api/writeups/{created['id']}",
            json={"title": "An even better title", "tags": ["#Pwn", "pwn"]},
        )
        assert patched.status_code == 200
        assert patched.json()["title"] == "An even better title"
        assert patched.json()["tags"] == ["pwn"]
        assert client.delete(f"/api/writeups/{created['id']}").status_code == 204
        assert client.get(f"/api/writeups/{created['id']}").status_code == 404

    def test_publication_workflow_over_http(self, client: TestClient) -> None:
        created = post_writeup(client)
        writeup_id = created["id"]
        assert client.post(f"/api/writeups/{writeup_id}/publish").status_code == 422
        assert client.post(f"/api/writeups/{writeup_id}/submit").status_code == 200
        assert client.post(f"/api/writeups/{writeup_id}/publish").status_code == 422
        review = client.post(
            f"/api/writeups/{writeup_id}/reviews",
            json={"reviewer_id": "reviewer-1", "verdict": "approve", "comment": "Well explained."},
        )
        assert review.status_code == 201
        assert review.json()["approved"]
        published = client.post(f"/api/writeups/{writeup_id}/publish")
        assert published.status_code == 200
        assert published.json()["status"] == "published"
        assert published.json()["published_at"] is not None
        assert len(client.get(f"/api/writeups/{writeup_id}/reviews").json()) == 1
        stats = client.get("/api/writeups/stats").json()
        assert stats["published"] == 1
        assert stats["by_status"][2]["count"] == 1
        assert client.post(f"/api/writeups/{writeup_id}/withdraw").json()["status"] == "draft"

    def test_rate_bookmark_and_mine_over_http(self, client: TestClient) -> None:
        created = post_writeup(client)
        writeup_id = created["id"]
        invalid = client.post(
            f"/api/writeups/{writeup_id}/rate", json={"member_id": "m2", "score": 9}
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "invalid_rating"
        rated = client.post(
            f"/api/writeups/{writeup_id}/rate", json={"member_id": "m2", "score": 5}
        )
        assert rated.json()["rating_count"] == 1
        assert 3.5 < rated.json()["bayesian_score"] <= 5.0
        bookmarked = client.post(f"/api/writeups/{writeup_id}/bookmark", json={"member_id": "m2"})
        assert bookmarked.json()["bookmarked"]
        assert bookmarked.json()["count"] == 1
        assert client.get("/api/writeups/bookmarks/m2").json()[0]["id"] == writeup_id
        assert len(client.get("/api/writeups/mine", params={"author_id": "member-1"}).json()) == 1
        assert len(client.get("/api/writeups/top").json()) == 0
        assert client.get("/api/writeups/stats").json()["bookmarks"] == 1

    def test_filters_search_and_errors(self, client: TestClient) -> None:
        post_writeup(client)
        post_writeup(
            client, title="Web shell walkthrough", challenge_id="c2", category="web", tags=["web"]
        )
        assert client.get("/api/writeups", params={"category": "web"}).json()["total"] == 1
        assert client.get("/api/writeups", params={"tag": "web"}).json()["total"] == 1
        assert client.get("/api/writeups", params={"search": "shell"}).json()["total"] == 1
        assert client.get("/api/writeups", params={"status": "published"}).json()["total"] == 0
        assert (
            client.get("/api/writeups", params={"sort": "rating", "limit": 1}).json()["limit"] == 1
        )
        duplicate = client.post(
            "/api/writeups",
            json={
                "challenge_id": "challenge-1",
                "author_id": "member-1",
                "title": "Duplicate",
                "summary": "A long enough summary here.",
                "body": BODY,
                "category": "crypto",
                "difficulty": "easy",
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "duplicate_writeup"
        missing = client.get("/api/writeups/wu_missing", params={"track_view": "false"})
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "not_found"
