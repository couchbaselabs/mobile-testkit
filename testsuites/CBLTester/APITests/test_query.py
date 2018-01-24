import unittest

from CBLClient.Document import Document
from CBLClient.Dictionary import Dictionary
from CBLClient.Database import Database
from CBLClient.Query import Query

from libraries.data.doc_generators import simple_user

baseUrl = "http://192.168.0.113:8080"
dbName = "foo"
docIdPrefix = "bar"


class TestQuery(unittest.TestCase):
    def test_collation(self):
        db = Database(baseUrl)
        query = Query(baseUrl)
        db_config = db.configure()
        db_obj = db.create(dbName, db_config)
        self.assertTrue(db.getName(db_obj) == "foo", "Database Create Failed")

        doc = {
            "name": "Hotel novotel paris la defense",
            "city": "la defense",
            "Country": "France"
        }
        db.addDocuments(db, doc)

        # Default ignoreAccents = true and ignoreCase = true
        ignoreCase = True
        collator = query.query_collator_ascii(ignoreCase)

#      let searchQuery = Query
#         .select(SelectResult.expression(Expression.meta().id),
#                 SelectResult.expression(Expression.property("name")))
#         .from(DataSource.database(db))
#         .where(Expression.property("type").equalTo("hotel")
#             .and(Expression.property("country").equalTo("France"))
#             .and(Expression.property("name").collate(collator).equalTo("Hotel novotel paris la defense")))
#         .limit(limit)
