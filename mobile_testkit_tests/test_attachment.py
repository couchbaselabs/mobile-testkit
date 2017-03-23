import pytest
from keywords import attachment


def test_load_from_data_dir_requires_list():
    with pytest.raises(TypeError):
        attachment.load_from_data_dir("test")


def test_load_from_data_dir():
    atts = attachment.load_from_data_dir(["sample_text.txt", "golden_gate_large.jpg"])
    assert len(atts) == 2 and atts[0].name == "sample_text.txt" and atts[1].name == "golden_gate_large.jpg"