import pytest
from quart import Blueprint

health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.route("/")
async def health_check():
    return {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check():
    from quart import Quart
    app = Quart(__name__)
    app.register_blueprint(health_bp)
    client = app.test_client()
    response = await client.get("/health/")
    assert response.status_code == 200
    assert await response.get_json() == {"status": "ok"}
