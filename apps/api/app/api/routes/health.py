from fastapi import APIRouter, Request
from sqlalchemy import text

from app.api.dependencies import get_session


router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    session = next(get_session(request))
    try:
        session.execute(text("select 1"))
        database_status = "healthy"
    except Exception:
        database_status = "unavailable"
    finally:
        session.close()

    ca_status = "healthy" if request.app.state.step_ca.health() else "unavailable"
    overall_status = "healthy" if database_status == "healthy" and ca_status == "healthy" else "degraded"
    return {
        "status": overall_status,
        "database": database_status,
        "certificate_authority": ca_status,
    }
