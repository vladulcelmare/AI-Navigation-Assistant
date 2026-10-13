import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import httpx
from openai import APIConnectionError
from openai.types.responses import ResponseFunctionToolCall

from backend.integrations import openai_client
from backend.tool_calling import call_tool


def candidate(index, score, qid=1):
    return {"qid": qid, "route_index": index, "rank_score": score,
            "distance_km": 10 * index, "distance_min": 20 * index}


def response(*calls, text=""):
    return SimpleNamespace(output=list(calls), output_text=text)


def function_call(call_id="call_1", name="recommend_route", arguments="{}"):
    return ResponseFunctionToolCall(type="function_call", name=name,
                                    call_id=call_id, arguments=arguments)


@pytest.fixture
def setup_agent(monkeypatch):
    client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock()))
    monkeypatch.setattr(openai_client, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(openai_client.LLM_Agent,
                        "_LLM_Agent__filter_explicit_language", staticmethod(lambda text: False))
    tool = AsyncMock()
    monkeypatch.setattr(openai_client, "call_tool", tool)
    return openai_client.LLM_Agent(), client.responses.create, tool


def run(agent, trip_history=None):
    agent.trip_history = trip_history or []
    return asyncio.run(agent.generate_response([{"role": "user", "content": "Plan a route"}]))


def test_plain_chat_does_not_execute_tools(setup_agent):
    agent, create, tool = setup_agent
    create.return_value = response(text="Hello")
    assert run(agent) == "Hello"
    tool.assert_not_called()


@pytest.mark.parametrize("routes", [
    [[candidate(1, 0.9), candidate(2, 0.7)]],
    [[candidate(1, 0.9)]],
])
def test_clear_winner_needs_no_second_llm_call(setup_agent, routes):
    agent, create, tool = setup_agent
    create.return_value = response(function_call())
    tool.return_value = {"origin": "A", "destination": "B", "routes": routes}
    answer = run(agent, trip_history=[{"distance_km": 20}])
    assert answer[0][1][0]["distance_km"] == 10
    assert answer[0][1][0]["route_index"] == 1
    assert create.await_count == 1
    tool.assert_awaited_once_with("recommend_route", {}, None)


@pytest.mark.parametrize("second_score", [0.3, 0.35, 0.4])
def test_close_scores_and_exact_epsilon_complete_tool_roundtrip(setup_agent, second_score):
    agent, create, tool = setup_agent
    reasoning = SimpleNamespace(type="reasoning")
    create.side_effect = [
        response(reasoning, function_call()),
        response(text=json.dumps({"call_1:0": 2})),
    ]
    tool.return_value = {"origin": "A", "destination": "B", "routes": [
        [candidate(1, 0.4), candidate(2, second_score), candidate(3, 0.1)],
        [candidate(1, 0.9, qid=2), candidate(2, 0.5, qid=2)],
    ]}
    answer = run(agent, trip_history=[{"distance_km": 20}])
    assert [route["route_index"] for route in answer[0][1]] == [2, 1]
    assert sum(route["distance_km"] for route in answer[0][1]) == 30
    followup = create.call_args.kwargs
    assert followup["tool_choice"] == "none"
    assert followup["tools"] == []
    assert reasoning in followup["input"]
    output = next(item for item in followup["input"]
                  if isinstance(item, dict) and item.get("type") == "function_call_output")
    assert output["call_id"] == "call_1"
    segments = json.loads(output["output"])["segments"]
    assert [route["route_index"] for route in segments[0]["alternatives"]] == [1, 2]
    assert len(segments[1]["alternatives"]) == 1


def test_missing_history_uses_ranker_without_second_call(setup_agent):
    agent, create, tool = setup_agent
    create.return_value = response(function_call())
    tool.return_value = {"origin": "A", "destination": "B", "routes": [
        [candidate(1, 0.4), candidate(2, 0.35)]]}
    assert run(agent, trip_history=[])[0][1][0]["route_index"] == 1
    assert create.await_count == 1


def test_third_alternative_can_win_if_within_epsilon(setup_agent):
    agent, create, tool = setup_agent
    create.side_effect = [response(function_call()), response(text=json.dumps({"call_1:0": 3}))]
    tool.return_value = {"origin": "A", "destination": "B", "routes": [
        [candidate(1, 0.4), candidate(2, 0.35), candidate(3, 0.32)]]}
    assert run(agent, trip_history=[{"distance_km": 30}])[0][1][0]["route_index"] == 3


def test_tiebreak_network_failure_keeps_winner(setup_agent):
    agent, create, tool = setup_agent
    create.side_effect = [response(function_call()),
                          APIConnectionError(request=httpx.Request("POST", "https://example.test"))]
    tool.return_value = {"origin": "A", "destination": "B", "routes": [
        [candidate(1, 0.4), candidate(2, 0.35)]]}
    assert run(agent, trip_history=[{"distance_km": 20}])[0][1][0]["route_index"] == 1


@pytest.mark.parametrize("text", [
    "not JSON", '{}', '[]', 'null',
    '{"call_1:0": 3}', '{"unknown": 1}', '{"call_1:0": true}',
])
def test_invalid_tie_selection_falls_back(setup_agent, text):
    agent, create, tool = setup_agent
    create.side_effect = [response(function_call()), response(text=text)]
    tool.return_value = {"origin": "A", "destination": "B", "routes": [
        [candidate(1, 0.4), candidate(2, 0.35), candidate(3, 0.1)]]}
    assert run(agent, trip_history=[{"distance_km": 20}])[0][1][0]["route_index"] == 1


@pytest.mark.parametrize("arguments", ["invalid", "{}"])
def test_tool_errors_return_readable_message(setup_agent, arguments):
    agent, create, tool = setup_agent
    create.return_value = response(function_call(arguments=arguments))
    tool.side_effect = ValueError("provider error")
    answer = run(agent)
    assert isinstance(answer, str) and answer
    assert create.await_count == 1


def test_multiple_tool_calls_are_all_executed(setup_agent):
    agent, create, tool = setup_agent
    create.return_value = response(function_call("one"), function_call("two"))
    tool.return_value = {"origin": "A", "destination": "B", "routes": [[candidate(1, 1)]]}
    assert len(run(agent)) == 2
    assert tool.await_count == 2


@pytest.mark.parametrize("epsilon", [-0.1, float("nan"), float("inf")])
def test_invalid_epsilon_rejected(setup_agent, epsilon):
    with pytest.raises(ValueError):
        openai_client.LLM_Agent(route_difference_max_tolerance=epsilon)


def test_unknown_tool_is_rejected():
    with pytest.raises(ValueError, match="Unknown tool"):
        asyncio.run(call_tool("delete_trip", {}))


def test_invalid_arguments_do_not_reach_routing(monkeypatch):
    from backend import tool_calling
    routing = AsyncMock()
    monkeypatch.setattr(tool_calling, "recommend_route", routing)
    with pytest.raises(ValueError):
        asyncio.run(call_tool("recommend_route", {"origin_name": "A"}))
    routing.assert_not_called()


def test_valid_arguments_execute_async_route_function(monkeypatch):
    from backend import tool_calling
    routing = AsyncMock(return_value={"routes": []})
    monkeypatch.setattr(tool_calling, "recommend_route", routing)
    args = {"origin_name": "A", "destination_name": "B"}
    parameters = {"engine_type": "Electric",
            "avg_consumption": 18.5, "fuel_price": 1.7, "electricity_price": 0.3,
            "preferences": {"road_conditions": "mixed", "age_group": "adult",
                            "driver_type": "calm", "tolls": False}}
    assert asyncio.run(call_tool("recommend_route", args, {"parameters": parameters})) == {"routes": []}
    routing.assert_awaited_once_with(**args, **parameters)
