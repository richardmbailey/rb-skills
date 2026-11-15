"""Qualification of fault selection and outcome interpretation."""

import pytest

from tools.run_mutations import MUTATIONS, failure_ids, replace_once


def test_mutation_anchors_cannot_silently_miss_or_duplicate():
    assert replace_once("abc", "b", "x") == "axc"
    for source in ("ac", "abbc"):
        with pytest.raises(ValueError):
            replace_once(source, "b", "x")


def test_six_declared_fault_classes_remain_distinct():
    assert set(MUTATIONS) == {
        "wrong_direction",
        "wrong_receiver",
        "wrong_rate",
        "wrong_final_step",
        "wrong_units",
        "missing_stability",
    }


def test_assertion_failures_and_collection_errors_are_distinct(tmp_path):
    path = tmp_path / "result.xml"
    path.write_text(
        '<testsuite><testcase classname="suite" name="mass"><failure/></testcase>'
        '<testcase classname="suite" name="broken"><error/></testcase></testsuite>'
    )
    assert failure_ids(path) == (["suite::mass"], 1)
    path.write_text('<testsuite><testcase classname="suite" name="mass"/></testsuite>')
    assert failure_ids(path) == ([], 0)
    assert failure_ids(tmp_path / "absent.xml") == ([], -1)
