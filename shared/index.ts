// Barrel export — ritual contract for web + future mobile.

export type {
  DailyRitual,
  RitualEmptyReason,
  RitualErrorBody,
  RitualResult,
  RitualScript,
} from "./types/ritual";

export { fetchDailyRitual, type FetchDailyRitualParams } from "./api/ritual";
