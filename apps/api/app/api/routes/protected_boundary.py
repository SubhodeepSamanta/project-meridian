from fastapi import APIRouter, Request

from app.schemas import ProtectedBoundaryResponse


router = APIRouter(prefix="/protected-boundary", tags=["protected-boundary"])


@router.get("", response_model=ProtectedBoundaryResponse)
def protected_boundary(request: Request) -> ProtectedBoundaryResponse:
    client = request.app.state.hsm_ca
    status = "healthy" if client is not None and client.health() else "unavailable"
    return ProtectedBoundaryResponse(
        status=status,
        token_label="meridian-hsm",
        key_store="PKCS#11 / SoftHSM2",
        key_objects=["meridian-hsm-root", "meridian-hsm-intermediate"],
        api_disk_key_access="not mounted",
        ca_endpoint=client.ca_url if client is not None else "not configured",
    )
