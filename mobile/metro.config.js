const { getDefaultConfig } = require("expo/metro-config");
const { withNativeWind } = require("nativewind/metro");

const config = getDefaultConfig(__dirname);

// Expo SDK 55 auto-detects npm workspaces — no manual watchFolders or
// nodeModulesPaths needed. Metro resolves shared/ via workspace symlinks.

module.exports = withNativeWind(config, { input: "./global.css" });
