---
name: pagepop-skill
description: Create and continue PagePop content-generation conversations from a host app. Use when the user wants PagePop to generate, refine, or retrieve content artifacts such as social posts, slides, documents, images, or design drafts.
---

# PagePop Skill

This skill connects a host application to PagePop.

On first use, the user opens a PagePop authorization page in a browser and confirms access. After authorization, the skill stores a local access key and reuses it for later requests.

## Capabilities

- Start a PagePop generation request.
- Continue the current PagePop conversation by default.
- Start a new conversation when explicitly requested.
- List locally saved conversations for switch-chat flows.
- Stream PagePop progress and artifact events.
- Emit a generic artifact delivery view plus channel-aware presentation payloads for host applications.
- Check whether the installed package should be updated.

## Commands

```bash
python3 scripts/pagepop_skill.py status
python3 scripts/pagepop_skill.py auth
python3 scripts/pagepop_skill.py conversations
python3 scripts/pagepop_skill.py stream --goal "Create a product launch deck"
python3 scripts/pagepop_skill.py stream --new-chat --goal "Create a rednote post about camping gear"
python3 scripts/pagepop_skill.py create-quote --selected-option-id standard
python3 scripts/pagepop_skill.py quote-status
python3 scripts/pagepop_skill.py stream --billing-session-id ags_xxx
python3 scripts/pagepop_skill.py resume-stream --conversation-id conv_xxx --offset 0
```

`stream --goal` always submits a chat request before reading SSE events. Use `resume-stream` when the host only needs to replay or continue reading events for an existing conversation without creating a new task. When `--offset` is omitted, `resume-stream` uses the saved SSE cursor for that conversation.

## Configuration

Production packages are built with a generated `skill-manifest.json`.

Common environment variables:

- `PAGEPOP_API_BASE_URL`
- `PAGEPOP_WEB_BASE_URL`
- `PAGEPOP_SKILL_ID`
- `PAGEPOP_SKILL_STATE_DIR`
- `PAGEPOP_SKILL_REGION`
- `PAGEPOP_SKILL_SOURCE_APP`
- `PAGEPOP_SKILL_DISPLAY_APP_NAME`
- `PAGEPOP_SKILL_RETURN_MODE`
- `PAGEPOP_SKILL_RETURN_TARGET`
- `PAGEPOP_SKILL_UPDATE_CHANNEL`
- `PAGEPOP_SKILL_WAIT_FOR_AUTHORIZATION`
- `PAGEPOP_SKILL_ARTIFACT_DIR`
- `PAGEPOP_SKILL_DOWNLOAD_IMAGES`

The legacy `PAGEPOP_OPENCLAW_*` names are still accepted as compatibility aliases for existing OpenClaw installations. New integrations should use the `PAGEPOP_SKILL_*` names. Host-specific usage notes belong in `adapters/`.

Before invoking this skill, host applications should determine whether the current user is in mainland China or outside mainland China. If `PAGEPOP_API_BASE_URL` is not set, production domain selection is region-based: mainland China (`PAGEPOP_SKILL_REGION=CN` or an Asia/Shanghai-style mainland timezone) uses `https://pc-api.pagepop.cn`; non-mainland users use `https://pc-api.pagepop.ai`. Missing region data defaults to the global `.ai` domain and emits an `integration_warning`.

## Host Integration

When a host invokes this skill on behalf of another app, it should pass launch context before authorization:

- `source_app`
- `display_app_name`
- `return_mode`
- `return_target`
- `region` or `PAGEPOP_SKILL_REGION`, after deciding mainland China vs non-mainland

If no launch context is provided, the authorization page falls back to the default host label.

Artifact delivery events include:

- `presentation`: channel-neutral content for fallback renderers.
- `channel_presentations.slack`: Slack Block Kit blocks.
- `channel_presentations.feishu`: Feishu interactive-card payload plus media upload hints.
- `target.preferred_channel`: normalized from `source_app` when the host passes launch context.

Hosts should prefer their matching `channel_presentations` entry, then fall back to `presentation.fallback_text`.
Feishu hosts should avoid rendering raw URLs from generic `presentation`; use the Feishu card buttons or Feishu-specific fallback text so underscores in URLs are not truncated by lark_md auto-linking.
When composing a Feishu chat message manually, send `channel_presentations.feishu.media.local_image_messages` as image messages first, then send `channel_presentations.feishu.plain_text` or `artifact.display_text`; do not copy raw image URLs from `artifact.text` or `sse_event.data` into `lark_md`.

## Paywall and Paid Session Flow

When `/v2/chat` returns `metadata.openclaw_reason=payment_offer_required`, pause the run and show the emitted `payment_required` event to the user. If the event includes `membership_offer`, present membership as the primary action and do not show PAYG option details by default.

The event may include `paywall_mode`, `primary_action`, `secondary_action`, `recommended_action`, `payg_role`, `membership_offer`, `insufficient_reason_text`, `available_points_text`, `payg_enabled`, `payg_available`, `payg_action_text`, `payg_hint`, and `payg_suppressed_reason`.

The user agent should:

1. Always first tell the user why PagePop paused. If `insufficient_reason_text` or `available_points_text` exists, include that context before the membership or payment actions.
2. Always present `membership_offer` as the primary action when it exists.
3. If `paywall_mode=membership_only` or `payg_available` is not true, do not call `create-quote`; open the membership URL and let the user return to the agent, then rerun `stream` without a new `--goal`.
4. If `payg_available=true`, treat PAYG as a secondary fallback only. Do not recommend PAYG by default and do not display preset prices/options until the user explicitly asks to pay only for the current run.
5. For explicit PAYG fallback, run `payment-options` to show the saved preset options, then create a quote with `create-quote --selected-option-id <option_id>` or `create-quote --requested-image-units <count>`. Advanced hosts may call `POST /api/agent-billing/v1/quotes` directly only after the user chooses PAYG.
6. Open or display the returned `payment_url`.
7. Run `quote-status` until `status` is `paid`. Advanced hosts may poll `GET /api/agent-billing/v1/quotes/{quote_id}` directly.
8. Retry the saved PagePop request by running `stream` without a new `--goal`; if the host stores the paid session itself, it may pass `--billing-session-id <session_id>`.

The paid session is consumed by the first real `/v2/chat` execution and ends with that run's first `finish_work`. Do not reuse the same `session_id` across later user turns. Paid continuation is session-only: retry `/v2/chat` with `X-Pagepop-Billing-Session`.

## Output

The skill emits JSON Lines. Important event kinds include:

- `auth_required`
- `auth_authorized`
- `payment_required`
- `payment_pending`
- `payment_authorized`
- `chat_context`
- `conversation_history`
- `chat_submitted`
- `stream_resumed`
- `progress_update`
- `artifact_update`
- `artifact_ready`
- `artifact_delivery`
- `sse_event`
- `stream_finished`
- `skill_update_available`
- `skill_update_required`
- `error`
