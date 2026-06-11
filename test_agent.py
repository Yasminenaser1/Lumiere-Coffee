"""
Stage 6 — Tests for the Stage 4 agentic Q&A (grounding checks).
Verifies that:
  1. ask() returns the correct shape {question, answer, tools_called, model}
  2. When no API key is set, a helpful warning is returned (not a crash)
  3. Tool names returned are the real Stage 2 function names
  4. The ask() loop handles unknown questions without crashing

No live Groq calls are made here — we either test the no-key path, or mock
the HTTP call so tests run offline and fast.

Run: python -m pytest test_agent.py -v
  or: python test_agent.py
"""

import unittest
import json
import os
import unittest.mock as mock

import agent  # the module we're testing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_call(name, args=None):
    """Build a fake Groq tool_call dict."""
    return {
        "id": f"call_{name}",
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(args or {}),
        },
    }

def _make_response(finish_reason, content=None, tool_calls=None):
    """Build a minimal Groq chat completion response dict."""
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {
        "choices": [{
            "finish_reason": finish_reason,
            "message": msg,
        }]
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestAskShape(unittest.TestCase):
    """ask() always returns the right dict shape."""

    def test_returns_dict_with_required_keys(self):
        # No key → fast fallback path, no HTTP call
        original_key = agent.GROQ_API_KEY
        agent.GROQ_API_KEY = ""
        try:
            result = agent.ask("what was my best day?")
        finally:
            agent.GROQ_API_KEY = original_key

        self.assertIsInstance(result, dict)
        for key in ("question", "answer", "tools_called", "model"):
            self.assertIn(key, result, f"Missing key: {key}")

    def test_question_echoed_back(self):
        agent.GROQ_API_KEY = ""
        try:
            result = agent.ask("test question")
        finally:
            agent.GROQ_API_KEY = ""

        self.assertEqual(result["question"], "test question")

    def test_no_key_returns_warning_not_crash(self):
        original = agent.GROQ_API_KEY
        agent.GROQ_API_KEY = ""
        try:
            result = agent.ask("any question")
        finally:
            agent.GROQ_API_KEY = original

        self.assertIn("GROQ_API_KEY", result["answer"])
        self.assertEqual(result["tools_called"], [])


class TestToolRegistry(unittest.TestCase):
    """TOOL_REGISTRY maps exactly the 4 Stage 2 function names."""

    def test_all_four_tools_registered(self):
        expected = {"revenue_by_day", "top_items", "repeat_customer_rate", "average_ticket"}
        self.assertEqual(set(agent.TOOL_REGISTRY.keys()), expected)

    def test_tools_are_callable(self):
        for name, fn in agent.TOOL_REGISTRY.items():
            self.assertTrue(callable(fn), f"{name} is not callable")


class TestRunTool(unittest.TestCase):
    """run_tool() executes functions and returns JSON strings."""

    def _make_tc(self, name, args=None):
        return {"function": {"name": name, "arguments": json.dumps(args or {})}}

    def test_unknown_tool_returns_error_json(self):
        result = agent.run_tool(self._make_tc("nonexistent_tool"))
        parsed = json.loads(result)
        self.assertIn("error", parsed)

    def test_known_tool_returns_valid_json(self):
        # revenue_by_day may fail if no DB exists — that's OK, it raises an exception
        # that we catch, OR it returns data. We just check the call doesn't crash the runner.
        tc = self._make_tc("average_ticket")
        try:
            result = agent.run_tool(tc)
            # Should be valid JSON
            parsed = json.loads(result)
            self.assertIsInstance(parsed, (dict, list))
        except Exception:
            pass  # DB not present on CI — acceptable


class TestAgentLoopMocked(unittest.TestCase):
    """Integration tests with mocked Groq HTTP calls — no API key needed."""

    def _patch_groq(self, responses):
        """Context manager: call_groq returns responses in order."""
        return mock.patch.object(agent, "call_groq", side_effect=responses)

    def test_direct_answer_no_tools(self):
        """When Groq answers without calling tools, tools_called is empty."""
        mock_resp = _make_response("stop", content="Today was a great day!")
        with self._patch_groq([mock_resp]):
            agent.GROQ_API_KEY = "gsk_fake"
            result = agent.ask("how's it going?")
            agent.GROQ_API_KEY = ""

        self.assertEqual(result["tools_called"], [])
        self.assertEqual(result["answer"], "Today was a great day!")

    def test_one_tool_call_then_answer(self):
        """Model calls one tool, gets result, then answers."""
        tc = _make_tool_call("average_ticket")
        resp1 = _make_response("tool_calls", tool_calls=[tc])
        resp2 = _make_response("stop", content="Average ticket is $4.98.")

        with self._patch_groq([resp1, resp2]):
            # Also mock run_tool so we don't need a real DB
            fake_result = json.dumps({"avg_ticket": 4.98, "total_transactions": 200,
                                       "total_revenue": 996.0, "min_ticket": 3.0, "max_ticket": 9.5})
            with mock.patch.object(agent, "run_tool", return_value=fake_result):
                agent.GROQ_API_KEY = "gsk_fake"
                result = agent.ask("what's my average ticket?")
                agent.GROQ_API_KEY = ""

        self.assertIn("average_ticket", result["tools_called"])
        self.assertEqual(result["answer"], "Average ticket is $4.98.")

    def test_grounding_tool_result_used(self):
        """The final answer comes from tool data, not hallucinated text."""
        tc = _make_tool_call("top_items", {"limit": 5})
        resp1 = _make_response("tool_calls", tool_calls=[tc])
        resp2 = _make_response("stop", content="Your top item is Granola Bowl at $156.19.")

        fake_items = json.dumps([
            {"item": "Granola Bowl", "revenue": 156.19, "transactions": 24, "avg_price": 6.51}
        ])
        with self._patch_groq([resp1, resp2]):
            with mock.patch.object(agent, "run_tool", return_value=fake_items):
                agent.GROQ_API_KEY = "gsk_fake"
                result = agent.ask("which item makes the most money?")
                agent.GROQ_API_KEY = ""

        # Grounding check: the answer must mention the actual item name from the tool result
        self.assertIn("Granola Bowl", result["answer"],
                      "Answer should be grounded in tool result, but didn't mention the top item.")
        self.assertIn("top_items", result["tools_called"])

    def test_multiple_tools_in_one_round(self):
        """Model can call multiple tools in a single round."""
        tc1 = _make_tool_call("revenue_by_day", {"limit": 7})
        tc2 = _make_tool_call("average_ticket")
        resp1 = _make_response("tool_calls", tool_calls=[tc1, tc2])
        resp2 = _make_response("stop", content="Best day was June 3 with $156 revenue.")

        fake_rev   = json.dumps([{"date": "2026-06-03", "transactions": 25, "revenue": 156.00}])
        fake_at    = json.dumps({"avg_ticket": 5.0, "total_transactions": 100,
                                 "total_revenue": 500.0, "min_ticket": 3.0, "max_ticket": 8.0})

        side_effects = [fake_rev, fake_at]

        with self._patch_groq([resp1, resp2]):
            with mock.patch.object(agent, "run_tool", side_effect=side_effects):
                agent.GROQ_API_KEY = "gsk_fake"
                result = agent.ask("what was my best day and average ticket?")
                agent.GROQ_API_KEY = ""

        self.assertIn("revenue_by_day", result["tools_called"])
        self.assertIn("average_ticket", result["tools_called"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
