"""Steel design automation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pythoncom
from win32com.client import VARIANT

from sap2000_automation.analysis import run_analysis
from sap2000_automation.client import open_sap_model
from sap2000_automation.config import AppConfig


def run_steel_design(session, *, design_code: str) -> None:
    steel_design = session.sap_model.DesignSteel
    ret = steel_design.SetCode(design_code)
    if ret != 0:
        raise RuntimeError(f"DesignSteel.SetCode failed for code '{design_code}'.")
    ret = steel_design.StartDesign()
    if ret != 0:
        raise RuntimeError("DesignSteel.StartDesign failed.")


def get_summary_results(session) -> pd.DataFrame:
    steel_design = session.sap_model.DesignSteel

    obj = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [])
    elm = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [])
    loc = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [])
    step_type = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [])
    step_num = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_I4, [])
    ratio = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [])
    stage = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [])
    errors = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [])

    ret = steel_design.GetSummaryResults(
        obj, elm, loc, step_type, step_num, ratio, stage, errors
    )
    if ret != 0:
        raise RuntimeError("DesignSteel.GetSummaryResults failed.")

    return pd.DataFrame(
        {
            "Member": list(obj.value or []),
            "Element": list(elm.value or []),
            "Location": list(loc.value or []),
            "Step Type": list(step_type.value or []),
            "Step Number": list(step_num.value or []),
            "Design Ratio": list(ratio.value or []),
            "Stage": list(stage.value or []),
            "Error": list(errors.value or []),
        }
    )


def export_steel_design_summary(
    config: AppConfig,
    *,
    filename: str = "design_results.xlsx",
) -> Path:
    """Run analysis + steel design and export summary ratios to Excel."""
    with open_sap_model(config) as session:
        run_analysis(session)
        run_steel_design(session, design_code=config.design_code)
        frame = get_summary_results(session)

    output_path = config.output_dir / filename
    frame.to_excel(output_path, index=False, sheet_name="Design Results")
    return output_path
