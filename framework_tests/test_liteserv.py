import pytest
from keywords.LiteServFactory import LiteServFactory

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


def test_running_liteserv():
    liteserv = LiteServFactory.create("macosx",
                                      version_build="1.3.1-6",
                                      host="localhost",
                                      port=59840,
                                      storage_engine="SQLite")
    logfile = open("test.txt", "w")
    liteserv.start(logfile=logfile)

    logfile_2 = open("test2.txt", "w")
    with pytest.raises(LiteServError) as lse:
        liteserv.start(logfile=logfile_2)

    ex_message = str(lse.value)
    assert ex_message == "There should be no service running on the port"

    liteserv.stop(logfile)
    logfile_2.close()