"""
AI Analysis Assistant.
Translates natural language analytical questions into safe, predefined analytical operations.
Never executes arbitrary AI-generated Python code.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import json
import re
import pandas as pd
import numpy as np
from ai.ai_client import AIClient
from analytics.statistics import StatisticsEngine


@dataclass
class AnalysisIntent:
    operation: str  # descriptive_stats, group_aggregation, top_performers, bottom_performers, correlation, trend_analysis, filter_records
    group_col: Optional[str] = None
    metric_col: Optional[str] = None
    agg_func: str = "sum"
    n: int = 5
    date_col: Optional[str] = None
    period: str = "ME"
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    sort_by: Optional[str] = None
    ascending: bool = False
    explanation: str = ""


class AnalysisAssistant:
    """Interprets analytical requests safely into predefined execution plans."""

    def __init__(self, ai_client: Optional[AIClient] = None):
        self.ai_client = ai_client or AIClient()

    @staticmethod
    def _match_column(term: str, columns: List[str]) -> Optional[str]:
        """Finds closest matching column name for a given word or term."""
        term_clean = re.sub(r"[_\W]+", "", term.lower())
        if not term_clean:
            return None

        # Exact match check
        for c in columns:
            if term_clean == re.sub(r"[_\W]+", "", c.lower()):
                return c

        # Substring match
        for c in columns:
            clean_c = re.sub(r"[_\W]+", "", c.lower())
            if term_clean in clean_c or clean_c in term_clean:
                return c

        return None

    @classmethod
    def parse_intent_rule_based(cls, query: str, df: pd.DataFrame) -> AnalysisIntent:
        """Heuristic parser for natural language analytics when AI API is unavailable."""
        q = query.lower()
        cols = list(df.columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
        date_cols = [c for c in cols if "date" in str(c).lower() or pd.api.types.is_datetime64_any_dtype(df[c])]

        # 1. Multi-Condition Filtering (e.g. "performance is low but salary is high")
        if ("low" in q or "poor" in q or "below" in q or "<" in q) and ("high" in q or "great" in q or "above" in q or ">" in q):
            conditions = []
            sort_target = None

            # Detect low metric
            low_matches = re.findall(r"(\w+)\s+(?:is\s+)?(?:low|poor|below)", q) or re.findall(r"(?:low|poor|below)\s+(\w+)", q)
            for m in low_matches:
                col = cls._match_column(m, cols)
                if col:
                    conditions.append({"column": col, "operator": "low"})

            # Detect high metric
            high_matches = re.findall(r"(\w+)\s+(?:is\s+)?(?:high|great|above)", q) or re.findall(r"(?:high|great|above)\s+(\w+)", q)
            for m in high_matches:
                col = cls._match_column(m, cols)
                if col:
                    conditions.append({"column": col, "operator": "high"})
                    sort_target = col

            if conditions:
                desc = " and ".join(f"'{c['column']}' is {c['operator']}" for c in conditions)
                return AnalysisIntent(
                    operation="filter_records",
                    conditions=conditions,
                    sort_by=sort_target or conditions[0]["column"],
                    ascending=False,
                    explanation=f"Filtered records where {desc}.",
                )

        # 2. Simple numeric comparison (e.g. "salary > 80000" or "salary above 80000")
        comp_match = re.search(r"(\w+)\s*(>|<|>=|<=|above|greater than|below|less than)\s*([0-9]+(?:\.[0-9]+)?)", q)
        if comp_match:
            c_name, op_text, val_text = comp_match.groups()
            matched_col = cls._match_column(c_name, numeric_cols)
            if matched_col:
                op_map = {
                    ">": ">", "above": ">", "greater than": ">",
                    ">=": ">=",
                    "<": "<", "below": "<", "less than": "<",
                    "<=": "<="
                }
                op = op_map.get(op_text, ">")
                return AnalysisIntent(
                    operation="filter_records",
                    conditions=[{"column": matched_col, "operator": op, "value": float(val_text)}],
                    sort_by=matched_col,
                    ascending=False,
                    explanation=f"Filtered records where {matched_col} {op} {val_text}.",
                )

        # 3. Categorical value filter (e.g. "in engineering", "department is HR", "north region")
        for cat_c in cat_cols:
            unique_vals = [str(v) for v in df[cat_c].dropna().unique()]
            for val in unique_vals:
                if val.lower() in q:
                    return AnalysisIntent(
                        operation="filter_records",
                        conditions=[{"column": cat_c, "operator": "==", "value": val}],
                        explanation=f"Filtered records where {cat_c} is '{val}'.",
                    )

        # 4. Top performers check
        if "top" in q or "best" in q or "highest" in q:
            n_match = re.search(r"\btop\s+(\d+)", q)
            n = int(n_match.group(1)) if n_match else 5
            entity = next((c for c in cat_cols if c.lower() in q), cat_cols[0] if cat_cols else cols[0])
            metric = next((c for c in numeric_cols if c.lower() in q), numeric_cols[0] if numeric_cols else cols[0])
            return AnalysisIntent(
                operation="top_performers",
                group_col=entity,
                metric_col=metric,
                n=n,
                explanation=f"Top {n} {entity} by {metric}.",
            )

        # 5. Bottom performers check
        if "bottom" in q or "lowest" in q or "worst" in q or "least" in q:
            n_match = re.search(r"\bbottom\s+(\d+)", q)
            n = int(n_match.group(1)) if n_match else 5
            entity = next((c for c in cat_cols if c.lower() in q), cat_cols[0] if cat_cols else cols[0])
            metric = next((c for c in numeric_cols if c.lower() in q), numeric_cols[0] if numeric_cols else cols[0])
            return AnalysisIntent(
                operation="bottom_performers",
                group_col=entity,
                metric_col=metric,
                n=n,
                explanation=f"Bottom {n} {entity} by {metric}.",
            )

        # 6. Correlation check
        if "correlation" in q or "correlate" in q or "relationship" in q:
            return AnalysisIntent(
                operation="correlation",
                explanation="Correlation matrix across numerical attributes.",
            )

        # 7. Trend check
        if "trend" in q or "monthly" in q or "over time" in q:
            d_col = date_cols[0] if date_cols else cols[0]
            m_col = next((c for c in numeric_cols if c.lower() in q), numeric_cols[0] if numeric_cols else cols[0])
            return AnalysisIntent(
                operation="trend_analysis",
                date_col=d_col,
                metric_col=m_col,
                explanation=f"Time trend of {m_col} over {d_col}.",
            )

        # 8. Group by / By check (e.g. "by department", "sales by region")
        if "by" in q or "average" in q or "sum" in q or "total" in q or "count" in q:
            agg_func = "mean" if ("average" in q or "avg" in q or "mean" in q) else ("count" if "count" in q else "sum")
            entity = next((c for c in cat_cols if c.lower() in q), cat_cols[0] if cat_cols else cols[0])
            metric = next((c for c in numeric_cols if c.lower() in q), numeric_cols[0] if numeric_cols else cols[0])
            return AnalysisIntent(
                operation="group_aggregation",
                group_col=entity,
                metric_col=metric,
                agg_func=agg_func,
                explanation=f"{agg_func.title()} of {metric} grouped by {entity}.",
            )

        # Default: Descriptive statistics
        return AnalysisIntent(
            operation="descriptive_stats",
            explanation="General statistical description of all dataset columns.",
        )

    def interpret_and_execute(self, query: str, df: pd.DataFrame) -> Tuple[AnalysisIntent, Any]:
        """Interprets request safely into intent and executes predefined stats function."""
        intent = None
        if self.ai_client.api_key and self.ai_client.api_key != "your_gemini_api_key_here":
            try:
                prompt = f"""
