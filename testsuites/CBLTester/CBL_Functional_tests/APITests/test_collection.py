import pytest
from keywords.utils import random_string


@pytest.mark.usefixtures("class_init")
class TestCollection(object):
    @pytest.mark.parametrize("db_name", [
        random_string(1),
        random_string(6),
        random_string(128),
        "_{}".format(random_string(6)),
        "{}_".format(random_string(6)),
        "_{}_".format(random_string(6)),
        random_string(6, digit=True),
        random_string(6).upper(),
    ])
    def test_defaultScope(self, db_name):
        db = self.db_obj.create(db_name)
        scope_name = self.db_obj.defaultScope(db)
        expected_name = "_default"
        assert scope_name == expected_name, "Default scope not present"
