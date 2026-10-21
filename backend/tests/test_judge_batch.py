import asyncio
import unittest
from types import SimpleNamespace

from app.services.generation_service import _judge_batch


def draft(index):
    return SimpleNamespace(
        title=f"用例 {index}",
        precondition="",
        steps="[]",
        expected_result="结果",
        judge_score=None,
        judge_issues="",
    )


def judgement(index):
    return {
        "index": index,
        "overall": 4.3,
        "relevance": 5,
        "executability": 4,
        "verifiability": 4,
    }


class PartialRegistry:
    def __init__(self):
        self.batch_sizes = []

    async def run(self, name, inputs, context):
        cases = inputs["cases"]
        self.batch_sizes.append(len(cases))
        if len(cases) == 5:
            return {"judgements": [judgement(i) for i in (0, 2, 4)]}
        return {"judgements": [judgement(i) for i in range(len(cases))]}


class FailedRegistry(PartialRegistry):
    async def run(self, name, inputs, context):
        cases = inputs["cases"]
        self.batch_sizes.append(len(cases))
        if len(cases) == 5:
            raise RuntimeError("temporary judge failure")
        return {"judgements": [judgement(i) for i in range(len(cases))]}


class JudgeBatchTests(unittest.TestCase):
    def test_retries_only_missing_scores(self):
        cases = [draft(i) for i in range(5)]
        registry = PartialRegistry()

        asyncio.run(_judge_batch(registry, {"feature": "测试"}, cases, None, 1))

        self.assertEqual(registry.batch_sizes, [5, 1, 1])
        self.assertTrue(all(case.judge_score == 4.3 for case in cases))
        self.assertTrue(all(case.judge_issues for case in cases))

    def test_splits_failed_batch(self):
        cases = [draft(i) for i in range(5)]
        registry = FailedRegistry()

        with self.assertLogs("app.services.generation_service", level="WARNING"):
            asyncio.run(_judge_batch(registry, {"feature": "测试"}, cases, None, 1))

        self.assertEqual(registry.batch_sizes, [5, 3, 2])
        self.assertTrue(all(case.judge_score == 4.3 for case in cases))


if __name__ == "__main__":
    unittest.main()
