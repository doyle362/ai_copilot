# Continuous Integration

The GitHub Actions workflow defined in `.github/workflows/ci.yml` automates validation for Level Analyst.

## Jobs

| Job       | Purpose                                             |
|-----------|-----------------------------------------------------|
| backend   | Installs backend dependencies and runs `pytest`     |
| frontend  | Uses Node.js 18, runs `npm run lint` and `build:artifact`, uploads the dist bundle as an artifact |
| security  | Executes `pip-audit` against the Python project and runs `npm audit` (non-blocking) |

## Running Locally

Mirror the CI steps:

```
# Backend
cd services/analyst
python3 -m pip install -e '.[dev]'
python3 -m pytest ../../tests -v

# Frontend
cd ../web/card
npm install
npm run lint
npm run build:artifact
```

For dependency auditing, install the tools locally:

```
pip install pip-audit
pip-audit --requirement services/analyst/pyproject.toml
npm audit --omit=dev
```

## CI Tips

- Set required checks on `main/master` branches to include the new jobs.
- Uploading the `dist/` tarball allows downstream deployment workflows to download and publish the static site without rebuilding.
- Security job treats findings as warnings (`|| true`). Tighten to fail the build once the backlog of vulnerabilities is resolved.
