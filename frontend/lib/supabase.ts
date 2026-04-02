import { createClient } from "@supabase/supabase-js";

// Provide fallback dummy values so Next.js static builds do not crash
// if these environment variables are not set in the build environment.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder-project.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
