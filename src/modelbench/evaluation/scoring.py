import numpy as np
import pandas as pd
import os
import logging
from tqdm import tqdm
from pegasus.metrics import LLMCouncil
from pegasus.utils import get_model
from modelbench.evaluation.metrics import METRICS
from modelbench.schemas.run_config import RunConfig

from functools import wraps
from time import perf_counter

logger = logging.getLogger(__name__)


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        result = func(*args, **kwargs)
        logger.info("%s took %.2fs", func.__name__, perf_counter() - start)
        return result
    return wrapper


def build_council(metric_name: str, run_config: RunConfig) -> LLMCouncil:
    """
    One council per metric. Median aggregation: robust to a single odd judge.
    """
    metric = METRICS[metric_name]
    api_key = os.getenv("CORTEX_V2_API_KEY", "").strip()
    base_url = os.getenv("CORTEX_V2_URL", "").strip()
    if not api_key or not base_url:
        raise RuntimeError(
            "CORTEX_V2_API_KEY and CORTEX_V2_URL must be set in .env to build"
            "Pegasus judge models via the cortex_v2 adapter."
        )
    judges = [
        get_model(
            "cortex_v2",
            model_type="llm",
            model_name=m,
            api_key=api_key,
            base_url=base_url,
        )
        for m in run_config.judge_models
    ]
    return LLMCouncil(
        metric_cls=metric["cls"],
        llms=judges,
        metric_kwargs=metric["metric_kwargs"],
        score_aggregation="median",  # not "mean"
        explanation_aggregation="vote",
        lower_is_better=not metric["larger_is_better"],
        max_workers=8,
        name=f"{metric_name}_council",
    )


def agentic_frame(
    questions: list[str],
    answers: list[str],
    backgrounds: list[str] | None = None,
) -> pd.DataFrame:
    """Input frame for Pegasus agentic metrics (e.g. ResponseAlignment).

    Required columns: ``query`` and ``agent_response``. ``background`` (the
    intended behaviour / requirements) is optional and only sent when the
    golden set has a ``background`` column.
    """
    frame = pd.DataFrame({"query": questions, "agent_response": answers})
    if backgrounds is not None:
        frame["background"] = backgrounds
    return frame


def score_one(
    council: LLMCouncil,
    metric_name: str,
    row: pd.Series,
    output: dict,
    run_config: RunConfig
) -> float:
    """Score a single input/output pair -> one float.

    The paired test needs ONE score per input, so we evaluate per row.
    If your Pegasus build returns per-row scores from a batched evaluate(),
    use that instead - it is the same numbers and far fewer calls.
    """
    kind = METRICS[metric_name]["kind"]
    if kind == "rag":
        frame = pd.DataFrame([{
            "question": row["question"],
            "answer": output["answer"],
            "retrieved_contexts": output["retrieved_contexts"],
            "reference_answer": row.get("reference_answer", ""),
        }])
        result = council.evaluate(frame, temperature=run_config.judge_temperature)
    elif kind == "hallucination":
        result = council.evaluate(
            query=row["question"],
            text=output["answer"],
            context=output.get("retrieved_contexts", []),
            temperature=run_config.judge_temperature,
        )
    elif kind == "agentic":
        backgrounds = None
        if "background" in row.index:
            backgrounds = ["" if pd.isna(row["background"]) else row["background"]]
        frame = agentic_frame([row["question"]], [output["answer"]], backgrounds)
        result = council.evaluate(frame, temperature=run_config.judge_temperature)
    else:  # safety metrics take a plain string
        result = council.evaluate(output["answer"], temperature=run_config.judge_temperature)
    return float(result["score"])


@timer
def score_run(
    councils: dict[str, LLMCouncil],
    data: pd.DataFrame,
    outputs: list[dict],
    run_config: RunConfig,
    desc: str = "Scoring",
) -> dict[str, np.ndarray]:

    questions = data["question"].tolist()
    answers = [output["answer"] for output in outputs]
    contexts = [output.get("retrieved_contexts", []) for output in outputs]

    scores = {}
    for metric_name, council in tqdm(
        councils.items(),
        desc=desc,
        leave=False,
    ):
        if metric_name == "answer_correctness":

            frame = pd.DataFrame(
                {
                    "question": questions,
                    "answer": answers,
                    "retrieved_contexts": contexts,
                    "reference_answer": (
                        data["reference_answer"].fillna("").tolist()
                        if "reference_answer" in data.columns
                        else [""] * len(data)
                    ),
                }
            )
            result = council.evaluate(frame, temperature=run_config.judge_temperature)
            judge_scores = np.asarray(list(result["council_row_scores"].values()), dtype=float)
            scores[metric_name] = np.median(judge_scores, axis=0)
            # print(json.dumps(result, indent=4))

        elif METRICS[metric_name]["kind"] == "agentic":
            backgrounds = (
                data["background"].fillna("").tolist()
                if "background" in data.columns
                else None
            )
            frame = agentic_frame(questions, answers, backgrounds)
            result = council.evaluate(frame, temperature=run_config.judge_temperature)
            judge_scores = np.asarray(list(result["council_row_scores"].values()), dtype=float)
            scores[metric_name] = np.median(judge_scores, axis=0)

        else:  # We need an if statement because council.evaluate hits
            frame = pd.DataFrame(
                {
                    "query": questions,
                    "text": answers,
                    "context": contexts,
                }
            )
            result = council.evaluate(text=frame, temperature=run_config.judge_temperature)
            judge_scores = np.asarray(list(result["council_row_scores"].values()), dtype=float)
            scores[metric_name] = np.median(judge_scores, axis=0)

    return scores
