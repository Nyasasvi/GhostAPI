# GhostAPI Bridge RPC and CLI Contract

**Status:** Draft v0.1 (Week 0 proposal; the Week 1 surface only; not implemented)
**Transport:** HTTP/1.1 + strict versioned JSON (ADR-008). Neutral wire contract for `PlatformBridge` (ADR-007).
**Rule:** this doc and the contract tests change together. Anything not listed here does not exist.

---

## 1. Envelope and conventions

- Base path: `/v1`. The server binds only to guest `127.0.0.1:<port>`. The host reaches it only through an SSH local forward bound to host `127.0.0.1`.
- Auth: `Authorization: Bearer <boot_token>`. The token is generated when the guest service starts, written to a 0600 file readable only by the GUI user, and fetched by the host over SSH. This is defense in depth on top of the tunnel.
- Required request headers:
  - `X-Ghost-Request-Id` (UUIDv4, unique per logical request, reused on retries);
  - `X-Ghost-Correlation-Id` (run/session/trial/action lineage);
  - `X-Ghost-Deadline-Ms` (client deadline; the server aborts past it).
- Every response carries `protocol_version`, `bridge_version`, `request_id`, and `server_time`.
- Body limits:
  - request bodies ≤ 64 KiB;
  - JSON response bodies ≤ 8 MiB (observations over the limit are truncated with `truncated: true` and reasons);
  - artifacts ≤ 32 MiB each.
- Content types: `application/json; charset=utf-8`. Artifacts use their own media type (`image/png`, `application/json`).
- Unknown fields in requests are rejected (`INVALID_REQUEST`). Responses may gain *additive* optional fields within `/v1`, and clients ignore unknown response fields only if a contract test allows it.
- JSON Schemas live in `ghost-bridge/schemas/v1/` and are the source of truth. Golden request/response fixtures are validated by both Swift and Python tests.

### 1.1 Error body

```json
{"error": {"code": "STALE_HANDLE", "message": "…", "retryable": false, "detail": {}},
 "protocol_version": "1", "request_id": "…"}
```

| Code | HTTP | Retryable | Meaning |
|---|---|---|---|
| `INVALID_REQUEST` | 400 | no | schema violation, unknown field, bad value |
| `UNAUTHORIZED` | 401 | no | missing/invalid boot token |
| `PERMISSION_DENIED` | 403 | no | Accessibility or Screen Recording not granted |
| `APP_NOT_FOUND` | 404 | no | application ref unknown or process gone |
| `WINDOW_NOT_FOUND` | 404 | no | window ref unknown |
| `ELEMENT_NOT_FOUND` | 404 | no | handle index not present in that generation |
| `ARTIFACT_NOT_FOUND` | 404 | no | unknown artifact id |
| `STALE_HANDLE` | 409 | no | handle's observation generation is no longer current |
| `BUSY` | 409 | yes (reads only) | another mutation is in progress (one active writer) |
| `ACTION_UNSUPPORTED` | 422 | no | element does not advertise the action |
| `PAYLOAD_TOO_LARGE` | 413 | no | request exceeds limits |
| `AX_ERROR` | 502 | no (mutations) / yes (reads) | platform accessibility error; raw code in `detail` |
| `CAPTURE_FAILED` | 502 | yes | screenshot capture failed |
| `TIMEOUT` | 504 | reads only | server deadline exceeded |
| `NOT_IN_VM` | 503 | no | the service refused to run on non-VM hardware |
| `PROTOCOL_MISMATCH` | 400 | no | client/server protocol versions incompatible |

---

## 2. Handles and generations

- `observation_generation` is a monotonically increasing integer per application. It increments on every `POST /v1/observations` for that application.
- `ElementHandle` = `{"generation": <int>, "index": <int>}`. It is opaque to Ghost Core and valid only while its generation is the latest for that application.
- Mutations with a stale handle return `STALE_HANDLE`. The bridge never re-resolves a stale handle by itself.
- Handles are never persisted in GIR (AGENTS invariant 7).

## 3. Retry and idempotency

- Reads (`GET`, `POST /v1/observations`, `POST /v1/captures`) may be retried by the client, up to 2 times with backoff, using the same `X-Ghost-Request-Id`.
- Mutations (`/v1/apps/launch`, `/v1/actions/*`) are **never retried automatically**. If the bridge sees a repeated `X-Ghost-Request-Id` for a mutation, it returns the stored result of the first execution and does not execute again (dedupe window: the life of the bridge process).
- Mutations are serialized. A second concurrent mutation gets `BUSY`.

---

## 4. Endpoints (Week 1)

Default deadlines (the client may lower them): health 2 s, list 5 s, launch 20 s, observation 15 s, capture 10 s, artifact 10 s, actions 5 s.

### `GET /v1/health`

Liveness and readiness. No side effects.

```json
{"live": true,
 "ready": false,
 "uptime_s": 12.4,
 "readiness": {"ax_permission": "granted|denied|unknown",
               "capture_permission": "granted|denied|unknown",
               "input_ready": true,
               "gui_session": true,
               "is_vm": true,
               "vm_evidence": {"hw_model": "…", "hv_vmm_present": 1}},
 "normalizer_version": "1",
 "protocol_version": "1", "bridge_version": "0.1.0+<git sha>"}
```

`ready` is true only if all of these hold: `ax_permission == granted`, `capture_permission == granted`, `gui_session`, `is_vm`. The VM-evidence fields must be verified in the Week 0/1 spike.

