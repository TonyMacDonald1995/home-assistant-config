# CLAUDE.md — MakeNashville Home Assistant Config

This file helps AI assistants understand how this repo works and how to make changes safely.

---

## What this repo is

Home Assistant configuration for the [MakeNashville](https://makenashville.org) makerspace. It manages:
- 3D printer lifecycle notifications (6 printers → `#3dprint-info` Slack)
- Facilities monitoring: temperature, water, power, Kaeser compressor (→ `#facilities-feed`)
- Air quality alerting for the 3D print room
- Eventbrite event + signup notifications (→ `#integrations_sandbox`)
- Automated nightly config backup to GitHub

---

## Key files

| File | Purpose |
|------|---------|
| `configuration.yaml` | Core HA config: recorder excludes, template sensors, input helpers, shell commands |
| `automations/printers.yaml` | All 3D printer automations |
| `automations/facilities.yaml` | Facilities Pulse smart alert + verbose mode + Air Quality Alert |
| `automations/kaeser.yaml` | Kaeser compressor overpressure alert + history purge |
| `automations/eventbrite.yaml` | Eventbrite new event + daily signup digest notifications |
| `automations/webhooks.yaml` | Stripe filament webhook + OctoEverywhere Gadget webhook + Slack cancel-print webhook |
| `automations/backup.yaml` | Triggers nightly backup via SSH addon |
| `git_backup.sh` | Backup script: checkouts ha-backup, merges main, commits, pushes, opens PR |
| `write_entity_list.sh` | Writes `entity_list.txt` from entities tagged with the `entity_list` HA label |
| `entity_list.txt` | Auto-generated entity ID reference. **Do not edit by hand.** |
| `dashboards/facilities.yaml` | Lovelace YAML dashboard for facilities overview |
| `esphome/kaeser-monitor.yaml` | ESPHome config for the Kaeser pressure/switch sensor |

---

## Branch and deploy workflow

```
feature branch → PR → validate-yaml.yml passes → merge to main → deploy.yml auto-deploys
```

- `main` is **branch-protected** — direct pushes are blocked
- Always branch off `main`, open a PR, wait for YAML validation, then merge
- On merge, `deploy.yml` pulls config onto HA, validates it, and reloads or restarts as needed
- Deployment status posts to `#deployment-feed`
- New integrations should post to `#integrations_sandbox` first for testing before moving to a production channel

### Backup branch

HA itself cannot push to `main`. The nightly backup:
1. Checks out `ha-backup`
2. Merges `origin/main`
3. Runs `write_entity_list.sh`
4. Commits any changed files
5. Pushes to `ha-backup`
6. Opens (or surfaces) a PR to `main`

A fine-grained GitHub PAT is stored at `/config/.github_token` with `Contents: write` and `Pull requests: write` scoped to this repo.

---

## Things that are NOT in this repo

- `secrets.yaml` — gitignored; must exist on the HA host
- `esphome/secrets.yaml` — gitignored; must exist on the HA host
- `.storage/` — gitignored; HA runtime state
- `custom_components/` — gitignored

---

## Printers

Six printers, named after fruits:

| Name | Integration | Notes |
|------|-------------|-------|
| Kiwi | Bambu Lab | |
| Mango | Bambu Lab | |
| Papaya | Bambu Lab | |
| Strawberry | Bambu Lab | |
| Huckleberry | Bambu Lab | |
| Pineapple | Prusa | Different state values (e.g. `completed` not `finish`) |
| Dragonfruit | (additional) | Template sensors only so far |

Bambu printers use anchors (`bambu_lab_printers`, `all_printers`) in `automations/printers.yaml` — add new Bambu printers to those anchors.

### Slack pause button

Print Starting, Print Progress, Print Paused, and Gadget AI notifications include a Slack Block Kit "Pause Print" button (Bambu printers only). Clicking it triggers a confirmation dialog, then POSTs to an HA webhook that presses `button.{printer}_pause_printing` and responds in Slack.

- The button uses `action_id: pause_bambu_print` with the printer name as `value`
- The webhook automation is in `automations/webhooks.yaml` (`Slack – Pause Bambu Print`)
- `rest_command.slack_respond` in `configuration.yaml` handles the Slack response via `response_url`
- Requires Slack app Interactivity enabled with Request URL pointing to the HA webhook
- Secret: `slack_cancel_print_webhook_id` in `secrets.yaml`

---

## Entity list opt-in

`entity_list.txt` is **not** all entities — it's only entities tagged with the `entity_list` HA label. To add an entity:
1. Go to HA > Settings > Labels → create `entity_list` if it doesn't exist
2. Go to the entity's settings page and apply the label

The file is regenerated automatically before each backup. Use it as an entity ID reference when writing automations or templates.

---

## Facilities Pulse label

The Facilities Pulse automation uses the `facilities_pulse` HA device label to find climate sensors dynamically. Tag any climate sensor device with this label and it appears automatically in pulse messages and the Facilities dashboard — no YAML changes needed.

---

## Shell scripts

Both scripts run inside the **SSH addon** container, not the HA core container.

- **`git_backup.sh`** — uses `jq` for JSON construction, reads token from `/config/.github_token`, sets up inline `credential.helper` to avoid auth prompts, traps EXIT to always return to `main`
- **`write_entity_list.sh`** — uses `jq` to parse `.storage/core.entity_registry`; **do not use `python3`** — the SSH addon does not have it

---

## Deploy workflow details

`deploy.yml` detects whether a full restart or a hot reload is needed by checking if `configuration.yaml` changed in the commit. Restart path notifies Slack first, then restarts. Reload path reloads automations, scripts, scenes, themes, and core config, then notifies. Failure always notifies with a link to the commit and the Actions run.

---

## What to avoid

- Do not add `python3` calls to shell scripts — the SSH addon doesn't have it; use `jq`
- Do not edit `entity_list.txt` by hand
- Do not push directly to `main`
- Do not add `notify:` file platform entries — that platform was removed in HA 2024.12
- Do not add `python_script:` integration entries — sandboxed file I/O makes it unusable here
- After merging a PR, always `git fetch origin && git log origin/main` to confirm all commits landed
