import requests
import json

from couchbase.bucket import Bucket


def main():

    bucket_name = 'travel-sample'

    sg_url = 'http://localhost:4984'

    cb = Bucket('couchbase://localhost/{}'.format(bucket_name), password='password')

    doc_ids = []
    for row in cb.n1ql_query("SELECT meta(`{}`) FROM `{}`".format(bucket_name, bucket_name)):
        row_doc_id = row['$1']['id']
        doc_ids.append(row_doc_id)

    airline_doc_ids = [doc_id for doc_id in doc_ids if doc_id.startswith('airline')]
    route_doc_ids = [doc_id for doc_id in doc_ids if doc_id.startswith('route')]
    airport_doc_ids = [doc_id for doc_id in doc_ids if doc_id.startswith('airport')]
    landmark_doc_ids = [doc_id for doc_id in doc_ids if doc_id.startswith('landmark')]
    hotel_doc_ids = [doc_id for doc_id in doc_ids if doc_id.startswith('hotel')]

    print('Number "airline" docs: {}'.format(len(airline_doc_ids)))
    print('Number "route" docs: {}'.format(len(route_doc_ids)))
    print('Number "airport" docs: {}'.format(len(airport_doc_ids)))
    print('Number "landmark" docs: {}'.format(len(landmark_doc_ids)))
    print('Number "hotel" docs: {}'.format(len(hotel_doc_ids)))

    num_all_docs = len(airline_doc_ids) + len(route_doc_ids) + len(airport_doc_ids) + len(landmark_doc_ids) + len(hotel_doc_ids)
    print('Nunmber of docs: {}'.format(num_all_docs))

    assert num_all_docs == 31591

    for doc_id in doc_ids:

        # Get doc from SDK
        doc = cb.get(doc_id)
        doc_id = doc.key
        doc_body = doc.value

        # Add doc to Sync Gateway
        req_body = doc_body
        req_body['_id'] = doc_id
        resp = requests.post('{}/db/'.format(sg_url), data=json.dumps(req_body), auth=('admin', 'pass'))
        resp.raise_for_status()

        print(doc_id)


if __name__ == '__main__':
    main()
