from libraries.testkit.cluster import validate_cluster


def test_validate_cluster():
    """
    Make sure validate cluster catches invalid clusters
    """
    sync_gateways = ["sg1"]
    sg_accels = []

    class MockConfig:
        def __init__(self, mode):
            self.mode = mode

    config = MockConfig(mode="di")

    is_valid, _ = validate_cluster(sync_gateways, sg_accels, config)
    assert is_valid is False

    sg_accels.append("sga1")
    is_valid, _ = validate_cluster(sync_gateways, sg_accels, config)
    assert is_valid is True
