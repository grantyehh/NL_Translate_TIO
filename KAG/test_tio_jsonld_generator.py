import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "KAG" / "openspg-kag"))
sys.path.insert(0, str(ROOT / "KAG"))


class FakePrompt:
    def is_json_format(self):
        return True


class FakeLLM:
    def __init__(self):
        self.calls = []

    def invoke(self, variables, prompt, **kwargs):
        self.calls.append((variables, prompt, kwargs))
        return '{"@type": "Intent", "id": "intent-TC001"}'


class FakeTask:
    def __init__(self, task_context):
        self._task_context = task_context

    def get_task_context(self):
        return self._task_context


class FakeContext:
    variables_graph = {"nodes": []}

    def __init__(self, tasks):
        self._tasks = tasks

    def gen_task(self, group=False):
        return list(self._tasks)


class TestTioJsonldGenerator(unittest.TestCase):
    def test_prompt_parse_response_returns_jsonld_string_from_object(self):
        from example_project.solver.tio_jsonld_generator import TIOJsonldGeneratorPrompt

        prompt = TIOJsonldGeneratorPrompt.__new__(TIOJsonldGeneratorPrompt)
        result = prompt.parse_response({"@type": "Intent", "id": "intent-TC001"})

        parsed = json.loads(result)
        self.assertEqual(parsed["@type"], "Intent")
        self.assertEqual(parsed["id"], "intent-TC001")

    def test_generator_invokes_llm_with_case_few_shot_and_solver_context(self):
        from example_project.solver.tio_jsonld_generator import TIOJsonldGenerator

        llm = FakeLLM()
        generator = TIOJsonldGenerator(llm_client=llm, generated_prompt=FakePrompt())
        context = FakeContext(
            [
                FakeTask(
                    {
                        "name": "Retriever",
                        "task": "Find EVSLA latency terms",
                        "result": "evsla:latency, evsla:p95",
                        "thought": "matched ontology terms",
                    }
                )
            ]
        )

        result = generator.invoke(
            "確保星河銀行總部至所有分點之延遲低於50ms。",
            context,
            tc_id="TC001",
            few_shot_block="--- Example 1 ---",
        )

        self.assertEqual(result, '{"@type": "Intent", "id": "intent-TC001"}')
        self.assertEqual(len(llm.calls), 1)
        variables, prompt, kwargs = llm.calls[0]
        self.assertEqual(prompt.__class__, FakePrompt)
        self.assertEqual(variables["tc_id"], "TC001")
        self.assertIn("--- Example 1 ---", variables["few_shot_block"])
        self.assertIn("Find EVSLA latency terms", variables["content"])
        self.assertIn("evsla:latency", variables["content"])
        self.assertTrue(kwargs["with_json_parse"])


if __name__ == "__main__":
    unittest.main()
