from datetime import datetime
from unittest import TestCase

from mock import MagicMock

from blockwart.cmdline.apply import bw_apply, format_node_result
from blockwart.node import ApplyResult


class FakeNode(object):
    name = "nodename"

    def apply(self, interactive=False, workers=4, force=False):
        assert interactive
        result = ApplyResult(self, ())
        result.start = datetime(2013, 8, 10, 0, 0)
        result.end = datetime(2013, 8, 10, 0, 1)
        return result


class ApplyTest(TestCase):
    """
    Tests blockwart.cmdline.apply.bw_apply.
    """
    def test_interactive(self):
        node1 = FakeNode()
        repo = MagicMock()
        repo.get_node.return_value = node1
        args = MagicMock()
        args.force = False
        args.interactive = True
        args.item_workers = 4
        args.target = "node1"
        output = list(bw_apply(repo, args))
        self.assertTrue(output[0].startswith("nodename: run started at "))
        self.assertTrue(output[1].startswith("nodename: run completed after "))
        self.assertTrue(output[1].endswith("(0 OK, 0 fixed, 0 skipped, 0 failed)\n"))
        self.assertEqual(len(output), 2)


class FormatNodeItemResultTest(TestCase):
    """
    Tests blockwart.cmdline.apply.format_node_item_result.
    """
    def test_values(self):
        result = MagicMock()
        result.correct = 0
        result.fixed = 1
        result.skipped = 2
        result.failed = 3
        self.assertEqual(
            format_node_result(result),
            "0 OK, 1 fixed, 2 skipped, 3 failed",
        )

    def test_zero(self):
        result = MagicMock()
        result.correct = 0
        result.fixed = 0
        result.skipped = 0
        result.failed = 0
        self.assertEqual(
            format_node_result(result),
            "0 OK, 0 fixed, 0 skipped, 0 failed",
        )
