# rowing MCP toolkit

One MCP server that lets you ask any Claude session (built for **Cowork**) to run
the whole training loop. It runs **in your environment** with **your tokens** — so
it can reach HubFit / Concept2 / ErgZone directly, and nothing sensitive is stored
in this repo.

## The four capabilities

| Ask | Tools |
|---|---|
| **1. Get workouts from HubFit** | `hubfit_list_workouts`, `hubfit_get_workout`, `hubfit_export_workouts` |
| **2. Get workouts from Concept2** | `concept2_list_results`, `concept2_get_workout` (per-interval splits) |
| **3. Create ErgZone workouts** (from plain text *or* a HubFit workout, keeping variable pacing) | `ergzone_build_workout`, `ergzone_create` |
| **4. Push workouts to your plan** | `plan_to_rows`, `plan_to_markdown` (+ `pace_split`, `pace_band`) |

Pace targets are **linear off your 500 m PB** (100 % = 1:39.9, each 1 % below = +1 s;
source of truth: the [conkers rowcalc](https://conkers.eatonrise.com/rowcalc/?m=1&s=40&t=0)).
`% → split` is computed everywhere, so changing `PB_500` recomputes all bands.

## Setup

```bash
pip install "mcp[cli]" certifi
```

Register the server with your Claude client (Cowork / Desktop use the same MCP
config shape). Point `command` at your Python and `args` at this file:

```json
{
  "mcpServers": {
    "rowing": {
      "command": "python3",
      "args": ["/absolute/path/to/rowing-plan/mcp/rowing_mcp.py"],
      "env": {
        "HUBFIT_TOKEN": "<persist:root -> clientAccess.token>",
        "HUBFIT_CLIENT_ID": "<clientAccess.clientId>",
        "ERGZONE_TOKEN": "<admin.erg.zone session token>",
        "C2_PROFILE": "2198296"
      }
    }
  }
}
```

### Grabbing the tokens (from your logged-in browser)

- **HubFit** — DevTools → Application → Local Storage → `app.hubfit.com` →
  `persist:root` → the JSON contains `clientAccess.token` (JWT) and
  `clientAccess.clientId`. Tokens expire; re-grab when a call says `invalidToken`.
- **ErgZone** — on `admin.erg.zone`, DevTools → Network → any `api` request →
  copy the `Authorization` value (or the session cookie). Only needed to create.
- **Concept2** — nothing; the logbook is public.

## Typical Cowork flow (monthly)

> "Export next month's non-strength HubFit workouts, turn each into an ErgZone
>  workout keeping its pacing, create them in my track, and give me the links +
>  a Markdown table for my plan."

Under the hood:
1. `hubfit_export_workouts(future_only=true)` → full detail incl. variable pacing.
2. For each: `ergzone_build_workout(<that workout's JSON>)` → ErgZone spec.
3. `ergzone_create(<spec>)` → creates it (or returns entry steps — see below).
4. `plan_to_markdown([...])` / `plan_to_rows([...])` → drop into your plan site.

## Enabling direct ErgZone creation

ErgZone has no public API, so `ergzone_create` needs the exact create endpoint.
Capture it **once** in Cowork: create any workout in the admin with DevTools →
Network open, find the `POST` request that saves it, and set two env vars:

```
ERGZONE_CREATE_URL=https://admin.erg.zone/<the/POST/path>
ERGZONE_TOKEN=<session token>
```

Until then, `ergzone_create` returns the ready-to-enter spec and step list, and
Cowork can create it in the browser directly from that.

## Notes

- Site-agnostic by design: your plan site is changing, so the plan tools only
  *render* workouts (rows / Markdown / derived bands) — Claude writes the output
  wherever the new plan lives.
- Everything is read-only except `ergzone_create`.
- `PB_500` env var overrides the default 1:39.9 anchor after a new 500 m PB.
