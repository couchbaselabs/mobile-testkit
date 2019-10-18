# content of test_module.py

import pytest


def test_setup_fails(something):
    assert 2 == 2


def test_call_fails(something):
    pass

def test_fail2(something):
    assert True