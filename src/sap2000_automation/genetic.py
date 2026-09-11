"""Simple genetic algorithm for discrete section selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np


Chromosome = tuple[int, ...]
FitnessFn = Callable[[Chromosome], float]


@dataclass(slots=True)
class GAConfig:
    population_size: int = 20
    generations: int = 25
    crossover_rate: float = 0.85
    mutation_rate: float = 0.12
    elite_count: int = 2
    tournament_size: int = 3
    random_state: int = 42


@dataclass(slots=True)
class GAResult:
    best_chromosome: Chromosome
    best_fitness: float
    history: list[float]


def _random_chromosome(rng: np.random.Generator, n_genes: int, n_alleles: int) -> Chromosome:
    return tuple(int(x) for x in rng.integers(0, n_alleles, size=n_genes))


def _tournament(
    rng: np.random.Generator,
    population: Sequence[Chromosome],
    fitness: dict[Chromosome, float],
    k: int,
) -> Chromosome:
    picks = [population[i] for i in rng.choice(len(population), size=k, replace=False)]
    return min(picks, key=lambda chrom: fitness[chrom])


def _crossover(
    rng: np.random.Generator,
    a: Chromosome,
    b: Chromosome,
    rate: float,
) -> tuple[Chromosome, Chromosome]:
    if rng.random() > rate or len(a) < 2:
        return a, b
    point = int(rng.integers(1, len(a)))
    child1 = a[:point] + b[point:]
    child2 = b[:point] + a[point:]
    return child1, child2


def _mutate(
    rng: np.random.Generator,
    chrom: Chromosome,
    n_alleles: int,
    rate: float,
) -> Chromosome:
    genes = list(chrom)
    for i in range(len(genes)):
        if rng.random() < rate:
            genes[i] = int(rng.integers(0, n_alleles))
    return tuple(genes)


def run_genetic_algorithm(
    *,
    n_genes: int,
    n_alleles: int,
    fitness_fn: FitnessFn,
    config: GAConfig = GAConfig(),
    on_generation: Callable[[int, float, Chromosome], None] | None = None,
) -> GAResult:
    """Minimize `fitness_fn` over integer-encoded chromosomes."""
    if n_genes < 1:
        raise ValueError("n_genes must be >= 1")
    if n_alleles < 2:
        raise ValueError("n_alleles must be >= 2")
    if config.population_size < 2:
        raise ValueError("population_size must be >= 2")

    rng = np.random.default_rng(config.random_state)
    population = [
        _random_chromosome(rng, n_genes, n_alleles) for _ in range(config.population_size)
    ]
    fitness: dict[Chromosome, float] = {}
    history: list[float] = []

    def evaluate(chrom: Chromosome) -> float:
        if chrom not in fitness:
            fitness[chrom] = float(fitness_fn(chrom))
        return fitness[chrom]

    for chrom in population:
        evaluate(chrom)

    for generation in range(config.generations):
        ranked = sorted(population, key=evaluate)
        best = ranked[0]
        best_fit = evaluate(best)
        history.append(best_fit)
        if on_generation is not None:
            on_generation(generation, best_fit, best)

        elite_n = min(config.elite_count, len(ranked))
        next_pop: list[Chromosome] = list(ranked[:elite_n])

        while len(next_pop) < config.population_size:
            parent_a = _tournament(rng, population, fitness, config.tournament_size)
            parent_b = _tournament(rng, population, fitness, config.tournament_size)
            child_a, child_b = _crossover(rng, parent_a, parent_b, config.crossover_rate)
            child_a = _mutate(rng, child_a, n_alleles, config.mutation_rate)
            child_b = _mutate(rng, child_b, n_alleles, config.mutation_rate)
            next_pop.append(child_a)
            if len(next_pop) < config.population_size:
                next_pop.append(child_b)

        population = next_pop
        for chrom in population:
            evaluate(chrom)

    best = min(population, key=evaluate)
    return GAResult(best_chromosome=best, best_fitness=evaluate(best), history=history)
