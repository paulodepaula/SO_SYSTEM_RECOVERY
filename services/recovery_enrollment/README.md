# RedeTI Recovery OS — Enrollment Broker (Hermes)

**Current stage: Phase A / private HTTP adapter.** The HTTP handler exists
but is deliberately **loopback-only**, with no operator approval endpoint
and no standalone launcher. Nothing is deployed on Hermes, no public
service is listening, and the ISO is **unchanged by the broker work**.
The separate static SSH banner does not alter the VPN or the identity
of the current ISO.

## Motivation

A one-off Tailscale auth key stored in Ventoy works only for one new device.
A reusable key in the ISO/USB would be a dangerous portable credential.
The Hermes enrollment broker instead creates a new tag-scoped, one-off,
ephemeral key **after** an authenticated technician approves a recovery
session. Neither the Recovery OS nor GitHub receives the OAuth client secret.

## Implemented in this phase

- `core.py` — short-lived pairing, separate 256-bit agent secret and 8-digit
  visual pairing code, approved-only issue, atomic one-time delivery,
  per-source rate limit, resource cap, expiry and safe event names.
- `tailscale_oauth.py` — backend-only OAuth client-credentials exchange,
  fixed HTTPS Tailscale URLs, single-use ephemeral auth keys with only
  `tag:redeti-recovery`, **15-minute expiry and pre-approval only after a
  verified operator approval** (avoids a second Tailscale device-approval
  workflow), provider-error redaction and injectable fake transport.
- `check_oauth.py` — read-only Hermes smoke check using root-owned `0700`
  directory and `0600` files under `/etc/redeti-recovery`. Requests only a
  short-lived OAuth token with `auth_keys` and `tag:redeti-recovery`, verifies
  its scope and prints only PASS/FAIL; **never creates an auth key**.
  Use `sudo python3 -m services.recovery_enrollment.check_oauth` from a
  trusted, reviewed checkout. Not part of ISO or an automated deploy.
- `smoke_local.py` — complete Hermes-side local dry-run (loopback agent
  interface, signed operator approval via UNIX socket, single mock claim).
  Run `python3 -m services.recovery_enrollment.smoke_local` from the repo root;
  **it never loads the OAuth credentials or accesses the Tailscale API**.
- `inspect_smoke_keys.py` — **read-only** reconciliation for any
  `revocation_unverified_review_keys_panel` event. Run `sudo python3 -m
  services.recovery_enrollment.inspect_smoke_keys`. Queries only OAuth token
  exchange + GET keys metadata; prints only number of matching
  `redeti-recovery-smoke` keys (active/inactive/uncertain), not IDs or tokens.
  If active/uncertain: inspect/revoke by description in the Tailscale Keys
  admin panel; **never rerun the create-and-revoke test** until reviewed.
  On `key_listing_null_keys`, the CLI now prints `INCONCLUSIVE`: the
  upstream API returned `keys: null`, which can represent a nil/empty
  collection in Tailscale's Go API client. No active keys are visible
  through this credential, but this cannot establish whether the previous
  DELETE succeeded or the 15-minute smoke key simply expired.
  **Review the Keys admin console once and close the incident manually.**
  This check does NOT itself revoke anything and a zero count is limited to
  what the OAuth credential is allowed to see. Expired one-off auth keys may
  disappear from the API listing.
- `check_authkey_lifecycle.py` — deliberate **live** API creation-and-immediate-
  revocation check, after successful simulated E2E. On Hermes only:
  `sudo python3 -m services.recovery_enrollment.check_authkey_lifecycle --create-and-revoke`.
  This operation intentionally **creates one Tailscale auth key** with a
  15-minute expiry, one-time/ephemeral, tag `tag:redeti-recovery` and
  `preauthorized=false` (unlike production approval). It verifies the returned
  scope and immediately **revokes the key**. It never shows/saves the
  key or registers a node; the OAuth secret is read only from protected files.
  A PASS confirms creation and successful API revocation. A FAIL ending
  `review_keys_panel` means check the Tailscale admin Keys page and manually
  revoke any surviving smoke-test key; **do not rerun until reconciled**.
  No Service Desk authorization and no ISO/field enrollment occurs here.
- `http_api.py` — private 127.0.0.1-only agent POST request, GET status and
  POST claim adapter; rejects unknown/operator routes, requires bearer
  proof for status/claim and sends no-store responses. Not deployed.
- `operator_auth.py` — validates 60-second HMAC-SHA256 approvals issued by
  trusted Service Desk backend with exact audience, role, permission, O.S.,
  pairing code and replay prevention. Test-only signing utility is not
  part of a publicly callable API.
- `operator_socket.py` — **separate AF_UNIX** HTTP approval adapter;
  private 0700 directory / 0600 socket, no TCP listener, uniform denial
  and no request/body logging. Not deployed.
- `SERVICE_DESK_APPROVAL_CONTRACT.md` — exact assertion format and
  boundary between signed Service Desk approval and Hermes broker.
- `openapi.yaml` — endpoint contract; **operator approval remains not
  implemented** until it is integrated with authenticated Service Desk roles.
