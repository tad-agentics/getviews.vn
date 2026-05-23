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
  graphql_public: {
    Tables: {
      [_ in never]: never
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      graphql: {
        Args: {
          extensions?: Json
          operationName?: string
          query?: string
          variables?: Json
        }
        Returns: Json
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      acqe_run_state: {
        Row: {
          cold_start_complete: boolean
          discovery_relax_active: boolean
          id: number
          last_run_at: string | null
          run_count: number
        }
        Insert: {
          cold_start_complete?: boolean
          discovery_relax_active?: boolean
          id: number
          last_run_at?: string | null
          run_count?: number
        }
        Update: {
          cold_start_complete?: boolean
          discovery_relax_active?: boolean
          id?: number
          last_run_at?: string | null
          run_count?: number
        }
        Relationships: []
      }
      admin_action_log: {
        Row: {
          action: string
          created_at: string
          duration_ms: number | null
          error_message: string | null
          id: string
          params_json: Json
          result_json: Json | null
          result_status: string
          user_id: string | null
        }
        Insert: {
          action: string
          created_at?: string
          duration_ms?: number | null
          error_message?: string | null
          id?: string
          params_json?: Json
          result_json?: Json | null
          result_status: string
          user_id?: string | null
        }
        Update: {
          action?: string
          created_at?: string
          duration_ms?: number | null
          error_message?: string | null
          id?: string
          params_json?: Json
          result_json?: Json | null
          result_status?: string
          user_id?: string | null
        }
        Relationships: []
      }
      admin_alert_fires: {
        Row: {
          context_json: Json
          created_at: string
          delivered_at: string | null
          id: string
          message: string
          phase: string
          rule_key: string
          severity: string
        }
        Insert: {
          context_json?: Json
          created_at?: string
          delivered_at?: string | null
          id?: string
          message: string
          phase?: string
          rule_key: string
          severity: string
        }
        Update: {
          context_json?: Json
          created_at?: string
          delivered_at?: string | null
          id?: string
          message?: string
          phase?: string
          rule_key?: string
          severity?: string
        }
        Relationships: [
          {
            foreignKeyName: "admin_alert_fires_rule_key_fkey"
            columns: ["rule_key"]
            isOneToOne: false
            referencedRelation: "admin_alert_rules"
            referencedColumns: ["rule_key"]
          },
        ]
      }
      admin_alert_rules: {
        Row: {
          created_at: string
          enabled: boolean
          id: string
          label: string
          rule_key: string
          severity: string
          threshold_json: Json
          updated_at: string
        }
        Insert: {
          created_at?: string
          enabled?: boolean
          id?: string
          label: string
          rule_key: string
          severity?: string
          threshold_json?: Json
          updated_at?: string
        }
        Update: {
          created_at?: string
          enabled?: boolean
          id?: string
          label?: string
          rule_key?: string
          severity?: string
          threshold_json?: Json
          updated_at?: string
        }
        Relationships: []
      }
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
      answer_session_idempotency: {
        Row: {
          created_at: string
          idempotency_key: string
          session_id: string
          user_id: string
        }
        Insert: {
          created_at?: string
          idempotency_key: string
          session_id: string
          user_id: string
        }
        Update: {
          created_at?: string
          idempotency_key?: string
          session_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "answer_session_idempotency_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "answer_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      answer_sessions: {
        Row: {
          archived_at: string | null
          created_at: string
          format: string
          id: string
          initial_q: string
          intent_type: string
          niche_id: number | null
          title: string
          turn_context: Json | null
          updated_at: string
          user_id: string
        }
        Insert: {
          archived_at?: string | null
          created_at?: string
          format: string
          id?: string
          initial_q: string
          intent_type: string
          niche_id?: number | null
          title: string
          turn_context?: Json | null
          updated_at?: string
          user_id: string
        }
        Update: {
          archived_at?: string | null
          created_at?: string
          format?: string
          id?: string
          initial_q?: string
          intent_type?: string
          niche_id?: number | null
          title?: string
          turn_context?: Json | null
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "answer_sessions_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      answer_turns: {
        Row: {
          classifier_confidence: string
          cloud_run_run_id: string | null
          created_at: string
          credits_used: number
          id: string
          intent_confidence: string
          kind: string
          payload: Json
          query: string
          session_id: string
          turn_index: number
        }
        Insert: {
          classifier_confidence: string
          cloud_run_run_id?: string | null
          created_at?: string
          credits_used?: number
          id?: string
          intent_confidence: string
          kind: string
          payload?: Json
          query: string
          session_id: string
          turn_index: number
        }
        Update: {
          classifier_confidence?: string
          cloud_run_run_id?: string | null
          created_at?: string
          credits_used?: number
          id?: string
          intent_confidence?: string
          kind?: string
          payload?: Json
          query?: string
          session_id?: string
          turn_index?: number
        }
        Relationships: [
          {
            foreignKeyName: "answer_turns_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "answer_sessions"
            referencedColumns: ["id"]
          },
        ]
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
      batch_http_log: {
        Row: {
          enqueued_at: string
          request_id: number
          url: string
        }
        Insert: {
          enqueued_at?: string
          request_id: number
          url: string
        }
        Update: {
          enqueued_at?: string
          request_id?: number
          url?: string
        }
        Relationships: []
      }
      batch_job_runs: {
        Row: {
          duration_ms: number | null
          error: string | null
          finished_at: string | null
          id: string
          job_name: string
          started_at: string
          status: string
          summary: Json | null
        }
        Insert: {
          duration_ms?: number | null
          error?: string | null
          finished_at?: string | null
          id?: string
          job_name: string
          started_at?: string
          status?: string
          summary?: Json | null
        }
        Update: {
          duration_ms?: number | null
          error?: string | null
          finished_at?: string | null
          id?: string
          job_name?: string
          started_at?: string
          status?: string
          summary?: Json | null
        }
        Relationships: []
      }
      channel_diagnoses: {
        Row: {
          channel_pattern: Json
          channel_persona: Json
          computed_at: string
          creator_match: Json | null
          handle: string
          hashtag_insights: Json
          inflection: Json | null
          next_video: Json | null
          niche_id: number
          peer_source: string | null
          recommendations: Json
          score_card: Json
          sections: Json
          top_performers: Json
          trajectory_shape: string
          ugc_creators: Json
          verdict_tiles: Json
          video_count: number
          video_url: string
          worst_performers: Json
        }
        Insert: {
          channel_pattern?: Json
          channel_persona?: Json
          computed_at?: string
          creator_match?: Json | null
          handle: string
          hashtag_insights?: Json
          inflection?: Json | null
          next_video?: Json | null
          niche_id: number
          peer_source?: string | null
          recommendations?: Json
          score_card?: Json
          sections?: Json
          top_performers?: Json
          trajectory_shape: string
          ugc_creators?: Json
          verdict_tiles?: Json
          video_count?: number
          video_url?: string
          worst_performers?: Json
        }
        Update: {
          channel_pattern?: Json
          channel_persona?: Json
          computed_at?: string
          creator_match?: Json | null
          handle?: string
          hashtag_insights?: Json
          inflection?: Json | null
          next_video?: Json | null
          niche_id?: number
          peer_source?: string | null
          recommendations?: Json
          score_card?: Json
          sections?: Json
          top_performers?: Json
          trajectory_shape?: string
          ugc_creators?: Json
          verdict_tiles?: Json
          video_count?: number
          video_url?: string
          worst_performers?: Json
        }
        Relationships: []
      }
      chat_archival_audit: {
        Row: {
          archived_at: string
          id: string
          message_count: number
          session_created_at: string | null
          session_id: string
          session_updated_at: string | null
          user_id: string | null
        }
        Insert: {
          archived_at?: string
          id?: string
          message_count: number
          session_created_at?: string | null
          session_id: string
          session_updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          archived_at?: string
          id?: string
          message_count?: number
          session_created_at?: string | null
          session_id?: string
          session_updated_at?: string | null
          user_id?: string | null
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
          first_message: string
          id: string
          intent_type: string | null
          is_pinned: boolean
          niche_id: number | null
          title: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          credits_used?: number
          first_message: string
          id?: string
          intent_type?: string | null
          is_pinned?: boolean
          niche_id?: number | null
          title?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          credits_used?: number
          first_message?: string
          id?: string
          intent_type?: string | null
          is_pinned?: boolean
          niche_id?: number | null
          title?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "chat_sessions_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      competitor_tracking: {
        Row: {
          added_at: string
          competitor_handle: string
          id: string
          last_checked_at: string | null
          last_format: string | null
          last_hook_type: string | null
          niche_id: number
          user_id: string
        }
        Insert: {
          added_at?: string
          competitor_handle: string
          id?: string
          last_checked_at?: string | null
          last_format?: string | null
          last_hook_type?: string | null
          niche_id: number
          user_id: string
        }
        Update: {
          added_at?: string
          competitor_handle?: string
          id?: string
          last_checked_at?: string | null
          last_format?: string | null
          last_hook_type?: string | null
          niche_id?: number
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "competitor_tracking_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "competitor_tracking_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      content_class_hook_effectiveness: {
        Row: {
          avg_completion_rate: number | null
          avg_engagement_rate: number | null
          avg_views: number | null
          computed_at: string | null
          content_class_id: number
          hook_type: string
          id: string
          sample_size: number | null
          trend_direction: string | null
        }
        Insert: {
          avg_completion_rate?: number | null
          avg_engagement_rate?: number | null
          avg_views?: number | null
          computed_at?: string | null
          content_class_id: number
          hook_type: string
          id?: string
          sample_size?: number | null
          trend_direction?: string | null
        }
        Update: {
          avg_completion_rate?: number | null
          avg_engagement_rate?: number | null
          avg_views?: number | null
          computed_at?: string | null
          content_class_id?: number
          hook_type?: string
          id?: string
          sample_size?: number | null
          trend_direction?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "content_class_hook_effectiveness_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
        ]
      }
      content_class_ingest_targets: {
        Row: {
          active: boolean
          content_class_id: number
          daily_vpn: number
          priority: number
          signal_hashtags: string[]
          updated_at: string
          viability_tier: string | null
        }
        Insert: {
          active?: boolean
          content_class_id: number
          daily_vpn?: number
          priority?: number
          signal_hashtags?: string[]
          updated_at?: string
          viability_tier?: string | null
        }
        Update: {
          active?: boolean
          content_class_id?: number
          daily_vpn?: number
          priority?: number
          signal_hashtags?: string[]
          updated_at?: string
          viability_tier?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "content_class_ingest_targets_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: true
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
        ]
      }
      content_class_trend_velocity: {
        Row: {
          computed_at: string
          content_class_id: number
          hook_type_shifts: Json | null
          new_hashtags: string[] | null
          week_start: string
        }
        Insert: {
          computed_at?: string
          content_class_id: number
          hook_type_shifts?: Json | null
          new_hashtags?: string[] | null
          week_start: string
        }
        Update: {
          computed_at?: string
          content_class_id?: number
          hook_type_shifts?: Json | null
          new_hashtags?: string[] | null
          week_start?: string
        }
        Relationships: [
          {
            foreignKeyName: "content_class_trend_velocity_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
        ]
      }
      content_classifications: {
        Row: {
          active: boolean
          created_at: string
          description_vn: string | null
          format_axis: string
          id: number
          name_en: string
          name_vn: string
          slug: string
          topic_axis: string
        }
        Insert: {
          active?: boolean
          created_at?: string
          description_vn?: string | null
          format_axis: string
          id?: number
          name_en: string
          name_vn: string
          slug: string
          topic_axis: string
        }
        Update: {
          active?: boolean
          created_at?: string
          description_vn?: string | null
          format_axis?: string
          id?: number
          name_en?: string
          name_vn?: string
          slug?: string
          topic_axis?: string
        }
        Relationships: []
      }
      creator_niche_content_classes: {
        Row: {
          content_class_id: number
          creator_niche_id: number
          is_primary: boolean
        }
        Insert: {
          content_class_id: number
          creator_niche_id: number
          is_primary?: boolean
        }
        Update: {
          content_class_id?: number
          creator_niche_id?: number
          is_primary?: boolean
        }
        Relationships: [
          {
            foreignKeyName: "creator_niche_content_classes_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "creator_niche_content_classes_creator_niche_id_fkey"
            columns: ["creator_niche_id"]
            isOneToOne: false
            referencedRelation: "creator_niches"
            referencedColumns: ["id"]
          },
        ]
      }
      creator_niches: {
        Row: {
          active: boolean
          created_at: string
          description_vn: string | null
          display_order: number
          id: number
          name_en: string
          name_vn: string
          slug: string
        }
        Insert: {
          active?: boolean
          created_at?: string
          description_vn?: string | null
          display_order?: number
          id?: number
          name_en: string
          name_vn: string
          slug: string
        }
        Update: {
          active?: boolean
          created_at?: string
          description_vn?: string | null
          display_order?: number
          id?: number
          name_en?: string
          name_vn?: string
          slug?: string
        }
        Relationships: []
      }
      creator_pattern: {
        Row: {
          avg_posting_hour: number | null
          avg_save_rate: number | null
          avg_views: number | null
          computed_at: string
          dominant_format: string | null
          dominant_hook_type: string | null
          format_distribution: Json | null
          hook_type_distribution: Json | null
          id: string
          niche_id: number
          recent_video_count: number | null
          repeating_pattern: string | null
          save_rate_vs_niche: number | null
          tiktok_handle: string
          untried_formats: Json | null
          user_id: string
          views_trend: string | null
          views_trend_data: Json | null
        }
        Insert: {
          avg_posting_hour?: number | null
          avg_save_rate?: number | null
          avg_views?: number | null
          computed_at?: string
          dominant_format?: string | null
          dominant_hook_type?: string | null
          format_distribution?: Json | null
          hook_type_distribution?: Json | null
          id?: string
          niche_id: number
          recent_video_count?: number | null
          repeating_pattern?: string | null
          save_rate_vs_niche?: number | null
          tiktok_handle: string
          untried_formats?: Json | null
          user_id: string
          views_trend?: string | null
          views_trend_data?: Json | null
        }
        Update: {
          avg_posting_hour?: number | null
          avg_save_rate?: number | null
          avg_views?: number | null
          computed_at?: string
          dominant_format?: string | null
          dominant_hook_type?: string | null
          format_distribution?: Json | null
          hook_type_distribution?: Json | null
          id?: string
          niche_id?: number
          recent_video_count?: number | null
          repeating_pattern?: string | null
          save_rate_vs_niche?: number | null
          tiktok_handle?: string
          untried_formats?: Json | null
          user_id?: string
          views_trend?: string | null
          views_trend_data?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "creator_pattern_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "creator_pattern_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      creator_velocity: {
        Row: {
          avg_views: number | null
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
          video_count: number | null
          view_velocity_30d_pct: number | null
          view_velocity_computed_at: string | null
        }
        Insert: {
          avg_views?: number | null
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
          video_count?: number | null
          view_velocity_30d_pct?: number | null
          view_velocity_computed_at?: string | null
        }
        Update: {
          avg_views?: number | null
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
          video_count?: number | null
          view_velocity_30d_pct?: number | null
          view_velocity_computed_at?: string | null
        }
        Relationships: [
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
      cross_creator_patterns: {
        Row: {
          computed_at: string
          creator_count: number
          creators: string[]
          hook_type: string
          id: string
          niche_id: number
          total_views: number
          week_of: string
        }
        Insert: {
          computed_at?: string
          creator_count: number
          creators?: string[]
          hook_type: string
          id?: string
          niche_id: number
          total_views: number
          week_of: string
        }
        Update: {
          computed_at?: string
          creator_count?: number
          creators?: string[]
          hook_type?: string
          id?: string
          niche_id?: number
          total_views?: number
          week_of?: string
        }
        Relationships: [
          {
            foreignKeyName: "cross_creator_patterns_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      daily_ritual: {
        Row: {
          adequacy: string
          generated_at: string
          generated_for_date: string
          grounded_video_ids: string[]
          niche_id: number
          scripts: Json
          user_id: string
        }
        Insert: {
          adequacy?: string
          generated_at?: string
          generated_for_date: string
          grounded_video_ids?: string[]
          niche_id: number
          scripts: Json
          user_id: string
        }
        Update: {
          adequacy?: string
          generated_at?: string
          generated_for_date?: string
          grounded_video_ids?: string[]
          niche_id?: number
          scripts?: Json
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "daily_ritual_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      douyin_niche_taxonomy: {
        Row: {
          active: boolean
          created_at: string
          id: number
          name_en: string
          name_vn: string
          name_zh: string
          signal_hashtags_zh: string[]
          slug: string
        }
        Insert: {
          active?: boolean
          created_at?: string
          id?: number
          name_en: string
          name_vn: string
          name_zh: string
          signal_hashtags_zh?: string[]
          slug: string
        }
        Update: {
          active?: boolean
          created_at?: string
          id?: number
          name_en?: string
          name_vn?: string
          name_zh?: string
          signal_hashtags_zh?: string[]
          slug?: string
        }
        Relationships: []
      }
      douyin_patterns: {
        Row: {
          cn_rise_pct_avg: number | null
          computed_at: string
          created_at: string
          format_signal_vi: string
          hook_template_vi: string
          id: string
          name_vn: string
          name_zh: string | null
          niche_id: number
          rank: number
          sample_video_ids: string[]
          week_of: string
        }
        Insert: {
          cn_rise_pct_avg?: number | null
          computed_at?: string
          created_at?: string
          format_signal_vi: string
          hook_template_vi: string
          id?: string
          name_vn: string
          name_zh?: string | null
          niche_id: number
          rank: number
          sample_video_ids: string[]
          week_of: string
        }
        Update: {
          cn_rise_pct_avg?: number | null
          computed_at?: string
          created_at?: string
          format_signal_vi?: string
          hook_template_vi?: string
          id?: string
          name_vn?: string
          name_zh?: string | null
          niche_id?: number
          rank?: number
          sample_video_ids?: string[]
          week_of?: string
        }
        Relationships: [
          {
            foreignKeyName: "douyin_patterns_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "douyin_niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      douyin_video_corpus: {
        Row: {
          adapt_level: string | null
          adapt_reason: string | null
          analysis_json: Json
          cn_rise_pct: number | null
          comments: number
          content_format: string | null
          content_type: string
          created_at: string
          creator_followers: number | null
          creator_handle: string
          creator_name: string | null
          cta_type: string | null
          douyin_url: string
          engagement_rate: number
          eta_weeks_max: number | null
          eta_weeks_min: number | null
          frame_urls: string[]
          hashtags_zh: string[] | null
          hook_phrase: string | null
          hook_type: string | null
          id: string
          indexed_at: string
          likes: number
          niche_id: number
          posted_at: string | null
          saves: number
          shares: number
          sub_vi: string | null
          synth_computed_at: string | null
          thumbnail_url: string | null
          title_vi: string | null
          title_zh: string | null
          translator_notes: Json | null
          video_duration: number | null
          video_id: string
          video_url: string | null
          views: number
        }
        Insert: {
          adapt_level?: string | null
          adapt_reason?: string | null
          analysis_json: Json
          cn_rise_pct?: number | null
          comments?: number
          content_format?: string | null
          content_type: string
          created_at?: string
          creator_followers?: number | null
          creator_handle: string
          creator_name?: string | null
          cta_type?: string | null
          douyin_url: string
          engagement_rate?: number
          eta_weeks_max?: number | null
          eta_weeks_min?: number | null
          frame_urls?: string[]
          hashtags_zh?: string[] | null
          hook_phrase?: string | null
          hook_type?: string | null
          id?: string
          indexed_at?: string
          likes?: number
          niche_id: number
          posted_at?: string | null
          saves?: number
          shares?: number
          sub_vi?: string | null
          synth_computed_at?: string | null
          thumbnail_url?: string | null
          title_vi?: string | null
          title_zh?: string | null
          translator_notes?: Json | null
          video_duration?: number | null
          video_id: string
          video_url?: string | null
          views?: number
        }
        Update: {
          adapt_level?: string | null
          adapt_reason?: string | null
          analysis_json?: Json
          cn_rise_pct?: number | null
          comments?: number
          content_format?: string | null
          content_type?: string
          created_at?: string
          creator_followers?: number | null
          creator_handle?: string
          creator_name?: string | null
          cta_type?: string | null
          douyin_url?: string
          engagement_rate?: number
          eta_weeks_max?: number | null
          eta_weeks_min?: number | null
          frame_urls?: string[]
          hashtags_zh?: string[] | null
          hook_phrase?: string | null
          hook_type?: string | null
          id?: string
          indexed_at?: string
          likes?: number
          niche_id?: number
          posted_at?: string | null
          saves?: number
          shares?: number
          sub_vi?: string | null
          synth_computed_at?: string | null
          thumbnail_url?: string | null
          title_vi?: string | null
          title_zh?: string | null
          translator_notes?: Json | null
          video_duration?: number | null
          video_id?: string
          video_url?: string | null
          views?: number
        }
        Relationships: [
          {
            foreignKeyName: "douyin_video_corpus_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "douyin_niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      douyin_video_shots: {
        Row: {
          created_at: string
          creator_handle: string | null
          description: string | null
          douyin_url: string | null
          end_s: number | null
          frame_url: string | null
          framing: string | null
          hook_type: string | null
          id: string
          motion: string | null
          niche_id: number
          overlay_style: string | null
          pace: string | null
          scene_index: number
          scene_type: string | null
          start_s: number | null
          subject: string | null
          thumbnail_url: string | null
          video_id: string
          views: number | null
        }
        Insert: {
          created_at?: string
          creator_handle?: string | null
          description?: string | null
          douyin_url?: string | null
          end_s?: number | null
          frame_url?: string | null
          framing?: string | null
          hook_type?: string | null
          id?: string
          motion?: string | null
          niche_id: number
          overlay_style?: string | null
          pace?: string | null
          scene_index: number
          scene_type?: string | null
          start_s?: number | null
          subject?: string | null
          thumbnail_url?: string | null
          video_id: string
          views?: number | null
        }
        Update: {
          created_at?: string
          creator_handle?: string | null
          description?: string | null
          douyin_url?: string | null
          end_s?: number | null
          frame_url?: string | null
          framing?: string | null
          hook_type?: string | null
          id?: string
          motion?: string | null
          niche_id?: number
          overlay_style?: string | null
          pace?: string | null
          scene_index?: number
          scene_type?: string | null
          start_s?: number | null
          subject?: string | null
          thumbnail_url?: string | null
          video_id?: string
          views?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "douyin_video_shots_video_fk"
            columns: ["video_id"]
            isOneToOne: false
            referencedRelation: "douyin_video_corpus"
            referencedColumns: ["video_id"]
          },
        ]
      }
      draft_scripts: {
        Row: {
          created_at: string
          duration_sec: number
          hook: string
          hook_delay_ms: number
          id: string
          niche_id: number | null
          shots: Json
          source_session_id: string | null
          tone: string
          topic: string
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          duration_sec: number
          hook: string
          hook_delay_ms: number
          id?: string
          niche_id?: number | null
          shots?: Json
          source_session_id?: string | null
          tone: string
          topic: string
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          duration_sec?: number
          hook?: string
          hook_delay_ms?: number
          id?: string
          niche_id?: number | null
          shots?: Json
          source_session_id?: string | null
          tone?: string
          topic?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "draft_scripts_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "draft_scripts_source_session_id_fkey"
            columns: ["source_session_id"]
            isOneToOne: false
            referencedRelation: "answer_sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      ensemble_calls: {
        Row: {
          call_site: string
          created_at: string
          duration_ms: number | null
          endpoint: string
          id: string
          request_class: string
        }
        Insert: {
          call_site?: string
          created_at?: string
          duration_ms?: number | null
          endpoint: string
          id?: string
          request_class?: string
        }
        Update: {
          call_site?: string
          created_at?: string
          duration_ms?: number | null
          endpoint?: string
          id?: string
          request_class?: string
        }
        Relationships: []
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
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      gemini_calls: {
        Row: {
          cached_content_token_count: number | null
          call_site: string
          cost_usd: number
          created_at: string
          duration_ms: number
          error_code: string | null
          gcp_stt_cost_usd: number | null
          id: string
          is_batch: boolean
          model_name: string
          session_id: string | null
          success: boolean
          tokens_in: number
          tokens_out: number
          user_id: string | null
        }
        Insert: {
          cached_content_token_count?: number | null
          call_site: string
          cost_usd: number
          created_at?: string
          duration_ms: number
          error_code?: string | null
          gcp_stt_cost_usd?: number | null
          id?: string
          is_batch?: boolean
          model_name: string
          session_id?: string | null
          success?: boolean
          tokens_in: number
          tokens_out: number
          user_id?: string | null
        }
        Update: {
          cached_content_token_count?: number | null
          call_site?: string
          cost_usd?: number
          created_at?: string
          duration_ms?: number
          error_code?: string | null
          gcp_stt_cost_usd?: number | null
          id?: string
          is_batch?: boolean
          model_name?: string
          session_id?: string | null
          success?: boolean
          tokens_in?: number
          tokens_out?: number
          user_id?: string | null
        }
        Relationships: []
      }
      hashtag_class_map: {
        Row: {
          confidence: number
          content_class_id: number
          hashtag: string
          last_seen_at: string | null
          occurrences: number
          source: string
          updated_at: string
          yield_14d: number | null
        }
        Insert: {
          confidence?: number
          content_class_id: number
          hashtag: string
          last_seen_at?: string | null
          occurrences?: number
          source?: string
          updated_at?: string
          yield_14d?: number | null
        }
        Update: {
          confidence?: number
          content_class_id?: number
          hashtag?: string
          last_seen_at?: string | null
          occurrences?: number
          source?: string
          updated_at?: string
          yield_14d?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "hashtag_class_map_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
        ]
      }
      hashtag_niche_map: {
        Row: {
          confidence: string | null
          created_at: string | null
          hashtag: string
          is_generic: boolean | null
          niche_count: number | null
          niche_id: number | null
          occurrences: number | null
          source: string | null
          updated_at: string | null
        }
        Insert: {
          confidence?: string | null
          created_at?: string | null
          hashtag: string
          is_generic?: boolean | null
          niche_count?: number | null
          niche_id?: number | null
          occurrences?: number | null
          source?: string | null
          updated_at?: string | null
        }
        Update: {
          confidence?: string | null
          created_at?: string | null
          hashtag?: string
          is_generic?: boolean | null
          niche_count?: number | null
          niche_id?: number | null
          occurrences?: number | null
          source?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "hashtag_niche_map_niche_id_fkey"
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
      niche_candidates: {
        Row: {
          assigned_niche_id: number | null
          avg_views: number | null
          created_at: string | null
          discovery_date: string
          hashtag: string
          id: number
          notes: string | null
          occurrences: number | null
          reviewed: boolean | null
          sample_video_ids: string[] | null
          updated_at: string | null
        }
        Insert: {
          assigned_niche_id?: number | null
          avg_views?: number | null
          created_at?: string | null
          discovery_date?: string
          hashtag: string
          id?: number
          notes?: string | null
          occurrences?: number | null
          reviewed?: boolean | null
          sample_video_ids?: string[] | null
          updated_at?: string | null
        }
        Update: {
          assigned_niche_id?: number | null
          avg_views?: number | null
          created_at?: string | null
          discovery_date?: string
          hashtag?: string
          id?: number
          notes?: string | null
          occurrences?: number | null
          reviewed?: boolean | null
          sample_video_ids?: string[] | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "niche_candidates_assigned_niche_id_fkey"
            columns: ["assigned_niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      niche_insights: {
        Row: {
          computed_at: string | null
          execution_tip: string | null
          id: string
          insight_text: string | null
          mechanisms: Json | null
          niche_id: number
          quality_flag: string | null
          staleness_risk: string | null
          top_formula_format: string | null
          top_formula_hook: string | null
          week_of: string
        }
        Insert: {
          computed_at?: string | null
          execution_tip?: string | null
          id?: string
          insight_text?: string | null
          mechanisms?: Json | null
          niche_id: number
          quality_flag?: string | null
          staleness_risk?: string | null
          top_formula_format?: string | null
          top_formula_hook?: string | null
          week_of: string
        }
        Update: {
          computed_at?: string | null
          execution_tip?: string | null
          id?: string
          insight_text?: string | null
          mechanisms?: Json | null
          niche_id?: number
          quality_flag?: string | null
          staleness_risk?: string | null
          top_formula_format?: string | null
          top_formula_hook?: string | null
          week_of?: string
        }
        Relationships: [
          {
            foreignKeyName: "niche_insights_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      niche_taxonomy: {
        Row: {
          created_at: string
          id: number
          last_hashtag_refresh: string | null
          name_en: string
          name_vn: string
          signal_hashtags: string[]
          stale_signal_count: number | null
          style_distribution: Json
        }
        Insert: {
          created_at?: string
          id?: number
          last_hashtag_refresh?: string | null
          name_en: string
          name_vn: string
          signal_hashtags?: string[]
          stale_signal_count?: number | null
          style_distribution?: Json
        }
        Update: {
          created_at?: string
          id?: number
          last_hashtag_refresh?: string | null
          name_en?: string
          name_vn?: string
          signal_hashtags?: string[]
          stale_signal_count?: number | null
          style_distribution?: Json
        }
        Relationships: []
      }
      niche_weekly_digest: {
        Row: {
          avg_save_rate: number | null
          avg_views: number | null
          best_posting_hours_json: Json | null
          carousel_avg_save_rate: number | null
          carousel_avg_views: number | null
          carousel_count: number | null
          computed_at: string
          cross_niche_signals: Json | null
          formula_changed: boolean | null
          formula_structural_pattern: Json | null
          id: string
          new_sounds_json: Json | null
          niche_id: number
          niche_insight_text: string | null
          previous_top_formula_json: Json | null
          top_formula_json: Json | null
          top_sounds_json: Json | null
          total_videos_indexed: number | null
          video_avg_save_rate: number | null
          video_avg_views: number | null
          video_count: number | null
          week_of: string
        }
        Insert: {
          avg_save_rate?: number | null
          avg_views?: number | null
          best_posting_hours_json?: Json | null
          carousel_avg_save_rate?: number | null
          carousel_avg_views?: number | null
          carousel_count?: number | null
          computed_at?: string
          cross_niche_signals?: Json | null
          formula_changed?: boolean | null
          formula_structural_pattern?: Json | null
          id?: string
          new_sounds_json?: Json | null
          niche_id: number
          niche_insight_text?: string | null
          previous_top_formula_json?: Json | null
          top_formula_json?: Json | null
          top_sounds_json?: Json | null
          total_videos_indexed?: number | null
          video_avg_save_rate?: number | null
          video_avg_views?: number | null
          video_count?: number | null
          week_of: string
        }
        Update: {
          avg_save_rate?: number | null
          avg_views?: number | null
          best_posting_hours_json?: Json | null
          carousel_avg_save_rate?: number | null
          carousel_avg_views?: number | null
          carousel_count?: number | null
          computed_at?: string
          cross_niche_signals?: Json | null
          formula_changed?: boolean | null
          formula_structural_pattern?: Json | null
          id?: string
          new_sounds_json?: Json | null
          niche_id?: number
          niche_insight_text?: string | null
          previous_top_formula_json?: Json | null
          top_formula_json?: Json | null
          top_sounds_json?: Json | null
          total_videos_indexed?: number | null
          video_avg_save_rate?: number | null
          video_avg_views?: number | null
          video_count?: number | null
          week_of?: string
        }
        Relationships: [
          {
            foreignKeyName: "niche_weekly_digest_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
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
          creator_niche_id: number | null
          credits_remaining: number
          credits_reset_at: string | null
          daily_free_query_count: number
          daily_free_query_reset_at: string | null
          display_name: string
          email: string
          id: string
          is_admin: boolean
          is_processing: boolean
          lifetime_credits_used: number
          niche_ids: number[] | null
          onboarding_free_diagnosis_used: boolean | null
          reference_channel_handles: string[]
          subscription_tier: string
          tiktok_handle: string | null
          updated_at: string
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string
          creator_niche_id?: number | null
          credits_remaining?: number
          credits_reset_at?: string | null
          daily_free_query_count?: number
          daily_free_query_reset_at?: string | null
          display_name?: string
          email: string
          id: string
          is_admin?: boolean
          is_processing?: boolean
          lifetime_credits_used?: number
          niche_ids?: number[] | null
          onboarding_free_diagnosis_used?: boolean | null
          reference_channel_handles?: string[]
          subscription_tier?: string
          tiktok_handle?: string | null
          updated_at?: string
        }
        Update: {
          avatar_url?: string | null
          created_at?: string
          creator_niche_id?: number | null
          credits_remaining?: number
          credits_reset_at?: string | null
          daily_free_query_count?: number
          daily_free_query_reset_at?: string | null
          display_name?: string
          email?: string
          id?: string
          is_admin?: boolean
          is_processing?: boolean
          lifetime_credits_used?: number
          niche_ids?: number[] | null
          onboarding_free_diagnosis_used?: boolean | null
          reference_channel_handles?: string[]
          subscription_tier?: string
          tiktok_handle?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "profiles_creator_niche_id_fkey"
            columns: ["creator_niche_id"]
            isOneToOne: false
            referencedRelation: "creator_niches"
            referencedColumns: ["id"]
          },
        ]
      }
      push_events: {
        Row: {
          created_at: string
          event_data: Json
          event_type: string
          id: string
          read_at: string | null
          sent_email: boolean | null
          sent_inapp: boolean | null
          user_id: string
        }
        Insert: {
          created_at?: string
          event_data: Json
          event_type: string
          id?: string
          read_at?: string | null
          sent_email?: boolean | null
          sent_inapp?: boolean | null
          user_id: string
        }
        Update: {
          created_at?: string
          event_data?: Json
          event_type?: string
          id?: string
          read_at?: string | null
          sent_email?: boolean | null
          sent_inapp?: boolean | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "push_events_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      scene_intelligence: {
        Row: {
          computed_at: string
          corpus_avg_duration: number | null
          niche_id: number
          overlay_samples: Json
          reference_video_ids: string[]
          sample_size: number
          scene_type: string
          tip: string | null
          winner_avg_duration: number | null
          winner_overlay_style: string | null
        }
        Insert: {
          computed_at?: string
          corpus_avg_duration?: number | null
          niche_id: number
          overlay_samples?: Json
          reference_video_ids?: string[]
          sample_size?: number
          scene_type: string
          tip?: string | null
          winner_avg_duration?: number | null
          winner_overlay_style?: string | null
        }
        Update: {
          computed_at?: string
          corpus_avg_duration?: number | null
          niche_id?: number
          overlay_samples?: Json
          reference_video_ids?: string[]
          sample_size?: number
          scene_type?: string
          tip?: string | null
          winner_avg_duration?: number | null
          winner_overlay_style?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "scene_intelligence_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      signal_grades: {
        Row: {
          computed_at: string
          creator_count: number
          hook_type: string
          id: string
          niche_id: number
          sample_size: number
          signal: string
          total_views: number
          week_start: string
        }
        Insert: {
          computed_at?: string
          creator_count?: number
          hook_type: string
          id?: string
          niche_id: number
          sample_size?: number
          signal: string
          total_views?: number
          week_start: string
        }
        Update: {
          computed_at?: string
          creator_count?: number
          hook_type?: string
          id?: string
          niche_id?: number
          sample_size?: number
          signal?: string
          total_views?: number
          week_start?: string
        }
        Relationships: [
          {
            foreignKeyName: "signal_grades_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      starter_creators: {
        Row: {
          avg_views: number
          display_name: string | null
          followers: number
          handle: string
          is_curated: boolean
          last_seeded_at: string
          niche_id: number
          rank: number
          video_count: number
        }
        Insert: {
          avg_views?: number
          display_name?: string | null
          followers?: number
          handle: string
          is_curated?: boolean
          last_seeded_at?: string
          niche_id: number
          rank?: number
          video_count?: number
        }
        Update: {
          avg_views?: number
          display_name?: string | null
          followers?: number
          handle?: string
          is_curated?: boolean
          last_seeded_at?: string
          niche_id?: number
          rank?: number
          video_count?: number
        }
        Relationships: [
          {
            foreignKeyName: "starter_creators_niche_id_fkey"
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
          credits_granted: number
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
          credits_granted: number
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
          credits_granted?: number
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
      thumbnail_failures: {
        Row: {
          failed_at: string
          failed_url: string | null
          id: number
          user_agent: string | null
          video_id: string
        }
        Insert: {
          failed_at?: string
          failed_url?: string | null
          id?: number
          user_agent?: string | null
          video_id: string
        }
        Update: {
          failed_at?: string
          failed_url?: string | null
          id?: number
          user_agent?: string | null
          video_id?: string
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
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      trending_cards: {
        Row: {
          computed_at: string
          corpus_cite: string | null
          description: string
          hook_template: string | null
          hook_type: string | null
          id: string
          meta_insight: string | null
          niche_id: number
          signal: string
          title: string
          video_ids: string[]
          week_of: string
        }
        Insert: {
          computed_at?: string
          corpus_cite?: string | null
          description: string
          hook_template?: string | null
          hook_type?: string | null
          id?: string
          meta_insight?: string | null
          niche_id: number
          signal: string
          title: string
          video_ids?: string[]
          week_of: string
        }
        Update: {
          computed_at?: string
          corpus_cite?: string | null
          description?: string
          hook_template?: string | null
          hook_type?: string | null
          id?: string
          meta_insight?: string | null
          niche_id?: number
          signal?: string
          title?: string
          video_ids?: string[]
          week_of?: string
        }
        Relationships: [
          {
            foreignKeyName: "trending_cards_niche_id_fkey"
            columns: ["niche_id"]
            isOneToOne: false
            referencedRelation: "niche_taxonomy"
            referencedColumns: ["id"]
          },
        ]
      }
      trending_sounds: {
        Row: {
          commerce_signal: boolean
          commercial_music_library_eligible: boolean | null
          computed_at: string
          content_class_id: number | null
          dialect_audio: string | null
          id: string
          is_original_sound: boolean
          lifecycle_phase: string | null
          sound_id: string
          sound_insight_text: string | null
          sound_name: string
          total_views: number
          usage_count: number
          week_of: string
        }
        Insert: {
          commerce_signal?: boolean
          commercial_music_library_eligible?: boolean | null
          computed_at?: string
          content_class_id?: number | null
          dialect_audio?: string | null
          id?: string
          is_original_sound?: boolean
          lifecycle_phase?: string | null
          sound_id: string
          sound_insight_text?: string | null
          sound_name: string
          total_views?: number
          usage_count?: number
          week_of: string
        }
        Update: {
          commerce_signal?: boolean
          commercial_music_library_eligible?: boolean | null
          computed_at?: string
          content_class_id?: number | null
          dialect_audio?: string | null
          id?: string
          is_original_sound?: boolean
          lifecycle_phase?: string | null
          sound_id?: string
          sound_insight_text?: string | null
          sound_name?: string
          total_views?: number
          usage_count?: number
          week_of?: string
        }
        Relationships: [
          {
            foreignKeyName: "trending_sounds_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
        ]
      }
      usage_events: {
        Row: {
          action: string
          created_at: string
          id: string
          metadata: Json
          user_id: string
        }
        Insert: {
          action: string
          created_at?: string
          id?: string
          metadata?: Json
          user_id: string
        }
        Update: {
          action?: string
          created_at?: string
          id?: string
          metadata?: Json
          user_id?: string
        }
        Relationships: []
      }
      video_corpus: {
        Row: {
          analysis_json: Json
          boost_attribution: string
          breakout_multiplier: number | null
          breakout_ratio: number | null
          caption: string | null
          class_assignment_disagreement: number | null
          class_assignment_tier: string | null
          comment_radar: Json | null
          comment_radar_fetched_at: string | null
          comments: number
          content_class_id: number | null
          content_format: string | null
          content_type: string
          created_at: string
          creator_followers: number | null
          creator_handle: string
          creator_median_views: number | null
          creator_tier: string | null
          cta_type: string | null
          dialect: string | null
          distribution_shape: string | null
          engagement_rate: number
          face_appears_at: number | null
          first_frame_type: string | null
          first_seen_at: string | null
          frame_urls: string[]
          has_caption_text: boolean | null
          has_vietnamese_hashtags: boolean | null
          hashtag_count: number | null
          hashtags: string[] | null
          hook_phrase: string | null
          hook_type: string | null
          id: string
          indexed_at: string
          inferred_creator_niche_id: number | null
          ingest_loop_content_class_id: number | null
          ingest_loop_niche_id: number | null
          ingest_relaxation_tier: number
          ingest_source: string | null
          is_commerce: boolean | null
          is_duet: boolean | null
          is_original_sound: boolean | null
          is_stitch: boolean | null
          language: string | null
          last_refetched_at: string | null
          last_refreshed_at: string | null
          likes: number
          niche_resolution_confidence: number | null
          niche_resolution_source: string | null
          pain_points: Json | null
          pattern_id: string | null
          posted_at: string | null
          posting_hour: number | null
          promotion_type: string | null
          quality_tier: string | null
          reference_eligible: boolean
          save_rate: number | null
          saves: number | null
          scene_count: number | null
          score_cohort_mismatch: boolean
          search_vector: unknown
          shares: number
          sound_id: string | null
          sound_name: string | null
          stats_history: Json
          style_tags: Json | null
          target_audience: string | null
          text_overlay_count: number | null
          thumbnail_analysis: Json | null
          thumbnail_analysis_fetched_at: string | null
          thumbnail_url: string | null
          tiktok_url: string
          tone: string | null
          topics: string[] | null
          transcript_snippet: string | null
          transitions_per_second: number | null
          video_duration: number | null
          video_id: string
          video_url: string | null
          views: number
        }
        Insert: {
          analysis_json: Json
          boost_attribution?: string
          breakout_multiplier?: number | null
          breakout_ratio?: number | null
          caption?: string | null
          class_assignment_disagreement?: number | null
          class_assignment_tier?: string | null
          comment_radar?: Json | null
          comment_radar_fetched_at?: string | null
          comments?: number
          content_class_id?: number | null
          content_format?: string | null
          content_type: string
          created_at?: string
          creator_followers?: number | null
          creator_handle: string
          creator_median_views?: number | null
          creator_tier?: string | null
          cta_type?: string | null
          dialect?: string | null
          distribution_shape?: string | null
          engagement_rate?: number
          face_appears_at?: number | null
          first_frame_type?: string | null
          first_seen_at?: string | null
          frame_urls?: string[]
          has_caption_text?: boolean | null
          has_vietnamese_hashtags?: boolean | null
          hashtag_count?: number | null
          hashtags?: string[] | null
          hook_phrase?: string | null
          hook_type?: string | null
          id?: string
          indexed_at?: string
          inferred_creator_niche_id?: number | null
          ingest_loop_content_class_id?: number | null
          ingest_loop_niche_id?: number | null
          ingest_relaxation_tier?: number
          ingest_source?: string | null
          is_commerce?: boolean | null
          is_duet?: boolean | null
          is_original_sound?: boolean | null
          is_stitch?: boolean | null
          language?: string | null
          last_refetched_at?: string | null
          last_refreshed_at?: string | null
          likes?: number
          niche_resolution_confidence?: number | null
          niche_resolution_source?: string | null
          pain_points?: Json | null
          pattern_id?: string | null
          posted_at?: string | null
          posting_hour?: number | null
          promotion_type?: string | null
          quality_tier?: string | null
          reference_eligible?: boolean
          save_rate?: number | null
          saves?: number | null
          scene_count?: number | null
          score_cohort_mismatch?: boolean
          search_vector?: unknown
          shares?: number
          sound_id?: string | null
          sound_name?: string | null
          stats_history?: Json
          style_tags?: Json | null
          target_audience?: string | null
          text_overlay_count?: number | null
          thumbnail_analysis?: Json | null
          thumbnail_analysis_fetched_at?: string | null
          thumbnail_url?: string | null
          tiktok_url: string
          tone?: string | null
          topics?: string[] | null
          transcript_snippet?: string | null
          transitions_per_second?: number | null
          video_duration?: number | null
          video_id: string
          video_url?: string | null
          views?: number
        }
        Update: {
          analysis_json?: Json
          boost_attribution?: string
          breakout_multiplier?: number | null
          breakout_ratio?: number | null
          caption?: string | null
          class_assignment_disagreement?: number | null
          class_assignment_tier?: string | null
          comment_radar?: Json | null
          comment_radar_fetched_at?: string | null
          comments?: number
          content_class_id?: number | null
          content_format?: string | null
          content_type?: string
          created_at?: string
          creator_followers?: number | null
          creator_handle?: string
          creator_median_views?: number | null
          creator_tier?: string | null
          cta_type?: string | null
          dialect?: string | null
          distribution_shape?: string | null
          engagement_rate?: number
          face_appears_at?: number | null
          first_frame_type?: string | null
          first_seen_at?: string | null
          frame_urls?: string[]
          has_caption_text?: boolean | null
          has_vietnamese_hashtags?: boolean | null
          hashtag_count?: number | null
          hashtags?: string[] | null
          hook_phrase?: string | null
          hook_type?: string | null
          id?: string
          indexed_at?: string
          inferred_creator_niche_id?: number | null
          ingest_loop_content_class_id?: number | null
          ingest_loop_niche_id?: number | null
          ingest_relaxation_tier?: number
          ingest_source?: string | null
          is_commerce?: boolean | null
          is_duet?: boolean | null
          is_original_sound?: boolean | null
          is_stitch?: boolean | null
          language?: string | null
          last_refetched_at?: string | null
          last_refreshed_at?: string | null
          likes?: number
          niche_resolution_confidence?: number | null
          niche_resolution_source?: string | null
          pain_points?: Json | null
          pattern_id?: string | null
          posted_at?: string | null
          posting_hour?: number | null
          promotion_type?: string | null
          quality_tier?: string | null
          reference_eligible?: boolean
          save_rate?: number | null
          saves?: number | null
          scene_count?: number | null
          score_cohort_mismatch?: boolean
          search_vector?: unknown
          shares?: number
          sound_id?: string | null
          sound_name?: string | null
          stats_history?: Json
          style_tags?: Json | null
          target_audience?: string | null
          text_overlay_count?: number | null
          thumbnail_analysis?: Json | null
          thumbnail_analysis_fetched_at?: string | null
          thumbnail_url?: string | null
          tiktok_url?: string
          tone?: string | null
          topics?: string[] | null
          transcript_snippet?: string | null
          transitions_per_second?: number | null
          video_duration?: number | null
          video_id?: string
          video_url?: string | null
          views?: number
        }
        Relationships: [
          {
            foreignKeyName: "video_corpus_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "video_corpus_inferred_creator_niche_id_fkey"
            columns: ["inferred_creator_niche_id"]
            isOneToOne: false
            referencedRelation: "creator_niches"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "video_corpus_pattern_id_fkey"
            columns: ["pattern_id"]
            isOneToOne: false
            referencedRelation: "video_patterns"
            referencedColumns: ["id"]
          },
        ]
      }
      video_dang_hoc: {
        Row: {
          breakout_multiplier: number | null
          id: string
          list_type: string
          rank: number
          refreshed_at: string
          velocity: number | null
          video_id: string
        }
        Insert: {
          breakout_multiplier?: number | null
          id?: string
          list_type: string
          rank: number
          refreshed_at?: string
          velocity?: number | null
          video_id: string
        }
        Update: {
          breakout_multiplier?: number | null
          id?: string
          list_type?: string
          rank?: number
          refreshed_at?: string
          velocity?: number | null
          video_id?: string
        }
        Relationships: []
      }
      video_diagnostics: {
        Row: {
          analysis_depth: string
          analysis_headline: string | null
          analysis_subtext: string | null
          bright_spot_signal: Json | null
          cached_response: Json | null
          channel_context: Json | null
          computed_at: string
          diagnosis: string | null
          flop_issues: Json | null
          format_cards: Json | null
          hook_phases: Json
          lessons: Json
          narrative_vi: Json | null
          niche_benchmark_curve: Json | null
          niche_posting_context: Json | null
          performance_tier: string | null
          reference_videos: Json | null
          retention_curve: Json | null
          segments: Json
          source: string
          tiktok_url: string | null
          video_id: string
          view_scenarios: Json | null
        }
        Insert: {
          analysis_depth?: string
          analysis_headline?: string | null
          analysis_subtext?: string | null
          bright_spot_signal?: Json | null
          cached_response?: Json | null
          channel_context?: Json | null
          computed_at?: string
          diagnosis?: string | null
          flop_issues?: Json | null
          format_cards?: Json | null
          hook_phases?: Json
          lessons?: Json
          narrative_vi?: Json | null
          niche_benchmark_curve?: Json | null
          niche_posting_context?: Json | null
          performance_tier?: string | null
          reference_videos?: Json | null
          retention_curve?: Json | null
          segments?: Json
          source?: string
          tiktok_url?: string | null
          video_id: string
          view_scenarios?: Json | null
        }
        Update: {
          analysis_depth?: string
          analysis_headline?: string | null
          analysis_subtext?: string | null
          bright_spot_signal?: Json | null
          cached_response?: Json | null
          channel_context?: Json | null
          computed_at?: string
          diagnosis?: string | null
          flop_issues?: Json | null
          format_cards?: Json | null
          hook_phases?: Json
          lessons?: Json
          narrative_vi?: Json | null
          niche_benchmark_curve?: Json | null
          niche_posting_context?: Json | null
          performance_tier?: string | null
          reference_videos?: Json | null
          retention_curve?: Json | null
          segments?: Json
          source?: string
          tiktok_url?: string | null
          video_id?: string
          view_scenarios?: Json | null
        }
        Relationships: []
      }
      video_patterns: {
        Row: {
          angles: Json | null
          careful: string | null
          computed_at: string
          deck_computed_at: string | null
          display_name: string | null
          first_seen_at: string
          id: string
          instance_count: number
          is_active: boolean
          last_seen_at: string
          niche_spread: number[]
          signature: Json
          signature_hash: string
          structure: Json | null
          weekly_instance_count: number
          weekly_instance_count_prev: number
          why: string | null
        }
        Insert: {
          angles?: Json | null
          careful?: string | null
          computed_at?: string
          deck_computed_at?: string | null
          display_name?: string | null
          first_seen_at: string
          id?: string
          instance_count?: number
          is_active?: boolean
          last_seen_at: string
          niche_spread?: number[]
          signature: Json
          signature_hash: string
          structure?: Json | null
          weekly_instance_count?: number
          weekly_instance_count_prev?: number
          why?: string | null
        }
        Update: {
          angles?: Json | null
          careful?: string | null
          computed_at?: string
          deck_computed_at?: string | null
          display_name?: string | null
          first_seen_at?: string
          id?: string
          instance_count?: number
          is_active?: boolean
          last_seen_at?: string
          niche_spread?: number[]
          signature?: Json
          signature_hash?: string
          structure?: Json | null
          weekly_instance_count?: number
          weekly_instance_count_prev?: number
          why?: string | null
        }
        Relationships: []
      }
      video_shots: {
        Row: {
          created_at: string
          creator_handle: string | null
          description: string | null
          end_s: number | null
          frame_url: string | null
          framing: string | null
          hook_type: string | null
          id: string
          motion: string | null
          niche_id: number
          overlay_style: string | null
          pace: string | null
          scene_index: number
          scene_type: string | null
          start_s: number | null
          subject: string | null
          thumbnail_url: string | null
          tiktok_url: string | null
          video_id: string
          views: number | null
        }
        Insert: {
          created_at?: string
          creator_handle?: string | null
          description?: string | null
          end_s?: number | null
          frame_url?: string | null
          framing?: string | null
          hook_type?: string | null
          id?: string
          motion?: string | null
          niche_id: number
          overlay_style?: string | null
          pace?: string | null
          scene_index: number
          scene_type?: string | null
          start_s?: number | null
          subject?: string | null
          thumbnail_url?: string | null
          tiktok_url?: string | null
          video_id: string
          views?: number | null
        }
        Update: {
          created_at?: string
          creator_handle?: string | null
          description?: string | null
          end_s?: number | null
          frame_url?: string | null
          framing?: string | null
          hook_type?: string | null
          id?: string
          motion?: string | null
          niche_id?: number
          overlay_style?: string | null
          pace?: string | null
          scene_index?: number
          scene_type?: string | null
          start_s?: number | null
          subject?: string | null
          thumbnail_url?: string | null
          tiktok_url?: string | null
          video_id?: string
          views?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "video_shots_video_fk"
            columns: ["video_id"]
            isOneToOne: false
            referencedRelation: "video_corpus"
            referencedColumns: ["video_id"]
          },
        ]
      }
      vietnamese_asr_cache: {
        Row: {
          audio_duration_sec: number | null
          created_at: string
          stt_cost_usd: number
          transcript: Json
          video_id: string
        }
        Insert: {
          audio_duration_sec?: number | null
          created_at?: string
          stt_cost_usd?: number
          transcript: Json
          video_id: string
        }
        Update: {
          audio_duration_sec?: number | null
          created_at?: string
          stt_cost_usd?: number
          transcript?: Json
          video_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      content_class_intelligence: {
        Row: {
          avg_duration: number | null
          avg_engagement_rate: number | null
          avg_face_appears_at: number | null
          avg_hashtag_count: number | null
          avg_text_overlays: number | null
          avg_transitions_per_second: number | null
          avg_views: number | null
          avg_views_7d: number | null
          avg_views_prior_7d: number | null
          claim_tier: string | null
          commerce_avg_views: number | null
          commerce_pct: number | null
          computed_at: string | null
          content_class_id: number | null
          format_momentum: number | null
          has_cta_pct: number | null
          hook_distribution: Json | null
          lifecycle_stage: string | null
          max_duration: number | null
          median_duration: number | null
          median_er: number | null
          median_scene_count: number | null
          median_views: number | null
          min_duration: number | null
          northern_count: number | null
          organic_avg_views: number | null
          p50_views: number | null
          pct_face_in_half_sec: number | null
          pct_has_caption_text: number | null
          pct_has_specific_hashtags: number | null
          pct_original_sound: number | null
          sample_size: number | null
          southern_count: number | null
          tone_distribution: Json | null
          video_count_7d: number | null
          video_count_prior_7d: number | null
          view_velocity: number | null
        }
        Relationships: [
          {
            foreignKeyName: "video_corpus_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
        ]
      }
      content_class_tier_intelligence: {
        Row: {
          avg_engagement_rate: number | null
          avg_views: number | null
          computed_at: string | null
          content_class_id: number | null
          creator_tier: string | null
          median_er: number | null
          median_views: number | null
          p75_views: number | null
          sample_size: number | null
        }
        Relationships: [
          {
            foreignKeyName: "video_corpus_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
        ]
      }
      creator_niche_content_class_stats: {
        Row: {
          avg_views: number | null
          claim_tier: string | null
          computed_at: string | null
          content_class_id: number | null
          creator_niche_id: number | null
          is_primary: boolean | null
          median_er: number | null
          sample_size: number | null
        }
        Relationships: [
          {
            foreignKeyName: "creator_niche_content_classes_content_class_id_fkey"
            columns: ["content_class_id"]
            isOneToOne: false
            referencedRelation: "content_classifications"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "creator_niche_content_classes_creator_niche_id_fkey"
            columns: ["creator_niche_id"]
            isOneToOne: false
            referencedRelation: "creator_niches"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Functions: {
      _prune_batch_http_log: { Args: never; Returns: undefined }
      admin_flush_video_diagnostics_cache: {
        Args: { p_tiktok_url: string }
        Returns: Json
      }
      admin_pg_net_batch_http_4xx_events: {
        Args: { p_hours?: number }
        Returns: {
          created_at: string
          request_url: string
          response_id: number
          status_code: number
        }[]
      }
      answer_session_list_title: {
        Args: { p_initial_q: string; p_title: string }
        Returns: string
      }
      begin_processing: { Args: { p_user_id: string }; Returns: boolean }
      channel_corpus_stats: {
        Args: { p_handle: string; p_niche: number }
        Returns: Json
      }
      content_class_channel_benchmarks: {
        Args: { p_content_class_id: number; p_creator_tier?: string }
        Returns: {
          avg_views_p50: number
          avg_views_p75: number
          channel_count: number
          engagement_p50: number
          engagement_p75: number
          posts_per_week_p50: number
          posts_per_week_p75: number
        }[]
      }
      content_class_stats_for_creator_niche: {
        Args: { p_creator_niche_id: number }
        Returns: {
          claim_tier: string
          content_class_id: number
          sample_size: number
        }[]
      }
      corpus_hashtag_yields_14d: {
        Args: never
        Returns: {
          hashtag: string
          ingest_count: number
          niche_id: number
        }[]
      }
      cron_assert_no_recent_pg_net_batch_http_4xx: {
        Args: { p_hours?: number }
        Returns: undefined
      }
      cross_creator_pattern_aggregate: {
        Args: { p_lookback_days?: number }
        Returns: {
          creator_count: number
          creators: string[]
          hook_type: string
          niche_id: number
          total_views: number
        }[]
      }
      daily_corpus_growth_by_niche: {
        Args: { p_since: string }
        Returns: {
          delta_24h: number
          niche_id: number
          niche_name: string
        }[]
      }
      decrement_and_grant_credits: {
        Args: {
          p_event_type: string
          p_payos_order_code: string
          p_payos_payment_id: string
        }
        Returns: Json
      }
      decrement_credit: {
        Args: { p_amount?: number; p_user_id: string }
        Returns: number
      }
      end_processing: { Args: { p_user_id: string }; Returns: boolean }
      get_weekly_trend_summaries: {
        Args: { p_week_of: string }
        Returns: {
          card_count: number
          niche_name: string
          top_hook_type: string
          top_signal: string
        }[]
      }
      history_union: {
        Args: { p_cursor?: string; p_filter?: string; p_limit?: number }
        Returns: {
          format: string
          id: string
          niche_id: number
          title: string
          turn_count: number
          type: string
          updated_at: string
        }[]
      }
      increment_free_query_count: { Args: { p_user_id: string }; Returns: Json }
      map_legacy_corpus_to_content_class: {
        Args: { p_content_format: string; p_niche_id: number }
        Returns: number
      }
      map_legacy_niche_to_creator_niche: {
        Args: { legacy_id: number }
        Returns: number
      }
      niche_channel_benchmarks: {
        Args: { p_niche_id: number }
        Returns: {
          avg_views_p25: number
          avg_views_p50: number
          avg_views_p75: number
          channel_count: number
          engagement_p50: number
          engagement_p75: number
          posts_per_week_p50: number
          posts_per_week_p75: number
        }[]
      }
      pattern_wow_diff_7d: {
        Args: { p_niche_id: number }
        Returns: {
          hook_type: string
          is_dropped: boolean
          is_new: boolean
          rank_change: number
          rank_now: number
          rank_prior: number
        }[]
      }
      refresh_content_class_intelligence: { Args: never; Returns: undefined }
      refresh_content_class_tier_intelligence: {
        Args: never
        Returns: undefined
      }
      refresh_creator_niche_content_class_stats: {
        Args: never
        Returns: undefined
      }
      search_history_union: {
        Args: { p_limit?: number; p_query: string }
        Returns: {
          format: string
          id: string
          niche_id: number
          title: string
          turn_count: number
          type: string
          updated_at: string
        }[]
      }
      search_sessions: {
        Args: { p_user_id: string; search_query: string }
        Returns: {
          created_at: string
          credits_used: number
          first_message: string
          id: string
          intent_type: string | null
          is_pinned: boolean
          niche_id: number | null
          title: string | null
          updated_at: string
          user_id: string
        }[]
        SetofOptions: {
          from: "*"
          to: "chat_sessions"
          isOneToOne: false
          isSetofReturn: true
        }
      }
      seed_starter_creators: {
        Args: { p_top_n?: number }
        Returns: {
          out_niche_id: number
          out_seeded: number
        }[]
      }
      thumbnail_failures_count_7d: {
        Args: { cutoff_ts: string }
        Returns: number
      }
      thumbnail_failures_top10: {
        Args: { cutoff_ts: string }
        Returns: {
          fail_count: number
          video_id: string
        }[]
      }
      timing_top_window_streak: {
        Args: { p_day: number; p_hour_bucket: number; p_niche_id: number }
        Returns: number
      }
      toggle_reference_channel: {
        Args: { p_handle: string }
        Returns: undefined
      }
      upsert_video_corpus_batch: {
        Args: { p_rows: Json }
        Returns: {
          out_action: string
          out_video_id: string
        }[]
      }
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
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {},
  },
} as const
