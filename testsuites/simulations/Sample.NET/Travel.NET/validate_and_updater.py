from __future__ import print_function

from couchbase.bucket import Bucket

BUCKET_NAME = 'travel-sample'
SDK_CLIENT = Bucket('couchbase://localhost/{}'.format(BUCKET_NAME), password='password')
SDK_CLIENT.timeout = 15
DOC_TYPES = ['airline', 'route', 'airport', 'landmark', 'hotel']


def check_lite_updates():

    expected_number_of_lite_updated_docs = 31591
    lite_updated_doc_count = 0
    for doc_type in DOC_TYPES:
        # SELECT META(`travel-sample`).id FROM `travel-sample` WHERE META(`travel-sample`).id LIKE "airport%";
        query = 'SELECT meta(`{}`).id FROM `{}` WHERE meta(`{}`).id LIKE "{}%"'.format(
            BUCKET_NAME,
            BUCKET_NAME,
            BUCKET_NAME,
            doc_type
        )
        print('Running: {}'.format(query))
        ids = [row['id'] for row in SDK_CLIENT.n1ql_query(query)]
        docs = SDK_CLIENT.get_multi(ids)
        for _, val in docs.items():
            if 'lite_touched' not in val.value:
                print('Doc with body: {} not updated!'.format(val.value))
            else:
                if val.value['lite_touched']:
                    lite_updated_doc_count += 1

    print('Expected number of updated docs: {}, Actual number of updated docs: {}'.format(
        expected_number_of_lite_updated_docs,
        lite_updated_doc_count
    ))

    if lite_updated_doc_count != expected_number_of_lite_updated_docs:
        raise ValueError('Lite did not update all of the expected docs. Expected: {}, Actual: {}'.format(
            expected_number_of_lite_updated_docs,
            lite_updated_doc_count
        ))
    else:
        print('SDK can see all of the lite updates!')


def update_from_sdk():
    for doc_type in DOC_TYPES:
        # SELECT META(`travel-sample`).id FROM `travel-sample` WHERE META(`travel-sample`).id LIKE "airport%";
        query = 'SELECT meta(`{}`).id FROM `{}` WHERE meta(`{}`).id LIKE "{}%"'.format(
            BUCKET_NAME,
            BUCKET_NAME,
            BUCKET_NAME,
            doc_type
        )
        print('Running: {}'.format(query))
        ids = [row['id'] for row in SDK_CLIENT.n1ql_query(query)]
        docs = SDK_CLIENT.get_multi(ids)
        print('Updating: {} docs'.format(len(docs)))
        for doc_id, val in docs.items():
            doc_body = val.value
            doc_body['sdk_touched'] = True
            SDK_CLIENT.upsert(doc_id, doc_body)


check_lite_updates()
update_from_sdk()
