import sys
import string
import random
import uuid
import json
import datetime

def random_bool():
    return random.choice([True, False])

def random_int():
    return random.randint(0, sys.maxint)

def random_float():
    # Arbirary range, maybe we could have something better?
    return random.uniform(-100000000000000.0, 100000000000000.0)

def random_string(length):
    return "".join(random.choice(string.ascii_letters) for _ in xrange(length))

def simple():
    data = {
        "date_time_added": str(datetime.datetime.now()),
        "updates": 0
    }
    return json.dumps(data)

def simple_user():
    data = {
        "index": 0,
        "date_time_added": str(datetime.datetime.now()),
        "guid": uuid.uuid4(),
        "isActive": True,
        "balance": "$3,175.30",
        "picture": random_string(10),
        "age": random_int(),
        "eyeColor": random_string(10),
        "name": {
            "first": random_string(10),
            "last": random_string(10)
        },
        "company": random_string(10),
        "email": random_string(20),
        "phone": random_string(10),
        "address": random_string(30),
        "about": random_string(50),
        "registered": random_string(20),
        "latitude": random_float(),
        "longitude": random_float(),
        "tags": [
            random_string(10),
            random_string(10),
            random_string(10)
        ],
        "range": [
            random_int(),
        ],
        "friends": [
            {
                "id": random_int(),
                "name": random_string(10)
            },
            {
                "id": random_int(),
                "name": random_string(10)
            }
        ]
    }
    return json.dumps(data)