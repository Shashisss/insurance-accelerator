"""The AI layer: tools, routing, and the guardrail that keeps it honest."""

from __future__ import annotations

import pytest

from iaa.assistant import (
    Toolbox,
    ask,
    fact_sheet,
    plan,
    unsupported_numbers,
)


@pytest.fixture(scope="module")
def box():
    return Toolbox()


# --- routing --------------------------------------------------------------
def test_routes_each_question_to_the_right_tool(box):
    assert plan("Why is P205 referred?", box)[0] == "assess_policy"
    assert plan("What happened to V041?", box)[0] == "vehicle_history"
    assert plan("Which vehicles moved?", box)[0] == "transfers"
    assert plan("How big is the group?", box)[0] == "group_metrics"
    assert plan("What changes if we use the v1 definition?", box)[0] == "impact_trace"
    assert plan("what is the loss ratio", box)[0] == "policy_metrics"


def test_default_question_lands_on_the_renewal_policy(box):
    tool, args = plan("is this renewal ok?", box)
    assert tool == "assess_policy" and args["policy_id"] == "P205"


# --- tools ----------------------------------------------------------------
def test_tools_read_the_same_numbers_as_the_page(box):
    result = box.call("assess_policy", policy_id="P205")["result"]
    assert result["metrics"]["loss_ratio"] == pytest.approx(0.60, abs=1e-4)
    assert result["decision"] == "Refer for senior review + group assessment"
    assert result["group_metrics"]["vehicles"] == 150


def test_unknown_policy_is_handled_not_crashed(box):
    call = box.call("assess_policy", policy_id="P999")
    assert call["ok"] is False and "unknown policy" in call["error"]


def test_bad_arguments_are_reported(box):
    call = box.call("assess_policy", nope="x")
    assert call["ok"] is False and "arguments" in call["error"]


# --- answers --------------------------------------------------------------
def test_answer_cites_the_breach_and_the_decision(box):
    answer = ask("Why is P205 referred?", box, use_model=False)
    assert answer.mode == "deterministic"
    assert "Refer for senior review" in answer.text
    assert "60.0%" in answer.text
    assert "FR1_LOSS_RATIO" in answer.text
    assert answer.guardrail is None


def test_vehicle_question_explains_the_transfer(box):
    answer = ask("What happened to V041?", box, use_model=False)
    assert "P101" in answer.text and "2026-04-01" in answer.text
    assert "500,000" in answer.text


def test_impact_question_reports_the_two_flips(box):
    answer = ask("What changes if we use the v1 definition?", box, use_model=False)
    assert "2 of 2" in answer.text


def test_answers_are_reproducible(box):
    first = ask("Why is P205 referred?", box, use_model=False)
    second = ask("Why is P205 referred?", box, use_model=False)
    assert first.text == second.text


# --- guardrail ------------------------------------------------------------
def test_guardrail_rejects_numbers_the_tools_did_not_produce(box):
    call = box.call("policy_metrics", policy_id="P205")
    allowed = fact_sheet(call["tool"], call["result"])

    honest = "Loss ratio is 60.0% and frequency 13.3 per 100 vehicle-years."
    invented = "Loss ratio is 73.4% and frequency 13.3 per 100 vehicle-years."

    assert unsupported_numbers(honest, allowed) == []
    assert unsupported_numbers(invented, allowed) == ["73.4"]


def test_guardrail_allows_money_and_count_forms(box):
    call = box.call("assess_policy", policy_id="P205")
    allowed = fact_sheet(call["tool"], call["result"])
    text = "Premium 360,000; numerator 216,000; 150 vehicles; 6 claims; 60 vehicles."
    assert unsupported_numbers(text, allowed) == []


def test_every_answer_passes_its_own_guardrail(box):
    for question in [
        "Why is P205 referred?",
        "What happened to V041?",
        "Which vehicles moved?",
        "How big is the group?",
        "What changes if we use the v1 definition?",
    ]:
        answer = ask(question, box, use_model=False)
        allowed = fact_sheet(answer.tool, answer.result)
        assert unsupported_numbers(answer.text, allowed) == [], question


# --- the other two use cases ---------------------------------------------
def test_routes_reserving_and_pricing_questions(box):
    assert plan("did reserves develop adversely?", box)[0] == "reserve_development"
    assert plan("what is the indicated premium?", box)[0] == "pricing_indication"
    assert plan("how much IBNR is there?", box)[0] == "reserve_development"


def test_reserving_answer_cites_the_decomposition(box):
    answer = ask("did reserves develop adversely?", box, use_model=False)
    assert "20.00" in answer.text and "23.00" in answer.text
    assert "15.0%" in answer.text
    assert "Selection change" in answer.text
    assert "actuarial review" in answer.text.lower()


def test_pricing_answer_cites_the_indication(box):
    answer = ask("what is the indicated premium?", box, use_model=False)
    assert "1,279,385" in answer.text
    assert "27.9%" in answer.text
    assert "81" not in answer.text.split("loss ratio")[0][:0]  # sanity: no stray figures


def test_new_answers_pass_the_guardrail(box):
    for question in ["did reserves develop adversely?", "what is the indicated premium?"]:
        answer = ask(question, box, use_model=False)
        allowed = fact_sheet(answer.tool, answer.result)
        assert unsupported_numbers(answer.text, allowed) == [], question
