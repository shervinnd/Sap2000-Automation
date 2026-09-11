"""Analysis helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sap2000_automation.client import SapSession, open_sap_model
from sap2000_automation.config import AppConfig


def run_analysis(session: SapSession) -> None:
    ret = session.sap_model.Analyze.RunAnalysis()
    if ret != 0:
        raise RuntimeError("Analyze.RunAnalysis failed.")


def get_analysis_log(session: SapSession) -> list[str]:
    log_text: list[str] = []
    ret = session.sap_model.Analyze.GetRunLog(log_text)
    if ret != 0:
        raise RuntimeError("Analyze.GetRunLog failed.")
    return list(log_text or [])


def export_analysis_log(config: AppConfig, *, filename: str = "analysis_log.xlsx") -> Path:
    """Open a model, run analysis, and write the analysis log to Excel."""
    with open_sap_model(config) as session:
        run_analysis(session)
        messages = get_analysis_log(session)

    output_path = config.output_dir / filename
    frame = pd.DataFrame({"Analysis Message": messages})
    frame.to_excel(output_path, index=False, sheet_name="Analysis Log")
    return output_path
