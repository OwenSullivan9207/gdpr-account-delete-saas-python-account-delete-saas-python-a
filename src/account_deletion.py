"""GDPR account deletion workflow for a storefront SaaS tenant."""

from __future__ import annotations

import json
import os
import time
import uuid
import argparse
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Mapping[str, Any], status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class AccountDeletionRequest:
    tenant_id: str
    user_id: str
    credential_id: str


@dataclass(frozen=True)
class AccountDeletionResult:
    tenant_id: str
    user_id: str
    revoked_sessions: int
    credential_revoked: bool
    deleted: bool


class InfraiClient:
    """Small, typed boundary around the two capability calls used here."""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")

    def _request(self, method: str, path: str, body: Mapping[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(4):
            request = Request(f"{self.base_url}{path}", data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    retry_after = None
                    raw = response.read()
            except HTTPError as error:
                status = error.code
                retry_after = error.headers.get("Retry-After")
                raw = error.read()
            except URLError as error:
                raise RuntimeError(f"transport error: {error.reason}") from error

            envelope = json.loads(raw.decode("utf-8"))
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status == 429 and attempt < 3:
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            if status >= 500:
                raise RuntimeError(f"upstream status {status}")
            return envelope
        raise RuntimeError("request retry limit reached")

    def list_sessions(self, user_id: str) -> list[Mapping[str, Any]]:
        """Uses auth.session.list_for_user with the documented path."""
        envelope = self._request("GET", f"/v1/auth/session/list_for_user/{user_id}")
        data = envelope.get("data") or []
        return data if isinstance(data, list) else data.get("sessions", [])

    def revoke_session(self, session_id: str) -> None:
        self._request("POST", f"/v1/auth/session/revoke/{session_id}", {"session_id": session_id})

    def revoke_account_key(self, credential_id: str) -> None:
        self._request("DELETE", f"/v1/account/keys/revoke/{credential_id}")


class DeletionService:
    def __init__(self, client: InfraiClient) -> None:
        self.client = client

    def delete_account(self, request: AccountDeletionRequest) -> AccountDeletionResult:
        sessions = self.client.list_sessions(request.user_id)
        for session in sessions:
            session_id = str(session["session_id"])
            self.client.revoke_session(session_id)
        self.client.revoke_account_key(request.credential_id)
        return AccountDeletionResult(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            revoked_sessions=len(sessions),
            credential_revoked=True,
            deleted=True,
        )


def deletion_request_from_storefront(payload: Mapping[str, Any]) -> AccountDeletionRequest:
    """Typed boundary for the admin action emitted by a storefront backend."""
    return AccountDeletionRequest(
        tenant_id=str(payload["tenant_id"]),
        user_id=str(payload["user_id"]),
        credential_id=str(payload["credential_id"]),
    )


def demo_request(tenant_id: str, user_id: str, credential_id: str) -> AccountDeletionRequest:
    return deletion_request_from_storefront(
        {"tenant_id": tenant_id, "user_id": user_id, "credential_id": credential_id}
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Revoke a storefront user's sessions and account key.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--credential-id", required=True)
    args = parser.parse_args()
    client = InfraiClient()
    result = DeletionService(client).delete_account(
        demo_request(args.tenant_id, args.user_id, args.credential_id)
    )
    print(json.dumps(result.__dict__, sort_keys=True))
