# /populate-from-rad-react

Populate the current workspace (or a given folder) with the latest files from the **RAD-React** template repository — for a **new app repo**, not for committing back to `tad-agentics/RAD-React`.

## When to use

- You created an **empty** GitHub repo and cloned it locally (or ran `git init` in an empty folder).
- You want the RAD template files copied in **without** using `origin` → `RAD-React` for day-to-day work.

## Steps

1. Confirm the human’s **target directory** (usually workspace root). It should be **empty** except optionally `.git`, unless they explicitly want `--force`.
2. Run from the repository root:

```bash
./scripts/populate-from-rad-react.sh
```

Or with an explicit path:

```bash
./scripts/populate-from-rad-react.sh /path/to/new-app
```

If the directory has files other than `.git`, refuse unless they ask for `--force`:

```bash
./scripts/populate-from-rad-react.sh --force /path/to/app
```

3. After success, tell the human to:
   - Point `origin` at **their** GitHub app repo (`git remote add origin ...` if missing).
   - **Never** push this app to `tad-agentics/RAD-React`.
4. Continue with Phase 1 docs and `/init` per `README.md`.

## Script behavior

- Clones `https://github.com/tad-agentics/RAD-React.git` (override with `RAD_REACT_TEMPLATE_URL`).
- Optional branch: `RAD_REACT_TEMPLATE_BRANCH` if the default branch is not what you need.
- Copies with `rsync`, **excludes** `.git` from the template so the app’s existing `.git` is preserved.

## If the script is missing locally

The human can copy `scripts/populate-from-rad-react.sh` from the [RAD-React](https://github.com/tad-agentics/RAD-React) repo, or use **Use this template** / `gh repo create --template` instead.
