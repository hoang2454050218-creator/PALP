"""DKT engine tests — pure functions, no DB."""
from __future__ import annotations

import pytest

from dkt.engine import AttemptRecord, DKTHyper, predict, predict_many


CONCEPT_IDS = [10, 20, 30, 40, 50]


class TestPredict:
    def test_empty_history_returns_neutral(self):
        out = predict(
            history=[],
            target_concept_id=10,
            concept_ids=CONCEPT_IDS,
        )
        assert out.p_correct_next == 0.5
        assert out.confidence == 0.0
        assert out.attention == []

    def test_unknown_target_concept_returns_neutral(self):
        out = predict(
            history=[AttemptRecord(10, True)],
            target_concept_id=999,
            concept_ids=CONCEPT_IDS,
        )
        assert out.p_correct_next == 0.5

    def test_correct_history_increases_probability(self):
        out = predict(
            history=[
                AttemptRecord(10, True),
                AttemptRecord(10, True),
                AttemptRecord(10, True),
            ],
            target_concept_id=10,
            concept_ids=CONCEPT_IDS,
        )
        assert out.p_correct_next > 0.5

    def test_incorrect_history_decreases_probability(self):
        out = predict(
            history=[
                AttemptRecord(10, False),
                AttemptRecord(10, False),
                AttemptRecord(10, False),
            ],
            target_concept_id=10,
            concept_ids=CONCEPT_IDS,
        )
        assert out.p_correct_next < 0.5

    def test_attention_returns_top_three(self):
        out = predict(
            history=[
                AttemptRecord(10, True),
                AttemptRecord(20, True),
                AttemptRecord(30, False),
                AttemptRecord(40, True),
                AttemptRecord(50, False),
            ],
            target_concept_id=10,
            concept_ids=CONCEPT_IDS,
        )
        assert 1 <= len(out.attention) <= 3
        for entry in out.attention:
            assert "concept_id" in entry
            assert "weight" in entry
            assert "was_correct" in entry

    def test_deterministic_given_same_seed(self):
        hyper = DKTHyper(seed=123)
        history = [AttemptRecord(20, True), AttemptRecord(30, False)]
        a = predict(
            history=history, target_concept_id=10,
            concept_ids=CONCEPT_IDS, hyper=hyper,
        )
        b = predict(
            history=history, target_concept_id=10,
            concept_ids=CONCEPT_IDS, hyper=hyper,
        )
        assert a.p_correct_next == b.p_correct_next
        assert a.attention == b.attention

    def test_confidence_grows_with_history(self):
        history_short = [AttemptRecord(10, True)]
        history_long = [AttemptRecord(10, True)] * 32
        a = predict(
            history=history_short, target_concept_id=10, concept_ids=CONCEPT_IDS,
        )
        b = predict(
            history=history_long, target_concept_id=10, concept_ids=CONCEPT_IDS,
        )
        assert b.confidence > a.confidence

    def test_predict_many_returns_one_per_target(self):
        outputs = predict_many(
            history=[AttemptRecord(10, True)],
            target_concept_ids=CONCEPT_IDS,
            concept_ids=CONCEPT_IDS,
        )
        assert set(outputs.keys()) == set(CONCEPT_IDS)
