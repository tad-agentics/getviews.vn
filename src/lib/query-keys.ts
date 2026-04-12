export const queryKeys = {
  profile: (userId: string) => ["profile", userId] as const,
  credits: (userId: string) => ["credits", userId] as const,
  subscription: (userId: string) => ["subscription", userId] as const,
  creditTransactions: (userId: string, limit: number) => ["credit_transactions", userId, limit] as const,
  chatHistory: (sessionId: string) => ["chat", sessionId] as const,
  nicheIntelligence: (niche: string) => ["niche_intelligence", niche] as const,
  trendVelocity: (niche: string) => ["trend_velocity", niche] as const,
  hookEffectiveness: (niche: string) => ["hook_effectiveness", niche] as const,
  videoDangHoc: () => ["video_dang_hoc"] as const,
};