You are a Data Analysis Assistant. A user asked this question about their dataset:
"{query}"

Dataset columns:
{list(df.columns)}

Select ONE operation from: ["filter_records", "group_aggregation", "top_performers", "bottom_performers", "correlation", "trend_analysis", "descriptive_stats"].
Respond ONLY with a JSON object:
{{
  "operation": "filter_records|group_aggregation|top_performers|bottom_performers|correlation|trend_analysis|descriptive_stats",
  "conditions": [{{"column": "...", "operator": "high|low|>|<|>=|<=|==|!=", "value": 100}}],
  "sort_by": "...",
  "ascending": false,
  "group_col": "...",
  "metric_col": "...",
  "agg_func": "sum|mean|count|min|max|median",
  "n": 5,
  "date_col": "...",
  "period": "ME",
  "explanation": "..."
}}
"""
                resp = self.ai_client.generate_json_response(prompt)
                intent = AnalysisIntent(
                    operation=resp.get("operation", "descriptive_stats"),
                    conditions=resp.get("conditions", []),
                    sort_by=resp.get("sort_by"),
                    ascending=resp.get("ascending", False),
                    group_col=resp.get("group_col"),
                    metric_col=resp.get("metric_col"),
                    agg_func=resp.get("agg_func", "sum"),
                    n=int(resp.get("n", 5)),
                    date_col=resp.get("date_col"),
                    period=resp.get("period", "ME"),
                    explanation=resp.get("explanation", ""),
                )
            except Exception:
                intent = None

        if not intent or intent.operation == "descriptive_stats":
            # Check rule-based before settling on default
            rb_intent = self.parse_intent_rule_based(query, df)
            if rb_intent.operation != "descriptive_stats" or not intent:
                intent = rb_intent

        # Execute safe predefined operation
        result = None
        if intent.operation == "filter_records" and intent.conditions:
            result = StatisticsEngine.filter_records(
                df,
                conditions=intent.conditions,
                sort_by=intent.sort_by,
                ascending=intent.ascending,
            )
        elif intent.operation == "descriptive_stats":
            result = StatisticsEngine.get_descriptive_stats(df)
        elif intent.operation == "group_aggregation" and intent.group_col and intent.metric_col:
            result = StatisticsEngine.aggregate_by_group(df, intent.group_col, intent.metric_col, intent.agg_func)
        elif intent.operation == "top_performers" and intent.group_col and intent.metric_col:
            result = StatisticsEngine.get_top_bottom_performers(df, intent.group_col, intent.metric_col, n=intent.n, ascending=False)
        elif intent.operation == "bottom_performers" and intent.group_col and intent.metric_col:
            result = StatisticsEngine.get_top_bottom_performers(df, intent.group_col, intent.metric_col, n=intent.n, ascending=True)
        elif intent.operation == "correlation":
            corr, pairs = StatisticsEngine.compute_correlation_matrix(df)
            result = {"correlation_matrix": corr, "top_pairs": pd.DataFrame(pairs)}
        elif intent.operation == "trend_analysis" and intent.date_col and intent.metric_col:
            result = StatisticsEngine.analyze_trend(df, intent.date_col, intent.metric_col, period=intent.period)
        else:
            result = StatisticsEngine.get_descriptive_stats(df)

        return intent, result
