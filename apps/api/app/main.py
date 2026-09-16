from fastapi import FastAPI

from app.api.routes import (
    actions,
    audit,
    certificates,
    health,
    identities,
    incidents,
    protected_boundary,
)
from app.core.config import Settings, settings
from app.db.database import create_database, ensure_schema
from app.integrations.step_ca import StepCaClient


def create_app(
    app_settings: Settings = settings,
    step_ca_client: StepCaClient | None = None,
) -> FastAPI:
    engine, session_factory = create_database(app_settings.database_url)
    ensure_schema(engine)

    app = FastAPI(title="Project Meridian API", version="0.1.0")
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.step_ca = step_ca_client or StepCaClient(
        ca_url=app_settings.step_ca_url,
        root_path=app_settings.step_ca_root,
        password_file=app_settings.step_ca_password_file,
        certificate_directory=app_settings.certificate_directory,
    )
    app.state.hsm_ca = (
        StepCaClient(
            ca_url=app_settings.hsm_ca_url,
            root_path=app_settings.hsm_ca_root,
            password_file="",
            certificate_directory=app_settings.certificate_directory,
        )
        if app_settings.hsm_ca_url and app_settings.hsm_ca_root
        else None
    )
    app.include_router(health.router)
    app.include_router(identities.router)
    app.include_router(certificates.router)
    app.include_router(actions.router)
    app.include_router(incidents.router)
    app.include_router(audit.router)
    app.include_router(protected_boundary.router)
    return app


app = create_app()
