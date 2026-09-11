"""Command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from sap2000_automation.analysis import export_analysis_log
from sap2000_automation.config import AppConfig
from sap2000_automation.design import export_steel_design_summary
from sap2000_automation.optimize import load_optimize_config, run_weight_optimization

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Automate SAP2000 analysis and steel design via COM.",
)
console = Console(safe_box=True)


def _config(
    model: Path,
    output_dir: Path,
    sap_exe: Path | None,
    design_code: str,
    visible: bool,
) -> AppConfig:
    return AppConfig.from_env(
        model_path=model,
        output_dir=output_dir,
        sap_exe=sap_exe,
        design_code=design_code,
        visible=visible,
    )


@app.command("analyze")
def analyze(
    model: Path = typer.Argument(..., exists=True, help="Path to .sdb model"),
    output_dir: Path = typer.Option(Path("outputs"), "--output-dir", "-o"),
    sap_exe: Path | None = typer.Option(None, "--sap-exe", help="Path to SAP2000.exe"),
    visible: bool = typer.Option(True, "--visible/--hidden"),
) -> None:
    """Run analysis and export the analysis log to Excel."""
    config = _config(model, output_dir, sap_exe, "AISC360-16", visible)
    path = export_analysis_log(config)
    console.print(f"[green]Analysis log saved:[/green] {path}")


@app.command("design")
def design(
    model: Path = typer.Argument(..., exists=True, help="Path to .sdb model"),
    output_dir: Path = typer.Option(Path("outputs"), "--output-dir", "-o"),
    sap_exe: Path | None = typer.Option(None, "--sap-exe", help="Path to SAP2000.exe"),
    design_code: str = typer.Option("AISC360-16", "--code"),
    visible: bool = typer.Option(True, "--visible/--hidden"),
) -> None:
    """Run analysis + steel design and export summary ratios to Excel."""
    config = _config(model, output_dir, sap_exe, design_code, visible)
    path = export_steel_design_summary(config)
    console.print(f"[green]Design results saved:[/green] {path}")


@app.command("optimize")
def optimize(
    model: Path = typer.Argument(..., exists=True, help="Path to .sdb model"),
    config_file: Path = typer.Option(
        ...,
        "--config",
        "-c",
        exists=True,
        help="JSON config with section_pool and member_groups",
    ),
    output_dir: Path = typer.Option(Path("outputs"), "--output-dir", "-o"),
    sap_exe: Path | None = typer.Option(None, "--sap-exe", help="Path to SAP2000.exe"),
    design_code: str = typer.Option("AISC360-16", "--code"),
    visible: bool = typer.Option(False, "--visible/--hidden", help="Show SAP2000 UI"),
    save_model: Path | None = typer.Option(
        None, "--save-model", help="Optional path to save the optimized .sdb"
    ),
) -> None:
    """Minimize structural weight with a genetic algorithm under design-ratio limits."""
    app_config = _config(model, output_dir, sap_exe, design_code, visible)
    problem = load_optimize_config(config_file)
    result = run_weight_optimization(
        app_config,
        problem,
        save_model_as=str(save_model) if save_model else None,
    )
    console.print(f"[bold]Best sections:[/bold] {result.best_sections}")
    console.print(f"Total weight: {result.total_weight:.4f}")
    console.print(f"Max design ratio: {result.max_ratio:.4f}")
    console.print(f"[green]History:[/green] {result.history_path}")
    console.print(f"[green]Assignment:[/green] {result.assignment_path}")


if __name__ == "__main__":
    app()
