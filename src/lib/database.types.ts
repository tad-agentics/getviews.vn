export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export type Database = {
  __InternalSupabase: {
    PostgrestVersion: "14.5";
  };
  public: {
    Tables: {
      anonymous_usage: {
        Row: {
          created_at: string;
          has_used_free_soikenh: boolean;
          id: string;
          ip_hash: string;
        };
        Insert: {
          created_at?: string;
          has_used_free_soikenh?: boolean;
          id?: string;
          ip_hash: string;
        };
        Update: {
          created_at?: string;
          has_used_free_soikenh?: boolean;
          id?: string;
          ip_hash?: string;
        };
        Relationships: [];
      };
      profiles: {
        Row: {
          id: string;
          email: string;
          display_name: string;
          subscription_tier: string;
          deep_credits_remaining: number;
          [key: string]: unknown;
        };
        Insert: Record<string, unknown>;
        Update: Record<string, unknown>;
        Relationships: [];
      };
      [key: string]: {
        Row: Record<string, unknown>;
        Insert: Record<string, unknown>;
        Update: Record<string, unknown>;
        Relationships: unknown[];
      };
    };
    Views: {
      niche_intelligence: {
        Row: Record<string, unknown>;
        Relationships: [];
      };
    };
    Functions: {
      decrement_credit: { Args: { p_user_id: string }; Returns: number };
      decrement_and_grant_credits: {
        Args: {
          p_payos_order_code: string;
          p_payos_payment_id: string;
          p_event_type: string;
        };
        Returns: Json;
      };
    };
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
};
