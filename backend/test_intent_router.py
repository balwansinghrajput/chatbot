import unittest

from routers.stream import _parse_tool_intent


class ToolIntentTests(unittest.TestCase):
    def test_live_score_uses_web_without_images(self):
        decision = _parse_tool_intent(
            "What is the live cricket score?",
            "web_search, image_search",
            False,
        )
        self.assertTrue(decision["web_search"])
        self.assertFalse(decision["image_search"])

    def test_classifier_explanation_cannot_activate_tools(self):
        decision = _parse_tool_intent(
            "Who won the match today?",
            "I considered web_search and image_search; use web_search.",
            False,
        )
        self.assertTrue(decision["web_search"])
        self.assertFalse(decision["image_search"])

    def test_explicit_image_request_can_use_image_search(self):
        decision = _parse_tool_intent(
            "Show me photos of the Taj Mahal",
            "image_search",
            False,
        )
        self.assertTrue(decision["image_search"])


if __name__ == "__main__":
    unittest.main()
