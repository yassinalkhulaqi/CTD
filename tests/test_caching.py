"""Tests for the response cache and the conditional responses."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ctf_team_dashboard.services.caching import (
    ResponseCache,
    conditional_response,
    get_response_cache,
    reset_response_cache,
)


def test_cache_key_includes_the_parameters() -> None:
    """Two different queries should produce two keys."""
    cache = ResponseCache()
    assert cache.key("/api/teams") != cache.key("/api/teams", {"team_id": "a"})


def test_cache_key_is_order_independent() -> None:
    """The parameter order should not change the key."""
    cache = ResponseCache()
    assert cache.key("/api/teams", {"a": 1, "b": 2}) == cache.key(
        "/api/teams", {"b": 2, "a": 1}
    )


def test_cache_stores_and_returns_a_payload() -> None:
    """A stored payload should be returned until it expires."""
    cache = ResponseCache(ttl_seconds=60)
    cache.set("/api/teams", b"[]")
    assert cache.get("/api/teams") is not None
    assert cache.hits == 1


def test_cache_expires_the_entries() -> None:
    """An expired entry should not be returned."""
    cache = ResponseCache(ttl_seconds=0.01)
    cache.set("/api/teams", b"[]")
    import time

    time.sleep(0.05)
    assert cache.get("/api/teams") is None


def test_cache_invalidates_a_prefix() -> None:
    """Invalidating a prefix should remove the matching entries."""
    cache = ResponseCache()
    cache.set("/api/teams/a", b"[]")
    cache.set("/api/teams/b", b"[]")
    cache.set("/api/members", b"[]")
    assert cache.invalidate_prefix("/api/teams") == 2
    assert cache.get("/api/members") is not None


def test_cache_is_bounded() -> None:
    """The cache should never hold more than its maximum size."""
    cache = ResponseCache(max_entries=3)
    for index in range(10):
        cache.set(f"/api/{index}", b"[]")
    assert len(cache.entries) <= 3


def test_etag_is_stable_for_the_same_payload() -> None:
    """The same payload should always produce the same entity tag."""
    cache = ResponseCache()
    assert cache.compute_etag(b"payload") == cache.compute_etag(b"payload")
    assert cache.compute_etag(b"payload") != cache.compute_etag(b"other")


def test_conditional_response_returns_304_for_a_matching_etag() -> None:
    """A matching entity tag should produce a not modified response."""
    cache = ResponseCache()
    status, body, headers = conditional_response(cache, "/api/teams", b"[]")
    assert status == 200
    assert body == b"[]"

    status, body, headers = conditional_response(
        cache, "/api/teams", b"[]", if_none_match=headers["ETag"]
    )
    assert status == 304
    assert body == b""


def test_global_cache_is_a_singleton() -> None:
    """The process wide cache should be a singleton."""
    assert get_response_cache() is get_response_cache()
    reset_response_cache()
    assert get_response_cache() is not None


def test_api_responses_carry_an_etag(client: TestClient) -> None:
    """The read only endpoints should carry an entity tag."""
    response = client.get("/api/teams")
    assert "ETag" in response.headers
    assert "Cache-Control" in response.headers


def test_conditional_request_returns_not_modified(client: TestClient) -> None:
    """A conditional request should be answered with a not modified status."""
    first = client.get("/api/teams")
    etag = first.headers["ETag"]
    second = client.get("/api/teams", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second.content == b""


def test_mutations_are_not_cached(client: TestClient) -> None:
    """A mutation should never be served from the cache."""
    response = client.post("/api/teams", json={"name": "Uncached Crew"})
    assert response.status_code == 201
    assert "ETag" not in response.headers
