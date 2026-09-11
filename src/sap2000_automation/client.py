"""SAP2000 COM session management."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import pythoncom
import win32com.client

from sap2000_automation.config import AppConfig


class SapSession:
    """Thin wrapper around a live SAP2000 COM session."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.helper = None
        self.sap_object = None
        self.sap_model = None

    def start(self) -> None:
        self.config.validate()
        pythoncom.CoInitialize()
        self.helper = win32com.client.Dispatch("SAP2000v1.Helper")
        self.sap_object = self.helper.CreateObject(str(self.config.sap_exe))
        self.sap_object.ApplicationStart(self.config.visible)
        self.sap_model = self.sap_object.SapModel

    def open_model(self) -> None:
        if self.sap_model is None:
            raise RuntimeError("SAP2000 session is not started.")
        ret = self.sap_model.File.OpenFile(str(self.config.model_path))
        if ret != 0:
            raise RuntimeError(f"Failed to open model: {self.config.model_path}")

    def close(self) -> None:
        try:
            if self.sap_object is not None:
                self.sap_object.ApplicationExit(False)
        finally:
            self.sap_model = None
            self.sap_object = None
            self.helper = None
            pythoncom.CoUninitialize()


@contextmanager
def open_sap_model(config: AppConfig) -> Iterator[SapSession]:
    """Start SAP2000, open a model, and always clean up COM resources."""
    session = SapSession(config)
    session.start()
    try:
        session.open_model()
        yield session
    finally:
        session.close()
