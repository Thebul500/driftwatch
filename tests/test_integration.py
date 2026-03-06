"""API integration tests using httpx TestClient against real endpoints.

No mocks — all tests hit the actual FastAPI app with a real SQLite database.
"""

import os

WRONG_PASSWORD = os.environ["DRIFTWATCH_TEST_WRONG_PASSWORD"]
SHORT_PASSWORD = os.environ["DRIFTWATCH_TEST_SHORT_PASSWORD"]

USER_DATA = {
    "username": "testuser",
    "email": "test@example.com",
    "password": os.environ["DRIFTWATCH_TEST_PASSWORD"],
}

SNAPSHOT_DATA = {
    "name": "docker-compose",
    "source": "docker",
    "content": '{"services": {"web": {"image": "nginx"}}}',
    "baseline": False,
}


def _register(client, **overrides):
    """Register a user and return the response."""
    data = {**USER_DATA, **overrides}
    return client.post("/auth/register", json=data)


def _login(client, username=None, password=None):
    """Login and return the response."""
    return client.post(
        "/auth/login",
        json={
            "username": username or USER_DATA["username"],
            "password": password or USER_DATA["password"],
        },
    )


def _auth_header(client):
    """Register, login, and return an Authorization header dict."""
    _register(client)
    resp = _login(client)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------- Health endpoints ----------


class TestHealth:
    def test_health_check(self, db_client):
        resp = db_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_readiness_check(self, db_client):
        resp = db_client.get("/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


# ---------- Auth: register ----------


class TestRegister:
    def test_register_success(self, db_client):
        resp = _register(db_client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == USER_DATA["username"]
        assert data["email"] == USER_DATA["email"]
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, db_client):
        _register(db_client)
        resp = _register(db_client, email="other@example.com")
        assert resp.status_code == 400
        assert "Username already taken" in resp.json()["detail"]

    def test_register_duplicate_email(self, db_client):
        _register(db_client)
        resp = _register(db_client, username="otheruser")
        assert resp.status_code == 400
        assert "Email already registered" in resp.json()["detail"]

    def test_register_short_username(self, db_client):
        resp = _register(db_client, username="ab")
        assert resp.status_code == 422

    def test_register_short_password(self, db_client):
        resp = _register(db_client, password=SHORT_PASSWORD)
        assert resp.status_code == 422

    def test_register_invalid_email(self, db_client):
        resp = _register(db_client, email="not-an-email")
        assert resp.status_code == 422


# ---------- Auth: login ----------


class TestLogin:
    def test_login_success(self, db_client):
        _register(db_client)
        resp = _login(db_client)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, db_client):
        _register(db_client)
        resp = _login(db_client, password=WRONG_PASSWORD)
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]

    def test_login_unknown_user(self, db_client):
        resp = _login(db_client, username="nobody")
        assert resp.status_code == 401
        assert "Invalid credentials" in resp.json()["detail"]


# ---------- Auth protection ----------


