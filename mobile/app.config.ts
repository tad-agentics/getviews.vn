import type { ExpoConfig, ConfigContext } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "[App Name]",
  slug: "[app-slug]",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  scheme: "[app-slug]", // Deep linking URI scheme
  userInterfaceStyle: "automatic",
  newArchEnabled: true,

  experiments: {
    reactCompiler: true,
  },

  splash: {
    image: "./assets/splash-icon.png",
    imageWidth: 200,
    resizeMode: "contain",
    backgroundColor: "#ffffff",
  },

  ios: {
    supportsTablet: false,
    bundleIdentifier: "com.[org].[app-slug]",
    infoPlist: {
      // Add per northstar §7c device APIs:
      // NSCameraUsageDescription: "...",
      // NSBluetoothAlwaysUsageDescription: "...",
    },
  },

  android: {
    adaptiveIcon: {
      foregroundImage: "./assets/adaptive-icon.png",
      backgroundColor: "#ffffff",
    },
    package: "com.[org].[app_slug]",
  },

  plugins: [
    "expo-router",
    "expo-secure-store",
    "expo-font",
    // Conditional — per northstar §7c:
    // "expo-camera",
    // "expo-notifications",
    // ["expo-local-authentication", { faceIDPermission: "Allow $(PRODUCT_NAME) to use Face ID" }],
  ],

  updates: {
    url: "https://u.expo.dev/[PROJECT_ID]",
  },

  runtimeVersion: {
    policy: "appVersion",
  },

  extra: {
    eas: { projectId: "[EAS_PROJECT_ID]" },
    supabaseUrl: process.env.EXPO_PUBLIC_SUPABASE_URL,
    supabaseKey: process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
  },
});
