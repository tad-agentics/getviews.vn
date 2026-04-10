export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      anonymous_usage: {
        Row: {
          created_at: string
          has_used_free_soikenh: boolean
          id: string
          ip_hash: string
        }
        Insert: {
          created_at?: string
          has_used_free_soikenh?: boolean
          id?: string
          ip_hash: string
        }
        Update: {
          created_at?: string
          has_used_free_soikenh?: boolean
          id?: string
          ip_hash?: string
        }
        Relationships: []
      }
      batch_failures: {
        Row: {
          created_at: string
          error_type: string
          excluded_permanently: boolean
          failure_count: number
          id: string
          last_failed_at: string | null
          video_id: string
        }
        Insert: {
          created_at?: string
          error_type: string
          excluded_permanently?: boolean
          failure_count?: number
          id?: string
          last_failed_at?: string | null
          video_id: string
        }
        Update: {
          created_at?: string
          error_type?: string
          excluded_permanently?: boolean
          failure_count?: number
          id?: string
          last_failed_at?: string | null
          video_id?: string
        }
        Relationships: []
      }
      chat_messages: {
        Row: {
          content: string | null
          created_at: string
          credits_used: number
          id: string
          intent_type: string | null
          is_free: boolean
          role: string
          session_id: string
          stream_id: string | null
          structured_output: Json | null
          user_id: string
        }
        Insert: {
          content?: string | null
          created_at?: string
          credits_used?: number
          id?: string
          intent_type?: string | null
          is_free?: boolean
          role: string
          session_id: string
          stream_id?: string | null
          structured_output?: Json | null
          user_id: string
        }
        Update: {
          content?: string | null
          created_at?: string
          credits_used?: number
          id?: string
          intent_type?: string | null
          is_free?: boolean
          role?: string
          session_id?: string
          stream_id?: string | null
          structured_output?: Json | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "chat_messages_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "chat_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      chat_sessions: {
        Row: {
          created_at: string
          credits_used: number
          deleted_at: string | null
          first_message: string
          id: string
          intent_type: string | null
          is_pinned: boolean
          title: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          credits_used?: number
          deleted_at?: string | null
          first_message: string
          id?: string
          intent_type?: string | null
          is_pinned?: boolean
          title?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          credits_used?: number
          deleted_at?: string | null
          first_message?: string
          id?: string
          intent_type?: string | null
          is_pinned?: boolean
          title?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      creator_velocity: {
        Row: {
          computed_at: string | null
          creator_handle: string
          dominant_format: string | null
          dominant_hook_type: string | null
          engagement_trend: string | null
          follower_trajectory: Json | null
          id: string
          niche_id: number
          posting_frequency_per_week: number | null
          velocity_score: number | null
        }
        Insert: {
          computed_at?: string | null
          creator_handle: string
          dominant_format?: string | null
          dominant_hook_type?: string | null
          engagement_trend?: string | null
          follower_trajectory?: Json | null
          id?: string
          niche_id: number
          posting_frequency_per_week?: number | null
          velocity_score?: number | null
        }
        Update: {
          computed_at?: string | null
          creator_handle?: string
          dominant_format?: string | null
          dominant_hook_type?: string | null
          engagement_trend?: string | null
          follower_trajectory?: Json | null
          id?: string
          niche_id?: number
          posting_frequency_per_week?: number | null
          velocity_score?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "creator_velocity_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_intelligence"
            referencedColumns: ["niche_id"]
          },
          {
            foreignKeyName: "creator_velocity_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      credit_transactions: {
        Row: {
          balance_after: number
          created_at: string
          delta: number
          id: string
          reason: string
          session_id: string | null
          subscription_id: string | null
          user_id: string
        }
        Insert: {
          balance_after: number
          created_at?: string
          delta: number
          id?: string
          reason: string
          session_id?: string | null
          subscription_id?: string | null
          user_id: string
        }
        Update: {
          balance_after?: number
          created_at?: string
          delta?: number
          id?: string
          reason?: string
          session_id?: string | null
          subscription_id?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "credit_transactions_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "chat_sessions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "credit_transactions_subscription_id_fkey"
            columns: ["subscription_id"]
            isOneToOne: false
            referencedRelation: "subscriptions"
            referencedColumns: ["id"]
          },
        ]
      }
      format_lifecycle: {
        Row: {
          computed_at: string | null
          engagement_trend: number | null
          format_type: string
          id: string
          lifecycle_stage: string | null
          niche_id: number
          volume_trend: number | null
          weeks_in_stage: number | null
        }
        Insert: {
          computed_at?: string | null
          engagement_trend?: number | null
          format_type: string
          id?: string
          lifecycle_stage?: string | null
          niche_id: number
          volume_trend?: number | null
          weeks_in_stage?: number | null
        }
        Update: {
          computed_at?: string | null
          engagement_trend?: number | null
          format_type?: string
          id?: string
          lifecycle_stage?: string | null
          niche_id?: number
          volume_trend?: number | null
          weeks_in_stage?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "format_lifecycle_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_intelligence"
            referencedColumns: ["niche_id"]
          },
          {
            foreignKeyName: "format_lifecycle_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      hook_effectiveness: {
        Row: {
          avg_completion_rate: number | null
          avg_engagement_rate: number | null
          avg_views: number | null
          computed_at: string | null
          hook_type: string
          id: string
          niche_id: number
          sample_size: number | null
          trend_direction: string | null
        }
        Insert: {
          avg_completion_rate?: number | null
          avg_engagement_rate?: number | null
          avg_views?: number | null
          computed_at?: string | null
          hook_type: string
          id?: string
          niche_id: number
          sample_size?: number | null
          trend_direction?: string | null
        }
        Update: {
          avg_completion_rate?: number | null
          avg_engagement_rate?: number | null
          avg_views?: number | null
          computed_at?: string | null
          hook_type?: string
          id?: string
          niche_id?: number
          sample_size?: number | null
          trend_direction?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "hook_effectiveness_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_intelligence"
            referencedColumns: ["niche_id"]
          },
          {
            foreignKeyName: "hook_effectiveness_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      llm_cache: {
        Row: {
          created_at: string
          input_hash: string
          response: Json
        }
        Insert: {
          created_at?: string
          input_hash: string
          response: Json
        }
        Update: {
          created_at?: string
          input_hash?: string
          response?: Json
        }
        Relationships: []
      }
      niche_taxonomy: {
        Row: {
          created_at: string
          id: number
          name_en: string
          name_vn: string
          signal_hashtags: string[]
        }
        Insert: {
          created_at?: string
          id?: number
          name_en: string
          name_vn: string
          signal_hashtags?: string[]
        }
        Update: {
          created_at?: string
          id?: number
          name_en?: string
          name_vn?: string
          signal_hashtags?: string[]
        }
        Relationships: []
      }
      processed_webhook_events: {
        Row: {
          created_at: string
          event_type: string
          id: string
          payos_order_code: string
        }
        Insert: {
          created_at?: string
          event_type: string
          id?: string
          payos_order_code: string
        }
        Update: {
          created_at?: string
          event_type?: string
          id?: string
          payos_order_code?: string
        }
        Relationships: []
      }
      profiles: {
        Row: {
          avatar_url: string | null
          created_at: string
          credits_reset_at: string | null
          daily_free_query_count: number
          daily_free_query_reset_at: string | null
          deep_credits_remaining: number
          display_name: string
          email: string
          id: string
          is_processing: boolean
          lifetime_credits_used: number
          niche_id: number | null
          primary_niche: string | null
          subscription_tier: string
          tiktok_handle: string | null
          updated_at: string
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string
          credits_reset_at?: string | null
          daily_free_query_count?: number
          daily_free_query_reset_at?: string | null
          deep_credits_remaining?: number
          display_name?: string
          email: string
          id: string
          is_processing?: boolean
          lifetime_credits_used?: number
          niche_id?: number | null
          primary_niche?: string | null
          subscription_tier?: string
          tiktok_handle?: string | null
          updated_at?: string
        }
        Update: {
          avatar_url?: string | null
          created_at?: string
          credits_reset_at?: string | null
          daily_free_query_count?: number
          daily_free_query_reset_at?: string | null
          deep_credits_remaining?: number
          display_name?: string
          email?: string
          id?: string
          is_processing?: boolean
          lifetime_credits_used?: number
          niche_id?: number | null
          primary_niche?: string | null
          subscription_tier?: string
          tiktok_handle?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "profiles_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_intelligence"
            referencedColumns: ["niche_id"]
          },
          {
            foreignKeyName: "profiles_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      subscriptions: {
        Row: {
          amount_vnd: number
          billing_period: string
          created_at: string
          deep_credits_granted: number
          expires_at: string
          id: string
          payos_order_code: string
          payos_payment_id: string | null
          reminder_1d_sent_at: string | null
          reminder_3d_sent_at: string | null
          reminder_7d_sent_at: string | null
          starts_at: string
          status: string
          tier: string
          user_id: string
        }
        Insert: {
          amount_vnd: number
          billing_period: string
          created_at?: string
          deep_credits_granted: number
          expires_at: string
          id?: string
          payos_order_code: string
          payos_payment_id?: string | null
          reminder_1d_sent_at?: string | null
          reminder_3d_sent_at?: string | null
          reminder_7d_sent_at?: string | null
          starts_at: string
          status?: string
          tier: string
          user_id: string
        }
        Update: {
          amount_vnd?: number
          billing_period?: string
          created_at?: string
          deep_credits_granted?: number
          expires_at?: string
          id?: string
          payos_order_code?: string
          payos_payment_id?: string | null
          reminder_1d_sent_at?: string | null
          reminder_3d_sent_at?: string | null
          reminder_7d_sent_at?: string | null
          starts_at?: string
          status?: string
          tier?: string
          user_id?: string
        }
        Relationships: []
      }
      trend_velocity: {
        Row: {
          created_at: string
          engagement_changes: Json | null
          format_changes: Json | null
          hook_type_shifts: Json | null
          id: string
          new_hashtags: string[] | null
          niche_id: number
          sound_trends: Json | null
          week_start: string
        }
        Insert: {
          created_at?: string
          engagement_changes?: Json | null
          format_changes?: Json | null
          hook_type_shifts?: Json | null
          id?: string
          new_hashtags?: string[] | null
          niche_id: number
          sound_trends?: Json | null
          week_start: string
        }
        Update: {
          created_at?: string
          engagement_changes?: Json | null
          format_changes?: Json | null
          hook_type_shifts?: Json | null
          id?: string
          new_hashtags?: string[] | null
          niche_id?: number
          sound_trends?: Json | null
          week_start?: string
        }
        Relationships: [
          {
            foreignKeyName: "trend_velocity_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_intelligence"
            referencedColumns: ["niche_id"]
          },
          {
            foreignKeyName: "trend_velocity_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      video_corpus: {
        Row: {
          analysis_json: Json
          comments: number
          content_type: string
          created_at: string
          creator_handle: string
          engagement_rate: number
          frame_urls: string[]
          id: string
          indexed_at: string
          likes: number
          niche_id: number
          shares: number
          thumbnail_url: string | null
          tiktok_url: string
          video_id: string
          video_url: string | null
          views: number
        }
        Insert: {
          analysis_json: Json
          comments?: number
          content_type: string
          created_at?: string
          creator_handle: string
          engagement_rate?: number
          frame_urls?: string[]
          id?: string
          indexed_at?: string
          likes?: number
          niche_id: number
          shares?: number
          thumbnail_url?: string | null
          tiktok_url: string
          video_id: string
          video_url?: string | null
          views?: number
        }
        Update: {
          analysis_json?: Json
          comments?: number
          content_type?: string
          created_at?: string
          creator_handle?: string
          engagement_rate?: number
          frame_urls?: string[]
          id?: string
          indexed_at?: string
          likes?: number
          niche_id?: number
          shares?: number
          thumbnail_url?: string | null
          tiktok_url?: string
          video_id?: string
          video_url?: string | null
          views?: number
        }
        Relationships: [
          {
            foreignKeyName: "video_corpus_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_intelligence"
            referencedColumns: ["niche_id"]
          },
          {
            foreignKeyName: "video_corpus_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      niche_intelligence: {
        Row: {
          avg_face_appears_at: number | null
          avg_transitions_per_second: number | null
          avg_video_length_seconds: number | null
          computed_at: string | null
          hook_type_distribution: Json | null
          median_engagement_rate: number | null
          niche_id: number | null
          sample_size: number | null
          trending_keywords: Json | null
          video_count_7d: number | null
        }
        Relationships: []
      }
    }
    Functions: {
      decrement_and_grant_credits: {
        Args: {
          p_event_type: string
          p_payos_order_code: string
          p_payos_payment_id: string
        }
        Returns: Json
      }
      decrement_credit: { Args: { p_user_id: string }; Returns: number }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
