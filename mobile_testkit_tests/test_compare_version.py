import pytest
from keywords import utils


@pytest.mark.parametrize('version_one, version_two, expected_output', [
    ('1.4.1', '1.4.1', 0),
    ('1.4.1-1235', '1.4.1-357', 0),
    ('1.4.1', '1.4.1-357', 0),
    ('1.4.1-123', '1.4.1', 0),
    ('1.4', '1.4', 0),
    ('1.4', '1.4.1', -1),
    ('1.4.0', '1.4.1', -1),
    ('1.4.0', '1.4', 1),
    ('1.4.1', '1.4.2', -1),
    ('1.4.2', '1.4.1', 1),
    ('2.0.0', '1.4.1', 1),
    ('1.4.1', '2.0.0', -1),
    ('1.4.0', '1.4', 0)
])
def test_compare_version(version_one, version_two, expected_output):
    assert utils.compare_versions(version_one, version_two) == expected_output
