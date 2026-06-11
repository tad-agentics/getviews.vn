/** F4/F5 channel analysis — single tier (3 credits). */
export const CHANNEL_CREDIT_COST = 3;

/** @deprecated Use CHANNEL_CREDIT_COST */
export const CHANNEL_SAU_CREDIT_COST = CHANNEL_CREDIT_COST;

export function channelDepthCreditCost(): number {
  return CHANNEL_CREDIT_COST;
}
