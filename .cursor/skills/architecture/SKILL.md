---
name: architecture
description: Technical architecture reference for the Tech Lead — complexity signals, stack constraints, domain patterns, and decision frameworks. Read this during /office-hours (stack fit check) and /phase4 (technical decisions). Not an agent — a knowledge base the Tech Lead consults.
disable-model-invocation: true
---

# Architecture Reference — Tech Lead Knowledge Base

This skill equips the Tech Lead with the structured knowledge needed to make technical decisions during `/office-hours` (stack fit validation) and `/phase4` (tech spec writing). It replaces guessing from training data with checklists and reference patterns.

---

## 1. Technical Complexity Signals

When reviewing the northstar or writing the tech spec, scan each feature for these signals. Any feature that triggers one or more signals needs **technical research** before the tech spec can specify its implementation.

### Money / Credits

| Signal | Why it's complex | Research needed |
|---|---|---|
| Credit balance that can be spent | Concurrent deductions race. Balance must never go negative. | Ledger pattern vs atomic decrement. Idempotent webhooks. |
| Subscription with plan changes | Proration, grace periods, upgrade/downgrade. | Provider-specific upgrade flow. Webhook sequence for plan changes. |
| Webhook-driven state changes | Webhook delivery is at-least-once, not exactly-once. | Idempotency keys. `processed_events` table. Replay handling. |
| Refunds | Reversing a transaction that may have triggered downstream actions. | Compensation pattern. Which downstream effects to undo. |

### Real-Time

| Signal | Why it's complex | Research needed |
|---|---|---|
| Live updates visible to other users | Supabase Realtime has connection limits and payload size limits. | Channel design. Whether to use Realtime subscriptions, polling, or Edge Function push. |
| Collaborative editing | Conflict resolution when two users edit the same resource. | CRDT vs last-write-wins. Whether this is achievable on the RAD stack at all. |
| Presence / online status | Connection tracking, heartbeats, stale state cleanup. | Supabase Realtime Presence API capabilities and limits. |

### File Processing

| Signal | Why it's complex | Research needed |
|---|---|---|
| File upload > 5MB | Edge Function request body limit. Supabase Storage has its own upload API. | Direct-to-Storage upload with signed URLs vs Edge Function proxy. |
| File transformation (resize, convert) | Edge Function CPU/memory limits. 60s execution timeout. | Client-side processing vs external service (Cloudinary, Imgix). |
| Document parsing (PDF, CSV) | Large files exceed Edge Function memory. | Chunked processing. Whether to use a dedicated service. |

### Complex Authorization

| Signal | Why it's complex | Research needed |
|---|---|---|
| Shared resources (team, family, group) | RLS `user_id = auth.uid()` doesn't work. Need membership join. | Membership table pattern. RLS policy with JOIN or security definer function. |
| Role-based access (admin, editor, viewer) | Multiple permission levels per resource. | Role column vs permissions table. RLS policy design for role hierarchy. |
| Resource ownership transfer | Changing who owns a resource affects RLS, notifications, history. | Transfer flow. Whether to reassign `user_id` or use a separate `owner_id`. |
| Public/private toggle | Same resource visible to owner always, others conditionally. | RLS policy with OR condition. Performance of conditional policies at scale. |

### Search / Filtering

| Signal | Why it's complex | Research needed |
|---|---|---|
| Full-text search across multiple columns | Postgres `tsvector` + GIN index setup. Vietnamese diacritics affect tokenization. | `to_tsvector('simple', ...)` vs language-specific config. Unaccent extension for Vietnamese. |
| Faceted filtering (price range + category + date) | Compound index design. Query performance with multiple conditions. | Index strategy. Whether to use a materialized view for complex filters. |
| Fuzzy matching / typo tolerance | Postgres `pg_trgm` extension. Performance at scale. | Trigram indexes. Whether Postgres is sufficient or needs external search. |

### State Machines

| Signal | Why it's complex | Research needed |
|---|---|---|
| Entity with lifecycle (draft → active → completed → archived) | Invalid transitions. Concurrent status updates. | CHECK constraint with valid transitions. Optimistic locking with `updated_at`. |
| Multi-step workflow (application → review → approved → rejected) | Branching paths. Notification triggers at each transition. | State machine pattern. Database triggers vs application logic for side effects. |

---

## 2. RAD Stack Constraints

Known limits of the fixed stack. Check these during `/office-hours` when validating northstar requirements against what the stack can deliver.

### Supabase Edge Functions
| Constraint | Limit | Workaround |
|---|---|---|
| Execution timeout | 60 seconds (can be extended to 300s on Pro) | Break into smaller operations. Use background tasks via pg_cron. |
| Request body size | 2MB (can be increased) | Direct-to-Storage upload with signed URLs. |
| Memory | 256MB (can be increased on Pro) | Avoid in-memory processing of large files. Stream instead. |
| Cold start | ~200ms (Deno runtime) | Not an issue for user-facing latency budgets. |
| No persistent state | Functions are stateless | All state in Postgres. No in-memory caches across invocations. |

### Supabase Realtime
| Constraint | Limit | Workaround |
|---|---|---|
| Connections per channel | 500 concurrent (Pro) | Shard channels by user group or resource ID. |
| Payload size | 1MB per message | Send IDs, not full objects. Client re-fetches on notification. |
| Broadcast only (no persistence) | Messages are fire-and-forget | Use database changes + Realtime listeners, not broadcast for critical data. |

