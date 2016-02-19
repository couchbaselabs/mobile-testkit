from lib.liteserv import LiteServ
from lib.user import User


def test_scenario_one():

    liteserv = LiteServ(port=5984)
    print(liteserv.verify_lauched())

    liteserv.delete_db("funcdb")
    liteserv.create_db("funcdb")

    user = User(target=liteserv, db="funcdb", name="seth", password="password", channels=["ABC"])
    user.add_docs(1000)
