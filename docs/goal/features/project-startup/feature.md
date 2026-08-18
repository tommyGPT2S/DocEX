# Feature: Project Startup

Status: `not-started`

## Summary

- Document the first commands an agent or developer should use to install, run, and verify `DocEX`.
- Keep startup assumptions visible so future feature work begins from the same project context.

## User Goal

- A new chat or developer can start work in `DocEX` without rediscovering the basic local commands.

## Feature Implementation Goal

- Maintain a current startup path for `DocEX` based on the repo manifests, README, and code layout before changing feature behavior.

## Required Inputs And Configuration

- Project root: `DocEX`.
- Install/runtime dependencies declared in repo manifests and README files.

## Startup Commands

- `pip install -e ".[dev]"`
- `docker compose up`

## Verification

- [ ] `pytest`

## Notes

- Console entry point(s): `DocEX`.

## Anchors

- README: `README.md`
- Python manifest: `pyproject.toml`
- Node manifest: `package.json`
- Docker compose: `docker-compose.yml`
- Make targets: `Makefile`
- Docs: `docs/goal/features/project-startup/feature.md`
