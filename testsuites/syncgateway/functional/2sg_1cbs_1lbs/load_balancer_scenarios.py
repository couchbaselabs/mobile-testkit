from keywords.utils import log_info
from keywords.MobileRestClient import MobileRestClient

def test_load_balance_sanity(cluster_config):
    log_info(cluster_config)

    admin_sg_one = cluster_config["sync_gateways"][0]["admin"]
    lb_url = cluster_config["load_balancers"][0]

    sg_db = "db"
    num_docs = 20000
    sg_user_name = "seth"
    sg_user_password = "password"

    client = MobileRestClient()

    user = client.create_user(admin_sg_one, sg_db, sg_user_name, sg_user_password)
    session = client.create_session(admin_sg_one, sg_db, sg_user_name)

    log_info(user)
    log_info(session)

    log_info("Adding docs to the load balancer ...")
    docs = client.add_docs(lb_url, sg_db, num_docs, "test_doc", auth=session)

    log_info(docs)