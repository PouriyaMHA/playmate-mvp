"""TEMPORARY (removed in the next commit): proves CI turns red when a test fails (Codex review 6, R6-H01)."""


def test_ci_must_fail_on_this():
    assert False, "deliberate failure: CI must be red for this commit"
