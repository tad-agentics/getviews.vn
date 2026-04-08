# /store-submit

EAS Build → EAS Submit for App Store and Google Play. Run after `/pre-handoff` passes.

## Pre-flight checks

- [ ] `/pre-handoff` QA passed (including mobile-specific: VoiceOver, TalkBack, deep links, push)
- [ ] `mobile/app.config.ts` has final `name`, `slug`, `version`, `bundleIdentifier`, `package`
- [ ] `mobile/eas.json` has production profile with store credentials
- [ ] Apple Developer account enrolled + app record created in App Store Connect
- [ ] Google Play Console account + app created + 14-day closed testing completed (12 testers minimum)
- [ ] App icons: `mobile/assets/icon.png` (1024×1024), `adaptive-icon.png`, `splash-icon.png`

If any check fails: report to human with specific gap.

## Step 1 — Version bump

```bash
cd mobile
# Verify version in app.config.ts — open the file and confirm name, slug, version, bundleIdentifier, package
cat app.config.ts | head -20
```

## Step 2 — Production build

```bash
eas build --platform all --profile production
```

Monitor build at https://expo.dev. Typical times: iOS ~15-20 min, Android ~10-15 min.

If build fails:
- iOS: check `bundleIdentifier` matches App Store Connect, signing certificates are valid
- Android: check `package` matches Play Console, `google-play-key.json` is valid

## Step 3 — Submit to stores

```bash
eas submit --platform all --profile production
```

This uploads the built binaries to both stores.

### Apple App Store

- First submission: budget **3-5 business days** for review
- Submit Monday–Tuesday for fastest turnaround
- Common rejection reasons: missing privacy policy URL, incomplete app metadata, crash on launch
- After approval: release manually or set auto-release

### Google Play Store

- First submission: **1-3 days** review
- Requires 14-day closed testing already completed
- Promote from internal → closed → production track
- Common rejection: missing data safety form, target API level too low

## Step 4 — OTA update setup

After initial store approval, JS-only changes deploy without store review:

```bash
cd mobile
eas update --branch production --message "fix: [description]"
```

Reaches users in ~15 minutes. No store review needed for:
- Bug fixes (JS/TS only)
- Copy changes
- Style changes
- New screens (if no new native modules)

**Cannot OTA:** New native modules, SDK upgrades, native config changes → requires new store build.

## Step 5 — Post-submission

1. Update `agent-workspace/ACTIVE_CONTEXT.md` — submitted, awaiting review
2. Set up monitoring: Sentry or expo-updates error tracking
3. Present to human:
```
Store submission complete.
  iOS: Submitted to App Store Connect — expect review in 3-5 business days
  Android: Submitted to Google Play — expect review in 1-3 days
  OTA updates: configured — JS changes deploy in ~15 min via eas update

Action required:
  - Monitor review status in App Store Connect / Play Console
  - Respond promptly to any reviewer questions
  - After approval: verify the app installs and launches from each store
```

## EAS pricing reminder

Starter plan ($19/mo): 30 iOS + 30 Android builds/month, priority queue. Sufficient for RAD cadence (1-2 apps/month, ~5-10 builds each including dev/preview/production).
