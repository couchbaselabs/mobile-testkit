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
        "updates": 0,
        "dict": {
            "name": random_string(10),
        },
        "list": [
            random_int(),
            random_int()
        ],
        "list_of_dicts": [
            {
                "friend_one": random_string(10)
            },
            {
                "friend_two": random_string(10)
            }
        ],
        "dict_with_list": {
            "list": [
                random_bool(),
                random_bool()
            ]
        }
    }
    return data

def simple_user():
    data = {
        "updates": 0,
        "index": 0,
        "date_time_added": str(datetime.datetime.now()),
        "guid": str(uuid.uuid4()),
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
    return data

def four_k():
    return {
            "_id": "568ff5e16b1faf957a6feeef",
            "index": 0,
            "guid": "d5dfa5fe-a19a-42fa-a421-c0f5a406d65a",
            "isActive": False,
            "balance": "$2,393.65",
            "picture": "http://placehold.it/32x32",
            "age": 35,
            "eyeColor": "blue",
            "name": "Ofelia Sears",
            "gender": "female",
            "company": "IMAGEFLOW",
            "email": "ofeliasears@imageflow.com",
            "phone": "+1 (939) 542-2185",
            "address": "210 Kingsland Avenue, Golconda, Colorado, 7073",
            "about": "Do adipisicing aliquip reprehenderit veniam. Do fugiat ad ut proident id eu aliqua laboris amet fugiat magna. Eu et enim magna do eu nisi ad do ut tempor eu ullamco esse.\r\n",
            "registered": "2015-09-27T07:45:21 +07:00",
            "latitude": -20.225808,
            "longitude": -78.23928,
            "tags": [
                "enim",
                "enim",
                "laborum",
                "consectetur",
                "tempor",
                "esse",
                "Lorem"
            ],
            "friends": [
                {
                    "id": 0,
                    "name": "Adriana Curry"
                },
                {
                    "id": 1,
                    "name": "Butler Delaney"
                },
                {
                    "id": 2,
                    "name": "Eaton Oneal"
                },
                {
                    "id": 3,
                    "name": "Latisha Barton"
                },
                {
                    "id": 4,
                    "name": "Cynthia Anthony"
                },
                {
                    "id": 5,
                    "name": "Vivian Mckee"
                },
                {
                    "id": 6,
                    "name": "Roy Foley"
                },
                {
                    "id": 7,
                    "name": "Marta Elliott"
                },
                {
                    "id": 8,
                    "name": "Daisy Kim"
                },
                {
                    "id": 9,
                    "name": "Socorro Benson"
                },
                {
                    "id": 10,
                    "name": "Whitney Fuller"
                },
                {
                    "id": 11,
                    "name": "Elisabeth Dennis"
                },
                {
                    "id": 12,
                    "name": "Kendra Rosario"
                },
                {
                    "id": 13,
                    "name": "Christian Miles"
                },
                {
                    "id": 14,
                    "name": "Noemi Acevedo"
                },
                {
                    "id": 15,
                    "name": "Sutton Blackwell"
                },
                {
                    "id": 16,
                    "name": "Andrews Meadows"
                },
                {
                    "id": 17,
                    "name": "Lula Roach"
                },
                {
                    "id": 18,
                    "name": "Lucinda Valenzuela"
                },
                {
                    "id": 19,
                    "name": "Hannah Marks"
                },
                {
                    "id": 20,
                    "name": "Moss Berry"
                },
                {
                    "id": 21,
                    "name": "Pearl Gray"
                },
                {
                    "id": 22,
                    "name": "Marisol Ingram"
                },
                {
                    "id": 23,
                    "name": "Rachael Wilkinson"
                },
                {
                    "id": 24,
                    "name": "Myrtle Hines"
                },
                {
                    "id": 25,
                    "name": "Hewitt Frazier"
                },
                {
                    "id": 26,
                    "name": "Susanne Herman"
                },
                {
                    "id": 27,
                    "name": "Pauline Skinner"
                },
                {
                    "id": 28,
                    "name": "Winters Moore"
                },
                {
                    "id": 29,
                    "name": "Sheree Gallagher"
                },
                {
                    "id": 30,
                    "name": "Kathrine Guthrie"
                },
                {
                    "id": 31,
                    "name": "Della Ramirez"
                },
                {
                    "id": 32,
                    "name": "Isabelle Ellison"
                },
                {
                    "id": 33,
                    "name": "Burgess Farley"
                },
                {
                    "id": 34,
                    "name": "Luella Villarreal"
                },
                {
                    "id": 35,
                    "name": "Mcclain Langley"
                },
                {
                    "id": 36,
                    "name": "Toni Owens"
                },
                {
                    "id": 37,
                    "name": "Harrell Sharp"
                },
                {
                    "id": 38,
                    "name": "Lara Olson"
                },
                {
                    "id": 39,
                    "name": "Johanna Mcclure"
                },
                {
                    "id": 40,
                    "name": "Arlene Bradford"
                },
                {
                    "id": 41,
                    "name": "Kelly Santana"
                },
                {
                    "id": 42,
                    "name": "Wood Rodriguez"
                },
                {
                    "id": 43,
                    "name": "Luz Wilson"
                },
                {
                    "id": 44,
                    "name": "Richmond Glover"
                },
                {
                    "id": 45,
                    "name": "Geneva Hopper"
                },
                {
                    "id": 46,
                    "name": "Natalie Bean"
                },
                {
                    "id": 47,
                    "name": "Valenzuela Vincent"
                },
                {
                    "id": 48,
                    "name": "Velasquez Washington"
                },
                {
                    "id": 49,
                    "name": "Bender Massey"
                },
                {
                    "id": 50,
                    "name": "Delia Harrington"
                },
                {
                    "id": 51,
                    "name": "Karin Gregory"
                },
                {
                    "id": 52,
                    "name": "Sallie Gonzales"
                },
                {
                    "id": 53,
                    "name": "Jami Randall"
                },
                {
                    "id": 54,
                    "name": "West Potts"
                },
                {
                    "id": 55,
                    "name": "Elvira Mckinney"
                },
                {
                    "id": 56,
                    "name": "Carol Shaffer"
                },
                {
                    "id": 57,
                    "name": "Farmer Snider"
                },
                {
                    "id": 58,
                    "name": "Taylor Moody"
                },
                {
                    "id": 59,
                    "name": "Farrell Black"
                },
                {
                    "id": 60,
                    "name": "Irma Hobbs"
                },
                {
                    "id": 61,
                    "name": "Bette Reed"
                },
                {
                    "id": 62,
                    "name": "Sweet Walls"
                },
                {
                    "id": 63,
                    "name": "Mercado Odonnell"
                },
                {
                    "id": 64,
                    "name": "Salas Yates"
                },
                {
                    "id": 65,
                    "name": "Shanna Guzman"
                },
                {
                    "id": 66,
                    "name": "Amanda Ruiz"
                },
                {
                    "id": 67,
                    "name": "Rosie Allison"
                },
                {
                    "id": 68,
                    "name": "Sykes William"
                },
                {
                    "id": 69,
                    "name": "Holder Nelson"
                },
                {
                    "id": 70,
                    "name": "Stuart Lyons"
                },
                {
                    "id": 71,
                    "name": "Humphrey Stewart"
                },
                {
                    "id": 72,
                    "name": "Carissa Bowen"
                },
                {
                    "id": 73,
                    "name": "Johnston Singleton"
                },
                {
                    "id": 74,
                    "name": "Jasmine Stanton"
                },
                {
                    "id": 75,
                    "name": "Elisa Gallegos"
                },
                {
                    "id": 76,
                    "name": "Velez Pitts"
                },
                {
                    "id": 77,
                    "name": "Lizzie Clements"
                },
                {
                    "id": 78,
                    "name": "Barker Waller"
                },
                {
                    "id": 79,
                    "name": "Stanley Rosales"
                },
                {
                    "id": 80,
                    "name": "Jeanne Willis"
                },
                {
                    "id": 81,
                    "name": "Washington Puckett"
                },
                {
                    "id": 82,
                    "name": "Hudson Knowles"
                },
                {
                    "id": 83,
                    "name": "Cochran Crosby"
                },
                {
                    "id": 84,
                    "name": "Bernard Garner"
                },
                {
                    "id": 85,
                    "name": "Corinne Fletcher"
                },
                {
                    "id": 86,
                    "name": "Vasquez Schneider"
                },
                {
                    "id": 87,
                    "name": "Contreras Hubbard"
                },
                {
                    "id": 88,
                    "name": "Glenn Landry"
                },
                {
                    "id": 89,
                    "name": "Bryan Carlson"
                },
                {
                    "id": 90,
                    "name": "Silva May"
                },
                {
                    "id": 91,
                    "name": "Horton Webb"
                },
                {
                    "id": 92,
                    "name": "Millicent Byrd"
                },
                {
                    "id": 93,
                    "name": "Huffman Erickson"
                },
                {
                    "id": 94,
                    "name": "Gilmore Hebert"
                },
                {
                    "id": 95,
                    "name": "Blackwell Mcknight"
                },
                {
                    "id": 96,
                    "name": "Erika Estes"
                },
                {
                    "id": 97,
                    "name": "Mills Finch"
                },
                {
                    "id": 98,
                    "name": "Combs Perry"
                },
                {
                    "id": 99,
                    "name": "Leta Macias"
                }
            ],
            "greeting": "Hello, Ofelia Sears! You have 4 unread messages.",
            "favoriteFruit": "banana"
        }

