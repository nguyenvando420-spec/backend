from typing import Any, Dict, Optional
from fastapi import APIRouter, Request, status

router = APIRouter(tags=["Dynamic APIs"])


@router.api_route(
    "/{system}/{router}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    status_code=status.HTTP_200_OK,
    summary="Dynamic API Handler for {system}/{router}/{path}",
    description="Captures dynamic API requests and routes them dynamically based on system, router, and path."
)
async def dynamic_route_handler(
    system: str,
    router: str,
    path: str,
    request: Request,
) -> Dict[str, Any]:
    """Dynamic endpoint handler matching pattern /{system}/{router}/{path:path}."""
    body: Optional[Any] = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except Exception:
            body = None

    return {
        "status": "success",
        "system": system,
        "router": router,
        "path": path,
        "method": request.method,
        "url_path": request.url.path,
        "query_params": dict(request.query_params),
        "body": body,
        "message": f"Successfully processed dynamic route '{system}/{router}/{path}'"
    }
