"""Authenticated API client for the dotclaude server.

Automatically injects JWT Bearer header and retries with refresh token on 401.
"""

from __future__ import annotations

from typing import Any

import httpx

from dotclaude.insights.config_store import (
    get_server_url,
    read_config,
    write_config,
)

_KEY_AUTH_TOKEN = "authToken"
_KEY_REFRESH_TOKEN = "refreshToken"


class ApiError(Exception):
    """Raised when the API returns a non-success response."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthRequiredError(Exception):
    """Raised when the user is not logged in."""

    def __init__(self) -> None:
        super().__init__("Not logged in. Run: dotclaude login")


async def _refresh_access_token(server_url: str) -> str:
    """Refresh the access token using the refresh token.

    Raises:
        AuthRequiredError: If refresh token is not available or refresh fails.
    """
    config = read_config()
    refresh_token = config.get(_KEY_REFRESH_TOKEN)
    if not refresh_token:
        raise AuthRequiredError()

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{server_url}/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    if not res.is_success:
        # Refresh failed — wipe tokens
        write_config({
            **config,
            _KEY_AUTH_TOKEN: None,
            _KEY_REFRESH_TOKEN: None,
        })
        raise AuthRequiredError()

    data: dict[str, Any] = res.json()
    write_config({
        **config,
        _KEY_AUTH_TOKEN: data["access_token"],
        _KEY_REFRESH_TOKEN: data["refresh_token"],
    })
    return str(data["access_token"])


async def api_request(
    path: str,
    method: str = "GET",
    json_body: Any = None,
    extra_headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Make an authenticated request to the dotclaude server.

    Automatically retries once with a refreshed token on 401.

    Args:
        path: API path (e.g., "/api/sync").
        method: HTTP method.
        json_body: JSON-serializable body.
        extra_headers: Additional headers to merge.

    Returns:
        The httpx.Response object.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: On non-auth HTTP errors.
    """
    server_url = get_server_url()
    config = read_config()
    auth_token = config.get(_KEY_AUTH_TOKEN)
    if not auth_token:
        raise AuthRequiredError()

    headers: dict[str, str] = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        **(extra_headers or {}),
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.request(
            method=method,
            url=f"{server_url}{path}",
            headers=headers,
            json=json_body,
        )

        if res.status_code == 401:
            new_token = await _refresh_access_token(server_url)
            headers["Authorization"] = f"Bearer {new_token}"
            res = await client.request(
                method=method,
                url=f"{server_url}{path}",
                headers=headers,
                json=json_body,
            )

    return res
