"""Weight optimization of SAP2000 frame sections via genetic algorithm."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from sap2000_automation.analysis import run_analysis
from sap2000_automation.client import SapSession, open_sap_model
from sap2000_automation.config import AppConfig
from sap2000_automation.design import get_summary_results, run_steel_design
from sap2000_automation.genetic import GAConfig, GAResult, run_genetic_algorithm


@dataclass(slots=True)
class MemberGroup:
    name: str
    frames: list[str]


@dataclass(slots=True)
class OptimizeProblem:
    section_pool: list[str]
    member_groups: list[MemberGroup]
    ratio_limit: float = 1.0
    penalty: float = 1_000_000.0
    ga: GAConfig = field(default_factory=GAConfig)


@dataclass(slots=True)
class OptimizeResult:
    ga: GAResult
    best_sections: dict[str, str]
    total_weight: float
    max_ratio: float
    history_path: Path | None
    assignment_path: Path | None


def load_optimize_config(path: str | Path) -> OptimizeProblem:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    ga_raw = payload.get("ga", {})
    groups = [
        MemberGroup(name=item["name"], frames=[str(f) for f in item["frames"]])
        for item in payload.get("member_groups", [])
    ]
    return OptimizeProblem(
        section_pool=[str(s) for s in payload["section_pool"]],
        member_groups=groups,
        ratio_limit=float(payload.get("ratio_limit", 1.0)),
        penalty=float(payload.get("penalty", 1_000_000.0)),
        ga=GAConfig(
            population_size=int(ga_raw.get("population_size", 20)),
            generations=int(ga_raw.get("generations", 25)),
            crossover_rate=float(ga_raw.get("crossover_rate", 0.85)),
            mutation_rate=float(ga_raw.get("mutation_rate", 0.12)),
            elite_count=int(ga_raw.get("elite_count", 2)),
            tournament_size=int(ga_raw.get("tournament_size", 3)),
            random_state=int(ga_raw.get("random_state", 42)),
        ),
    )


def list_frame_names(session: SapSession) -> list[str]:
    number_names = 0
    names: list[str] = []
    result = session.sap_model.FrameObj.GetNameList(number_names, names)
    if isinstance(result, tuple):
        names = list(result[2] if len(result) > 2 else result[1])
    return [str(n) for n in names]


def get_frame_section(session: SapSession, frame: str) -> str:
    prop_name = ""
    sauto = ""
    result = session.sap_model.FrameObj.GetSection(frame, prop_name, sauto)
    if isinstance(result, tuple):
        return str(result[1])
    return str(prop_name)


def set_frame_section(session: SapSession, frame: str, section: str) -> None:
    ret = session.sap_model.FrameObj.SetSection(frame, section)
    if isinstance(ret, tuple):
        ret = ret[0]
    if ret != 0:
        raise RuntimeError(f"Failed to set section '{section}' on frame '{frame}'.")


def get_section_unit_weight(session: SapSession, section: str) -> float:
    weight = 0.0
    mass = 0.0
    result = session.sap_model.PropFrame.GetWeightAndMass(section, weight, mass)
    if isinstance(result, tuple):
        return float(result[1])
    return float(weight)


def get_frame_length(session: SapSession, frame: str) -> float:
    length = 0.0
    result = session.sap_model.FrameObj.GetLength(frame, length)
    if isinstance(result, tuple):
        return float(result[1])
    return float(length)


def discover_groups_by_current_sections(session: SapSession) -> list[MemberGroup]:
    buckets: dict[str, list[str]] = {}
    for frame in list_frame_names(session):
        section = get_frame_section(session, frame)
        buckets.setdefault(section or "UNASSIGNED", []).append(frame)
    return [
        MemberGroup(name=f"group_{section}", frames=frames)
        for section, frames in sorted(buckets.items())
        if section and section != "UNASSIGNED"
    ]


def apply_chromosome(
    session: SapSession,
    problem: OptimizeProblem,
    chromosome: tuple[int, ...],
) -> dict[str, str]:
    assignment: dict[str, str] = {}
    for gene, group in zip(chromosome, problem.member_groups, strict=True):
        section = problem.section_pool[int(gene)]
        assignment[group.name] = section
        for frame in group.frames:
            set_frame_section(session, frame, section)
    return assignment


def compute_total_weight(session: SapSession, frames: list[str] | None = None) -> float:
    selected = frames or list_frame_names(session)
    total = 0.0
    for frame in selected:
        section = get_frame_section(session, frame)
        if not section:
            continue
        unit_w = get_section_unit_weight(session, section)
        length = get_frame_length(session, frame)
        total += unit_w * length
    return float(total)


def evaluate_design(
    session: SapSession,
    *,
    design_code: str,
) -> tuple[float, float, pd.DataFrame]:
    run_analysis(session)
    run_steel_design(session, design_code=design_code)
    summary = get_summary_results(session)
    ratios = pd.to_numeric(summary.get("Design Ratio"), errors="coerce").dropna()
    max_ratio = float(ratios.max()) if not ratios.empty else float("inf")
    weight = compute_total_weight(session)
    return weight, max_ratio, summary


def fitness_from_metrics(
    weight: float,
    max_ratio: float,
    *,
    ratio_limit: float,
    penalty: float,
) -> float:
    if max_ratio > ratio_limit:
        return weight + penalty * (max_ratio - ratio_limit + 1.0)
    return weight


def run_weight_optimization(
    config: AppConfig,
    problem: OptimizeProblem,
    *,
    history_filename: str = "ga_history.csv",
    assignment_filename: str = "ga_best_assignment.json",
    save_model_as: str | None = None,
) -> OptimizeResult:
    """Optimize discrete section choices to minimize steel weight under ratio limit."""
    with open_sap_model(config) as session:
        if not problem.member_groups:
            problem.member_groups = discover_groups_by_current_sections(session)
        if not problem.member_groups:
            raise RuntimeError("No member groups found to optimize.")
        if len(problem.section_pool) < 2:
            raise RuntimeError("section_pool must contain at least 2 sections.")

        # Validate section names exist by probing unit weight.
        for section in problem.section_pool:
            get_section_unit_weight(session, section)

        cache: dict[tuple[int, ...], float] = {}

        def fitness_fn(chromosome: tuple[int, ...]) -> float:
            if chromosome in cache:
                return cache[chromosome]
            apply_chromosome(session, problem, chromosome)
            weight, max_ratio, _ = evaluate_design(session, design_code=config.design_code)
            value = fitness_from_metrics(
                weight,
                max_ratio,
                ratio_limit=problem.ratio_limit,
                penalty=problem.penalty,
            )
            cache[chromosome] = value
            return value

        def on_generation(generation: int, best_fit: float, best_chrom: tuple[int, ...]) -> None:
            sections = {
                group.name: problem.section_pool[idx]
                for group, idx in zip(problem.member_groups, best_chrom, strict=True)
            }
            print(
                f"[gen {generation + 1:03d}] best_fitness={best_fit:.4f} sections={sections}"
            )

        ga_result = run_genetic_algorithm(
            n_genes=len(problem.member_groups),
            n_alleles=len(problem.section_pool),
            fitness_fn=fitness_fn,
            config=problem.ga,
            on_generation=on_generation,
        )

        best_sections = apply_chromosome(session, problem, ga_result.best_chromosome)
        total_weight, max_ratio, _ = evaluate_design(session, design_code=config.design_code)

        if save_model_as:
            target = Path(save_model_as)
            target.parent.mkdir(parents=True, exist_ok=True)
            ret = session.sap_model.File.Save(str(target))
            if isinstance(ret, tuple):
                ret = ret[0]
            if ret != 0:
                raise RuntimeError(f"Failed to save optimized model to {target}")

        history_path = config.output_dir / history_filename
        assignment_path = config.output_dir / assignment_filename
        config.output_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "generation": list(range(1, len(ga_result.history) + 1)),
                "best_fitness": ga_result.history,
            }
        ).to_csv(history_path, index=False)
        assignment_path.write_text(
            json.dumps(
                {
                    "best_sections": best_sections,
                    "best_fitness": ga_result.best_fitness,
                    "total_weight": total_weight,
                    "max_ratio": max_ratio,
                    "chromosome": list(ga_result.best_chromosome),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        return OptimizeResult(
            ga=ga_result,
            best_sections=best_sections,
            total_weight=total_weight,
            max_ratio=max_ratio,
            history_path=history_path,
            assignment_path=assignment_path,
        )
