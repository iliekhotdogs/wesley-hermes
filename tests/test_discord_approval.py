import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        discord = types.ModuleType('tools.discord_tool')
        discord.DiscordAPIError = type('DiscordAPIError', (Exception,), {})
        discord._get_bot_token = Mock(return_value='test-token')
        discord._discord_request = Mock(return_value={'guild_id': '111111111111111111', 'id': '222222222222222222', 'type': 0})
        approval = types.ModuleType('tools.approval')
        approval.request_tool_approval = Mock(return_value={'approved': False})
        context = types.ModuleType('tools.approval_context')
        context._get_approval_mode = Mock(return_value='manual')
        self.discord, self.approval, self.context = discord, approval, context
        self.modules = patch.dict(sys.modules, {'tools': types.ModuleType('tools'), 'tools.discord_tool': discord, 'tools.approval': approval, 'tools.approval_context': context})
        self.modules.start(); self.addCleanup(self.modules.stop)
        self.env = patch.dict(os.environ, {'DISCORD_GUILD_ID': '111111111111111111'})
        self.env.start(); self.addCleanup(self.env.stop)
        spec = importlib.util.spec_from_file_location('channels_test', Path(__file__).resolve().parents[1] / 'extensions/discord-channel-management/__init__.py')
        self.plugin = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.plugin)

    def test_model_confirmation_does_not_authorize_deletion(self):
        result = json.loads(self.plugin._run({'action': 'delete', 'channel_id': '222222222222222222', 'confirm_delete': '222222222222222222'}))
        self.assertIn('Blocked', result['error'])
        self.discord._get_bot_token.assert_not_called()
        self.discord._discord_request.assert_not_called()

    def test_exact_human_gate_and_fresh_rule_per_attempt(self):
        self.approval.request_tool_approval.return_value = {'approved': True}
        args = {'action': 'delete', 'channel_id': '222222222222222222'}
        self.assertTrue(json.loads(self.plugin._run(args))['success'])
        first = self.approval.request_tool_approval.call_args.kwargs['rule_key']
        self.assertTrue(json.loads(self.plugin._run(args))['success'])
        self.assertNotEqual(first, self.approval.request_tool_approval.call_args.kwargs['rule_key'])
        self.assertIn('222222222222222222', self.approval.request_tool_approval.call_args.args[1])

    def test_off_policy_and_category_changes_fail_closed(self):
        self.context._get_approval_mode.return_value = 'off'
        result = json.loads(self.plugin._run({'action': 'edit', 'channel_id': '222222222222222222', 'parent_id': ''}))
        self.assertIn('Blocked', result['error'])
        self.discord._discord_request.assert_not_called()

    def test_approval_error_does_not_issue_http(self):
        self.approval.request_tool_approval.side_effect = TimeoutError()
        self.assertIn('error', json.loads(self.plugin._run({'action': 'delete', 'channel_id': '222222222222222222'})))
        self.discord._discord_request.assert_not_called()
