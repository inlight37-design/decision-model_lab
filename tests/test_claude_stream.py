"""A plausible final answer cannot hide drift in Claude's actual tool surface."""
import json
import unittest

from core import adapters
from test_core_adapters import fake


class StreamTests(unittest.TestCase):
    def events(self):
        return [{'type': 'system', 'subtype': 'init', 'tools': ['Read'],
                 'permissionMode': 'dontAsk', 'mcp_servers': []},
                {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Read'}]}},
                {'type': 'result', 'is_error': False, 'result': 'bounded answer',
                 'modelUsage': {'claude-test': {}}, 'permission_denials': [{'tool_name': 'Read'}],
                 'usage': {'input_tokens': 30, 'output_tokens': 10}}]

    def interpret(self, events):
        return adapters.interpret('claude-code', fake('\n'.join(json.dumps(e) for e in events)),
                                  requested_model='claude-test', claude_tools=('Read',))

    def test_complete_stream_preserves_usage_model_tool_count_and_denial(self):
        outcome = self.interpret(self.events())
        self.assertTrue(outcome.ok)
        self.assertTrue(outcome.model_match)
        self.assertEqual(outcome.usage['input_tokens'], 30)
        self.assertEqual((outcome.tool_events, outcome.permission_denials), (1, 1))

    def test_incomplete_duplicate_and_trailing_streams_are_rejected(self):
        events = self.events()
        for bad in (events[1:], events[:-1], events + [events[-1]],
                    [events[0]] + events, events + [{'type': 'system'}], [events[-1]], [3]):
            with self.subTest(events=bad):
                self.assertFalse(self.interpret(bad).ok)

    def test_changed_surface_or_unoffered_tool_cannot_be_accepted(self):
        for field, value in (('tools', ['Read', 'Bash']), ('tools', None),
                             ('permissionMode', 'bypassPermissions'), ('mcp_servers', [{}])):
            events = self.events()
            events[0][field] = value
            self.assertEqual(self.interpret(events).status, 'permission_mismatch')
        events = self.events()
        events[1]['message']['content'][0]['name'] = 'Write'
        self.assertEqual(self.interpret(events).status, 'permission_mismatch')


if __name__ == '__main__':
    unittest.main()