### `GET /v1/apps`

```json
{"applications": [{"application_ref": "app_3f2a…", "display_name": "…", "is_active": true,
                   "is_hidden": false, "version_hash": "sha256:…"}]}
```

`application_ref` is opaque and stable for the process lifetime. `display_name` is observable metadata. It is replaced with an alias before reaching any LLM (`semantics/` does this, not the bridge).

### `GET /v1/windows?application_ref=…`

```json
{"windows": [{"window_ref": "win_…", "title": "…", "bounds": {"x":0,"y":0,"w":800,"h":600,
              "space": "screen_points_top_left"}, "focused": true, "main": true, "minimized": false}]}
```

### `POST /v1/apps/launch` (mutation)

```json
{"launch_ref": "seed:app_under_test", "activate": true}
```

`launch_ref` is an **operator-provided opaque reference**, declared in the VM seed manifest, that the bridge maps to a local app path. Ghost Core never holds app names, bundle IDs, or paths. Response: `{"application_ref": "…", "launched": true, "already_running": false}`.

### `POST /v1/observations`

```json
{"application_ref": "app_…", "max_depth": 40, "max_nodes": 5000, "include_menus": true,
 "include_capture": true}
```

Response:

```json
{"observation_id": "obs_…", "generation": 17, "captured_at": "…",
 "raw": {"artifact_id": "sha256:…", "media_type": "application/json", "bytes": 482113},
 "capture": {"artifact_id": "sha256:…", "media_type": "image/png", "width": 1280, "height": 800},
 "platform_observation": {"normalizer_version": "1",
   "windows": [ … ], "focused": {"generation": 17, "index": 42},
   "root": {"handle": {"generation": 17, "index": 0}, "role": "window", "label": "…",
            "value": null, "states": ["focused"], "bounds": {…}, "actions": [],
            "stable_id_hint": null, "children": [ … ], "truncated": false}},
 "truncation": {"truncated": false, "reasons": []},
 "timing_ms": {"ax": 310, "capture": 95, "normalize": 12}}
```

- The raw AX capture is stored as an artifact first, and its hash is returned. The PlatformObservation is derived from exactly that raw artifact.
- `truncated` and `reasons` (`max_nodes`, `max_depth`, `attribute_error`, `virtualized`) make missing content explicit, so it is recorded as UNKNOWN.
- Generic AX enablement (for example, requesting an enhanced accessibility tree from an application) is **off in Week 1**. If enabled later, it applies to all apps identically and is recorded in the raw capture metadata and the run manifest.

### `POST /v1/captures`

```json
{"application_ref": "app_…", "window_ref": "win_…"}
```

Response: `{"capture_id": "cap_…", "artifact_id": "sha256:…", "width": 1280, "height": 800, "captured_at": "…", "correlated_observation_id": null}`. Captures are raw evidence only. Nothing in Ghost Core performs visual inference on them (ADR-009).

### `GET /v1/artifacts/{artifact_id}`

Returns the bytes with `Content-Type`, `Content-Length`, and `X-Ghost-Sha256`. The host must verify the hash before storing. Artifacts are kept in the guest only until extraction. The host store is authoritative.

### `POST /v1/actions/invoke` (mutation)

```json
{"handle": {"generation": 17, "index": 42}, "deadline_ms": 5000}
```

Response: `{"action_id": "act_…", "executed": true, "platform_status": "success", "elapsed_ms": 38}`. This is an **executor claim only**. It never proves success (AGENTS invariant 5).

### `POST /v1/actions/set-value` (mutation)

```json
{"handle": {"generation": 17, "index": 51}, "value": {"type": "string", "value": "GP-7c1e…"},
 "deadline_ms": 5000}
```

Allowed value types in Week 1: `string` (≤ 4,096 chars), `bool`, `number`. Same response shape as `invoke`.

---

## 5. Explicitly excluded in Week 1

No exploration APIs, semantic APIs, GIR APIs, arbitrary shell execution, arbitrary filesystem access, coordinate clicks, generic keyboard endpoints, product REST APIs, VM lifecycle APIs, or future-platform APIs.

## 6. Planned additions (each needs its own reviewed API change)

| Addition | Needed by | Notes |
|---|---|---|
| `POST /v1/actions/type-text`, `POST /v1/actions/key-chord` | Week 2 (exploration: commit text fields) | neutral `TYPE_TEXT`, `KEY_CHORD` primitives |
| `POST /v1/apps/quit` (graceful/force) | Week 4 (relaunch verification, stratum S1) | mutation, never auto-retried |
| `POST /v1/windows/arrange` | Week 4 (stratum S2) | move/resize to seeded bounds |
| raw-input endpoints (coordinate click, type, key, scroll) | Week 4, benchmark harness only | baseline arms B1/B2; not callable by discovery code (invariant) |

---

## 7. `ghost` CLI (Week 1 surface)

The CLI is thin: parse arguments, call a module, print. It runs only when the sandbox guard passes.

```text
ghost observe <launch-ref|application-ref> [--max-nodes N] [--no-capture]   # prints PlatformObservation summary + artifact ids
ghost press <generation:index>                                             # invoke; then re-observe and print the diff
ghost set <generation:index> <value>                                       # set-value; then re-observe and print the diff
```

The later CLI (`explore`, `hypothesize`, `trial`, `learn`, `inspect`, `call`, `bench`) is documented when its week begins. The public `ghost call` CLI arrives in Week 5 (Week 4 proves the internal GIR runtime).
