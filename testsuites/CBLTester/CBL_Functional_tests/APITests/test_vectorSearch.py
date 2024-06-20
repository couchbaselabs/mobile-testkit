import pytest
import time
import uuid
import random
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from libraries.testkit import cluster
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit.admin import Admin
from keywords import couchbaseserver
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN
from CBLClient.VectorSearch import VectorSearch
from CBLClient.Collection import Collection
from CBLClient.Document import Document

bucket = "travel-sample"
sync_function = "function(doc){channel(doc.channels);}"
sg_admin_url = None
sg_db = "db"
sg_blip_url = None
sg_url = None
gteSmallDims = 384  # constant for the number of dims of gteSmall embeddings
liteserv_platform = None


@pytest.fixture
def vector_search_test_fixture(params_from_base_test_setup, params_from_base_suite_setup):
    global sg_admin_url
    global sg_db
    global sg_blip_url
    global sg_url
    global liteserv_platform
    sg_client = sg_url = sg_admin_url = None
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    liteserv_platform = params_from_base_test_setup["liteserv_platform"]

    random_suffix = str(uuid.uuid4())[:8]
    scope = '_default'
    # Names for the four collections
    def_col = '_default'
    st_col_name = 'searchTerms'
    dbv_col_name = 'docBodyVectors'
    iv_col_name = 'indexVectors'
    aw_col_name = 'auxiliaryWords'

    need_sgw_admin_auth = params_from_base_test_setup["need_sgw_admin_auth"]
    sg_username = "vector_search_user" + random_suffix
    sg_password = "password"
    data = {
        "bucket": bucket, "scopes":
        {
            scope: {
                "collections": {
                    def_col: {"sync": sync_function},
                    st_col_name: {"sync": sync_function},
                    dbv_col_name: {"sync": sync_function},
                    aw_col_name: {"sync": sync_function},
                    iv_col_name: {"sync": sync_function}
                }
            }
        }, "num_index_replicas": 0  # This might need to change idk what vectors are
    }

    c = cluster.Cluster(config=cluster_config)
    auth = need_sgw_admin_auth and [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']] or None
    admin_client = Admin(c.sync_gateways[0])
    db = Database(base_url)
    vsHandler = VectorSearch(base_url)
    sg_client = MobileRestClient()
    db.configure()

    sync_gateway_version = params_from_base_test_setup["sync_gateway_version"]
    if sync_gateway_version < "3.1.0":
        pytest.skip('This test cannot run with sg version below 3.1')

    cluster_helper = ClusterKeywords(cluster_config)
    topology = cluster_helper.get_cluster_topology(cluster_config)
    cbs_url = topology["couchbase_servers"][0]
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    does_scope_exist = cb_server.does_scope_exist(bucket, scope)
    if does_scope_exist is False:
        cb_server.create_scope(bucket, scope)

    cb_server.create_collection(bucket, scope, dbv_col_name)
    cb_server.create_collection(bucket, scope, st_col_name)
    cb_server.create_collection(bucket, scope, iv_col_name)
    cb_server.create_collection(bucket, scope, aw_col_name)

    # sgw database creation
    if admin_client.does_db_exist(sg_db) is False:
        admin_client.create_db(sg_db, data)
    else:
        admin_client.post_db_config(sg_db, data)

    # load vsTestDatabase on cbl
    vsTestDatabase = vsHandler.loadDatabase()

    channels = ["ABC"]
    user_scopes_collections = {scope: {
        dbv_col_name: {"admin_channels": channels},
        st_col_name: {"admin_channels": channels},
        iv_col_name: {"admin_channels": channels}
    }}
    pre_test_user_exists = admin_client.does_user_exist(sg_db, sg_username)
    if not pre_test_user_exists:
        sg_client.create_user(sg_admin_url, sg_db, sg_username, sg_password, auth=auth, channels=channels, collection_access=user_scopes_collections)

    yield base_url, scope, dbv_col_name, st_col_name, iv_col_name, aw_col_name, cb_server, vsTestDatabase, sg_client, sg_username
    db.deleteDB(vsTestDatabase)


@pytest.mark.skip(reason="Waiting for all the test apps chanegs to be merged")
def test_vector_search_index_correctness(vector_search_test_fixture):
    '''
    @summary: Modifying and pulling documents leads to correct vector embeddings
    We set up a vector search-enabled CBL with four collections:
        a.  SearchTerms - contains the search terms used for querying with embeddings
            For now, we'll stick to one document which just has an ID and embedding

        b.  AuxiliaryWords - disjoint with the other collections, and contains documents
            to add to IndexVectors to check that the index updates
            This collection will have 10 ducments with fields id, word and catid,
            where catid is an arbitrary category for testing queries with vector and non-vector conditions.
            All the docs in this collection will be cat3

        c.  DocBodyVectors - contains documents with the vector embeddings contained
            within the document themselves. Some documents in this collection will
            have no embeddings to begin with
            This collection has 300 documents with fields id, word, vector and catid.
            Some of these documents in cat1 and cat2 will have no vector

        d.  IndexVectors - contains documents, and indexes with vector embeddings.
            The documents in c. and d. will be conjoint (the same apart from embeddings)
            These 300 documents in this collection have fields id, word and catid
            Some of the docs in cat3 have no word field

    We also set up a server-side db with a., c., and d. identical to the CBL and corresponding SGW

    TODO use load words to get db
    '''
    # setup
    base_url, scope, dbv_col_name, st_col_name, iv_col_name, aw_col_name, cb_server, vsTestDatabase, sg_client, sg_username = vector_search_test_fixture
    db = Database(base_url)

    # Check that all 4 collections on CBL exist
    cbl_collections = db.collectionsInScope(vsTestDatabase, scope)
    # TODO check if _default counts towards this
    assert len(cbl_collections) == 5, "wrong number of collections returned"
    assert dbv_col_name in cbl_collections, "no CBL collection found for doc body vectors"
    assert st_col_name in cbl_collections, "no CBL collection found for search terms"
    assert iv_col_name in cbl_collections, "no CBL collection found for index vectors"
    assert aw_col_name in cbl_collections, "no CBL collection found for auxiliary words"

    # replicate docs to server via sgw
    #   assert replicateDocs(cbl_db=vsTestDatabase, collection=dbv_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 300, "Number of docs mismatched"
    #   assert replicateDocs(cbl_db=vsTestDatabase, collection=st_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 326, "Number of docs mismatched"
    #   assert replicateDocs(cbl_db=vsTestDatabase, collection=iv_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 300, "Number of docs mismatched"
    #   assert replicateDocs(cbl_db=vsTestDatabase, collection=aw_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 25, "Number of docs mismatched"

    # Very rough draft of CBL side work
    # Register model
    vsHandler = VectorSearch(base_url)
    vsHandler.register_model(key="word", name="gteSmall")
    print("Registered model gteSmall on field 'word'")

    # create indexes
    vsHandler.createIndex(
        database=vsTestDatabase,
        scopeName="_default",
        collectionName="docBodyVectors",
        indexName="docBodyVectorsIndex",
        expression="vector",
        dimensions=gteSmallDims,
        centroids=8,
        metric="euclidean",
        minTrainingSize=25 * 8,  # default training size values (25* 256*), need to adjust handler so values are optional
        maxTrainingSize=256 * 8)

    # worth checking an index with subquantizers? fine for now but dbl check in future
    vsHandler.createIndex(
        database=vsTestDatabase,
        scopeName="_default",
        collectionName="indexVectors",
        indexName="indexVectorsIndex",
        expression="prediction(gteSmall, {\"word\": word}).vector",
        dimensions=gteSmallDims,
        centroids=8,
        metric="cosine",
        minTrainingSize=25 * 8,
        maxTrainingSize=256 * 8)

    # TODO test index training using a known term - distance should be very small but non zero if trained but if not then 0/null
    ivQueryAll = vsHandler.query(term="dinner",
                                 sql=("SELECT word, vector_distance(indexVectorsIndex) AS distance "
                                      "FROM indexVectors "
                                      "WHERE vector_match(indexVectorsIndex, $vector, 300)"),
                                 database=vsTestDatabase)

    dbvQueryAll = vsHandler.query(term="dinner",
                                  sql=("SELECT word, vector_distance(docBodyVectorsIndex) AS distance "
                                       "FROM docBodyVectors "
                                       "WHERE vector_match(docBodyVectorsIndex, $vector, 300)"),
                                  database=vsTestDatabase)

    ivQueryCat3 = vsHandler.query(term="dinner",
                                  sql=("SELECT word, vector_distance(indexVectorsIndex) AS distance "
                                       "FROM indexVectors "
                                       "WHERE vector_match(indexVectorsIndex, $vector, 300) "
                                       "AND catid=\"cat3\""),
                                  database=vsTestDatabase)

    dbvQueryCat1 = vsHandler.query(term="dinner",
                                   sql=("SELECT word, vector_distance(docBodyVectorsIndex) AS distance "
                                        "FROM docBodyVectors "
                                        "WHERE vector_match(docBodyVectorsIndex, $vector, 300) "
                                        "AND catid=\"cat1\""),
                                   database=vsTestDatabase)

    dbvQueryCat2 = vsHandler.query(term="dinner",
                                   sql=("SELECT word, vector_distance(docBodyVectorsIndex) AS distance "
                                        "FROM docBodyVectors "
                                        "WHERE vector_match(docBodyVectorsIndex, $vector, 300) "
                                        "AND catid=\"cat2\""),
                                   database=vsTestDatabase)

    print(f"Index vector query all: {len(ivQueryAll)}")
    print(f"Document body vector query all: {len(dbvQueryAll)}")
    print(f"Index vector query cat3: {len(ivQueryCat3)}")
    print(f"Document body vector query cat1: {len(dbvQueryCat1)}")
    print(f"Document body vector query cat2: {len(dbvQueryCat2)}")

    assert len(ivQueryAll) == 295, "wrong number of docs returned from query on index vectors"
    assert len(dbvQueryAll) == 280, "wrong number of docs returned from query on docBody vectors"
    assert len(ivQueryCat3) == 45, "wrong number of docs returned from query on index vectors cat3"
    assert len(dbvQueryCat1) == 40, "wrong number of docs returned from query on docBody vectors cat1"
    assert len(dbvQueryCat2) == 40, "wrong number of docs returned from query on docBody vectors cat2"

    collectionHandler = Collection(base_url)
    collectionDict = {
        "_default": db.createCollection(vsTestDatabase, "_default", scope),
        "docBodyVectors": db.createCollection(vsTestDatabase, "docBodyVectors", scope),
        "indexVectors": db.createCollection(vsTestDatabase, "indexVectors", scope),
        "auxiliaryWords": db.createCollection(vsTestDatabase, "auxiliaryWords", scope),
        "searchTerms": db.createCollection(vsTestDatabase, "searchTerms", scope)
    }

    docIdsNeedEmbedding = list(range(1, 11)) + list(range(51, 61))
    docIdsNeedEmbedding = ["word" + str(num) for num in docIdsNeedEmbedding]
    docsNeedEmbedding = collectionHandler.getDocuments(collection=collectionDict["docBodyVectors"], ids=docIdsNeedEmbedding)

    for docId, docBody in docsNeedEmbedding.items():
        word = docBody["word"]
        embedding = vsHandler.getEmbedding(word)
        docBody["vector"] = embedding
        collectionHandler.updateDocument(collection=collectionDict["docBodyVectors"], data=docBody, doc_id=docId)

    docIdsNeedWord = ["word" + str(num) for num in range(101, 106)]
    wordsToAdd = ["fizzy", "booze", "whiskey", "daiquiri", "drinking"]
    docsNeedWord = collectionHandler.getDocuments(collection=collectionDict["indexVectors"], ids=docIdsNeedWord)

    for i in range(1, 6):
        docId = f"word{100+i}"
        word = wordsToAdd[i - 1]
        docBody = docsNeedWord[docId]
        docBody["word"] = word
        collectionHandler.updateDocument(collection=collectionDict["indexVectors"], data=docBody, doc_id=docId)

    auxWordsIds = ["word" + str(i) for i in range(301, 311)]
    auxWordsDocs = collectionHandler.getDocuments(collection=collectionDict["auxiliaryWords"], ids=auxWordsIds)
    documentHandler = Document(base_url)

    for docId, docBody in auxWordsDocs.items():
        docMemoryObj = documentHandler.create(doc_id=docId, dictionary=docBody)
        collectionHandler.saveDocument(collection=collectionDict["indexVectors"], document=docMemoryObj)

    docIdsCat4And5 = ["word" + str(i) for i in range(201, 301)]
    deleteFromDbv = list(random.sample(docIdsCat4And5, 10))
    deleteFromIv = list(random.sample(docIdsCat4And5, 10))

    # update docs to remove vector embedding and verify that doc is removed from index
    for id in deleteFromDbv:
        dbv = collectionDict["docBodyVectors"]
        docMemoryObj = collectionHandler.getDocument(collection=dbv, docId=id)
        docMemoryObj = documentHandler.toMutable(document=docMemoryObj)
        documentHandler.remove(document=docMemoryObj, key="vector")
        collectionHandler.saveDocument(collection=dbv, document=docMemoryObj)

    for id in deleteFromIv:
        iv = collectionDict["indexVectors"]
        docMemoryObj = collectionHandler.getDocument(collection=iv, docId=id)
        collectionHandler.deleteDocument(collection=iv, doc=docMemoryObj)

    print("Waiting for indexes to update")
    # TODO find a better way than sleep
    # takes around 50-100ms per word so should cover all the words with this
    time.sleep(15)

    ivQueryAll = vsHandler.query(term="dinner",
                                 sql=("SELECT word, vector_distance(indexVectorsIndex) AS distance "
                                      "FROM indexVectors "
                                      "WHERE vector_match(indexVectorsIndex, $vector, 350)"),
                                 database=vsTestDatabase)

    dbvQueryAll = vsHandler.query(term="dinner",
                                  sql=("SELECT word, vector_distance(docBodyVectorsIndex) AS distance "
                                       "FROM docBodyVectors "
                                       "WHERE vector_match(docBodyVectorsIndex, $vector, 350)"),
                                  database=vsTestDatabase)

    ivQueryCat3 = vsHandler.query(term="dinner",
                                  sql=("SELECT word, vector_distance(indexVectorsIndex) AS distance "
                                       "FROM indexVectors "
                                       "WHERE vector_match(indexVectorsIndex, $vector, 350) "
                                       "AND catid=\"cat3\""),
                                  database=vsTestDatabase)

    dbvQueryCat1 = vsHandler.query(term="dinner",
                                   sql=("SELECT word, vector_distance(docBodyVectorsIndex) AS distance "
                                        "FROM docBodyVectors "
                                        "WHERE vector_match(docBodyVectorsIndex, $vector, 350) "
                                        "AND catid=\"cat1\""),
                                   database=vsTestDatabase)

    dbvQueryCat2 = vsHandler.query(term="dinner",
                                   sql=("SELECT word, vector_distance(docBodyVectorsIndex) AS distance "
                                        "FROM docBodyVectors "
                                        "WHERE vector_match(docBodyVectorsIndex, $vector, 350) "
                                        "AND catid=\"cat2\""),
                                   database=vsTestDatabase)

    print(f"Index vector query all: {len(ivQueryAll)}")
    print(f"Document body vector query all: {len(dbvQueryAll)}")
    print(f"Index vector query cat3: {len(ivQueryCat3)}")
    print(f"Document body vector query cat1: {len(dbvQueryCat1)}")
    print(f"Document body vector query cat2: {len(dbvQueryCat2)}")

    assert len(ivQueryAll) == 300, "wrong number of docs returned from query on index vectors"
    assert len(dbvQueryAll) == 290, "wrong number of docs returned from query on docBody vectors"
    assert len(ivQueryCat3) == 60, "wrong number of docs returned from query on index vectors cat3"
    assert len(dbvQueryCat1) == 50, "wrong number of docs returned from query on docBody vectors cat1"
    assert len(dbvQueryCat2) == 50, "wrong number of docs returned from query on docBody vectors cat2"


# we should do further checks on the documents being returned by the query, i.e. verify that categories are correct etc.
def replicateDocs(cbl_db, collection, base_url, sg_client, sg_username, scope):
    db = Database(base_url)
    createdCollection = db.createCollection(cbl_db, collection, scope)
    channels_sg = ["ABC"]
    # setup replicator and replicate
    replicator = Replication(base_url)
    collections = []
    collections_configuration = []
    collections_configuration.append(replicator.collectionConfigure(channels=channels_sg, collection=createdCollection))
    collections.append(createdCollection)
    try:
        session, replicator_authenticator, repl = replicator.create_session_configure_replicate_collection(base_url, sg_admin_url, sg_db, sg_username, sg_client, sg_blip_url, continuous=True, replication_type="push", auth=None, collections=collections, collection_configuration=collections_configuration)
    except Exception as e:
        pytest.fail("Replication failed due to " + str(e))

    sg_docs = sg_client.get_all_docs(url=sg_admin_url, db=sg_db, auth=session, scope=scope, collection=collection)
    sg_docs = sg_docs["rows"]
    return len(sg_docs)


# TODO might be worth checking if a. this test case is small enough for vector search and
# b. whether this is an appropriate fixture for a sanity test
# TODO make this test only pull documents from server that have embeddings then query them
@pytest.mark.skip(reason="Waiting for all the test apps chanegs to be merged")
@pytest.mark.sanity
def test_vector_search_sanity(vector_search_test_fixture):
    base_url, scope, dbv_col_name, st_col_name, iv_col_name, aw_col_name, cb_server, vsTestDatabase, sg_client, sg_username = vector_search_test_fixture

    db = Database(base_url)

    # Check for correct server version
    server_version = couchbaseserver.get_server_version(cb_server.host)
    if server_version >= "7.6.0":
        pytest.skip("Server version must be before 7.6 for this test")

    # Load vsTestDatabase
    vsHandler = VectorSearch(base_url)

    # Register Model
    vsHandler.registerModel(key="word", name="gteSmall")

    # Create Index
    # This function requires an index name, expression (strings), number of dimensions and centroids (ints)
    vsHandler.createIndex(
        database=vsTestDatabase,
        scopeName="_default",
        collectionName="indexVectors",
        indexName="indexVectorsIndex",
        expression="prediction(gteSmall, {\"word\": word}).vector",
        dimensions=gteSmallDims,
        centroids=4,
        metric="cosine",
        minTrainingSize=25 * 8,
        maxTrainingSize=256 * 8)

    # Queries - we query indexVector collection
    queryAll = vsHandler.query(term="dinner",
                               sql=("SELECT word, vector_distance(indexVectorsIndex) AS distance "
                                    "FROM indexVectors "
                                    "WHERE vector_match(indexVectorsIndex, $vector, 300)"),
                               database=vsTestDatabase)

    queryCat2 = vsHandler.query(term="dinner",
                                sql=("SELECT word, vector_distance(indexVectorsIndex) AS distance "
                                     "FROM indexVectors "
                                     "WHERE vector_match(indexVectorsIndex, $vector, 300) "
                                     "AND catid=\"cat2\""),
                                database=vsTestDatabase)

    assert len(queryAll) == 295, len(queryAll) + " documents returned, 295 expected"
    assert len(queryCat2) == 50, len(queryCat2) + " documents returned, 50 expected"

    # Delete vsTestDatabase
    db.close(vsTestDatabase)
    db.deleteDBbyName("vsTestDatabase")
