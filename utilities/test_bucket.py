from requests import Session
from couchbase.exceptions import CouchbaseError
from couchbase.bucket import Bucket
import requests
import time
from couchbase.exceptions import NotFoundError

url = "http://s61401cnt72.sc.couchbase.com:8091"
host = "s61401cnt72.sc.couchbase.com"

name = "data-bucket"
ram_quota_mb = 2510
session = Session()
session.auth = ("Administrator", "password")

data = {
    "name": name,
    "ramQuotaMB": str(ram_quota_mb),
    "authType": "sasl",
    "bucketType": "couchbase",
    "flushEnabled": "1"
}

resp = session.post("{}/pools/default/buckets".format(url), data=data)
print "Bucket creation" + resp.text
print "Bucket creation" + str(resp)


try:
    # Create user and assign role
    data_user_params = {
        "name": name,
        "roles": "cluster_admin,bucket_admin[data-bucket]",
        "password": 'password'
    }

    rbac_url = "{}/settings/rbac/users/builtin/{}".format(url, name)
    # print rbac_url

    resp_user = requests.put(rbac_url, data=data_user_params, auth=('Administrator', 'password'))
    print "User creation" + resp_user.text
    print "User creation" + str(resp_user)

    start = time.time()
    while True:

        if time.time() - start > 120:
            raise Exception("TIMEOUT while trying to create server buckets.")
        try:
            bucket = Bucket("couchbase://{}/{}".format(host, name), password='password')
            bucket.get('foo')
        except NotFoundError:
            print("Key not found error: Bucket is ready!")
            break
        except CouchbaseError as e:
            print("Error from server: {}, Retrying ...".format(e))
            time.sleep(1)
            continue
except CouchbaseError as e:
    print("Error from server: {},". format(e))
