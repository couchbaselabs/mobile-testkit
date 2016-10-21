import datetime

import pytest

from keywords.LiteServFactory import LiteServFactory
from keywords.constants import RESULTS_DIR
from keywords.exceptions import LiteServError


def test_invalid_platform():

    with pytest.raises(ValueError) as ve:
        _ = LiteServFactory.create("ias",
                                   version_build="1.3.1-6",
                                   host="localhost",
                                   port=59840,
                                   storage_engine="SQLite")
    ve_message = str(ve.value)
    assert ve_message == "Unsupported 'platform': ias"


def test_invalid_storage_engine():

    with pytest.raises(ValueError) as ve:
        _ = LiteServFactory.create("macosx",
                                   version_build="1.3.1-6",
                                   host="localhost",
                                   port=59840,
                                   storage_engine="SQLit")
    ve_message = str(ve.value)
    assert ve_message == "Unsupported 'storage_engine': SQLit"


def test_running_liteserv(request):
    liteserv = LiteServFactory.create("macosx",
                                      version_build="1.3.1-6",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")

    liteserv.download()

    test_name = request.node.name

    logfile = "{}/logs/{}-{}-{}-1.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    liteserv.start(logfile)

    logfile_2 = "{}/logs/{}-{}-{}-2.txt".format(RESULTS_DIR, type(liteserv).__name__, test_name, datetime.datetime.now())
    with pytest.raises(LiteServError) as lse:
        liteserv.start(logfile_2)

    ex_message = str(lse.value)
    assert ex_message == "There should be no service running on the port"

    liteserv.stop()
