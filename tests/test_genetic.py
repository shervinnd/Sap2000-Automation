from __future__ import annotations

from sap2000_automation.genetic import GAConfig, run_genetic_algorithm
from sap2000_automation.optimize import fitness_from_metrics


def test_genetic_algorithm_minimizes_simple_objective() -> None:
    # Ideal chromosome is all zeros for this toy objective.
    def fitness(chrom: tuple[int, ...]) -> float:
        return float(sum(chrom) + 0.1 * len(set(chrom)))

    result = run_genetic_algorithm(
        n_genes=4,
        n_alleles=5,
        fitness_fn=fitness,
        config=GAConfig(
            population_size=24,
            generations=30,
            mutation_rate=0.15,
            crossover_rate=0.9,
            elite_count=2,
            random_state=7,
        ),
    )
    assert result.best_fitness <= fitness((1, 1, 1, 1))
    assert len(result.history) == 30
    assert result.history[-1] <= result.history[0]


def test_fitness_penalty_when_ratio_exceeds_limit() -> None:
    ok = fitness_from_metrics(100.0, 0.9, ratio_limit=1.0, penalty=1_000_000)
    bad = fitness_from_metrics(100.0, 1.2, ratio_limit=1.0, penalty=1_000_000)
    assert ok == 100.0
    assert bad > ok
