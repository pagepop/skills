from __future__ import annotations

import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock
from types import SimpleNamespace

import sys


SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import pagepop_skill as client  # noqa: E402


class PagepopSkillTests(unittest.TestCase):
    def test_load_skill_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = pathlib.Path(temp_dir) / "skill-manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "skill_id": "pagepop-skill",
                        "package_version": "2099.01.01-r1",
                        "channel": "prod",
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(client, "skill_root_dir", return_value=pathlib.Path(temp_dir)):
                manifest = client.load_skill_manifest()

        self.assertEqual(manifest.skill_id, "pagepop-skill")
        self.assertEqual(manifest.package_version, "2099.01.01-r1")
        self.assertEqual(manifest.channel, "prod")

    def test_load_skill_manifest_uses_source_defaults_when_manifest_missing_from_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = pathlib.Path(temp_dir) / "skill-manifest.template.json"
            template_path.write_text("{}", encoding="utf-8")
            with mock.patch.object(client, "skill_root_dir", return_value=pathlib.Path(temp_dir)):
                manifest = client.load_skill_manifest()

        self.assertEqual(manifest.skill_id, "pagepop-skill")
        self.assertEqual(manifest.package_version, "source")
        self.assertEqual(manifest.channel, "prod")
        self.assertEqual(manifest.build_sha, "source")
        self.assertEqual(manifest.repo, "pagepop/skills")

    def test_normalize_login_token_cookie_string(self) -> None:
        self.assertEqual(
            client.normalize_login_token("pagepop-token=abc123; path=/; secure"),
            "abc123",
        )
        self.assertEqual(
            client.normalize_login_token("f-pagepop-token=xyz789"),
            "xyz789",
        )

    def test_auth_required_keeps_server_authorize_url(self) -> None:
        config = client.Config(
            api_base_url="https://pc-api.pagepop.cn",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
            source_app="feishu",
            display_app_name="飞书",
        )
        state = client.SkillState()

        with mock.patch.object(
            client,
            "init_auth",
            return_value={
                "auth_session_id": "oas-test",
                "authorize_url": "https://www.pagepop.cn/openclaw/authorize?session=oas-test",
                "expires_at": "2026-04-20T18:00:00Z",
                "poll_interval_seconds": 1,
            },
        ), mock.patch.object(client, "save_state"), mock.patch.object(client, "emit_event") as emit_event:
            with self.assertRaises(client.AuthorizationPending):
                client.ensure_authorized(config, state)

        auth_required_call = emit_event.call_args_list[0]
        self.assertEqual(auth_required_call.args[0], "auth_required")
        self.assertEqual(
            auth_required_call.kwargs["authorize_url"],
            "https://www.pagepop.cn/openclaw/authorize-v2?session=oas-test",
        )
        self.assertEqual(auth_required_call.kwargs["title"], "Authorize PagePop before first use")
        self.assertEqual(
            auth_required_call.kwargs["message"],
            "Open the authorization page in your browser and confirm once before using this skill.",
        )
        self.assertEqual(auth_required_call.kwargs["action_text"], "Open authorization page")
        self.assertEqual(
            auth_required_call.kwargs["result_hint"],
            "After authorization, return to the source app and continue the current request.",
        )
        self.assertEqual(auth_required_call.kwargs["is_reauth"], False)
        self.assertEqual(auth_required_call.kwargs["requires_user_action"], True)
        self.assertEqual(auth_required_call.kwargs["pause_execution"], True)
        self.assertEqual(auth_required_call.kwargs["resume_mode"], "rerun_same_command")

    def test_auth_required_emits_region_warning_when_region_context_is_missing(self) -> None:
        config = client.Config(
            api_base_url="https://pc-api.pagepop.ai",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
            source_app="feishu",
            display_app_name="Feishu",
            region_context_missing=True,
        )
        state = client.SkillState()

        with mock.patch.object(
            client,
            "init_auth",
            return_value={
                "auth_session_id": "oas-test",
                "authorize_url": "https://www.pagepop.ai/openclaw/authorize?session=oas-test",
                "expires_at": "2026-04-20T18:00:00Z",
                "poll_interval_seconds": 1,
            },
        ), mock.patch.object(client, "save_state"), mock.patch.object(client, "emit_event") as emit_event:
            with self.assertRaises(client.AuthorizationPending):
                client.ensure_authorized(config, state)

        integration_warning_call = emit_event.call_args_list[0]
        self.assertEqual(integration_warning_call.args[0], "integration_warning")
        self.assertEqual(integration_warning_call.kwargs["title"], "Region context missing")
        self.assertIn("mainland China", integration_warning_call.kwargs["message"])
        self.assertEqual(integration_warning_call.kwargs["current_api_base_url"], "https://pc-api.pagepop.ai")

        auth_required_call = emit_event.call_args_list[1]
        self.assertEqual(auth_required_call.args[0], "auth_required")

    def test_auth_required_emits_integration_warning_for_default_launch_context(self) -> None:
        config = client.Config(
            api_base_url="https://pc-api.pagepop.cn",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
        )
        state = client.SkillState()

        with mock.patch.object(
            client,
            "init_auth",
            return_value={
                "auth_session_id": "oas-test",
                "authorize_url": "https://www.pagepop.cn/openclaw/authorize?session=oas-test",
                "expires_at": "2026-04-20T18:00:00Z",
                "poll_interval_seconds": 1,
            },
        ), mock.patch.object(client, "save_state"), mock.patch.object(client, "emit_event") as emit_event:
            with self.assertRaises(client.AuthorizationPending):
                client.ensure_authorized(config, state)

        integration_warning_call = emit_event.call_args_list[0]
        self.assertEqual(integration_warning_call.args[0], "integration_warning")
        self.assertEqual(integration_warning_call.kwargs["current_source_app"], "")
        self.assertEqual(integration_warning_call.kwargs["current_display_app_name"], "OpenClaw")
        self.assertIn("Feishu, Slack, or another host app", integration_warning_call.kwargs["message"])

        auth_required_call = emit_event.call_args_list[1]
        self.assertEqual(auth_required_call.args[0], "auth_required")

    def test_pending_auth_session_authorizes_on_next_run(self) -> None:
        state = client.SkillState(
            pending_auth=client.PendingAuth(
                auth_session_id="oas-test",
                authorize_url="https://www.pagepop.cn/openclaw/authorize-v2?session=oas-test",
                expires_at="2026-04-20T18:00:00Z",
            )
        )
        config = client.Config(
            api_base_url="https://pc-api.pagepop.cn",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
            source_app="feishu",
            display_app_name="飞书",
        )

        with mock.patch.object(
            client,
            "get_auth_status",
            return_value={
                "status": "authorized",
                "expires_at": "2026-04-20T18:00:00Z",
                "access_key": "pp_sk_test",
                "user": {"id": 1},
            },
        ), mock.patch.object(client, "save_state"), mock.patch.object(client, "emit_event") as emit_event:
            next_state = client.ensure_authorized(config, state)

        self.assertEqual(next_state.access_key, "pp_sk_test")
        self.assertIsNone(next_state.pending_auth)
        auth_authorized_call = emit_event.call_args_list[0]
        self.assertEqual(auth_authorized_call.args[0], "auth_authorized")
        self.assertEqual(auth_authorized_call.kwargs["auth_session_id"], "oas-test")

    def test_init_auth_includes_launch_context(self) -> None:
        config = client.Config(
            api_base_url="https://pc-api.pagepop.cn",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
            package_version="2026.04.21-r8",
            source_app="feishu",
            display_app_name="飞书",
            return_mode="manual",
            return_target="",
        )

        with mock.patch.object(client, "http_json", return_value={"auth_session_id": "oas-test"}) as http_json:
            self.assertEqual(client.init_auth(config), {"auth_session_id": "oas-test"})

        http_json.assert_called_once_with(
            "POST",
            "https://pc-api.pagepop.cn/v1/openclaw/auth/init",
            payload={
                "skill_id": "pagepop-skill",
                "client_name": client.DEFAULT_CLIENT_NAME,
                "client_version": client.DEFAULT_CLIENT_VERSION,
                "launch_context": {
                    "source_app": "feishu",
                    "display_app_name": "飞书",
                    "return_mode": "manual",
                    "return_target": "",
                },
            },
        )

    def test_emit_skill_update_available(self) -> None:
        config = client.Config(
            api_base_url="https://pc-api.pagepop.cn",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
            package_version="2026.04.21-r8",
            update_channel="prod",
            update_repo="pagepop/skills",
            update_release_tag="pagepop-skill-v2026.04.21-r8",
        )

        with mock.patch.object(
            client,
            "get_skill_update",
            return_value={
                "current_version": "2026.04.21-r8",
                "latest_version": "2026.04.22-r1",
                "min_supported_version": "2026.04.20-r6",
                "update_level": "recommended",
                "download_url": "https://github.com/example/release.zip",
                "sha256": "abc123",
                "repo": "pagepop/skills",
                "release_tag": "pagepop-skill-v2026.04.22-r1",
                "release_notes": ["Fix auth copy"],
                "message": "A newer PagePop skill is available.",
            },
        ), mock.patch.object(client, "emit_event") as emit_event:
            client.emit_skill_update_event(config)

        emit_event.assert_called_once()
        self.assertEqual(emit_event.call_args.args[0], "skill_update_available")
        self.assertEqual(emit_event.call_args.kwargs["latest_version"], "2026.04.22-r1")
        self.assertEqual(emit_event.call_args.kwargs["release_tag"], "pagepop-skill-v2026.04.22-r1")

    def test_emit_skill_update_skips_source_install(self) -> None:
        config = client.Config(
            api_base_url="https://pc-api.pagepop.cn",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
            package_version="source",
            update_channel="prod",
        )

        with mock.patch.object(client, "get_skill_update") as get_skill_update, mock.patch.object(
            client,
            "emit_event",
        ) as emit_event:
            client.emit_skill_update_event(config)

        get_skill_update.assert_not_called()
        emit_event.assert_not_called()

    def test_emit_skill_update_required_raises(self) -> None:
        config = client.Config(
            api_base_url="https://pc-api.pagepop.cn",
            skill_id="pagepop-skill",
            state_path=pathlib.Path("/tmp/pagepop-skill-test-state.json"),
            package_version="2026.04.18-r1",
            update_channel="prod",
        )

        with mock.patch.object(
            client,
            "get_skill_update",
            return_value={
                "current_version": "2026.04.18-r1",
                "latest_version": "2026.04.22-r1",
                "min_supported_version": "2026.04.20-r6",
                "update_level": "required",
                "download_url": "https://github.com/example/release.zip",
                "sha256": "abc123",
                "release_tag": "pagepop-skill-v2026.04.22-r1",
                "message": "This PagePop skill version is no longer supported.",
                "release_notes": ["Fix auth copy"],
            },
        ), mock.patch.object(client, "emit_event") as emit_event:
            with self.assertRaises(RuntimeError):
                client.emit_skill_update_event(config)

        emit_event.assert_called_once()
        self.assertEqual(emit_event.call_args.args[0], "skill_update_required")

    def test_main_returns_zero_for_authorization_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = pathlib.Path(temp_dir) / "skill-manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "skill_id": "pagepop-skill",
                        "package_version": "2099.01.01-r1",
                        "channel": "prod",
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(client, "skill_root_dir", return_value=pathlib.Path(temp_dir)), mock.patch.object(
                client, "run_auth_command", side_effect=client.AuthorizationPending("wait")
            ):
                self.assertEqual(client.main(["auth"]), 0)

    def test_access_key_reset_emits_user_friendly_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(state_path, client.SkillState(access_key="pp_sk_old"))
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                goal="hello",
                artifact_type="auto",
                link=[],
                conversation_id="",
                resume_conversation_id="",
                new_conversation=False,
            )

            with mock.patch.object(
                client,
                "ensure_authorized",
                side_effect=lambda cfg, state: client.SkillState(access_key="pp_sk_new", pending_run=state.pending_run),
            ), mock.patch.object(
                client,
                "submit_chat",
                side_effect=[
                    client.PagepopAPIError(
                        code=700000001,
                        message="skill key expired",
                        metadata={"openclaw_reason": "SKILL_KEY_EXPIRED"},
                    ),
                    {"conversation_id": "conv-1", "sse_max_offset": 0},
                ],
            ), mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-1", terminal_command="done", last_offset=2),
            ), mock.patch.object(client, "emit_event") as emit_event:
                self.assertEqual(client.run_stream_command(config, args), 0)

            access_key_reset_call = next(call for call in emit_event.call_args_list if call.args[0] == "access_key_reset")
            self.assertEqual(access_key_reset_call.kwargs["reason"], "SKILL_KEY_EXPIRED")
            self.assertEqual(
                access_key_reset_call.kwargs["message"],
                "Open the authorization page again and confirm once to continue.",
            )
            self.assertEqual(access_key_reset_call.kwargs["backend_message"], "skill key expired")
            self.assertEqual(access_key_reset_call.kwargs["action_text"], "Re-authorize PagePop")
            self.assertEqual(
                access_key_reset_call.kwargs["result_hint"],
                "After authorization, return to the source app and continue the current request.",
            )
            self.assertEqual(access_key_reset_call.kwargs["is_reauth"], True)

    def test_stream_reuses_active_conversation_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(
                state_path,
                client.SkillState(
                    access_key="pp_sk_existing",
                    active_conversation_id="conv-prev",
                    active_conversation_updated_at="2026-04-22T10:00:00Z",
                    saved_conversations=[
                        client.SavedConversation(
                            conversation_id="conv-prev",
                            label="布偶猫入门指南",
                            last_goal="先生成一版布偶猫入门指南",
                            artifact_type="rednote",
                            last_activity_at="2026-04-22T10:00:00Z",
                        )
                    ],
                ),
            )
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                goal="继续帮我优化一下文案",
                artifact_type="auto",
                link=[],
                conversation_id="",
                resume_conversation_id="",
                new_conversation=False,
            )

            with mock.patch.object(client, "emit_skill_update_event"), mock.patch.object(
                client,
                "submit_chat",
                return_value={"conversation_id": "conv-prev", "sse_max_offset": 0},
            ) as submit_chat, mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-prev", terminal_command="done", last_offset=3),
            ), mock.patch.object(client, "emit_event") as emit_event:
                self.assertEqual(client.run_stream_command(config, args), 0)

            submit_chat.assert_called_once()
            self.assertEqual(submit_chat.call_args.kwargs["conversation_id"], "conv-prev")
            context_call = next(call for call in emit_event.call_args_list if call.args[0] == "chat_context")
            self.assertEqual(context_call.kwargs["mode"], "continue")
            self.assertEqual(context_call.kwargs["conversation_id"], "conv-prev")
            self.assertEqual(context_call.kwargs["label"], "布偶猫入门指南")
            next_state = client.load_state(state_path)
            self.assertEqual(next_state.active_conversation_id, "conv-prev")
            self.assertIsNone(next_state.pending_run)
            self.assertEqual(next_state.saved_conversations[0].conversation_id, "conv-prev")

    def test_stream_new_conversation_resets_active_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(
                state_path,
                client.SkillState(
                    access_key="pp_sk_existing",
                    active_conversation_id="conv-prev",
                    active_conversation_updated_at="2026-04-22T10:00:00Z",
                    saved_conversations=[
                        client.SavedConversation(
                            conversation_id="conv-prev",
                            label="布偶猫入门指南",
                            last_goal="先生成一版布偶猫入门指南",
                            artifact_type="rednote",
                            last_activity_at="2026-04-22T10:00:00Z",
                        )
                    ],
                ),
            )
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                goal="我们重新开始一个全新的主题",
                artifact_type="auto",
                link=[],
                conversation_id="",
                resume_conversation_id="",
                new_conversation=True,
            )

            with mock.patch.object(client, "emit_skill_update_event"), mock.patch.object(
                client,
                "submit_chat",
                return_value={"conversation_id": "conv-new", "sse_max_offset": 0},
            ) as submit_chat, mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-new", terminal_command="done", last_offset=2),
            ), mock.patch.object(client, "emit_event") as emit_event:
                self.assertEqual(client.run_stream_command(config, args), 0)

            submit_chat.assert_called_once()
            self.assertEqual(submit_chat.call_args.kwargs["conversation_id"], "")
            context_call = next(call for call in emit_event.call_args_list if call.args[0] == "chat_context")
            self.assertEqual(context_call.kwargs["mode"], "new")
            next_state = client.load_state(state_path)
            self.assertEqual(next_state.active_conversation_id, "conv-new")
            self.assertIsNone(next_state.pending_run)
            self.assertEqual(next_state.saved_conversations[0].conversation_id, "conv-new")

    def test_stream_uses_chat_sse_max_offset_even_when_local_cursor_is_larger(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(
                state_path,
                client.SkillState(
                    access_key="pp_sk_existing",
                    active_conversation_id="conv-prev",
                    active_conversation_updated_at="2026-04-22T10:00:00Z",
                    conversation_streams={
                        "conv-prev": client.ConversationStreamState(cursor_offset=100, last_done_offset=100),
                    },
                ),
            )
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                goal="继续生成一版",
                artifact_type="auto",
                link=[],
                conversation_id="",
                resume_conversation_id="",
                new_conversation=False,
            )

            with mock.patch.object(client, "emit_skill_update_event"), mock.patch.object(
                client,
                "submit_chat",
                return_value={"conversation_id": "conv-prev", "sse_max_offset": 1},
            ), mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-prev", terminal_command="done", last_offset=4),
            ) as stream_sse_events, mock.patch.object(client, "emit_event"):
                self.assertEqual(client.run_stream_command(config, args), 0)

            self.assertEqual(stream_sse_events.call_args.kwargs["offset"], 1)
            next_state = client.load_state(state_path)
            self.assertEqual(next_state.conversation_streams["conv-prev"].cursor_offset, 4)
            self.assertEqual(next_state.conversation_streams["conv-prev"].last_done_offset, 4)

    def test_resume_stream_uses_active_conversation_without_submit_chat(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(
                state_path,
                client.SkillState(
                    access_key="pp_sk_existing",
                    pending_run=client.PendingRun(
                        goal="生成一篇小红书，内容是奶牛猫，带3张图",
                        artifact_type="auto",
                        conversation_id="conv-prev",
                    ),
                    active_conversation_id="conv-prev",
                    active_conversation_updated_at="2026-04-22T10:00:00Z",
                    saved_conversations=[
                        client.SavedConversation(
                            conversation_id="conv-prev",
                            label="奶牛猫小红书",
                            last_goal="生成一篇小红书，内容是奶牛猫，带3张图",
                            artifact_type="rednote",
                            last_activity_at="2026-04-22T10:00:00Z",
                        )
                    ],
                ),
            )
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                conversation_id="",
                resume_conversation_id="",
                offset=5,
            )

            with mock.patch.object(client, "emit_skill_update_event"), mock.patch.object(
                client,
                "submit_chat",
            ) as submit_chat, mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-prev", terminal_command="done", last_offset=9),
            ) as stream_sse_events, mock.patch.object(client, "emit_event") as emit_event:
                self.assertEqual(client.run_resume_stream_command(config, args), 0)

            submit_chat.assert_not_called()
            stream_sse_events.assert_called_once()
            self.assertEqual(stream_sse_events.call_args.kwargs["conversation_id"], "conv-prev")
            self.assertEqual(stream_sse_events.call_args.kwargs["offset"], 5)
            context_call = next(call for call in emit_event.call_args_list if call.args[0] == "chat_context")
            self.assertEqual(context_call.kwargs["mode"], "continue")
            self.assertEqual(context_call.kwargs["conversation_id"], "conv-prev")
            resumed_call = next(call for call in emit_event.call_args_list if call.args[0] == "stream_resumed")
            self.assertEqual(resumed_call.kwargs["offset"], 5)
            self.assertEqual(resumed_call.kwargs["offset_source"], "explicit")
            next_state = client.load_state(state_path)
            self.assertEqual(next_state.active_conversation_id, "conv-prev")
            self.assertIsNotNone(next_state.pending_run)
            assert next_state.pending_run is not None
            self.assertEqual(next_state.pending_run.goal, "生成一篇小红书，内容是奶牛猫，带3张图")
            self.assertEqual(next_state.conversation_streams["conv-prev"].cursor_offset, 9)
            self.assertEqual(next_state.conversation_streams["conv-prev"].last_done_offset, 9)

    def test_resume_stream_uses_explicit_conversation_without_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(state_path, client.SkillState(access_key="pp_sk_existing"))
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                conversation_id="conv-explicit",
                resume_conversation_id="",
                offset=0,
            )

            with mock.patch.object(client, "emit_skill_update_event"), mock.patch.object(
                client,
                "submit_chat",
            ) as submit_chat, mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-explicit", terminal_command="done", last_offset=2),
            ) as stream_sse_events, mock.patch.object(client, "emit_event"):
                self.assertEqual(client.run_resume_stream_command(config, args), 0)

            submit_chat.assert_not_called()
            self.assertEqual(stream_sse_events.call_args.kwargs["conversation_id"], "conv-explicit")

    def test_resume_stream_uses_saved_cursor_when_offset_is_not_provided(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(
                state_path,
                client.SkillState(
                    access_key="pp_sk_existing",
                    active_conversation_id="conv-prev",
                    conversation_streams={
                        "conv-prev": client.ConversationStreamState(cursor_offset=12, last_done_offset=10),
                    },
                ),
            )
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                conversation_id="",
                resume_conversation_id="",
                offset=None,
            )

            with mock.patch.object(client, "emit_skill_update_event"), mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-prev", terminal_command="done", last_offset=15),
            ) as stream_sse_events, mock.patch.object(client, "emit_event") as emit_event:
                self.assertEqual(client.run_resume_stream_command(config, args), 0)

            self.assertEqual(stream_sse_events.call_args.kwargs["offset"], 12)
            resumed_call = next(call for call in emit_event.call_args_list if call.args[0] == "stream_resumed")
            self.assertEqual(resumed_call.kwargs["offset_source"], "state")
            next_state = client.load_state(state_path)
            self.assertEqual(next_state.conversation_streams["conv-prev"].cursor_offset, 15)
            self.assertEqual(next_state.conversation_streams["conv-prev"].last_done_offset, 15)

    def test_resume_stream_explicit_offset_can_reset_saved_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(
                state_path,
                client.SkillState(
                    access_key="pp_sk_existing",
                    active_conversation_id="conv-prev",
                    conversation_streams={
                        "conv-prev": client.ConversationStreamState(cursor_offset=100, last_done_offset=100),
                    },
                ),
            )
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                conversation_id="",
                resume_conversation_id="",
                offset=1,
            )

            with mock.patch.object(client, "emit_skill_update_event"), mock.patch.object(
                client,
                "stream_sse_events",
                return_value=client.StreamResult(conversation_id="conv-prev", terminal_command="done", last_offset=3),
            ) as stream_sse_events, mock.patch.object(client, "emit_event"):
                self.assertEqual(client.run_resume_stream_command(config, args), 0)

            self.assertEqual(stream_sse_events.call_args.kwargs["offset"], 1)
            next_state = client.load_state(state_path)
            self.assertEqual(next_state.conversation_streams["conv-prev"].cursor_offset, 3)
            self.assertEqual(next_state.conversation_streams["conv-prev"].last_done_offset, 3)

    def test_resume_stream_requires_conversation_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(state_path, client.SkillState(access_key="pp_sk_existing"))
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            args = SimpleNamespace(
                conversation_id="",
                resume_conversation_id="",
                offset=0,
            )

            with mock.patch.object(client, "emit_skill_update_event"), self.assertRaisesRegex(
                RuntimeError,
                "conversation_id is required",
            ):
                client.run_resume_stream_command(config, args)

    def test_parser_supports_resume_stream_command(self) -> None:
        args = client.build_parser().parse_args(
            ["resume-stream", "--conversation-id", "conv-1", "--offset", "7"]
        )

        self.assertEqual(args.command, "resume-stream")
        self.assertEqual(args.conversation_id, "conv-1")
        self.assertEqual(args.offset, 7)

    def test_run_conversations_command_prints_saved_conversations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            client.save_state(
                state_path,
                client.SkillState(
                    access_key="pp_sk_existing",
                    active_conversation_id="conv-prev",
                    active_conversation_updated_at="2026-04-22T10:00:00Z",
                    saved_conversations=[
                        client.SavedConversation(
                            conversation_id="conv-prev",
                            label="布偶猫入门指南",
                            last_goal="先生成一版布偶猫入门指南",
                            artifact_type="rednote",
                            last_activity_at="2026-04-22T10:00:00Z",
                        ),
                        client.SavedConversation(
                            conversation_id="conv-old",
                            label="露营装备推荐",
                            last_goal="做一版露营装备推荐",
                            artifact_type="rednote",
                            last_activity_at="2026-04-21T09:00:00Z",
                        ),
                    ],
                    conversation_streams={
                        "conv-prev": client.ConversationStreamState(cursor_offset=12, last_done_offset=10),
                    },
                ),
            )
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )
            with mock.patch.object(client, "emit_record") as emit_record:
                self.assertEqual(client.run_conversations_command(config), 0)

            emit_record.assert_called_once()
            payload = emit_record.call_args.args[0]
            self.assertEqual(payload["kind"], "conversation_history")
            self.assertEqual(payload["active_conversation_id"], "conv-prev")
            self.assertEqual(payload["items"][0]["conversation_id"], "conv-prev")
            self.assertEqual(payload["items"][0]["sse_cursor_offset"], 12)
            self.assertEqual(payload["items"][0]["last_done_offset"], 10)
            self.assertEqual(payload["items"][1]["label"], "露营装备推荐")

    def test_summarize_progress_event_for_heartbeat_control_done(self) -> None:
        done_record = client.summarize_progress_event(
            "control",
            {"conversation_id": "conv-1", "cmd": "done"},
        )
        assert done_record is not None
        self.assertEqual(done_record["kind"], "progress_update")
        self.assertEqual(done_record["stage"], "completed")
        self.assertEqual(done_record["summary"], "PagePop finished streaming all events.")

    def test_build_artifact_summary_from_finish_work_slides(self) -> None:
        summary = client.build_artifact_summary(
            {
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "type": "tool_call",
                "status": "begin",
                "name": "finish_work",
                "data": {
                    "type": "slides",
                    "title": "Quarterly review deck",
                    "data": {
                        "outline_id": "outline-1",
                        "version": 2,
                        "slides": [
                            {"image_id": "img-1", "image_url": "https://example.com/slide-1.png"},
                            {"image_id": "img-2", "image_url": "https://example.com/slide-2.png"},
                        ],
                    },
                },
            }
        )
        assert summary is not None
        self.assertEqual(summary["artifact_type"], "slide")
        self.assertEqual(summary["artifact_id"], "outline-1")
        self.assertEqual(summary["title"], "Quarterly review deck")
        self.assertEqual(summary["current_version"], 2)
        self.assertEqual(
            summary["urls"],
            ["https://example.com/slide-1.png", "https://example.com/slide-2.png"],
        )
        self.assertFalse(summary["ready"])

    def test_merge_artifact_summary_preserves_begin_data_for_ready_event(self) -> None:
        begin_summary = {
            "source": "finish_work",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
            "artifact_id": "outline-1",
            "artifact_type": "slide",
            "scope_id": "",
            "status": "begin",
            "title": "Quarterly review deck",
            "text_content": "",
            "text_preview": "",
            "current_version": 2,
            "page_count": 1,
            "urls": ["https://example.com/slide-1.png"],
            "ready": False,
        }
        done_summary = {
            "source": "finish_work",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
            "artifact_id": "",
            "artifact_type": "slide",
            "scope_id": "",
            "status": "done",
            "title": "",
            "text_content": "",
            "text_preview": "",
            "current_version": None,
            "page_count": None,
            "urls": [],
            "ready": True,
        }
        merged = client.merge_artifact_summary(begin_summary, done_summary)
        self.assertEqual(merged["artifact_id"], "outline-1")
        self.assertEqual(merged["title"], "Quarterly review deck")
        self.assertEqual(merged["urls"], ["https://example.com/slide-1.png"])
        self.assertTrue(merged["ready"])

    def test_build_pagepop_project_url_matches_api_environment(self) -> None:
        self.assertEqual(
            client.build_pagepop_project_url("https://pc-api.pagepop.cn", "conv-1"),
            "https://www.pagepop.cn/project?cid=conv-1",
        )
        self.assertEqual(
            client.build_pagepop_project_url("https://pc-api.pagepop.ai", "conv-1"),
            "https://www.pagepop.ai/project?cid=conv-1",
        )
        self.assertEqual(
            client.build_pagepop_project_url("http://127.0.0.1:10086", "conv-1"),
            "http://127.0.0.1:11073/project?cid=conv-1",
        )

    def test_resolve_api_base_url_uses_region_for_production_domains(self) -> None:
        self.assertEqual(
            client.resolve_api_base_url("", region="CN", timezone=""),
            "https://pc-api.pagepop.cn",
        )
        self.assertEqual(
            client.resolve_api_base_url("", region="US", timezone=""),
            "https://pc-api.pagepop.ai",
        )
        self.assertEqual(
            client.resolve_api_base_url("", region="", timezone="Asia/Shanghai"),
            "https://pc-api.pagepop.cn",
        )
        self.assertEqual(
            client.resolve_api_base_url("", region="", timezone="America/Los_Angeles"),
            "https://pc-api.pagepop.ai",
        )
        self.assertEqual(
            client.resolve_api_base_url("", region="", timezone=""),
            "https://pc-api.pagepop.ai",
        )
        self.assertEqual(
            client.resolve_api_base_url("https://custom.example.test/", region="US", timezone=""),
            "https://custom.example.test",
        )

    def test_build_artifact_delivery_uses_generic_presentation_shape(self) -> None:
        delivery = client.build_artifact_delivery(
            {
                "source": "finish_work",
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "artifact_id": "artifact-1",
                "artifact_type": "rednote",
                "scope_id": "",
                "status": "done",
                "title": "Ragdoll Cat Guide",
                "text_content": "Ragdoll cats are gentle, beautiful, and friendly for first-time cat owners.",
                "text_preview": "Ragdoll cats are gentle, beautiful, and friendly for first-time cat owners.",
                "current_version": 3,
                "page_count": 3,
                "urls": [
                    "https://example.com/export.json",
                    "https://example.com/cover-1.png",
                    "https://example.com/cover-2.png",
                ],
                "ready": True,
            },
            api_base_url="https://pc-api.pagepop.cn",
            latest_text_message="",
            suggestions=[
                "Help me change the color palette",
                "Add one more page about pricing",
                "Use a cuter font style",
            ],
        )
        self.assertEqual(delivery["kind"], "artifact_delivery")
        self.assertEqual(delivery["artifact"]["id"], "artifact-1")
        self.assertEqual(delivery["artifact"]["type"], "rednote")
        self.assertEqual(delivery["artifact"]["pages"], 3)
        self.assertEqual(
            delivery["artifact"]["pagepop_project_url"],
            "https://www.pagepop.cn/project?cid=conv-1",
        )
        self.assertEqual(
            delivery["presentation"]["headline"],
            'Generated "Ragdoll Cat Guide"',
        )
        self.assertEqual(
            delivery["presentation"]["subtitle"],
            "Rednote Post · 3 pages",
        )
        self.assertEqual(
            delivery["presentation"]["preview_images"],
            ["https://example.com/cover-1.png", "https://example.com/cover-2.png"],
        )
        self.assertEqual(
            delivery["presentation"]["actions"][0],
            "Help me change the color palette",
        )
        self.assertEqual(
            delivery["presentation"]["resources"][0],
            {
                "label": "Open in PagePop",
                "url": "https://www.pagepop.cn/project?cid=conv-1",
            },
        )
        self.assertTrue(
            delivery["presentation"]["fallback_text"].startswith('Generated "Ragdoll Cat Guide"')
        )
        self.assertIn(
            "Open in PagePop for the full rendered view: https://www.pagepop.cn/project?cid=conv-1",
            delivery["presentation"]["fallback_text"],
        )
        self.assertEqual(delivery["target"]["preferred_channel"], "")
        self.assertIn("slack", delivery["channel_presentations"])
        self.assertIn("feishu", delivery["channel_presentations"])

    def test_build_artifact_delivery_includes_channel_presentations(self) -> None:
        delivery = client.build_artifact_delivery(
            {
                "source": "finish_work",
                "conversation_id": "conv-1",
                "message_id": "msg-1",
                "artifact_id": "artifact-1",
                "artifact_type": "slides",
                "status": "done",
                "title": "Launch Plan",
                "text_content": "封面: <https://example.com/gpt_image2/a_b.png>",
                "text_preview": "封面: <https://example.com/gpt_image2/a_b.png>",
                "page_count": 5,
                "urls": [
                    "https://example.com/gpt_image2/a_b.png",
                    "https://example.com/slide-1.png",
                    "https://example.com/export_file.pdf",
                ],
                "ready": True,
            },
            api_base_url="https://pc-api.pagepop.cn",
            latest_text_message="",
            suggestions=["Use https://example.com/a_b as reference"],
            source_app="slack",
            image_attachments=[
                {
                    "label": "封面",
                    "source_url": "https://example.com/gpt_image2/a_b.png",
                    "local_path": "/tmp/pagepop/image-1.png",
                    "mime_type": "image/png",
                    "send_as": "image_message",
                }
            ],
        )

        self.assertEqual(delivery["target"]["source_app"], "slack")
        self.assertEqual(delivery["channel_presentations"]["preferred"], "slack")
        self.assertIn("已随图片消息发送", delivery["artifact"]["display_text"])
        self.assertNotIn("gpt_image2/a_b.png", delivery["artifact"]["display_text"])
        self.assertEqual(delivery["attachments"]["images"][0]["local_path"], "/tmp/pagepop/image-1.png")

        slack = delivery["channel_presentations"]["slack"]
        self.assertEqual(slack["format"], "slack_block_kit")
        self.assertEqual(slack["blocks"][0]["type"], "header")
        self.assertEqual(slack["blocks"][0]["text"]["text"], 'Generated "Launch Plan"')
        self.assertTrue(any(block["type"] == "image" for block in slack["blocks"]))
        slack_buttons = [
            element
            for block in slack["blocks"]
            if block["type"] == "actions"
            for element in block["elements"]
        ]
        self.assertEqual(slack_buttons[0]["url"], "https://www.pagepop.cn/project?cid=conv-1")

        feishu = delivery["channel_presentations"]["feishu"]
        self.assertEqual(feishu["format"], "feishu_interactive_card")
        self.assertIn("已随图片消息发送", feishu["plain_text"])
        self.assertNotIn("gpt_image2/a_b.png", feishu["plain_text"])
        self.assertIn("export%5Ffile.pdf", feishu["plain_text"])
        self.assertEqual(feishu["media"]["local_image_messages"][0]["path"], "/tmp/pagepop/image-1.png")
        self.assertTrue(feishu["media"]["image_message_required"])
        self.assertTrue(feishu["card"]["config"]["wide_screen_mode"])
        self.assertEqual(feishu["card"]["header"]["title"]["content"], 'Generated "Launch Plan"')
        self.assertEqual(
            feishu["media"]["preview_image_urls"],
            ["https://example.com/gpt_image2/a_b.png", "https://example.com/slide-1.png"],
        )
        self.assertTrue(feishu["media"]["image_upload_required"])
        feishu_buttons = [
            action
            for element in feishu["card"]["elements"]
            if element.get("tag") == "action"
            for action in element["actions"]
        ]
        self.assertEqual(feishu_buttons[1]["url"], "https://example.com/export%5Ffile.pdf")
        feishu_text = "\n".join(
            element["text"]["content"]
            for element in feishu["card"]["elements"]
            if element.get("tag") == "div"
        )
        self.assertIn("https://example.com/a%5Fb", feishu_text)

    def test_feishu_safe_text_urls_encodes_underscores_in_bare_urls(self) -> None:
        self.assertEqual(
            client.feishu_safe_text_urls("Open https://example.com/a_b?x=y_z now"),
            "Open https://example.com/a%5Fb?x=y%5Fz now",
        )

    def test_download_image_attachment_writes_local_file(self) -> None:
        class FakeImageResponse:
            headers = {"Content-Type": "image/png"}

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

            def read(self, _size: int) -> bytes:
                return b"fake-png"

        with tempfile.TemporaryDirectory() as tmpdir:
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=pathlib.Path(tmpdir) / "state.json",
                artifact_dir=pathlib.Path(tmpdir) / ".pagepop-artifacts",
            )

            with mock.patch.object(client.urllib.request, "urlopen", return_value=FakeImageResponse()):
                attachment = client.download_image_attachment(
                    config,
                    conversation_id="conv-1",
                    url="https://example.com/path/a_b.png",
                    index=1,
                )

            self.assertEqual(attachment["label"], "封面")
            self.assertEqual(attachment["mime_type"], "image/png")
            self.assertEqual(pathlib.Path(attachment["local_path"]).read_bytes(), b"fake-png")

    def test_unwrap_base_response_success(self) -> None:
        raw = json.dumps({"code": 1000, "data": {"conversation_id": "conv-1"}}).encode("utf-8")
        self.assertEqual(client.unwrap_base_response(raw)["conversation_id"], "conv-1")

    def test_unwrap_base_response_error(self) -> None:
        raw = json.dumps(
            {
                "code": 700000001,
                "message": "illegal request",
                "reason": "ILLEGAL_REQUEST",
                "metadata": {"openclaw_reason": "SKILL_KEY_EXPIRED"},
            }
        ).encode("utf-8")
        with self.assertRaises(client.PagepopAPIError) as ctx:
            client.unwrap_base_response(raw)
        self.assertEqual(ctx.exception.openclaw_reason, "SKILL_KEY_EXPIRED")
        self.assertTrue(ctx.exception.should_reset_access_key())

    def test_http_json_reports_non_json_http_error_preview(self) -> None:
        error = urllib.error.HTTPError(
            url="https://example.com/v2/chat",
            code=500,
            msg="Internal Server Error",
            hdrs={"Content-Type": "text/plain"},
            fp=io.BytesIO(b"upstream exploded"),
        )
        with mock.patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(client.PagepopHTTPError) as ctx:
                client.http_json(
                    "POST",
                    "https://example.com/v2/chat",
                    payload={"goal": "hello"},
                )

        exc = ctx.exception
        self.assertEqual(exc.status, 500)
        self.assertEqual(exc.url, "https://example.com/v2/chat")
        self.assertEqual(exc.content_type, "text/plain")
        self.assertEqual(exc.response_preview, "upstream exploded")
        self.assertIn("Expecting value", exc.parse_error)
        record = exc.to_record()
        self.assertEqual(record["code"], "http_error")
        self.assertEqual(record["http_status"], 500)
        self.assertEqual(record["response_preview"], "upstream exploded")

    def test_parse_sse_events(self) -> None:
        lines = [
            "event: message\n",
            "data: {\"offset\":1,\"text\":\"hello\"}\n",
            "\n",
            "event: control\n",
            "data: {\"cmd\":\"done\",\"offset\":2}\n",
            "\n",
        ]
        events = list(client.parse_sse_events(lines))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event, "message")
        self.assertEqual(events[0].data["offset"], 1)
        self.assertEqual(events[1].event, "control")
        self.assertEqual(events[1].data["cmd"], "done")

    def test_stream_sse_events_updates_cursor_to_smaller_remote_offset(self) -> None:
        class FakeSseResponse:
            def __init__(self) -> None:
                self.headers = {"Content-Type": "text/event-stream"}
                self._lines = [
                    b"event: message\n",
                    b"data: {\"conversation_id\":\"conv-1\",\"data\":\"hello\",\"offset\":1}\n",
                    b"\n",
                    b"event: control\n",
                    b"data: {\"conversation_id\":\"conv-1\",\"cmd\":\"done\",\"offset\":2}\n",
                    b"\n",
                ]

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

            def __iter__(self):
                return iter(self._lines)

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            state = client.SkillState(
                access_key="pp_sk_existing",
                conversation_streams={
                    "conv-1": client.ConversationStreamState(cursor_offset=100, last_done_offset=100),
                },
            )
            client.save_state(state_path, state)
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
            )

            with mock.patch.object(client.urllib.request, "urlopen", return_value=FakeSseResponse()), mock.patch.object(
                client,
                "emit_event",
            ), mock.patch.object(client, "emit_record"):
                result = client.stream_sse_events(config, state, conversation_id="conv-1", offset=100)

            self.assertEqual(result.last_offset, 2)
            next_state = client.load_state(state_path)
            self.assertEqual(next_state.conversation_streams["conv-1"].cursor_offset, 2)
            self.assertEqual(next_state.conversation_streams["conv-1"].last_done_offset, 2)

    def test_stream_sse_events_persists_smaller_offset_before_stream_failure(self) -> None:
        class FakeFailingSseResponse:
            headers = {"Content-Type": "text/event-stream"}

            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _tb) -> None:
                return None

            def __iter__(self):
                yield b"event: message\n"
                yield b"data: {\"conversation_id\":\"conv-1\",\"data\":\"hello\",\"offset\":1}\n"
                yield b"\n"
                raise RuntimeError("connection dropped")

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            state = client.SkillState(
                access_key="pp_sk_existing",
                conversation_streams={
                    "conv-1": client.ConversationStreamState(cursor_offset=100, last_done_offset=100),
                },
            )
            client.save_state(state_path, state)
            config = client.Config(
                api_base_url="https://pc-api.pagepop.cn",
                skill_id="pagepop-skill",
                state_path=state_path,
                max_stream_reconnects=0,
            )

            with mock.patch.object(
                client.urllib.request,
                "urlopen",
                return_value=FakeFailingSseResponse(),
            ), mock.patch.object(client, "emit_event"), mock.patch.object(client, "emit_record"):
                with self.assertRaises(RuntimeError):
                    client.stream_sse_events(config, state, conversation_id="conv-1", offset=100)

            next_state = client.load_state(state_path)
            self.assertEqual(next_state.conversation_streams["conv-1"].cursor_offset, 1)
            self.assertEqual(next_state.conversation_streams["conv-1"].last_done_offset, 100)

    def test_save_state_does_not_reuse_fixed_tmp_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            fixed_tmp_path = state_path.with_suffix(state_path.suffix + ".tmp")
            fixed_tmp_path.write_text("occupied", encoding="utf-8")

            client.save_state(state_path, client.SkillState(access_key="pp_sk_existing"))

            self.assertTrue(state_path.exists())
            self.assertEqual(fixed_tmp_path.read_text(encoding="utf-8"), "occupied")
            self.assertEqual(list(pathlib.Path(tmpdir).glob(".state.json.*.tmp")), [])

    def test_state_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = pathlib.Path(tmpdir) / "state.json"
            state = client.SkillState(
                access_key="pp_sk_example_secret",
                pending_run=client.PendingRun(goal="hello", artifact_type="auto", links=["https://example.com"]),
                active_conversation_id="conv-1",
                active_conversation_updated_at="2026-04-22T10:00:00Z",
                saved_conversations=[
                    client.SavedConversation(
                        conversation_id="conv-1",
                        label="Hello deck",
                        last_goal="hello",
                        artifact_type="slide",
                        last_activity_at="2026-04-22T10:00:00Z",
                    )
                ],
                conversation_streams={
                    "conv-1": client.ConversationStreamState(
                        cursor_offset=12,
                        last_done_offset=10,
                        last_terminal_command="done",
                        updated_at="2026-04-22T10:01:00Z",
                    )
                },
            )
            client.save_state(state_path, state)
            loaded = client.load_state(state_path)
            self.assertEqual(loaded.access_key, "pp_sk_example_secret")
            self.assertIsNotNone(loaded.pending_run)
            assert loaded.pending_run is not None
            self.assertEqual(loaded.pending_run.goal, "hello")
            self.assertEqual(loaded.pending_run.links, ["https://example.com"])
            self.assertEqual(loaded.active_conversation_id, "conv-1")
            self.assertEqual(loaded.saved_conversations[0].label, "Hello deck")
            self.assertEqual(loaded.conversation_streams["conv-1"].cursor_offset, 12)
            self.assertEqual(loaded.conversation_streams["conv-1"].last_done_offset, 10)
            self.assertEqual(loaded.conversation_streams["conv-1"].last_terminal_command, "done")


if __name__ == "__main__":
    unittest.main()
