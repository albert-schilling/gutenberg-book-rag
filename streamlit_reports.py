"""A dashboard for the evaluation reports: compare runs and find the questions to work on.

Run it from the project root with:

    uv run streamlit run streamlit_reports.py
"""

import pandas as pd
import streamlit as st

from book_rag.evaluation.compare import (
    LOWER_IS_BETTER,
    changed_settings,
    compare_questions,
    flat_metrics,
    list_reports,
    load_report,
    metrics_frame,
    question_frame,
    report_label,
)
from book_rag.evaluation.report import REPORT_DIR

RETRIEVAL_METRICS = ["context_recall", "hit_rate", "mrr", "context_precision"]
GENERATION_METRICS = ["answer_correctness", "faithfulness", "abstention_accuracy", "answered_when_answerable",
                      "abstained_when_unanswerable", "empty_answer_rate"]
KPIS = {"context_recall": "Context recall", "mrr": "MRR", "answer_correctness": "Answer correctness",
        "faithfulness": "Faithfulness", "abstention_accuracy": "Abstention accuracy"}

st.set_page_config(page_title="Evaluation reports", page_icon=":material/monitoring:", layout="wide")
st.title("Evaluation reports")

paths = list_reports()
if not paths:
    st.info("No reports yet. Create one with `uv run book-rag-eval`.", icon=":material/info:")
    st.stop()

reports = {path.stem: load_report(path) for path in paths}
names = list(reports)  # oldest first
labels = {name: report_label(report) for name, report in reports.items()}

with st.sidebar:
    selected = st.selectbox("Report", names[::-1], format_func=labels.get, help="Newest first")
    others = [name for name in names[::-1] if name != selected]
    older = [name for name in names[: names.index(selected)]]
    compare_with = st.selectbox(
        "Compare with", [None, *others], index=1 + others.index(older[-1]) if older else 0,
        format_func=lambda name: "Nothing" if name is None else labels[name],
    )
    st.caption(f"{len(names)} reports in `{REPORT_DIR.name}/`")

report = reports[selected]
baseline = reports[compare_with] if compare_with else None
scores = flat_metrics(report)
baseline_scores = flat_metrics(baseline) if baseline else {}

# --- Key metrics -------------------------------------------------------------------------------
st.subheader("Key metrics")
with st.container(horizontal=True):
    for metric, name in KPIS.items():
        if scores.get(metric) is None:
            continue
        delta = None
        if baseline_scores.get(metric) is not None:
            delta = scores[metric] - baseline_scores[metric]
        st.metric(
            name, f"{scores[metric]:.2f}",
            delta=None if delta is None else round(delta, 2),
            delta_color="inverse" if metric in LOWER_IS_BETTER else "normal",
            border=True,
        )

# --- What changed between the two runs ----------------------------------------------------------
if baseline:
    changes = changed_settings(baseline, report)
    with st.container(border=True):
        st.markdown("**Settings that differ between the two reports**")
        if changes.empty:
            st.caption("None: the same settings, so differences come from randomness of the language models.")
        else:
            st.dataframe(changes, hide_index=True, width="stretch", alt="Settings that differ between the reports")
        if baseline["metadata"]["dataset_sha1"] != report["metadata"]["dataset_sha1"]:
            st.warning("The question set changed, so the scores are not directly comparable.", icon=":material/warning:")

# --- Comparison charts ---------------------------------------------------------------------------
shown = {labels[selected]: selected, **({labels[compare_with]: compare_with} if baseline else {})}
frame = metrics_frame({label: reports[name] for label, name in shown.items()})
left, right = st.columns(2)
for column, title, metrics in [(left, "Retrieval", RETRIEVAL_METRICS), (right, "Answers", GENERATION_METRICS)]:
    with column, st.container(border=True):
        st.markdown(f"**{title}**")
        rows = frame.reindex([m for m in metrics if m in frame.index]).dropna(how="all")
        if rows.empty:
            st.caption("Not in this report (it ran with --retrieval-only).")
        else:
            st.bar_chart(rows, horizontal=True, stack=False, x_label="Score (0 to 1)", y_label="",
                         alt=f"{title} metrics of the selected reports")

# --- History ---------------------------------------------------------------------------------------
if len(names) > 1:
    with st.container(border=True):
        st.markdown("**All reports over time**")
        history = metrics_frame(reports).T
        history.index = [report_label(reports[name]) for name in history.index]
        trend = [m for m in ["context_recall", "mrr", "answer_correctness", "faithfulness"] if m in history.columns]
        st.line_chart(history[trend], x_label="Report", y_label="Score (0 to 1)", alt="Key metrics of all reports over time")
        with st.expander("Table"):
            st.dataframe(history, alt="All metrics of all reports")

# --- Questions -------------------------------------------------------------------------------------
st.subheader("Questions")
questions = question_frame(report)
if baseline:
    diff = compare_questions(baseline, report)
    questions = questions.join(diff["change"])
column_config = {
    "question": st.column_config.TextColumn("Question", width="large"),
    "recall": st.column_config.ProgressColumn("Recall", min_value=0, max_value=1, format="%.2f"),
    "faithfulness": st.column_config.ProgressColumn("Faithful", min_value=0, max_value=1, format="%.2f"),
    "correctness": st.column_config.ProgressColumn("Correct", min_value=0, max_value=1, format="%.2f"),
    "rank": st.column_config.NumberColumn("Rank", format="%d", help="Rank of the first passage with evidence"),
}
st.dataframe(questions.drop(columns=["answerable"]), column_config=column_config, width="stretch",
             alt="Scores for every question of the selected report")

# --- One question in detail ------------------------------------------------------------------------
st.subheader("One question in detail")
problem_first = sorted(questions.index, key=lambda i: (questions.loc[i, "correctness"] == 1, i))
question_id = st.selectbox("Question", problem_first, format_func=lambda i: f"{i}: {questions.loc[i, 'question']}")
result = next(r for r in report["results"] if r["id"] == question_id)
generation, retrieval = result["generation"], result["retrieval"]

if result["reference_answer"]:
    st.markdown(f"**Reference answer:** {result['reference_answer']}")
else:
    st.markdown("**The book cannot answer this question.**")
if generation:
    st.markdown(f"**Answer of the system:** {result['answer'] or '(empty)'}")
    if generation["correctness_reason"]:
        st.caption(f"Judge ({generation['correctness']:.1f}): {generation['correctness_reason']}")
    if generation["claims"]:
        with st.expander("Claims of the answer checked against the passages"):
            st.dataframe(pd.DataFrame(generation["claims"]), hide_index=True, width="stretch", alt="Claims and whether the passages support them")

st.markdown("**Retrieved passages**")
if retrieval:
    st.caption("Evidence the retrieval should find: " + " · ".join(
        f"{':green[found]' if found else ':red[missing]'} “{phrase}”"
        for phrase, found in zip(result["evidence"], retrieval["evidence_found"])
    ))
for rank, passage in enumerate(result["retrieved"], 1):
    with st.expander(f"{rank}. position {passage['start_index']:,} · similarity {passage['similarity']:.2f}"):
        st.write(passage["preview"] + " …")
