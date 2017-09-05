from keywords import utils
import pytest


@pytest.mark.parametrize("test_data_cluster_config, expected_cbs_string", [
    ("mobile_testkit_tests/test_data/cluster_configs/1sg_2ac_3cbs", "111.111.11.111,111.111.11.112,111.111.11.113"),
    ("mobile_testkit_tests/test_data/cluster_configs/1sg_1ac_1cbs_1lgs", "111.111.11.111")
])
def test_add_cbs_to_sg_config_server_field(test_data_cluster_config, expected_cbs_string):
    cluster_config = test_data_cluster_config
    assert expected_cbs_string == utils.add_cbs_to_sg_config_server_field(cluster_config)
