from keywords.utils import add_cbs_to_sg_config_server_field
import pytest


@pytest.mark.parametrize("test_data_cluster_config, expected_cbs_string", [
    ("mobile_testkit_tests/test_data/mock_base_di", "192.168.33.20"),
    ("mobile_testkit_tests/test_data/mock_ci_di", "192.168.33.20,192.168.33.23,192.168.33.24"),
    ("mobile_testkit_tests/test_data/mock_ci_di_sg14", "192.168.33.20")
])
def test_add_cbs_to_sg_config_server_field(test_data_cluster_config, expected_cbs_string):
    cluster_config = test_data_cluster_config
    assert expected_cbs_string == add_cbs_to_sg_config_server_field(cluster_config)
