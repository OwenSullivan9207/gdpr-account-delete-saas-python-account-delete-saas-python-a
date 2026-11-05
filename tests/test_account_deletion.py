import pytest

from account_deletion import AccountDeletionRequest, DeletionService, demo_request


def test_demo_request_requires_explicit_identifiers():
    with pytest.raises(TypeError):
        demo_request()  # type: ignore[call-arg]


class FakeClient:
    def __init__(self):
        self.calls = []

    def list_sessions(self, user_id):
        self.calls.append(("list", user_id))
        return [{"session_id": "s-1"}, {"session_id": "s-2"}]

    def revoke_session(self, session_id):
        self.calls.append(("session", session_id))

    def revoke_account_key(self, credential_id):
        self.calls.append(("key", credential_id))


def test_deletion_revokes_every_session_before_the_account_key():
    client = FakeClient()
    result = DeletionService(client).delete_account(
        AccountDeletionRequest("tenant-1", "user-1", "key-1")
    )

    assert result.revoked_sessions == 2
    assert result.credential_revoked is True
    assert result.deleted is True
    assert client.calls == [
        ("list", "user-1"),
        ("session", "s-1"),
        ("session", "s-2"),
        ("key", "key-1"),
    ]
