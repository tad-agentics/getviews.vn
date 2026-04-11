/**
 * One-time backfill script: populate classifier columns for existing video_corpus rows.
 * Reads analysis_json from each row, runs classifiers, updates the row.
 *
 * Run with: npx tsx scripts/backfill-corpus-classifiers.ts
 *
 * Requires env vars:
 *   SUPABASE_URL — your project URL
 *   SUPABASE_SERVICE_ROLE_KEY — service role key (bypasses RLS)
 *
 * NOTE: ED metadata columns (saves, posted_at, sound_id, etc.) cannot be backfilled
 * because the original API responses were not stored. They will be NULL for existing rows
 * and will populate for all new rows going forward.
 */

import { createClient } from '@supabase/supabase-js';
import {
  classifyCTA,
  classifyFormat,
  detectCommerce,
  detectDialect,
  detectLanguage,
  normalizeHookType,
  type Analysis,
} from '../src/lib/batch/classifiers';

const SUPABASE_URL = process.env.SUPABASE_URL ?? '';
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? '';

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

const PAGE_SIZE = 50;

async function main() {
  console.log('Starting classifier backfill...');

  let offset = 0;
  let totalUpdated = 0;
  let totalSkipped = 0;

  while (true) {
    const { data: rows, error } = await supabase
      .from('video_corpus')
      .select('id, niche_id, analysis_json')
      .range(offset, offset + PAGE_SIZE - 1);

    if (error) {
      console.error('Fetch error:', error.message);
      process.exit(1);
    }

    if (!rows || rows.length === 0) break;

    for (const row of rows) {
      const analysis = row.analysis_json as Analysis | null;

      if (!analysis || Object.keys(analysis).length === 0) {
        totalSkipped++;
        continue;
      }

      const transcript: string = (analysis.audio_transcript as string) ?? '';

      const updates = {
        hook_type: normalizeHookType((analysis.hook_analysis?.hook_type as string) ?? 'other'),
        content_format: classifyFormat(analysis, row.niche_id as number),
        cta_type: classifyCTA((analysis.cta as string | null) ?? null),
        is_commerce: detectCommerce(analysis),
        dialect: detectDialect(transcript),
        language: detectLanguage(analysis),
        topics: (analysis.topics as string[]) ?? [],
        transcript_snippet: transcript.slice(0, 500) || null,
      };

      const { error: updateError } = await supabase
        .from('video_corpus')
        .update(updates)
        .eq('id', row.id);

      if (updateError) {
        console.warn(`  Row ${row.id}: update failed — ${updateError.message}`);
      } else {
        totalUpdated++;
      }
    }

    console.log(`  Processed ${offset + rows.length} rows (updated: ${totalUpdated}, skipped: ${totalSkipped})`);
    offset += PAGE_SIZE;

    if (rows.length < PAGE_SIZE) break;
  }

  console.log(`\nBackfill complete. Updated: ${totalUpdated}, Skipped: ${totalSkipped}`);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
