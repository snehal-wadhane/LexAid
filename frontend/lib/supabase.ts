import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
// Supabase renamed "anon key" to "publishable key" in newer dashboard versions
const supabaseKey =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseKey);

export type Conversation = {
  id: string;
  title: string;
  created_at: string;
};

export type DBMessage = {
  role: "user" | "assistant";
  content: string;
  sources: string[];
};
