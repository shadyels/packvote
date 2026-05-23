export const TITLE_MAX = 120;
export const DESTINATION_MAX = 100;
export const NOTES_MAX = 2000;
export const NAME_MAX = 80;
export const INTERESTS_MAX = 1000;
export const ACTIVITY_TAG_MAX = 40;
export const ACTIVITY_TAGS_MAX_ITEMS = 20;
export const PARTICIPANT_EMAILS_MAX = 20;
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 72;

const SAFE_OUTPUT_TOKENS = 15_000;
const OPTION_OVERHEAD_TOKENS = 250;
const PER_DAY_TOKENS = 360;

export function maxTripDays(numOptions: number): number {
  if (numOptions < 1) return 1;
  const result = Math.floor(
    (SAFE_OUTPUT_TOKENS - numOptions * OPTION_OVERHEAD_TOKENS) /
      (numOptions * PER_DAY_TOKENS)
  );
  return Math.max(1, result);
}