### Supabase Postgres
| Constraint | Limit | Workaround |
|---|---|---|
| Connection pool | 60 direct / 200 pooled (Pro) | Use connection pooling (Supavisor). Edge Functions use pooled connections. |
| Row-level security overhead | ~5-15% query overhead per RLS policy | Keep policies simple. Avoid correlated subqueries in RLS. |
| No background workers | pg_cron only (cron schedule, not event-driven) | For event-driven: use database triggers → `pg_net` to call Edge Functions. |
| Full-text search | Postgres-native only (no Elasticsearch) | `tsvector` + GIN index. Sufficient for most B2C apps. Consider external search if >1M documents. |

### Vercel (Static SPA)
| Constraint | Limit | Workaround |
|---|---|---|
| No server runtime | Pre-rendered landing + client-side SPA | All server logic in Supabase Edge Functions. |
| Build output size | 100MB (free) / 1GB (Pro) | Code split aggressively. Lazy load routes. |
| Edge Middleware | Available but not used in RAD (SPA mode) | If needed for redirects: use Vercel config rewrites instead. |

### When the stack doesn't fit

If a northstar requirement triggers a stack constraint with no viable workaround:

1. **Flag it** — report the specific constraint and the requirement it conflicts with
2. **Present options** using AskUserQuestion format:
   - A) Reduce scope — adjust the requirement to fit the stack (e.g., "limit file uploads to 5MB")
   - B) Add a service — extend the stack with a specific external service (e.g., Cloudinary for image processing)
   - C) Accept risk — build it and see if the limit is actually hit in practice (appropriate for v1/MVP)
   - D) Abandon RAD — if the requirement is core and non-negotiable, RAD may not be the right template

Option D is rare but honest. RAD is not the right tool for real-time collaborative editors, large-scale data pipelines, or compute-heavy ML inference.

---

## 3. Domain Reference Patterns

Common domain architectures on the RAD stack. When Phase 4 identifies a feature in one of these domains, the Tech Lead should compare the proposed schema against these reference patterns before writing the tech spec.

### Credit-Based Billing

**Core tables:**
- `credit_packages` — purchasable credit bundles (amount, price, active)
- `credit_balances` — one row per user (balance, updated_at)
- `credit_transactions` — append-only ledger (user_id, amount, type, reference_id, created_at)

**Key patterns:**
- Balance is a denormalized cache of `SUM(transactions.amount)`. Rebuilt from ledger if corrupted.
- Deduction: `UPDATE credit_balances SET balance = balance - $1 WHERE user_id = $2 AND balance >= $1 RETURNING balance` — atomic check-and-decrement, no application-level read-modify-write.
- Every spend creates a transaction row with `type = 'spend'` and `reference_id` pointing to the resource consumed.
- Webhook top-up: check `processed_events` table for idempotency before crediting.

**Anti-patterns:**
- Storing balance without a transaction log (no audit trail, no recovery)
- Read-modify-write balance updates (race condition under concurrent requests)
- Crediting on webhook without idempotency check (double-credit on retry)

### Subscription Billing

**Core tables:**
- `subscriptions` — one active row per user (plan_id, status, current_period_end, cancel_at_period_end)
- `subscription_events` — append-only log of all provider events (event_id, type, data, processed_at)

**Key patterns:**
- Subscription status is source-of-truth from the payment provider. Local `status` column is a cache.
- Webhook handler: upsert subscription row based on provider's subscription ID, not user ID.
- Plan changes: provider handles proration. App updates `plan_id` on webhook, not on user click.
- Grace period: `current_period_end` may be in the future even after cancellation. RLS checks `current_period_end > now()`.

### Multi-Tenant / Shared Resources

**Core tables:**
- `teams` or `groups` — organizational unit
- `team_members` — junction table (team_id, user_id, role)
- Resources have `team_id` FK instead of (or in addition to) `user_id`

**Key patterns:**
- RLS: `EXISTS (SELECT 1 FROM team_members WHERE team_id = resource.team_id AND user_id = auth.uid())`
- Role-based: add `role` column to `team_members`, check in RLS: `... AND role IN ('admin', 'editor')`
- Personal resources: keep `user_id` for personal items. Team items use `team_id`. Never mix in the same RLS policy.

### Social / Activity Feed

**Core tables:**
- `activities` — append-only log (actor_id, action, target_type, target_id, created_at)
- `follows` or `connections` — junction table for social graph

**Key patterns:**
- Fan-out-on-read: query activities for all followed users at read time. Simple but slow at scale.
- Fan-out-on-write: pre-compute feeds into a `feed_items` table. Complex but fast reads.
- For RAD/MVP: fan-out-on-read is fine. Switch to fan-out-on-write when >10K DAU.

---

## 4. Technical Decision Template

When the Tech Lead identifies a non-trivial technical decision during Phase 4, document it in the tech spec using this format:

```markdown
### TD-[N]: [Decision Title]

**Context:** [What feature requires this decision. 1-2 sentences.]
**Options considered:**
- A) [Option] — [trade-off]
- B) [Option] — [trade-off]

**Decision:** [Which option and why]
**Research basis:** [training data / Context7 / web search / artifacts/integrations/[name].md]
**Risks:** [What could go wrong with this decision]
**Revisit trigger:** [What condition would make us reconsider — e.g., ">1000 concurrent users"]
```

If the research basis is "training data" for a decision with a complexity signal, the Tech Lead should dispatch the Research Agent before finalizing.
