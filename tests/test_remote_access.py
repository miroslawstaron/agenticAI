import httpx
import pytest

from agenticai.api import create_app


@pytest.fixture
def remote_settings(monkeypatch):
    monkeypatch.setenv("AGENTICAI_REMOTE_PASSWORD", "fixture-password-for-tests")
    monkeypatch.setenv("AGENTICAI_REMOTE_USER", "studio")
    monkeypatch.setenv("AGENTICAI_ALLOWED_HOSTS", "studio.example")


async def test_remote_login_protects_interface_and_session(tmp_path, remote_settings):
    app = create_app(tmp_path)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, client=("192.0.2.20", 1234))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://studio.example:8876"
        ) as client:
            for path in ("/", "/api/v1/session", "/health", "/docs", "/tutorial/"):
                response = await client.get(path)
                assert response.status_code == 401
                assert response.headers["www-authenticate"].startswith("Basic ")
            assert (
                await client.get(
                    "/health", headers={"Authorization": "Basic malformed!"}
                )
            ).status_code == 401
            assert (
                await client.get("/health", auth=("studio", "incorrect"))
            ).status_code == 401
            client.auth = ("studio", "fixture-password-for-tests")
            response = await client.get("/api/v1/session")
            assert response.status_code == 200 and response.json()["external_access"]
            assert "fixture-password-for-tests" not in response.text
            assert (
                await client.post("/api/v1/networks/validate", json={})
            ).status_code == 403
            client.headers["X-Studio-Token"] = response.json()["token"]
            assert (
                await client.post(
                    "/api/v1/networks/validate",
                    json={},
                    headers={"Origin": "http://studio.example:8876"},
                )
            ).status_code == 200
            assert (
                await client.post(
                    "/api/v1/networks/validate",
                    json={},
                    headers={"Origin": "http://evil.example"},
                )
            ).status_code == 403
            assert (
                await client.get("/health", headers={"Host": "evil.example"})
            ).status_code == 400


@pytest.mark.parametrize("peer", ["127.0.0.1", "::1", "::ffff:127.0.0.1"])
async def test_loopback_access_stays_available(tmp_path, remote_settings, peer):
    app = create_app(tmp_path)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, client=(peer, 1234))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://localhost"
        ) as client:
            assert (await client.get("/health")).status_code == 200


async def test_remote_policy_is_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENTICAI_REMOTE_PASSWORD", raising=False)
    app = create_app(tmp_path)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, client=("192.0.2.20", 1234))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://localhost"
        ) as client:
            assert (await client.get("/health")).status_code == 200


async def test_loopback_relay_to_external_host_requires_login(tmp_path, remote_settings):
    app = create_app(tmp_path)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 1234))
        async with httpx.AsyncClient(
            transport=transport, base_url="http://studio.example:8876"
        ) as client:
            assert (await client.get("/health")).status_code == 401
            assert (
                await client.get("/health", auth=("studio", "fixture-password-for-tests"))
            ).status_code == 200
