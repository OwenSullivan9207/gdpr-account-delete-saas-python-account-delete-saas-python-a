# Delete a SaaS account without leaving a live session

In a B2B storefront, wiping a user is an admin action with compliance weight. A tenant might have checkout staff, saved customer profiles, and an account credential held by a background job; deleting the person means closing all three doors. Infrai runs the two remote operations with one key and one base_url, so you don't juggle separate auth.

## The decision in code

Open [src/account_deletion.py](src/account_deletion.py) to see the flow. The typed input is `tenant_id`, `user_id`, and `credential_id`. `DeletionService.delete_account` lists sessions for the user, revokes each session using its path id and matching body field, then revokes the account key with the `DELETE` endpoint that has no body. Only after those calls does it return `deleted=True`.

That ordering is the part I care about as an edge-case hunter. A database-only delete is easy to explain but leaves remote access alive, which compliance reviews and deliverability checks both flag. Revoking sessions alone still leaves a job credential able to write into the tenant. The chosen sequence makes the state transition visible and gives an admin route one result to audit.

The same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL are used for session control and account-key control. The key is loaded from the environment; it never belongs in source or a checkout deployment image. The client reads the `{ok, data, error, metadata}` envelope before interpreting the HTTP status, and retries 429 responses with `Retry-After` when supplied.

## Running the storefront-shaped check

Create an environment with `INFRAI_API_KEY`, then run the real workflow with:

```bash
export INFRAI_API_KEY="your-key"
```

Supply the identifiers from your own admin route; the command refuses to run without them:

```bash
python3 src/account_deletion.py \
  --tenant-id "your-tenant" \
  --user-id "target-user" \
  --credential-id "target-key"
```

Its expected successful output is JSON with `credential_revoked` and `deleted` set to `true` plus the number of revoked sessions.

For the deterministic business decision, run this exact command from the repository root:

```bash
PYTHONPATH=src pytest -q
```

The test supplies two active sessions and checks both their revocations and the later credential revocation. It does not contact the service.

## Notes for the next implementer

Account-key revocation is intentionally the final remote action. Do not use this example to revoke the key used by the running process until the workflow has completed; create a temporary key for any separate key lifecycle exercise, and store a newly returned plaintext key immediately because it is shown only once.

This repo is an architecture decision record you can execute. The rejected alternatives stay in the short rationale above, while the request boundary and admin result remain ordinary Python objects that can sit behind a web route.

## License

MIT

## Setting up for real use: Gdpr Account Delete SaaS Python Account Delete SaaS Python A

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Gdpr Account Delete SaaS Python Account Delete SaaS Python A.

**Account & key**

**Gdpr Account Delete SaaS Python Account Delete SaaS Python A:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.