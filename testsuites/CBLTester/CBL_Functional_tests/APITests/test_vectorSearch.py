import pytest
import uuid
from keywords.utils import random_string
from CBLClient.Database import Database
from CBLClient.Replication import Replication
from CBLClient.Authenticator import Authenticator
from libraries.testkit import cluster
from keywords.ClusterKeywords import ClusterKeywords
from libraries.testkit.admin import Admin
from keywords import couchbaseserver
from keywords.MobileRestClient import MobileRestClient
from keywords.constants import RBAC_FULL_ADMIN
from CBLClient.VectorSearch import VectorSearch


bucket = "travel-sample"
sync_function = "function(doc){channel(doc.channels);}"
sg_admin_url = None
sg_db = "db"
sg_blip_url = None
cbl_db = None
sg_url = None

@pytest.fixture
def vector_search_test_fixture(params_from_base_test_setup):
    global sg_admin_url
    global sg_db
    global sg_blip_url
    global cbl_db
    global sg_url
    sg_client = sg_url = sg_admin_url = None
    cluster_config = params_from_base_test_setup["cluster_config"]
    sg_admin_url = params_from_base_test_setup["sg_admin_url"]
    sg_url = params_from_base_test_setup["sg_url"]
    base_url = params_from_base_test_setup["base_url"]
    sg_blip_url = params_from_base_test_setup["target_url"]
    cbl_db = params_from_base_test_setup["source_db"]

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
          "bucket": bucket, "scopes": {scope: {
            "collections": {
                def_col : {"sync": sync_function},
                st_col_name: {"sync": sync_function},
                dbv_col_name: {"sync": sync_function},
                aw_col_name: {"sync": sync_function},
                iv_col_name: {"sync": sync_function}
            }
          }
        }, "num_index_replicas": 0 # This might need to change idk what vectors are
    }

    c = cluster.Cluster(config=cluster_config)
    auth = need_sgw_admin_auth and [RBAC_FULL_ADMIN['user'], RBAC_FULL_ADMIN['pwd']] or None
    admin_client = Admin(c.sync_gateways[0])
    vsTestDatabase = Database(base_url)
    vsHandler = VectorSearch(base_url)
    sg_client = MobileRestClient()
    db_config = vsTestDatabase.configure()
    vsTestDatabase.create("vsTestDatabase", db_config)

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
    if admin_client.does_db_exist(sg_db) is True:
        admin_client.delete_db(sg_db)
    admin_client.create_db(sg_db, data)

    # load vsTestDatabase on cbl
    # vsTestDatabase = vsHandler.loadDatabase()
    db_prefix = "vstestDatabase"
    prebuilt_db_path = "{}.cblite2.zip".format(db_prefix)
    vsTestDatabase.get_pre_built_db(prebuilt_db_path)

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
        # Check that all 3 collections on CBS exist
        dbv_id = cb_server.get_collection_id(bucket, scope, dbv_col_name)
        assert dbv_id is not None, "no server collection found for doc body vectors"
        st_id = cb_server.get_collection_id(bucket, scope, st_col_name)
        assert st_id is not None, "no server collection found for search terms"
        iv_id = cb_server.get_collection_id(bucket, scope, iv_col_name)
        assert iv_id is not None, "no server collection found for index vectors"
        aw_id = cb_server.get_collection_id(bucket, scope, aw_col_name)
        assert aw_id is not None, "no server collection found for aw"
        assert dbv_id != st_id and dbv_id != iv_id and st_id != iv_id, "duplicate collection ids: these collections are not all distinct"
        

        # Check that all 4 collections on CBL exist
        cbl_collections = db.collectionsInScope(vsTestDatabase, scope)
        # TODO check if _default counts towards this
        assert len(cbl_collections) == 5, "wrong number of collections returned"
        assert dbv_col_name in cbl_collections, "no CBL collection found for doc body vectors"
        assert st_col_name in cbl_collections, "no CBL collection found for search terms"
        assert iv_col_name in cbl_collections, "no CBL collection found for index vectors"
        assert aw_col_name in cbl_collections, "no CBL collection found for auxiliary words"

        username = "autotest"
        password = "password"
        channels_sg = ["ABC"]

        assert replicateDocs(cbl_db=vsTestDatabase, collection=dbv_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 300, "Number of docs mismatched"
        assert replicateDocs(cbl_db=vsTestDatabase, collection=st_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 1, "Number of docs mismatched"
        assert replicateDocs(cbl_db=vsTestDatabase, collection=iv_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 300, "Number of docs mismatched"
        assert replicateDocs(cbl_db=vsTestDatabase, collection=aw_col_name, base_url=base_url, sg_client=sg_client, sg_username=sg_username, scope=scope) == 10, "Number of docs mismatched"

        db.close(vsTestDatabase)
        db.deleteDBbyName("vsTestDatabase")

        # Check that all 3 collections on SGW exist

        

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