- `appliance/tests/test_enrollment_broker.py` — fake issuance tests covering
  stolen pairing code, wrong agent secret, concurrent claims, TTL, rejection,
  exhausted rate limits and disallowed auth-key capabilities.
- `appliance/tests/test_enrollment_http.py` — local socket tests for loopback
  binding, no-store, agent secret authentication and blocked operator paths.
- `appliance/tests/test_enrollment_check_oauth.py` — fake API responses,
  missing scope, credential error redaction and strict file permissions.
- `appliance/tests/test_enrollment_smoke_local.py` — end-to-end exercise
  of the mock issuer through both private agent and operator interfaces.
- `appliance/tests/test_enrollment_check_authkey_lifecycle.py` — offline
  transport mocks verify that the live checker revokes keys after creation,
  detects malformed capabilities and never blindly retries uncertain issuance.
- `appliance/tests/test_enrollment_operator_auth.py` and
  `test_enrollment_operator_socket.py` — signature, role, expiry, replay,
  wrong session, concurrent calls and UNIX-only socket security.

Run from repository root:

```bash
python3 -m unittest discover -s appliance/tests -v
```

No internet access, Tailscale credentials or running Hermes is required
for these tests.

## Server deployment requirements — NOT done yet

1. Integrate technician authentication with the RedeTI Service Desk,
   MFA, roles, CSRF and work-order authorization before deploying the
   broker. `http_api.py` has no approval route by design; approval remains
   a trusted internal method, never a public browser endpoint.
2. Put operator approval endpoints behind authenticated Service Desk/Access
   with explicit verification of the matching device's pairing code.
   **Do not expose `EnrollmentBroker.approve()` directly on the internet.**
3. Expose only the agent bootstrap and claim endpoints via HTTPS with WAF,
   source-specific and global rate limits, request size limits, safe clock,
   no-cache responses and body redaction in all proxy/access logs.
4. Use a server-side secret manager and an OAuth client with **`auth_keys`
   scope restricted to `tag:redeti-recovery`**. Store the OAuth secret
   only on Hermes (not GitHub, .env committed to source control, or Ventoy).
   Never call `tailscale up` with the OAuth secret in the client.
5. Replace in-memory session storage with carefully constrained Redis or
   equivalent shared storage (ephemeral and protected), distributed locking,
   durable non-secret audit and rigorous resilience/load testing.
   Handle API timeout/unknown-issuance outcomes without blind retries.
6. Develop and validate agent-side HTTPS bootstrap/proof and LVGL pairing UI,
   without affecting the LAN SSH fallback or writing customer disks.
7. Independently resolve the existing tailnet SSH **banner timeout** before
   declaring remote access production-ready. `tailscale ping` and a TCP
   handshake alone are not SSH success.

## Trust boundaries

`untrusted Recovery Agent -> HTTPS bootstrap -> pending (random code)`

`authenticated technician + OS authorization -> approval -> approved`

`original agent (separate 256-bit claim secret) -> HTTPS -> one key -> consumed`

A code photographed on the Recovery screen is **not** a credential.
The server delivers the Tailscale enrollment key only to the same agent
that initiated the pending session, after technician approval. Approval
includes an authenticated technician and work order. All approval, API
and state transition paths must fail closed.

Do not print the auth key or claim secret, include either in a URL/QR,
pass client OAuth secrets to Recovery, or persist the enrollment key in a
customer disk/USB. Auth key is consumed in tmpfs and discarded.

## Policy and operator preparation

The current tailnet policy created for testing permits only authenticated
RedeTI technicians to reach `tag:redeti-recovery` on TCP/22, with a
Tailscale SSH `check` rule for Linux user `paulo`. Before production,
revalidate access tests for each technician, verify no legacy wildcard
grant applies, and validate that this policy is actually saved.

Create an OAuth client from the Tailscale Trust Credentials section
with the minimum `auth_keys` scope and the recovery tag. **Do not
provide the secret to this repository or chat.** No production OAuth
client is needed for Phase A tests.

## Status

| Feature | Status |
|---|---|
| Pairing state machine | Implemented; offline tests |
| Mocked Tailscale OAuth issuer | Implemented; offline tests |
| OAuth credential test on Hermes | Operator confirmed PASS (token exchange only) |
| Local end-to-end broker dry-run | Implemented, CI tests; field run pending |
| Real Tailscale auth-key issuance / revocation | Explicit smoke checker implemented; operator test pending |
| Private loopback HTTP agent adapter | Implemented, offline tests; not deployed |
| Signed approval verifier / private operator UNIX socket | Implemented, offline tests; not deployed |
| Service Desk-side signing and authenticated session integration | Not implemented |
| HTTPS ingress and operator permissions integration | Not implemented |
| Service Desk technician authentication | Not integrated |
| Hermes secrets + deployment | Not implemented |
| ISO / LVGL agent integration | Not implemented |
| Tailscale field enrollment | Not homologated |
| SSH over VPN | Previous banner timeout unresolved |

Reference design: `appliance/design/FIELD_VPN_ZERO_TOUCH_PROVISIONING.md`.
