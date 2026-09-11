"""Configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SAP_PATH = r"C:\Program Files\Computers and Structures\SAP2000 24\SAP2000.exe"


@dataclass(slots=True)
class AppConfig:
    sap_exe: Path
    model_path: Path
    output_dir: Path
    design_code: str = "AISC360-16"
    visible: bool = True

    @classmethod
    def from_env(
        cls,
        *,
        model_path: str | Path,
        output_dir: str | Path = "outputs",
        sap_exe: str | Path | None = None,
        design_code: str = "AISC360-16",
        visible: bool = True,
    ) -> "AppConfig":
        exe = Path(
            sap_exe
            or os.environ.get("SAP2000_EXE", DEFAULT_SAP_PATH)
        )
        return cls(
            sap_exe=exe,
            model_path=Path(model_path),
            output_dir=Path(output_dir),
            design_code=design_code,
            visible=visible,
        )

    def validate(self) -> None:
        if not self.sap_exe.exists():
            raise FileNotFoundError(f"SAP2000 executable not found: {self.sap_exe}")
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
