"""
╔══════════════════════════════════════════════════════════════╗
║         CrewAI Data Analysis Agent  —  FREE / No API Key    ║
║         Uses Ollama (runs 100% locally on your machine)      ║
╠══════════════════════════════════════════════════════════════╣
║  SETUP (one time only):                                      ║
║                                                              ║
║  1. Install Ollama:                                          ║
║       https://ollama.com  → download & install               ║
║                                                              ║
║  2. Pull a free model (pick one):                            ║
║       ollama pull llama3          ← recommended              ║
║       ollama pull mistral         ← lighter / faster         ║
║       ollama pull phi3            ← very lightweight         ║
║                                                              ║
║  3. Install Python packages:                                 ║
║       pip install crewai pandas openpyxl xlrd                ║
║                                                              ║
║  4. Run the agent:                                           ║
║       python data_analyst_agent.py your_file.csv             ║
║       python data_analyst_agent.py your_file.xlsx report.md  ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from textwrap import dedent
from typing import Optional, Type

# ── CrewAI ──────────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ════════════════════════════════════════════════════════════════════════════
# CONFIG  —  change MODEL here if needed
# ════════════════════════════════════════════════════════════════════════════

OLLAMA_MODEL = "ollama/mistral"
# Other free options:
#   "ollama/mistral"   — lighter & faster
#   "ollama/phi3"      — very lightweight (good for low-RAM machines)
#   "ollama/gemma"     — Google's open model


# ════════════════════════════════════════════════════════════════════════════
# GLOBAL DATA STORE  (shared between all tools in one run)
# ════════════════════════════════════════════════════════════════════════════

class _DataStore:
    df: Optional[pd.DataFrame] = None
    file_path: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# TOOL 1 — File Loader
# ════════════════════════════════════════════════════════════════════════════

class FileLoaderInput(BaseModel):
    file_path: str = Field(..., description="C:/Users/ROG/Downloads/Ecommerce_Sales_Data_2024_2025.csv")


class FileLoaderTool(BaseTool):
    name: str = "file_loader"
    description: str = (
        "Load a data file (CSV, Excel, or JSON) and return its shape, "
        "column names, data types, null counts, and first 5 rows as JSON."
    )
    args_schema: Type[BaseModel] = FileLoaderInput

    def _run(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {file_path}"})

        ext = path.suffix.lower()
        try:
            if ext == ".csv":
                df = pd.read_csv(path)
            elif ext in (".xls", ".xlsx"):
                df = pd.read_excel(path)
            elif ext == ".json":
                df = pd.read_json(path)
            else:
                return json.dumps({"error": f"Unsupported file type: {ext}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

        _DataStore.df = df
        _DataStore.file_path = str(path)

        result = {
            "file":         str(path),
            "rows":         int(df.shape[0]),
            "columns":      int(df.shape[1]),
            "column_names": df.columns.tolist(),
            "dtypes":       {c: str(t) for c, t in df.dtypes.items()},
            "null_counts":  df.isnull().sum().to_dict(),
            "null_percent": (df.isnull().mean() * 100).round(2).to_dict(),
            "sample_rows":  df.head(5).to_dict(orient="records"),
        }
        return json.dumps(result, default=str)


# ════════════════════════════════════════════════════════════════════════════
# TOOL 2 — Statistics
# ════════════════════════════════════════════════════════════════════════════

class StatisticsInput(BaseModel):
    columns: Optional[str] = Field(
        default="all",
        description="Comma-separated column names to analyse, or 'all'."
    )


class StatisticsTool(BaseTool):
    name: str = "statistics_tool"
    description: str = (
        "Compute descriptive statistics (mean, median, std, min, max, "
        "skewness, kurtosis) for numeric columns and value counts for "
        "categorical columns of the loaded dataset."
    )
    args_schema: Type[BaseModel] = StatisticsInput

    def _run(self, columns: str = "all") -> str:
        df = _DataStore.df
        if df is None:
            return json.dumps({"error": "No dataset loaded. Run file_loader first."})

        if columns.strip().lower() != "all":
            wanted = [c.strip() for c in columns.split(",")]
            df = df[[c for c in wanted if c in df.columns]]

        numeric     = df.select_dtypes(include="number")
        categorical = df.select_dtypes(exclude="number")
        result: dict = {}

        if not numeric.empty:
            desc = numeric.describe().T
            desc["skewness"] = numeric.skew()
            desc["kurtosis"] = numeric.kurt()
            result["numeric_stats"] = desc.to_dict()

        if not categorical.empty:
            cat = {}
            for col in categorical.columns:
                vc = df[col].value_counts(dropna=False)
                cat[col] = {
                    "unique_values": int(df[col].nunique()),
                    "top_10":        vc.head(10).to_dict(),
                }
            result["categorical_stats"] = cat

        return json.dumps(result, default=str)


# ════════════════════════════════════════════════════════════════════════════
# TOOL 3 — Correlation
# ════════════════════════════════════════════════════════════════════════════

class CorrelationInput(BaseModel):
    method: str = Field(
        default="pearson",
        description="Correlation method: 'pearson', 'spearman', or 'kendall'."
    )


class CorrelationTool(BaseTool):
    name: str = "correlation_tool"
    description: str = (
        "Compute the correlation matrix for numeric columns in the loaded "
        "dataset. Returns the top 10 strongest positive and negative pairs."
    )
    args_schema: Type[BaseModel] = CorrelationInput

    def _run(self, method: str = "pearson") -> str:
        df = _DataStore.df
        if df is None:
            return json.dumps({"error": "No dataset loaded. Run file_loader first."})

        numeric = df.select_dtypes(include="number")
        if numeric.shape[1] < 2:
            return json.dumps({"info": "Not enough numeric columns for correlation."})

        corr = numeric.corr(method=method)
        pairs = []
        cols = corr.columns.tolist()
        for i, c1 in enumerate(cols):
            for c2 in cols[i + 1:]:
                pairs.append({
                    "col1": c1,
                    "col2": c2,
                    "correlation": round(corr.loc[c1, c2], 4)
                })

        pairs_sorted = sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True)

        return json.dumps({
            "method":       method,
            "top_positive": [p for p in pairs_sorted if p["correlation"] > 0][:10],
            "top_negative": [p for p in pairs_sorted if p["correlation"] < 0][:10],
        }, default=str)


# ════════════════════════════════════════════════════════════════════════════
# TOOL 4 — Outlier Detection
# ════════════════════════════════════════════════════════════════════════════

class OutlierInput(BaseModel):
    threshold: float = Field(
        default=3.0,
        description="Z-score threshold. Values beyond this are flagged as outliers."
    )


class OutlierTool(BaseTool):
    name: str = "outlier_tool"
    description: str = (
        "Detect outliers in numeric columns using the Z-score method. "
        "Returns per-column outlier counts, percentages, and example values."
    )
    args_schema: Type[BaseModel] = OutlierInput

    def _run(self, threshold: float = 3.0) -> str:
        df = _DataStore.df
        if df is None:
            return json.dumps({"error": "No dataset loaded. Run file_loader first."})

        numeric = df.select_dtypes(include="number")
        result = {}
        for col in numeric.columns:
            s = numeric[col].dropna()
            z = (s - s.mean()) / (s.std() + 1e-9)
            outliers = s[abs(z) > threshold]
            result[col] = {
                "outlier_count": int(len(outliers)),
                "outlier_pct":   round(len(outliers) / max(len(s), 1) * 100, 2),
                "examples":      outliers.head(5).tolist(),
            }
        return json.dumps(result, default=str)


# ════════════════════════════════════════════════════════════════════════════
# BUILD AGENTS  (powered by local Ollama — zero cost, zero API key)
# ════════════════════════════════════════════════════════════════════════════

def build_agents():
    llm = LLM(model=OLLAMA_MODEL)   # ← 100% free, runs on your machine

    loader_agent = Agent(
        role="Data Ingestion Specialist",
        goal="Load the dataset and produce a thorough structural overview.",
        backstory=dedent("""\
            You are an expert data engineer who has processed thousands of datasets.
            You immediately spot data quality issues, understand schema nuances, and
            provide concise, actionable summaries that set the stage for deeper analysis.
        """),
        tools=[FileLoaderTool(), StatisticsTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    analysis_agent = Agent(
        role="Senior Data Analyst",
        goal=(
            "Perform in-depth statistical analysis, correlation analysis, and "
            "outlier detection to surface every meaningful pattern in the data."
        ),
        backstory=dedent("""\
            With a PhD in statistics and 15 years of industry experience, you turn
            raw numbers into compelling stories. You dig deep into distributions,
            relationships, and anomalies that others miss.
        """),
        tools=[StatisticsTool(), CorrelationTool(), OutlierTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    report_agent = Agent(
        role="Chief Data Insights Officer",
        goal=(
            "Synthesise all findings into a polished, executive-level analysis "
            "report with clear sections, ranked insights, and concrete recommendations."
        ),
        backstory=dedent("""\
            You have presented data insights to Fortune 500 boards and startups alike.
            You craft reports that are both rigorous and immediately actionable,
            always leading with the most impactful findings.
        """),
        tools=[],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    return loader_agent, analysis_agent, report_agent


# ════════════════════════════════════════════════════════════════════════════
# BUILD TASKS
# ════════════════════════════════════════════════════════════════════════════

def build_tasks(file_path: str, loader_agent, analysis_agent, report_agent):

    load_task = Task(
        description=dedent(f"""\
            1. Use the file_loader tool to load: {file_path}
            2. Use the statistics_tool (columns='all') for a first-pass summary.
            3. Document:
               - Dataset shape (rows x columns)
               - Column names and data types
               - Missing value counts and percentages
               - What this dataset likely represents
               - Any data quality red flags
        """),
        agent=loader_agent,
        expected_output=(
            "A structured summary covering dataset shape, schema, "
            "null counts, and initial data-quality observations."
        ),
    )

    analysis_task = Task(
        description=dedent("""\
            Using the already-loaded dataset, perform a full analysis:

            1. Descriptive Statistics — run statistics_tool for all columns.
               Flag the most interesting distributions (skewed, near-constant, bimodal).

            2. Correlation Analysis — run correlation_tool (pearson). Identify:
               - Top 5 positive correlations
               - Top 5 negative correlations
               - Any multicollinearity concerns

            3. Outlier Detection — run outlier_tool (threshold=3.0). Report:
               - Which columns have the most outliers
               - Whether they look like errors or genuine extremes

            4. Key Patterns — write 5 to 10 bullet-point findings
               ranked by business or analytical importance.
        """),
        agent=analysis_agent,
        expected_output=(
            "A detailed report with sections for Descriptive Stats, "
            "Correlations, Outliers, and ranked Key Patterns."
        ),
        context=[load_task],
    )

    report_task = Task(
        description=dedent("""\
            Write the Final Top Analysis Report using all prior findings.
            Use this exact structure:

            # Data Analysis Report

            ## 1. Executive Summary
            (3 to 5 sentences summarising the most important findings)

            ## 2. Dataset Overview
            (file name, shape, column list)

            ## 3. Top 10 Insights  (numbered, ranked by importance)
            For each: bold title — 2 to 3 sentences explaining it and why it matters.

            ## 4. Statistical Highlights
            (notable distributions, skewed columns, extremes)

            ## 5. Correlation Findings
            (top positive and negative pairs with interpretation)

            ## 6. Data Quality Issues
            (missing values, anomalies, how to fix them)

            ## 7. Recommendations and Next Steps  (numbered list)
            (concrete actions a decision-maker can take)

            ## 8. Appendix — Raw Stats Summary

            Be professional, precise, and useful to a non-technical decision-maker.
        """),
        agent=report_agent,
        expected_output=(
            "A complete Markdown analysis report with all 8 sections "
            "filled in using the headings above."
        ),
        context=[load_task, analysis_task],
    )

    return load_task, analysis_task, report_task


# ════════════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ════════════════════════════════════════════════════════════════════════════

def run_analysis(file_path: str, output_file: str = "analysis_report.md") -> str:
    print("\n" + "=" * 60)
    print("  CrewAI Data Analysis Agent  —  Powered by Ollama (Free)")
    print(f"  Model : {OLLAMA_MODEL}")
    print(f"  File  : {file_path}")
    print("=" * 60 + "\n")

    loader_agent, analysis_agent, report_agent = build_agents()
    load_task, analysis_task, report_task = build_tasks(
        file_path, loader_agent, analysis_agent, report_agent
    )

    crew = Crew(
        agents=[loader_agent, analysis_agent, report_agent],
        tasks=[load_task, analysis_task, report_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    report_text = str(result)
    Path(output_file).write_text(report_text, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"  Report saved to: {output_file}")
    print("=" * 60 + "\n")
    print(report_text)
    return report_text


# ════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print()
        print("  Usage:")
        print("    python data_analyst_agent.py <data_file> [output_report.md]")
        print()
        print("  Examples:")
        print("    python data_analyst_agent.py sales.csv")
        print("    python data_analyst_agent.py data.xlsx my_report.md")
        print("    python data_analyst_agent.py records.json analysis.md")
        print()
        print("  Supported file types: .csv  .xlsx  .xls  .json")
        print()
        sys.exit(1)

    data_file   = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "analysis_report.md"

    run_analysis(data_file, output_path)
