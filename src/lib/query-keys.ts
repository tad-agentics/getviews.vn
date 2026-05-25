export const queryKeys = {
  profile: (userId: string) => ["profile", userId] as const,
  credits: (userId: string) => ["credits", userId] as const,
  subscription: (userId: string) => ["subscription", userId] as const,
  creditTransactions: (userId: string, limit: number) => ["credit_transactions", userId, limit] as const,
  trendVelocity: (niche: string) => ["trend_velocity", niche] as const,
};
