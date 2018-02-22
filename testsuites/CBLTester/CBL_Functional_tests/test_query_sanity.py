"""
import pytest

from keywords.utils import log_info
from CBLClient.Database import Database
from CBLClient.Query import Query
from keywords.utils import host_for_url
from couchbase.bucket import Bucket
from couchbase.n1ql import N1QLQuery
from CBLClient.Document import Document


def test_sanity(params_from_base_test_setup):
    cluster_topology = params_from_base_test_setup["cluster_topology"]
    source_db = params_from_base_test_setup["source_db"]
    base_url = params_from_base_test_setup["base_url"]
    cbs_url = cluster_topology['couchbase_servers'][0]
    db_obj = Database(base_url)
    doc_obj = Document(base_url)
    qy = Query(base_url)

    cbs_ip = host_for_url(cbs_url)
    for id in range(10):
        data = {
            "callsign": "MILE-AIR",
            "country": "United States",
            "iata": "Q" + str(id * 5),
            "icao": "MLA",
            "name": "40{}-Mile Air".format(id),
            "type": "airline"}
        document = doc_obj.create(id, data)
        db_obj.saveDocument(source_db, document)

    new_data = data = {
            "callsign": "MILE-AIR",
            "country": "United States",
            "iata": "Q",
            "icao": "MLA",
            "name": "4010-Mile Air",
            "type": None}
    new_doc = doc_obj.create(10, new_data)
    db_obj.saveDocument(source_db, new_doc)
    new_data = data = {
            "callsign": "MILE-AIR",
            "country": "United States",
            "iata": "Q2",
            "icao": "MLA",
            "name": "4011-Mile Air",
            "type": "Le Clos Fleuri"}
    new_doc = doc_obj.create(11, new_data)
    db_obj.saveDocument(source_db, new_doc)
    ids = db_obj.getDocIds(source_db)
#     print qy.query_get_doc(source_db, ids[0])
#     print qy.query_collation(source_db, "type", "country", "United States", "icao", "MLA", "Le Clos Fleuri")
#     print qy.query_isNullOrMissing(source_db, "type", 1)
#     print qy.query_substring(source_db, "name", "country", "Mile")
#     print qy.query_ordering(source_db, "name", "type", "airline")
#     print qy.query_regex(source_db, "icao", "MLA", "name", "iata", "name", ".*?Mile.*?")
#     print qy.query_like(source_db, "type", "airline", "iata", "name", "name", "%Mile%")
    print qy.query_get_docs_limit_offset(source_db, 5, 5)
    print qy.query_multiple_selects(source_db, "country", "type", "name", "401-Mile Air")
    print qy.query_where_and_or(source_db, "callsign", "MILE-AIR", "iata", "Q10", "iata", "Q5", "type", "airline")
    for doc_id in ids:
        try:
            print qy.query_get_doc(source_db, doc_id)
        except Exception,e:
            pass

"""
