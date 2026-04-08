# /regen-feature [name]

Regenerate one feature's context package in `build-plan.md` after a BLOCKING spec amendment.

Usage: `/regen-feature goal-creation`

## Pre-flight checks

- [ ] The BLOCKING amendment is logged in `artifacts/docs/changelog.md`
- [ ] The relevant spec files (`tech-spec.md` and/or `screen-specs-[app]-v1.md`) have been updated
- [ ] The feature `[name]` exists in `build-plan.md`

## Steps

1. Read `artifacts/plans/build-plan.md` — locate the `[name]` feature section
2. Read the updated spec files:
   - `artifacts/docs/tech-spec.md` — re-extract backend scope
   - `artifacts/docs/screen-specs-[app]-v1.md` — re-extract frontend scope (interaction flows, copy slots, dopamine flags, credit costs, Make component names)
   - `artifacts/docs/emotional-design-system.md` — §6 if any screen has a dopamine flag
3. Rewrite only the `[name]` feature section — do not touch other features
4. Note what changed

## After completion

```
build-plan.md updated for feature [name].
Changed: [what was different]
Ready to re-dispatch: /feature [name]
```

Commit: `chore([name]): regen feature context after amendment`
