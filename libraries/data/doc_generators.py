import sys
import string
import random
import uuid
import datetime


def random_bool():
    return random.choice([True, bool(random.getrandbits(1))])


def random_int():
    return random.randint(0, sys.maxint)


def random_float():
    # Arbirary range, maybe we could have something better?
    return random.uniform(-100000000000000.0, 100000000000000.0)


def random_string(length):
    return "".join(random.choice(string.ascii_letters) for _ in xrange(length))


def random_long():
    return long(random.choice(range(0, 10000000)))


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


def complex_doc():
    return {
        "code": "CM/AUV/01/1700229",
        "controller": "",
        "createdby": "office04",
        "dateofpurchase": "2017-11-06T00: 00: 00",
        "db": "purchase",
        "department": None,
        "key": "0951e35a-bcc5-4055-af1d-d37b3a7b70b5",
        "lastupdatedby": "Logistique",
        "number": "1700229",
        "origin": "Server",
        "purchasedetails": [
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "7ee2c016-6c2d-4ec8-8504-18e3b991a65e"
                },
                "item": {
                    "barcodediscount": "1083685",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083685"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145453"
                        }
                    ],
                    "code": "2800000145453/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "ea1c8797-c78a-4c1e-8694-51835446e773",
                    "mainbarcode": "2800000145453",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX MANNEQUIN OR",
                    "namenl": "JUWELENHOUDER GOUDEN MANNEQUIN",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "ea1c8797-c78a-4c1e-8694-51835446e773",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45453",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "d673c8e8-b0be-48d8-8ae4-985ff9af72af",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "3aa617a8-79b1-485e-a0e7-0a89eb3a25fe"
                },
                "item": {
                    "barcodediscount": "1083676",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083676"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145361"
                        }
                    ],
                    "code": "2800000145361/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "255ce416-b64e-441a-b495-e93d3212739f",
                    "mainbarcode": "2800000145361",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX PLASTRON ROSE",
                    "namenl": "JUWELENHOUDER ROZE BORSTSTUK",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "255ce416-b64e-441a-b495-e93d3212739f",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45361",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "2876f416-e76f-4c21-ae3e-78d78887171b",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "af59f667-acd2-4d23-bd2c-575dca415b70"
                },
                "item": {
                    "barcodediscount": "1083675",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083675"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145354"
                        }
                    ],
                    "code": "2800000145354/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "547de31c-cdc9-4471-8685-500579c4ca09",
                    "mainbarcode": "2800000145354",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX CHAUSSURE ROSE",
                    "namenl": "JUWELENHOUDER ROZE SCHOEN",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "547de31c-cdc9-4471-8685-500579c4ca09",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45354",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "e6ca0875-a230-4ebc-a8c4-fe5f4f77f03b",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "e466d193-01dc-4e55-9db1-4dc3b700beb9"
                },
                "item": {
                    "barcodediscount": "1083686",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083686"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145460"
                        }
                    ],
                    "code": "2800000145460/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "9d2a87a9-290f-43fd-b22d-7f304f5cff37",
                    "mainbarcode": "2800000145460",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX CHAUSSURE BLEU",
                    "namenl": "JUWELENHOUDER VORM BLAUWE SCHOEN",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "9d2a87a9-290f-43fd-b22d-7f304f5cff37",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45360",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "2b943b61-1528-4237-a2a4-76620774038b",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "9e21cc37-286b-40ce-88eb-4bf78b94d7d4"
                },
                "item": {
                    "barcodediscount": "1083682",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083682"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145422"
                        }
                    ],
                    "code": "2800000145422/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "67a71f6c-5374-41bb-af3d-807ef50f059f",
                    "mainbarcode": "2800000145422",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX CHAT/RENNE OR 2ASS",
                    "namenl": "JUWELENHOUDER MET GOUDEN KAT/RENDIER 2ASS",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "67a71f6c-5374-41bb-af3d-807ef50f059f",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45422",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "dc8a3a23-1e9c-4c73-be73-ef69d952f596",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "5332d845-c98e-4967-a3bb-26394c612f10"
                },
                "item": {
                    "barcodediscount": "1083677",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083677"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145378"
                        }
                    ],
                    "code": "2800000145378/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "c5f86443-adf9-4137-a643-5286bb101145",
                    "mainbarcode": "2800000145378",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE MANTEAU FLEUR OR",
                    "namenl": "KLEDINGHAAK BLOEM GOUD",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "c5f86443-adf9-4137-a643-5286bb101145",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45378",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "19858a6d-82fd-4317-871a-4e057ba6a5a7",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "9fd3c5fb-6fc3-47d2-958f-e863574c10bd"
                },
                "item": {
                    "barcodediscount": "1083697",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083697"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145514"
                        }
                    ],
                    "code": "2800000145514/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "1e617741-fe8c-4322-9d2a-0d2046a70954",
                    "mainbarcode": "2800000145514",
                    "minimumsellingqty": random_int(),
                    "namefr": "BUSTE GRANDE SUR PIED 37X23X160CM ECRU IMPR",
                    "namenl": "PASPOP GROOT OP VOETSTUK 37X23X160CM ECRU BEDRUKT",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "1e617741-fe8c-4322-9d2a-0d2046a70954",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45514",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "38b117f0-8504-4f21-8ba7-e12cac656d79",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "490397e4-221f-4ddc-80ed-cfc4faaddb03"
                },
                "item": {
                    "barcodediscount": "1083684",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083684"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145446"
                        }
                    ],
                    "code": "2800000145446/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "2743e4a8-04e6-4972-99e4-0772a5b9bca9",
                    "mainbarcode": "2800000145446",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX BARRE OR",
                    "namenl": "JUWELENHOUDER GOUDEN STAAF",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "2743e4a8-04e6-4972-99e4-0772a5b9bca9",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45446",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "988c8eda-a5cd-4001-bd30-a3ee784a0f09",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "dfdd4c72-dedc-496a-ade4-289608a232a2"
                },
                "item": {
                    "barcodediscount": "1083683",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083683"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145439"
                        }
                    ],
                    "code": "2800000145439/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "d0a304d8-bd7c-477a-ac13-6568bf055d93",
                    "mainbarcode": "2800000145439",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX TRANSPARENT ACRYLIC OR",
                    "namenl": "JUWELENHOUDER TRANSPARANT ACRYL GOUD",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "d0a304d8-bd7c-477a-ac13-6568bf055d93",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45439",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "8f13cd51-7af9-4115-b9f1-8983e6f36b1d",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "1c6a379c-ae07-4377-904d-48d25e55eb0a"
                },
                "item": {
                    "barcodediscount": "1083690",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083690"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145484"
                        }
                    ],
                    "code": "2800000145484/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "8fd70f28-d80f-4a28-90c9-c18087fc0d9d",
                    "mainbarcode": "2800000145484",
                    "minimumsellingqty": random_int(),
                    "namefr": "BOITE A BIJOUX BLEU",
                    "namenl": "JUWELENDOOS BLAUW",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "8fd70f28-d80f-4a28-90c9-c18087fc0d9d",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45484",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "cc582b44-87a5-4da9-9cfd-239c77aec7bf",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "d76f09f0-35a8-45bf-9241-96bba09dbc7a"
                },
                "item": {
                    "barcodediscount": "1083668",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083668"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145309"
                        }
                    ],
                    "code": "2800000145309/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "cb6d6145-ecd5-48d0-b357-7384d020e395",
                    "mainbarcode": "2800000145309",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE MANTEAU LETTRE ROSE",
                    "namenl": "KLEDINGHAAK LETTER ROZE",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "cb6d6145-ecd5-48d0-b357-7384d020e395",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45309",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "0a631d08-fc32-4f57-8954-787966353699",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "97953945-70cc-4e75-b963-1de8e4282e80"
                },
                "item": {
                    "barcodediscount": "1083692",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083692"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145507"
                        }
                    ],
                    "code": "2800000145507/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "3d2d44fd-142b-4a1d-b582-19b4363a3f9b",
                    "mainbarcode": "2800000145507",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX BOITE BLEU+BARRE*2",
                    "namenl": "JUWELENHOUDER BLAUWE DOOS+STAAF*2",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "3d2d44fd-142b-4a1d-b582-19b4363a3f9b",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45507",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "98d0939d-bd2a-4797-8404-f83bed06b617",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "bdc8ea2d-2ea8-4d24-8ac7-312683cf49fd"
                },
                "item": {
                    "barcodediscount": "1083691",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083691"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145491"
                        }
                    ],
                    "code": "2800000145491/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "2d4c1131-dc45-4d90-a7d5-de5a7190ea37",
                    "mainbarcode": "2800000145491",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX PLASTRON BLEU",
                    "namenl": "JUWELENHOUDER BLAUW BORSTSTUK",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "2d4c1131-dc45-4d90-a7d5-de5a7190ea37",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45391",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "23488603-a4eb-4466-a292-914f4ae06d69",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "0e98cc03-48ce-45c5-96ce-6aa79a6d9225"
                },
                "item": {
                    "barcodediscount": "1083679",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083679"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145392"
                        }
                    ],
                    "code": "2800000145392/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "76b564ea-a032-4a80-979d-79d2e8410a92",
                    "mainbarcode": "2800000145392",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX BOITE+COMP ROSE",
                    "namenl": "JUWELENHOUDER DOOS+COMP ROZE",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "76b564ea-a032-4a80-979d-79d2e8410a92",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45392",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "fc5ed130-51ac-4cbf-9331-c4744aac5f78",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "f1fcfe07-865b-4366-b70b-6553e82aaacc"
                },
                "item": {
                    "barcodediscount": "1083678",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083678"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145385"
                        }
                    ],
                    "code": "2800000145385/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "945d4eee-4d66-49f8-902e-dafa0c429d27",
                    "mainbarcode": "2800000145385",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE MANTEAU CROCHET*2 ROSE&GRIS",
                    "namenl": "KLEDINGHAAK HAAKJE*2 ROZE&GRIJS",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "945d4eee-4d66-49f8-902e-dafa0c429d27",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45385",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "1ab76c31-1065-4c9d-89e1-e464762cbfd9",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "b847072d-0f89-43da-b401-852ff4596dc3"
                },
                "item": {
                    "barcodediscount": "1083674",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083674"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145347"
                        }
                    ],
                    "code": "2800000145347/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "ae0a38d9-c47d-44c0-acd3-a9c1dc808f5d",
                    "mainbarcode": "2800000145347",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE MANTEAU FLEUR ROSE&GRIS",
                    "namenl": "KLEDINGHAAK BLOEM ROZE&GRIJS",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "ae0a38d9-c47d-44c0-acd3-a9c1dc808f5d",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45347",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "020ac6cd-c661-42ed-9bff-53e45e380852",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "5934141c-c71f-4e8c-be99-f210901f4244"
                },
                "item": {
                    "barcodediscount": "1083688",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083688"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145477"
                        }
                    ],
                    "code": "2800000145477/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "5c06f304-4b08-492e-86d1-dbba280776f5",
                    "mainbarcode": "2800000145477",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX MANNEQUIN BLEU",
                    "namenl": "JUWELENHOUDER BLAUWE MANNEQUIN",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "5c06f304-4b08-492e-86d1-dbba280776f5",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45477",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "6dfd4d6e-f2e7-4648-a30d-02c5d275cce4",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "85c25937-1c26-42a7-9760-74e53943e530"
                },
                "item": {
                    "barcodediscount": "1083680",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083680"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145408"
                        }
                    ],
                    "code": "2800000145408/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "254b2453-3915-4cd7-93bd-aa5215e69e39",
                    "mainbarcode": "2800000145408",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX LAPIN*2 OR",
                    "namenl": "JUWELENHOUDER MET GOUDEN HAAS*2",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "254b2453-3915-4cd7-93bd-aa5215e69e39",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45408",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "8cb24b6f-ca79-4075-85a3-3c246799cb56",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "cb0beaef-1cfa-4005-8d33-2fe677c155d4"
                },
                "item": {
                    "barcodediscount": "1083670",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083670"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145323"
                        }
                    ],
                    "code": "2800000145323/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "9eb24402-a4c5-4b42-b6ff-2a86bd63a463",
                    "mainbarcode": "2800000145323",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX COEUR ROSE",
                    "namenl": "JUWELENHOUDER ROZE HART",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "9eb24402-a4c5-4b42-b6ff-2a86bd63a463",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45323",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "f34042cb-bcec-42dd-8657-2d99a5c6723e",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "b2e2141e-3dff-4add-a492-d5b747d01727"
                },
                "item": {
                    "barcodediscount": "1083698",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083698"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145521"
                        }
                    ],
                    "code": "2800000145521/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "61051d8a-c58b-4645-a0af-abdc76880c40",
                    "mainbarcode": "2800000145521",
                    "minimumsellingqty": random_int(),
                    "namefr": "BUSTE GRANDE SUR PIED 37X23X160CM GRIS IMPR",
                    "namenl": "PASPOP GROOT OP VOETSTUK 37X23X160CM GRIJS BEDRUKT",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "61051d8a-c58b-4645-a0af-abdc76880c40",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45514",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "65e2c6aa-f710-4559-9496-d756207b4a90",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "22375b64-9c1c-4140-bec7-2f71345c330c"
                },
                "item": {
                    "barcodediscount": "1083681",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083681"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145415"
                        }
                    ],
                    "code": "2800000145415/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "58bb8f94-ba0f-4d80-ba60-f83d8d3899fa",
                    "mainbarcode": "2800000145415",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX CHIEN OR",
                    "namenl": "JUWELENHOUDER MET GOUDEN HOND",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "58bb8f94-ba0f-4d80-ba60-f83d8d3899fa",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45415",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "f66785a7-dca9-46ae-921b-9df08c28bbbc",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            },
            {
                "barcode": {
                    "barcode": str(random_long()),
                    "key": "343d6b7e-687a-4ce6-9160-e46e47fe1084"
                },
                "item": {
                    "barcodediscount": "1083673",
                    "barcodes": [
                        {
                            "barcode": str(random_long()),
                            "key": "1083673"
                        },
                        {
                            "barcode": str(random_long()),
                            "key": "2800000145330"
                        }
                    ],
                    "code": "2800000145330/017",
                    "controller": "",
                    "db": "item",
                    "information": None,
                    "key": "7fc5e747-a878-4077-8f2f-c8b0a819ec19",
                    "mainbarcode": "2800000145330",
                    "minimumsellingqty": random_int(),
                    "namefr": "PORTE BIJOUX MANNEQUIN",
                    "namenl": "JUWELENHOUDER VORM MANNEQUIN",
                    "origin": "Server",
                    "piramide": {
                        "code": "22.009.0500",
                        "key": "ce41bf82-d410-4de9-8019-b74edb80e322",
                        "namefr": "CATHEM PORTE-BIJOUX",
                        "namenl": "CATHEM PORTE-BIJOUX"
                    },
                    "preferedsupplier": {
                        "address": None,
                        "code": "017",
                        "controller": "",
                        "db": "supplier",
                        "email": None,
                        "fax": None,
                        "info": None,
                        "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                        "manager": None,
                        "name": "DISTRILOGISTIQUE",
                        "origin": "Server",
                        "representatives": None,
                        "supbackorder": bool(random.getrandbits(1)),
                        "tel": None,
                        "town": None,
                        "vat": None,
                        "website": None,
                        "zipcode": None
                    },
                    "prices": [
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Selling"
                        },
                        {
                            "amount": random_float(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Promotional"
                        },
                        {
                            "amount": random_int(),
                            "enddate": "0001-01-01T00: 00: 00",
                            "key": None,
                            "startdate": "0001-01-01T00: 00: 00",
                            "type": "Deposit"
                        }
                    ],
                    "sellingunit": "ST",
                    "statistics": None,
                    "status": bool(random.getrandbits(1)),
                    "stock": [
                        {
                            "artId": None,
                            "controller": "lijn",
                            "db": "stock",
                            "key": None,
                            "location": "",
                            "quantity": random_int(),
                            "stockcreatedby": None,
                            "stockdatum": "0001-01-01T00: 00: 00",
                            "store": "AUV",
                            "tijdstipstart": "0001-01-01T00: 00: 00"
                        }
                    ],
                    "suffix": "ATT",
                    "supplieritems": [
                        {
                            "itemid": "7fc5e747-a878-4077-8f2f-c8b0a819ec19",
                            "key": None,
                            "minbuyingqty": random_int(),
                            "purchasebrutvalue": random_float(),
                            "purchasenetvalue": random_float(),
                            "supitemref": "874/22/45330",
                            "supplierid": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec"
                        }
                    ],
                    "suppliers": [
                        {
                            "address": None,
                            "code": "017",
                            "controller": "",
                            "db": "supplier",
                            "email": None,
                            "fax": None,
                            "info": None,
                            "key": "d8ef8025-e1fe-4f2c-8a35-315783a7b5ec",
                            "manager": None,
                            "name": "DISTRILOGISTIQUE",
                            "origin": "Server",
                            "representatives": None,
                            "supbackorder": bool(random.getrandbits(1)),
                            "tel": None,
                            "town": None,
                            "vat": None,
                            "website": None,
                            "zipcode": None
                        }
                    ],
                    "vat": 21
                },
                "key": "e5161ffc-79c1-4504-b0cc-644999595930",
                "minquantitycolli": random_int(),
                "purchasedbrutvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "purchasednetvalue": {
                    "amount": random_float(),
                    "enddate": "0001-01-01T00: 00: 00",
                    "key": None,
                    "startdate": "0001-01-01T00: 00: 00",
                    "type": "Purchase"
                },
                "quantityordered": random_int(),
                "quantityreceived": random_int(),
                "source": "CM"
            }
        ],
        "receiver": None,
        "retourreden": None,
        "status": "Picking",
        "supplier": {
            "address": "BLOKKESTRAAT 57",
            "code": "CM",
            "controller": "",
            "db": "supplier",
            "email": None,
            "fax": None,
            "info": None,
            "key": "af81544f-f533-4dee-b6d4-81f4a5f7ec56",
            "manager": {
                "email": None,
                "fax": None,
                "info": None,
                "key": None,
                "mobile": "0491711754",
                "name": "JOERI",
                "tel": None
            },
            "name": "DEPOT",
            "origin": "Server",
            "representatives": [
                {
                    "email": None,
                    "fax": None,
                    "info": None,
                    "key": None,
                    "mobile": "056/723.203",
                    "name": "HEIDI BURO",
                    "tel": None
                }
            ],
            "supbackorder": bool(random.getrandbits(1)),
            "tel": "056/31 39 55",
            "town": "ZWEVEGEM",
            "vat": None,
            "website": None,
            "zipcode": "8550"
        },
        "trackingnumber": None,
        "type": "CentralDepot"
    }


def four_k(channels=[]):

    return {
        "channels": channels,
        "iden": "568ff5e16b1faf957a6feeef",
        "index": 0,
        "guid": "d5dfa5fe-a19a-42fa-a421-c0f5a406d65a",
        "isActive": bool(random.getrandbits(1)),
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
