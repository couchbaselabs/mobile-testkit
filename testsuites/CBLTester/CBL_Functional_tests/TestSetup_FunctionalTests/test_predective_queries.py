import pytest

from CBLClient.Document import Document
from CBLClient.PredictiveQueries import PredictiveQueries
from libraries.data import doc_generators
from libraries.testkit import cluster
from keywords.utils import deep_dict_compare


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.parametrize(
    'doc_generator_type',
    [
        ('four_k'),
        ('simple_user'),
        ('complex_doc'),
        ('simple')
    ]
)
def test_predictiveQueries_basicInputOutput(params_from_base_test_setup, doc_generator_type):
    '''
        @summary:
        1. Register the model
        2. Create bulk docs with differrent types of dictionaries
        3. Get the prediction query result and verify whatever the dictionary input is given,
           it should send back same result
        4. Verify that prediction query throws error when invalid input is provided
    '''
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]

    if liteserv_version < "2.5.0":
        pytest.skip('This test cannnot run with CBL version below 2.5')

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    # Register model
    modelName = "EchoModel"
    predictive_query = PredictiveQueries(base_url)
    model = predictive_query.registerModel(modelName)

    # Create dictionary and get the prediction query
    if doc_generator_type == "four_k":
        doc_body = doc_generators.four_k()
    elif doc_generator_type == "simple_user":
        doc_body = doc_generators.simple_user()
    elif doc_generator_type == "complex_doc":
        doc_body = doc_generators.complex_doc()
    else:
        doc_body = doc_generators.simple()

    db.create_bulk_docs(2, "cbl-predictive", db=cbl_db, generator=doc_generator_type)
    result_set = predictive_query.getPredictionQueryResult(model, doc_body, cbl_db)

    for result in result_set:
        assert deep_dict_compare(doc_body, result[result.keys()[0]])

    non_dict = "non_dict"
    error = predictive_query.queryNonDictionaryInput(model, non_dict, cbl_db)
    assert "Parameter of prediction() must be a dictionary" in error


@pytest.mark.sanity
@pytest.mark.listener
@pytest.mark.predictivequeries
@pytest.mark.parametrize("coordinates, euclidean_result, squareEuclidean_result, cosine_result",
                         [
                             ([[10, 10], [13, 14]], 5, 25, 0.0006851662332328923),
                             ([[10, 0], [13, 14]], 14.317821063276, 205, 0.319548900632722),
                             ([[1, 2, 3, 4], [12, 1]], None, None, None),
                             ([[], [3]], None, None, None),
                             ([None, [1, 3, 4]], None, None, None),
                             ([[3, 6, 10], [34, 23, 4]], 35.86084215408221, 1286, 0.43620415177230565),
                             ([[3, 6, 10, 34], [34, 23, 4, -45]], 86.75828490697589, 7527, 1.5677405830676259),
                             ([[1, 2], "foo"], None, None, None)
                         ]
                         )
def test_predictiveQueries_euclideanCosineDistance(params_from_base_test_setup, coordinates, euclidean_result,
                                                   squareEuclidean_result, cosine_result):
    '''
        @summary:
        1. Create docs with x,y,z coordinates
        2. find the euclidean distance, square euclidean distance, and cosine distance
        3. Verify all 3 distances return right value
    '''
    base_url = params_from_base_test_setup["base_url"]
    db = params_from_base_test_setup["db"]
    cbl_db = params_from_base_test_setup["source_db"]
    sg_config = params_from_base_test_setup["sg_config"]
    cluster_config = params_from_base_test_setup["cluster_config"]
    liteserv_version = params_from_base_test_setup["liteserv_version"]

    if liteserv_version < "2.5.0":
        pytest.skip('This test cannnot run with CBL version below 2.5')

    document = Document(base_url)

    # Reset cluster to ensure no data in system
    c = cluster.Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_config)

    predictive_query = PredictiveQueries(base_url)

    # Create dictionary and get the prediction query for euclidean distance
    keys = ["abc", "def"]
    doc_list = coordinates
    mut_doc = document.create()
    for item, key in zip(doc_list, keys):
        document.setValue(mut_doc, key, item)
    db.saveDocument(cbl_db, mut_doc)
    result_euclidean_dist = predictive_query.getEuclideanDistance(cbl_db, keys[0], keys[1])[0]
    result_square_euclidean_dist = predictive_query.getSquaredEuclideanDistance(cbl_db, keys[0], keys[1])[0]
    result_consine_distance = predictive_query.getCosineDistance(cbl_db, keys[0], keys[1])[0]
    if euclidean_result is not None:
        euclidean_value = result_euclidean_dist[result_euclidean_dist.keys()[0]]
        square_euclidean_value = result_square_euclidean_dist[result_square_euclidean_dist.keys()[0]]
        consine_distance_value = result_consine_distance[result_consine_distance.keys()[0]]
        assert str(euclidean_result) in str(euclidean_value), "euclidean distance did not get the right value for coordinates {}".format(coordinates)
        assert square_euclidean_value == squareEuclidean_result, "square euclidean distance did not get the right value for coordinates {}".format(coordinates)
        assert str(cosine_result) in str(consine_distance_value), "cosine distance did not get the right value for coordinates"
    else:
        assert not result_euclidean_dist, "euclidean distance did not get the right value for euclidean coordinates {}".format(coordinates)
        assert not result_square_euclidean_dist, "Square euclidean distance did not get the right value for euclidean coordinates {}".format(coordinates)
        assert not cosine_result, "cosine distance result did not get the right value for euclidean coordinates {}".format(coordinates)
