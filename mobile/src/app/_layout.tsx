// Template — populated during /foundation mobile setup.
// Replace all [PLACEHOLDER] values. Uncomment conditional providers as needed.

import "../global.css";
import { Stack } from "expo-router";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { KeyboardProvider } from "react-native-keyboard-controller";
import { PortalHost } from "@rn-primitives/portal";
import { SupabaseProvider } from "shared/api/supabase-context";
import { useAuthState } from "shared/hooks/useAuthState";

// Platform-specific Supabase client — uses expo-secure-store for token persistence
// import { createSupabaseClient } from "shared/api/supabase";
// import * as SecureStore from "expo-secure-store";
// const supabase = createSupabaseClient(
//   process.env.EXPO_PUBLIC_SUPABASE_URL!,
//   process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
//   { getItem: SecureStore.getItemAsync, setItem: SecureStore.setItemAsync, removeItem: SecureStore.deleteItemAsync }
// );

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000 } },
});

export default function RootLayout() {
  const { isLoggedIn } = useAuthState();
  return (
    <SafeAreaProvider>
      {/* <SupabaseProvider value={supabase}> */}
      <QueryClientProvider client={queryClient}>
        <KeyboardProvider>
          <Stack screenOptions={{ headerShown: false }}>
            <Stack.Protected guard={isLoggedIn}>
              <Stack.Screen name="(app)" />
              <Stack.Screen name="modal" options={{ presentation: "modal" }} />
            </Stack.Protected>
            <Stack.Protected guard={!isLoggedIn}>
              <Stack.Screen name="(auth)" />
            </Stack.Protected>
          </Stack>
          <PortalHost />
        </KeyboardProvider>
      </QueryClientProvider>
      {/* </SupabaseProvider> */}
    </SafeAreaProvider>
  );
}
