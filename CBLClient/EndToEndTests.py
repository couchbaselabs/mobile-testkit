from Client import Client
from Args import Args
from Database import Databse
from Dictionary import Dictionary
from Document import Document



class Testcases:

    _baseUrl = "http://192.168.225.153:8080/"

    def test_database(self):
        db = Database(self._baseUrl)
        db_ptr = db.database_create("foo")
        db_name = db.database_getName(db_ptr)
        doc = Document(self._baseUrl)
        doc_id = doc.document_create()

if __name__ == "__main__":
    testcase = Testcases()
    testcase.test_database();