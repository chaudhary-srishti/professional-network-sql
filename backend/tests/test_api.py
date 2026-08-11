"""End-to-end API tests covering the security fixes and core flows."""
from __future__ import annotations

from conftest import auth, make_user


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


async def test_create_and_get_user(client):
    user = await make_user(client, "a@x.com", "Alice")
    got = await client.get(f"/users/{user['id']}")
    assert got.status_code == 200
    assert got.json()["email"] == "a@x.com"


async def test_auth_required(client):
    # Creating a post without the auth header is rejected.
    resp = await client.post("/posts", json={})
    assert resp.status_code == 401


async def test_like_is_idempotent(client):
    author = await make_user(client, "author@x.com", "Author")
    liker = await make_user(client, "liker@x.com", "Liker")
    post = (await client.post("/posts", json={"hashtags": ["finance"]}, headers=auth("author@x.com"))).json()

    first = await client.post(f"/posts/{post['id']}/likes", headers=auth("liker@x.com"))
    second = await client.post(f"/posts/{post['id']}/likes", headers=auth("liker@x.com"))
    assert first.json() == {"liked": True, "like_count": 1}
    assert second.json() == {"liked": True, "like_count": 1}  # double-tap does not inflate

    unlike = await client.delete(f"/posts/{post['id']}/likes", headers=auth("liker@x.com"))
    assert unlike.json() == {"liked": False, "like_count": 0}


async def test_post_delete_requires_author(client):
    author = await make_user(client, "author@x.com", "Author")
    other = await make_user(client, "other@x.com", "Other")
    post = (await client.post("/posts", json={}, headers=auth("author@x.com"))).json()

    forbidden = await client.delete(f"/posts/{post['id']}", headers=auth("other@x.com"))
    assert forbidden.status_code == 403

    ok = await client.delete(f"/posts/{post['id']}", headers=auth("author@x.com"))
    assert ok.status_code == 204


async def test_connection_accept_only_by_target(client):
    a = await make_user(client, "a@x.com", "A")
    b = await make_user(client, "b@x.com", "B")
    conn = (await client.post("/connections", json={"target_id": b["id"]}, headers=auth("a@x.com"))).json()

    # Requester cannot accept their own request.
    self_accept = await client.post(f"/connections/{conn['id']}/accept", headers=auth("a@x.com"))
    assert self_accept.status_code == 403

    # Target can.
    accept = await client.post(f"/connections/{conn['id']}/accept", headers=auth("b@x.com"))
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"


async def test_duplicate_connection_conflicts(client):
    a = await make_user(client, "a@x.com", "A")
    b = await make_user(client, "b@x.com", "B")
    first = await client.post("/connections", json={"target_id": b["id"]}, headers=auth("a@x.com"))
    assert first.status_code == 201
    # Reverse direction is the same undirected pair -> 409 via the LEAST/GREATEST unique index.
    dup = await client.post("/connections", json={"target_id": a["id"]}, headers=auth("b@x.com"))
    assert dup.status_code == 409


async def test_email_is_not_client_updatable(client):
    user = await make_user(client, "keep@x.com", "Keep")
    # Even if a client sends email, it is dropped from the update model.
    resp = await client.patch(
        f"/users/{user['id']}",
        json={"email": "hacked@x.com", "bio": "updated"},
        headers=auth("keep@x.com"),
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "keep@x.com"
    assert resp.json()["bio"] == "updated"


async def test_firm_create_makes_creator_owner_and_member_request_flow(client):
    owner = await make_user(client, "owner@x.com", "Owner")
    applicant = await make_user(client, "applicant@x.com", "Applicant")
    org = (await client.post("/organizations", json={"name": "Acme Capital"}, headers=auth("owner@x.com"))).json()
    assert org["firm_url"].startswith("acme-capital-")  # trigger-generated slug

    req = (await client.post("/member-requests", json={"organization_id": org["id"]}, headers=auth("applicant@x.com"))).json()

    # A non-owner cannot accept.
    assert (await client.post(f"/member-requests/{req['id']}/accept", headers=auth("applicant@x.com"))).status_code == 403
    # The owner can, and the applicant becomes a member.
    assert (await client.post(f"/member-requests/{req['id']}/accept", headers=auth("owner@x.com"))).status_code == 200

    members = (await client.get(f"/organizations/{org['id']}/members")).json()
    member_ids = {m["user_id"] for m in members}
    assert owner["id"] in member_ids and applicant["id"] in member_ids
