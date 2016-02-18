from lib.liteserv import LiteServ

def test_scenario_one():

    liteserv = LiteServ(port=5984)
    print(liteserv.verify_lauched())