class TestAuthProtection:
    def test_snapshots_list_requires_auth(self, db_client):
        resp = db_client.get("/snapshots")
        assert resp.status_code == 401

    def test_snapshots_create_requires_auth(self, db_client):
        resp = db_client.post("/snapshots", json=SNAPSHOT_DATA)
        assert resp.status_code == 401

    def test_snapshots_get_requires_auth(self, db_client):
        resp = db_client.get("/snapshots/1")
        assert resp.status_code == 401

    def test_snapshots_update_requires_auth(self, db_client):
        resp = db_client.put("/snapshots/1", json={"name": "updated"})
        assert resp.status_code == 401

    def test_snapshots_delete_requires_auth(self, db_client):
        resp = db_client.delete("/snapshots/1")
        assert resp.status_code == 401

    def test_invalid_token_rejected(self, db_client):
        resp = db_client.get(
            "/snapshots",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


# ---------- Snapshot CRUD ----------


class TestSnapshotCreate:
    def test_create_snapshot(self, db_client):
        headers = _auth_header(db_client)
        resp = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == SNAPSHOT_DATA["name"]
        assert data["source"] == SNAPSHOT_DATA["source"]
        assert data["content"] == SNAPSHOT_DATA["content"]
        assert data["baseline"] is False
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data

    def test_create_snapshot_missing_fields(self, db_client):
        headers = _auth_header(db_client)
        resp = db_client.post("/snapshots", json={}, headers=headers)
        assert resp.status_code == 422

    def test_create_snapshot_empty_name(self, db_client):
        headers = _auth_header(db_client)
        data = {**SNAPSHOT_DATA, "name": ""}
        resp = db_client.post("/snapshots", json=data, headers=headers)
        assert resp.status_code == 422


class TestSnapshotRead:
    def test_list_snapshots_empty(self, db_client):
        headers = _auth_header(db_client)
        resp = db_client.get("/snapshots", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_list_snapshots(self, db_client):
        headers = _auth_header(db_client)
        db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        db_client.post(
            "/snapshots",
            json={**SNAPSHOT_DATA, "name": "crontab-backup"},
            headers=headers,
        )
        resp = db_client.get("/snapshots", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

    def test_list_snapshots_pagination(self, db_client):
        headers = _auth_header(db_client)
        for i in range(5):
            db_client.post(
                "/snapshots",
                json={**SNAPSHOT_DATA, "name": f"snap-{i}"},
                headers=headers,
            )
        resp = db_client.get("/snapshots?limit=2&offset=0", headers=headers)
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

        resp = db_client.get("/snapshots?limit=2&offset=4", headers=headers)
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 5

    def test_list_snapshots_filter_source(self, db_client):
        headers = _auth_header(db_client)
        db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        db_client.post(
            "/snapshots",
            json={**SNAPSHOT_DATA, "name": "crontab", "source": "cron"},
            headers=headers,
        )
        resp = db_client.get("/snapshots?source=docker", headers=headers)
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["source"] == "docker"
        assert data["total"] == 1

    def test_list_snapshots_filter_baseline(self, db_client):
        headers = _auth_header(db_client)
        db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        db_client.post(
            "/snapshots",
            json={**SNAPSHOT_DATA, "name": "baseline-snap", "baseline": True},
            headers=headers,
        )
        resp = db_client.get("/snapshots?baseline=true", headers=headers)
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["baseline"] is True
        assert data["total"] == 1

    def test_get_snapshot_by_id(self, db_client):
        headers = _auth_header(db_client)
        create_resp = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        snapshot_id = create_resp.json()["id"]

        resp = db_client.get(f"/snapshots/{snapshot_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == snapshot_id
        assert resp.json()["name"] == SNAPSHOT_DATA["name"]

    def test_get_snapshot_not_found(self, db_client):
        headers = _auth_header(db_client)
        resp = db_client.get("/snapshots/999", headers=headers)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestSnapshotUpdate:
    def test_update_snapshot(self, db_client):
        headers = _auth_header(db_client)
        create_resp = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        snapshot_id = create_resp.json()["id"]

        update_data = {"name": "updated-name", "baseline": True}
        resp = db_client.put(f"/snapshots/{snapshot_id}", json=update_data, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "updated-name"
        assert data["baseline"] is True
        assert data["source"] == SNAPSHOT_DATA["source"]  # unchanged

    def test_update_snapshot_partial(self, db_client):
        headers = _auth_header(db_client)
        create_resp = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        snapshot_id = create_resp.json()["id"]

        resp = db_client.put(
            f"/snapshots/{snapshot_id}",
            json={"content": "new content"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "new content"
        assert resp.json()["name"] == SNAPSHOT_DATA["name"]  # unchanged

    def test_update_snapshot_not_found(self, db_client):
        headers = _auth_header(db_client)
        resp = db_client.put("/snapshots/999", json={"name": "x"}, headers=headers)
        assert resp.status_code == 404


class TestSnapshotDelete:
    def test_delete_snapshot(self, db_client):
        headers = _auth_header(db_client)
        create_resp = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        snapshot_id = create_resp.json()["id"]

        resp = db_client.delete(f"/snapshots/{snapshot_id}", headers=headers)
        assert resp.status_code == 204

        # Confirm it's gone
        resp = db_client.get(f"/snapshots/{snapshot_id}", headers=headers)
        assert resp.status_code == 404

    def test_delete_snapshot_not_found(self, db_client):
        headers = _auth_header(db_client)
        resp = db_client.delete("/snapshots/999", headers=headers)
        assert resp.status_code == 404


# ---------- Ownership isolation ----------


class TestOwnershipIsolation:
    def test_user_cannot_see_other_users_snapshots(self, db_client):
        # User A creates a snapshot
        _register(db_client, username="userA", email="a@example.com")
        resp = _login(db_client, username="userA")
        headers_a = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers_a)

        # User B should see no snapshots
        _register(db_client, username="userB", email="b@example.com")
        resp = _login(db_client, username="userB")
        headers_b = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        resp = db_client.get("/snapshots", headers=headers_b)
        assert resp.status_code == 200
        assert resp.json()["items"] == []
        assert resp.json()["total"] == 0

    def test_user_cannot_modify_other_users_snapshot(self, db_client):
        # User A creates a snapshot
        _register(db_client, username="userA", email="a@example.com")
        resp = _login(db_client, username="userA")
        headers_a = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        create_resp = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers_a)
        snapshot_id = create_resp.json()["id"]

        # User B tries to update it
        _register(db_client, username="userB", email="b@example.com")
        resp = _login(db_client, username="userB")
        headers_b = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        resp = db_client.put(
            f"/snapshots/{snapshot_id}", json={"name": "hacked"}, headers=headers_b
        )
        assert resp.status_code == 404

    def test_user_cannot_delete_other_users_snapshot(self, db_client):
        # User A creates a snapshot
        _register(db_client, username="userA", email="a@example.com")
        resp = _login(db_client, username="userA")
        headers_a = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        create_resp = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers_a)
        snapshot_id = create_resp.json()["id"]

        # User B tries to delete it
        _register(db_client, username="userB", email="b@example.com")
        resp = _login(db_client, username="userB")
        headers_b = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        resp = db_client.delete(f"/snapshots/{snapshot_id}", headers=headers_b)
        assert resp.status_code == 404


# ---------- Snapshot diff ----------


class TestSnapshotDiff:
    def test_diff_identical_snapshots(self, db_client):
        headers = _auth_header(db_client)
        r1 = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        r2 = db_client.post(
            "/snapshots", json={**SNAPSHOT_DATA, "name": "snap2"}, headers=headers
        )
        resp = db_client.post(
            "/snapshots/diff",
            json={"base_snapshot_id": r1.json()["id"], "target_snapshot_id": r2.json()["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["drift_detected"] is False
        assert data["diff_lines"] == []
        assert data["additions"] == 0
        assert data["deletions"] == 0

    def test_diff_changed_snapshots(self, db_client):
        headers = _auth_header(db_client)
        r1 = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        new_content = '{"services": {"web": {"image": "apache"}}}'
        changed = {**SNAPSHOT_DATA, "name": "snap2", "content": new_content}
        r2 = db_client.post("/snapshots", json=changed, headers=headers)
        resp = db_client.post(
            "/snapshots/diff",
            json={"base_snapshot_id": r1.json()["id"], "target_snapshot_id": r2.json()["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["drift_detected"] is True
        assert data["additions"] > 0 or data["deletions"] > 0
        assert len(data["diff_lines"]) > 0

    def test_diff_snapshot_not_found(self, db_client):
        headers = _auth_header(db_client)
        r1 = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        resp = db_client.post(
            "/snapshots/diff",
            json={"base_snapshot_id": r1.json()["id"], "target_snapshot_id": 999},
            headers=headers,
        )
        assert resp.status_code == 404

    def test_diff_requires_auth(self, db_client):
        resp = db_client.post(
            "/snapshots/diff",
            json={"base_snapshot_id": 1, "target_snapshot_id": 2},
        )
        assert resp.status_code == 401


# ---------- Drift check ----------


class TestDriftCheck:
    def test_drift_check_no_drift(self, db_client):
        headers = _auth_header(db_client)
        # Create a baseline
        baseline_data = {**SNAPSHOT_DATA, "baseline": True, "name": "baseline"}
        db_client.post("/snapshots", json=baseline_data, headers=headers)
        # Create a snapshot with same content
        r2 = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        resp = db_client.get(f"/snapshots/{r2.json()['id']}/drift", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["drift_detected"] is False
        assert data["additions"] == 0
        assert data["deletions"] == 0

    def test_drift_check_with_drift(self, db_client):
        headers = _auth_header(db_client)
        # Create a baseline
        baseline_data = {**SNAPSHOT_DATA, "baseline": True, "name": "baseline"}
        db_client.post("/snapshots", json=baseline_data, headers=headers)
        # Create a snapshot with different content
        changed = {**SNAPSHOT_DATA, "content": "changed content"}
        r2 = db_client.post("/snapshots", json=changed, headers=headers)
        resp = db_client.get(f"/snapshots/{r2.json()['id']}/drift", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["drift_detected"] is True
        assert len(data["diff_lines"]) > 0

    def test_drift_check_no_baseline(self, db_client):
        headers = _auth_header(db_client)
        r1 = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        resp = db_client.get(f"/snapshots/{r1.json()['id']}/drift", headers=headers)
        assert resp.status_code == 404
        assert "No baseline found" in resp.json()["detail"]

    def test_drift_check_uses_same_source(self, db_client):
        headers = _auth_header(db_client)
        # Create a baseline for a different source
        other_baseline = {
            "name": "cron-baseline",
            "source": "cron",
            "content": "some cron data",
            "baseline": True,
        }
        db_client.post("/snapshots", json=other_baseline, headers=headers)
        # Create a docker snapshot — should not match the cron baseline
        r2 = db_client.post("/snapshots", json=SNAPSHOT_DATA, headers=headers)
        resp = db_client.get(f"/snapshots/{r2.json()['id']}/drift", headers=headers)
        assert resp.status_code == 404
        assert "No baseline found" in resp.json()["detail"]

    def test_drift_check_requires_auth(self, db_client):
        resp = db_client.get("/snapshots/1/drift")
        assert resp.status_code == 401
