# utility-powerbi

A [Meltano](https://meltano.com) utility extension that triggers and
monitors Power BI semantic-model refreshes as a step in a Meltano
pipeline. Built on the [Meltano EDK](https://github.com/meltano/edk) and
[`azure-identity`](https://pypi.org/project/azure-identity/).

Forked from [`lgrosjean/powerbi-ext`](https://github.com/lgrosjean/powerbi-ext)
and extended with async refresh handling, polling, status lookup, and
history listing — see the **Bug fixes vs upstream** section near the end.

## Use case

Today many teams rely on Power BI Service's scheduled-refresh UI, which
is decoupled from data-pipeline completion: refresh timing drifts from
when data lands. This utility moves the refresh trigger into the
Meltano pipeline itself so the orchestrated path is
extract → load → transform → **refresh** — and a refresh failure fails
the pipeline.

## Install

Add the utility to your Meltano project, pinned to a release tag:

```yaml
# meltano.yml
plugins:
  utilities:
    - name: powerbi
      variant: matatika
      pip_url: git+https://github.com/Matatika/utility-powerbi.git@v0.1.0
```

Then:

```sh
meltano install utility powerbi
```

## Prerequisites — Azure AD service principal setup

The utility authenticates non-interactively using a Microsoft Entra
(Azure AD) service principal. Set this up once per tenant:

1. **Register an application in Azure AD.** Portal → Azure Active
   Directory → App registrations → New registration. Capture the
   resulting **Tenant ID** and **Client (Application) ID**.
2. **Create a client secret.** App registration → Certificates &
   secrets → New client secret. Capture the **Client Secret value** —
   it is shown only at creation.
3. **Enable service-principal API access in Power BI.** Power BI Admin
   Portal → Tenant settings → "Service principals can use Power BI
   APIs". Either enable for the whole tenant or for a specific
   security group containing the principal.
4. **Grant the principal access to your workspaces.** In each Power BI
   workspace whose datasets you intend to refresh, add the service
   principal as a **Member** (or higher).
5. **Capture workspace + dataset IDs.** Open the dataset in Power BI
   Service; the URL contains both:
   `https://app.powerbi.com/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/...`

## Configuration

| Setting | Env var | Required | Description |
|---|---|---|---|
| `tenant_id` | `POWERBI_TENANT_ID` | yes | Azure AD tenant ID. |
| `client_id` | `POWERBI_CLIENT_ID` | yes | Azure AD application (client) ID. |
| `client_secret` | `POWERBI_CLIENT_SECRET` | yes | Azure AD application client secret. |
| `workspace_id` | `POWERBI_WORKSPACE_ID` | yes | Power BI workspace (group) ID. |
| `dataset_id` | `POWERBI_DATASET_ID` | yes | Power BI dataset (semantic model) ID. |
| `api_url` | `POWERBI_API_URL` | no | Override API base URL (default `https://api.powerbi.com/v1.0/myorg`). Useful for sovereign clouds (e.g. `https://api.powerbigov.us/v1.0/myorg`). |

Configure interactively:

```sh
meltano config powerbi set --interactive
```

Or via environment variables in your shell / `.env`:

```sh
export POWERBI_TENANT_ID=...
export POWERBI_CLIENT_ID=...
export POWERBI_CLIENT_SECRET=...
export POWERBI_WORKSPACE_ID=...
export POWERBI_DATASET_ID=...
```

## Commands

### `refresh` — trigger and (by default) wait for completion

```sh
meltano invoke powerbi:refresh [--wait/--no-wait] [--poll-interval=30] [--timeout=3600] [--notify=NoNotification]
```

| Flag | Default | Description |
|---|---|---|
| `--wait` / `--no-wait` | `--wait` | Block until the refresh reaches a terminal status. |
| `--poll-interval` | 30 | Seconds between status polls when waiting. |
| `--timeout` | 3600 | Max seconds to wait before exiting with timeout. |
| `--notify` | `NoNotification` | Power BI `notifyOption`: one of `NoNotification`, `MailOnCompletion`, `MailOnFailure`. |

The request ID is always echoed to stdout on trigger, so it can be
captured by an outer script even when `--no-wait` is used.

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Refresh completed successfully |
| 1 | Refresh ended in `Failed` or `Disabled` terminal state |
| 2 | Refresh did not reach a terminal state within `--timeout` |
| 3 | Auth or HTTP error (credentials, permissions, network, 4xx/5xx) |

### `status` — look up a refresh

```sh
meltano invoke powerbi:status [--request-id=<id>]
```

Without `--request-id`, returns the most recent refresh from history.
Output is JSON containing `requestId`, `status`, `startTime`, `endTime`,
`refreshType`, and `serviceExceptionJson` when applicable.

Exit codes mirror `refresh` (0 / 1 / 3). Empty history returns exit 3.

### `history` — list recent refreshes

```sh
meltano invoke powerbi:history [--top=10]
```

Returns a JSON array of recent refreshes for the configured dataset.
`--top` caps the count (Power BI accepts up to 200).

Exit 0 on success, 3 on auth/HTTP error.

## Pipeline usage

Append `powerbi:refresh` to the `actions` of any Meltano pipeline that
runs after data has landed:

```yaml
# meltano.yml
schedules:
  - name: daily_refresh
    interval: '@daily'
    job: ingest_and_refresh

jobs:
  - name: ingest_and_refresh
    tasks:
      - tap-postgres target-snowflake
      - dbt-snowflake:run
      - powerbi:refresh
```

A non-zero exit from `powerbi:refresh` fails the Meltano job.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Exit 3 with `401 Unauthorized` | Service principal not enabled in Power BI Admin Portal, or not added to the workspace. Re-check prerequisites 3 + 4. |
| Exit 3 with `403 Forbidden` on `refresh` | Principal has read access but not write — make it a Member, not Viewer. |
| Exit 3 with `404 Not Found` | Wrong `workspace_id` or `dataset_id`, or the dataset is in "My workspace" (personal, not API-accessible). |
| `400 Bad Request` with `Operation in progress` | Power BI allows only one refresh in progress per dataset at a time. Wait for the running refresh to finish or check `powerbi:history`. |
| Exit 3 with `429 Too Many Requests` | Shared-capacity datasets are limited to 8 refreshes/day. Either move to Premium capacity or reduce schedule frequency. |
| Exit 2 (timeout) | Refresh is still running but exceeded `--timeout`. Bump `--timeout`, or use `--no-wait` and poll with `powerbi:status`. |

## Local development

```sh
poetry install
poetry run pytest

# Verify the CLI loads:
poetry run powerbi-extension --help
poetry run powerbi-extension describe --format=yaml

# Invoke against a real tenant (sandbox recommended):
export POWERBI_TENANT_ID=... POWERBI_CLIENT_ID=... POWERBI_CLIENT_SECRET=...
export POWERBI_WORKSPACE_ID=... POWERBI_DATASET_ID=...
poetry run powerbi-extension refresh --no-wait
poetry run powerbi-extension status
poetry run powerbi-extension history --top 5
```

## Bug fixes vs upstream (`lgrosjean/powerbi-ext`)

The upstream is dormant since Oct 2023 and never tagged a release. This
fork corrects the following functional issues:

1. **`refresh` raised on every success.** Upstream checked
   `status_code != 200`; Power BI's enhanced refresh API returns
   `202 Accepted`.
2. **Wrong header for `requestId`.** Upstream read
   `res.headers["RequestId"]`, which Power BI does not emit. Fixed to
   parse the `Location` header path tail with `x-ms-request-id` as
   fallback.
3. **Settings were declared but never read.** `workspace_id` and
   `dataset_id` were declared in `meltano.yml` but the code only
   accepted them as CLI args. Fixed to read from
   `POWERBI_WORKSPACE_ID` / `POWERBI_DATASET_ID` env vars (which
   Meltano populates from settings).
4. **Mail spam by default.** Upstream defaulted `notifyOption` to
   `MailOnCompletion`. Changed to `NoNotification` for unattended ETL;
   callers can opt in via `--notify`.
5. **`describe` reported a phantom command.** Fixed to list the three
   real commands.
6. **No status / history / polling.** All three added as part of the
   trigger-and-wait flow required for pipeline integration.

## License

Apache-2.0. Copyright 2023 Leo Grosjean, 2026 Matatika Ltd. See
[LICENSE](LICENSE).
