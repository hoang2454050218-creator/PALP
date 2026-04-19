"""Benchmark dataset loaders.

Each loader returns an ``Iterable[Attempt]`` where ``Attempt`` is a
small dataclass with the (student_id, concept_id, correct, ts)
quadruple — enough for any KT model to train + evaluate.

We ship synthetic generators by default. They are *deterministic*
(seeded), produce realistic distributions of mastery curves, and
therefore make tests pass without shipping copyrighted data. When a
real dataset CSV is mounted into the container, operators point
``settings.PALP_BENCHMARKS["LOADERS"]`` at the matching real loader.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List

import numpy as np


@dataclass(frozen=True)
class Attempt:
    student_id: int
    concept_id: int
    correct: int
    ts_ms: int


def _generate_synthetic(
    *,
    students: int,
    concepts: int,
    interactions_per_student: int,
    seed: int,
    base_difficulty_range: tuple[float, float],
    learning_rate_range: tuple[float, float],
) -> List[Attempt]:
    """Deterministic IRT-flavoured synthetic generator.

    Each (student, concept) pair gets a slowly-improving Bernoulli
    process. Correct probability follows
    ``sigmoid(ability - difficulty + learning * t)`` so the
    interactions look like a real KT dataset rather than uniform
    noise. We keep arithmetic in pure NumPy so this loader runs
    inside the Django test process without extra deps.
    """
    rng = np.random.default_rng(seed)
    abilities = rng.normal(0.0, 1.0, size=students)
    difficulties = rng.uniform(*base_difficulty_range, size=concepts)
    learning_rates = rng.uniform(*learning_rate_range, size=(students, concepts))

    out: List[Attempt] = []
    ts = 0
    for s in range(students):
        for _ in range(interactions_per_student):
            c = int(rng.integers(0, concepts))
            t_so_far = sum(
                1 for atom in out
                if atom.student_id == s and atom.concept_id == c
            )
            logit = (
                abilities[s]
                - difficulties[c]
                + 0.04 * learning_rates[s, c] * t_so_far
            )
            prob = 1.0 / (1.0 + math.exp(-logit))
            correct = 1 if rng.random() < prob else 0
            ts += int(rng.integers(2_000, 90_000))
            out.append(Attempt(s, c, correct, ts))
    return out


def ednet_synthetic(
    *,
    students: int = 80,
    concepts: int = 30,
    interactions_per_student: int = 40,
    seed: int = 42,
) -> Iterable[Attempt]:
    """Stand-in for EdNet-KT1 distributional shape.

    EdNet has long sequences per student over a small concept set —
    so we crank ``interactions_per_student`` up while keeping
    ``concepts`` modest. Difficulties are slightly easier on average
    (positive centred range) because EdNet's TOEIC items have known
    skew.
    """
    return _generate_synthetic(
        students=students,
        concepts=concepts,
        interactions_per_student=interactions_per_student,
        seed=seed,
        base_difficulty_range=(-0.5, 1.4),
        learning_rate_range=(0.3, 1.4),
    )


def assistments_2009_synthetic(
    *,
    students: int = 60,
    concepts: int = 50,
    interactions_per_student: int = 25,
    seed: int = 42,
) -> Iterable[Attempt]:
    """Stand-in for ASSISTments 2009-2010 shape.

    ASSISTments has more concepts per student over shorter sessions
    than EdNet, so the parameter sweep above is swapped.
    """
    return _generate_synthetic(
        students=students,
        concepts=concepts,
        interactions_per_student=interactions_per_student,
        seed=seed,
        base_difficulty_range=(-1.0, 1.0),
        learning_rate_range=(0.2, 1.0),
    )
