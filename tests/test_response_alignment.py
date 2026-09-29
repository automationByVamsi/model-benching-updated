"""Response Alignment - metric registry and live scoring.

Registry tests run with every ``pytest`` (no model calls).

Live tests call the REAL Pegasus council through Cortex, so they only run when
asked for and when the Cortex credentials are available:

    MODELBENCH_LIVE=1 uv run --with pytest python -m pytest tests/test_response_alignment.py -v
"""

import os

import numpy as np
import pandas as pd
import pytest
from dotenv import load_dotenv

from modelbench.evaluation.metrics import METRICS, selected_metrics

load_dotenv()

LIVE = (
    os.getenv("MODELBENCH_LIVE") == "1"
    and bool(os.getenv("CORTEX_V2_API_KEY"))
    and bool(os.getenv("CORTEX_V2_URL"))
)
live = pytest.mark.skipif(
    not LIVE, reason="live judge calls: set MODELBENCH_LIVE=1 and the CORTEX_V2_* variables"
)

QUESTION = "How to add a support need?"
ALIGNED_ANSWER = (
    "Open the customer's profile, go to the 'Support Needs' tab and select 'Amend'. "
    "On the 'Customer support needs' screen select 'Add', fill in the details "
    "(F1 lists the available support needs), then select 'OK' to confirm."
)
OFF_TOPIC_ANSWER = "Our branches are open from 9am to 5pm on weekdays."


# --- metric registry (no model calls) -------------------------------------------

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


# --- live scoring with the real council (Cortex judges) ------------------------

@pytest.fixture(scope="module")
def council_and_config():
    from modelbench.evaluation.scoring import build_council
    from modelbench.schemas.run_config import RunConfig

    config = RunConfig()
    return build_council("response_alignment", config), config


@live
def test_live_score_one_ranks_aligned_above_off_topic(council_and_config):
    from modelbench.evaluation.scoring import score_one

    council, config = council_and_config
    row = pd.Series({"question": QUESTION})

    aligned = score_one(council, "response_alignment", row, {"answer": ALIGNED_ANSWER}, config)
    off_topic = score_one(council, "response_alignment", row, {"answer": OFF_TOPIC_ANSWER}, config)

    print(f"\naligned={aligned:.3f}  off_topic={off_topic:.3f}")
    assert 0.0 <= off_topic <= 1.0 and 0.0 <= aligned <= 1.0
    assert aligned > off_topic


@live
def test_live_score_run_gives_one_score_per_input(council_and_config):
    from modelbench.evaluation.scoring import score_run

    council, config = council_and_config
    data = pd.DataFrame({"question": [QUESTION, QUESTION]})
    outputs = [{"answer": ALIGNED_ANSWER}, {"answer": OFF_TOPIC_ANSWER}]

    scores = score_run({"response_alignment": council}, data, outputs, config)["response_alignment"]

    print(f"\nper-input scores={scores}")
    assert scores.shape == (2,)
    assert not np.isnan(scores).any()          # every judge scored every row
    assert ((scores >= 0.0) & (scores <= 1.0)).all()
    assert scores[0] > scores[1]
