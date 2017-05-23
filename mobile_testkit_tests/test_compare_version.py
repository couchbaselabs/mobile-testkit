import pytest
from keywords import utils
from keywords.exceptions import FeatureSupportedError


@pytest.mark.parametrize('version_one, version_two, expected_output', [
    ('1.4.1', '1.4.1', 0),
    ('1.4.1-1235', '1.4.1-357', 0),
    ('1.4.1', '1.4.1-357', 0),
    ('1.4.1-123', '1.4.1', 0),
    ('1.4', '1.4', 0),
    ('1.4', '1.4.1', -1),
    ('1.4.0', '1.4.1', -1),
    ('1.4.0', '1.4', 0),
    ('1.4.1', '1.4.2', -1),
    ('1.4.2', '1.4.1', 1),
    ('2.0.0', '1.4.1', 1),
    ('1.4.1', '2.0.0', -1),
    ('1.4.0', '1.4', 0),
    ('1.4.0.1', '1.4', 1),
    ('1.4.0.0', '1.4', 0),
    ('1.4.0', '1.4.0.0', 0),
])
def test_compare_version(version_one, version_two, expected_output):
    assert utils.compare_versions(version_one, version_two) == expected_output


@pytest.mark.parametrize('server_version, sync_gateway_version, supported', [
    ('5.0.0-123', '1.5.0-123', True),
    ('5.0.0', '1.5-123', True),
    ('5.0.0', '1.5', True),
    ('5.0.0-123', '1.5.0', True),
    ('4.6.2-123', '1.5.0', False),
    ('4.6.2', '1.5.0', False),
    ('5.0.0-123', '1.4.0', False),
    ('5.0.0', '1.4.0-123', False),
    ('4.2.0', '1.4.0-123', False),
    ('4.2.0', '1.4.0', False)
])
def test_check_xattr_support(server_version, sync_gateway_version, supported):
    if not supported:
        with pytest.raises(FeatureSupportedError):
            utils.check_xattr_support(server_version, sync_gateway_version)
    else:
        utils.check_xattr_support(server_version, sync_gateway_version)
