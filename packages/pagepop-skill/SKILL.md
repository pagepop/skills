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
- Emit a generic artifact delivery view for host applications.
- Check whether the installed package should be updated.

## Commands

```bash
python3 scripts/pagepop_skill.py status
python3 scripts/pagepop_skill.py auth
python3 scripts/pagepop_skill.py conversations
python3 scripts/pagepop_skill.py stream --goal "Create a product launch deck"
python3 scripts/pagepop_skill.py stream --new-chat --goal "Create a rednote post about camping gear"
```

## Configuration

Production packages are built with a generated `skill-manifest.json`.

Common environment variables:

- `PAGEPOP_API_BASE_URL`
- `PAGEPOP_WEB_BASE_URL`
- `PAGEPOP_SKILL_ID`
- `PAGEPOP_SKILL_STATE_DIR`
- `PAGEPOP_SKILL_SOURCE_APP`
- `PAGEPOP_SKILL_DISPLAY_APP_NAME`
- `PAGEPOP_SKILL_RETURN_MODE`
- `PAGEPOP_SKILL_RETURN_TARGET`
- `PAGEPOP_SKILL_UPDATE_CHANNEL`
- `PAGEPOP_SKILL_WAIT_FOR_AUTHORIZATION`

The legacy `PAGEPOP_OPENCLAW_*` names are still accepted as compatibility aliases for existing OpenClaw installations. New integrations should use the `PAGEPOP_SKILL_*` names. Host-specific usage notes belong in `adapters/`.

## Host Integration

When a host invokes this skill on behalf of another app, it should pass launch context before authorization:

- `source_app`
- `display_app_name`
- `return_mode`
- `return_target`

If no launch context is provided, the authorization page falls back to the default host label.

## Output

The skill emits JSON Lines. Important event kinds include:

- `auth_required`
- `auth_authorized`
- `chat_context`
- `conversation_history`
- `chat_submitted`
- `progress_update`
- `artifact_update`
- `artifact_ready`
- `artifact_delivery`
- `sse_event`
- `stream_finished`
- `skill_update_available`
- `skill_update_required`
- `error`
