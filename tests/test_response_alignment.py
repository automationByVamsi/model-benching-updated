"""Response Alignment wiring - metric registry and scoring.

No LLM calls: a fake council records what it was given and returns fixed
per-judge, per-row scores in the same shape as Pegasus LLMCouncil.
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from modelbench.evaluation.metrics import METRICS, selected_metrics
from modelbench.evaluation.scoring import score_one, score_run

RUN_CONFIG = SimpleNamespace(judge_temperature=0.0)


class FakeCouncil:
    """Stands in for LLMCouncil: records every evaluate() call."""

    def __init__(self, row_scores):
        self.row_scores = row_scores  # {"judge-name": [score per row]}
        self.calls = []

    def evaluate(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        first_judge = next(iter(self.row_scores.values()))
        return {"score": float(np.mean(first_judge)), "council_row_scores": self.row_scores}


def golden_set(with_background=False):
    data = pd.DataFrame({"question": ["How to add a support need?", "How to close an account?"]})
    if with_background:
        data["background"] = ["Give step-by-step instructions.", None]
    return data


OUTPUTS = [{"answer": "Step 1 ..."}, {"answer": "Go to Accounts ..."}]


# --- metric registry ---------------------------------------------------------

def test_default_selection_is_unchanged():
    # The existing model-swap / prompt-swap runs must score exactly what they did before.
    assert list(selected_metrics(None)) == ["hallucination", "answer_correctness", "toxicity", "bias"]


def test_response_alignment_runs_only_when_named():
    assert "response_alignment" not in selected_metrics(None)
    assert list(selected_metrics(("response_alignment",))) == ["response_alignment"]
    assert list(selected_metrics(("response_alignment", "hallucination"))) == [
        "response_alignment",
        "hallucination",
    ]


def test_response_alignment_spec():
    spec = METRICS["response_alignment"]
    assert spec["role"] == "primary"        # gated by Gate 2 when selected
    assert spec["larger_is_better"] is True  # 0-1 alignment, higher is better
    assert spec["kind"] == "agentic"
    assert spec["delta"] == 0.05             # comparison.py reads spec["delta"]
    assert "critical_threshold" not in spec  # not a safety metric


def test_unknown_metric_still_rejected():
    with pytest.raises(KeyError, match="unknown metrics"):
        selected_metrics(("not_a_metric",))


# --- score_run (batched, used in Step 3) ---------------------------------------

def test_score_run_sends_query_and_agent_response():
    council = FakeCouncil({"judge-a": [0.8, 0.4], "judge-b": [0.6, 0.2]})

    scores = score_run({"response_alignment": council}, golden_set(), OUTPUTS, RUN_CONFIG)

    args, kwargs = council.calls[0]
    frame = args[0]  # DataFrame passed positionally, not as text=
    assert list(frame.columns) == ["query", "agent_response"]
    assert frame["query"].tolist() == golden_set()["question"].tolist()
    assert frame["agent_response"].tolist() == ["Step 1 ...", "Go to Accounts ..."]
    assert kwargs == {"temperature": 0.0}
    # One score per input: median across judges, row by row.
    np.testing.assert_allclose(scores["response_alignment"], [0.7, 0.3])


def test_score_run_sends_background_when_golden_set_has_it():
    council = FakeCouncil({"judge-a": [0.9, 0.9], "judge-b": [0.9, 0.9]})

    score_run({"response_alignment": council}, golden_set(with_background=True), OUTPUTS, RUN_CONFIG)

    frame = council.calls[0][0][0]
    assert frame["background"].tolist() == ["Give step-by-step instructions.", ""]


# --- score_one (single row, used for judge variance in Step 4) ------------------

def test_score_one_sends_one_row_frame():
    council = FakeCouncil({"judge-a": [0.7], "judge-b": [0.7]})

    score = score_one(council, "response_alignment", golden_set().iloc[0], OUTPUTS[0], RUN_CONFIG)

    frame = council.calls[0][0][0]
    assert frame.to_dict("records") == [
        {"query": "How to add a support need?", "agent_response": "Step 1 ..."}
    ]
    assert isinstance(score, float)
    assert score == pytest.approx(0.7)


def test_score_one_blank_background_becomes_empty_string():
    council = FakeCouncil({"judge-a": [0.7]})

    score_one(council, "response_alignment", golden_set(with_background=True).iloc[1], OUTPUTS[1], RUN_CONFIG)

    frame = council.calls[0][0][0]
    assert frame["background"].tolist() == [""]


# --- existing metrics must be called exactly as before ------------------------

def test_existing_hallucination_call_is_unchanged():
    council = FakeCouncil({"judge-a": [0.1, 0.2]})

    score_run({"hallucination": council}, golden_set(), OUTPUTS, RUN_CONFIG)

    args, kwargs = council.calls[0]
    assert args == ()                                  # still text=... keyword call
    assert list(kwargs["text"].columns) == ["query", "text", "context"]
