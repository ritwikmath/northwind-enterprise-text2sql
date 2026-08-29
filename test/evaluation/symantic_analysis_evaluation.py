from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from langchain.messages import HumanMessage

from agent import agent


def test_correctness():
    correctness_metric = GEval(
        name="Correctness",
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        criteria="Determine if the 'actual output' similar to 'expected output'. Main facts are available in 'actual output' even if few irrelevant simple english words are missing. The values of field is valid if they are semantically similar.",
        threshold=0.7
    )

    messages = [
        HumanMessage("Customer names who are from London")
    ]
    result = agent.invoke({"messages": messages})

    test_case = LLMTestCase(
        input="Customer names who are from London",
        actual_output=str(result["symantic_analysis"]),
        expected_output="{'intent': ['list individual records'], 'entities': ['customers'], 'fields': [{'name': 'customer names', 'type': 'dimension', 'aggregation': None}], 'filters': [{'entity': 'customers', 'field': 'location', 'operator': 'equals', 'value': 'London'}], 'grouping': [], 'time_range': None}"
    )
    assert_test(test_case, [correctness_metric])