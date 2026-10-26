# RedeTI Recovery OS — Enrollment Broker (Hermes)

**Current stage: Phase A, server-only core + mocked OAuth integration.**
No service is listening on a network port and the ISO is **unchanged**.

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
  `tag:redeti-recovery`, provider-error redaction, injectable fake transport.
- `openapi.yaml` — proposed HTTPS endpoint contract for **future** agent
  and Service Desk integrations; not an implemented HTTP service.
- `appliance/tests/test_enrollment_broker.py` — fake issuance tests covering
  stolen pairing code, wrong agent secret, concurrent claims, TTL, rejection,
  exhausted rate limits and disallowed auth-key capabilities.

Run from repository root:

```bash
python3 -m unittest discover -s appliance/tests -v
```

No internet access, Tailscale credentials or running Hermes is required
for these tests.

## Server deployment requirements — NOT done yet

1. Deploy a **dedicated backend** on Hermes, not inside the Recovery ISO or
   the public static Pages site. Integrate technician authentication with
   RedeTI Service Desk, MFA, roles, CSRF and work-order authorization.
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
| HTTPS ingress/API backend | Not implemented |
| Service Desk technician authentication | Not integrated |
| Hermes secrets + deployment | Not implemented |
| ISO / LVGL agent integration | Not implemented |
| Tailscale field enrollment | Not homologated |
| SSH over VPN | Previous banner timeout unresolved |

Reference design: `appliance/design/FIELD_VPN_ZERO_TOUCH_PROVISIONING.md`.
