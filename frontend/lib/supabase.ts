/**
 * EduPath AI — Supabase Client
 * Team KRIYA | Meta Hackathon 2026
 *
 * Initialises the Supabase browser client with PKCE auth flow.
 * Uses placeholder values during static builds to prevent build-time crashes.
 */

import { createClient } from "@supabase/supabase-js";

// Provide fallback dummy values so Next.js static builds do not crash
// if these environment variables are not set in the build environment.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder-project.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true,
    flowType: "pkce",
  },
});
