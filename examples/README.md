# Feeding the Familiar

Ready-to-copy integrations for the trio the README promises. All of them
end at the same place — one authenticated POST:

```sh
curl -X POST http://<board-ip>:8123/poke \
     -H "X-Familiar-Key: <contents of ~/.config/familiar/key>" \
     -d '{"kind":"ci_green"}'
```

Kinds → moods: `ci_green`/`deploy_ok`/`merge` → happy · `ci_red`/
`deploy_fail` → sad · `alert`/`incident` → alert · `mention`/`poke` →
curious · `hot` → sleepy. Unknown kinds are ignored.

| File | For | Notes |
|---|---|---|
| `github-action.yml` | GitHub Actions | Inline workflow step (composite actions can't read `secrets`/`job.status`, so copy the step into your job); `continue-on-error` because the webhook rate-limits at 12 req/min per source — a pet must never fail your CI. Needs repo secrets `FAMILIAR_URL` + `FAMILIAR_KEY`; engine running with `--lan`. |
| `home-assistant.yaml` | Home Assistant | `rest_command` + two example automations. Key goes in `secrets.yaml` (`familiar_key`). |

LAN mode: the webhook binds loopback by default; start the engine with
`--lan` (the installer's unit uses the default — add a systemd drop-in or
edit the ExecStart) before pointing anything at the board's IP. Note the
key then travels as a header over plain HTTP on your LAN — fine for most
home networks (it only grants mood-pokes, rate-limited); route through
Tailscale or an HTTPS reverse proxy if that bothers you.

Anything that can POST JSON can feed it — the two files above are just
the ones we get asked about.
