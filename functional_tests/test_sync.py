import time

import pytest
import concurrent.futures

from lib.admin import Admin
from lib.verify import verify_changes
from lib.verify import verify_docs_removed

from fixtures import cluster

import lib.settings
import logging
log = logging.getLogger(lib.settings.LOGGER)

@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf",
    [
        ("sync_gateway_custom_sync_access_sanity_di.json"),
        ("sync_gateway_custom_sync_access_sanity_cc.json")
    ],
    ids=["DI-1", "CC-2"]
)
def test_sync_access_sanity(cluster, conf):

    num_docs = 100

    log.info("Using conf: {}".format(conf))

    mode = cluster.reset(config=conf)
    admin = Admin(cluster.sync_gateways[2])

    seth = admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password")

    # Push some ABC docs
    abc_doc_pusher = admin.register_user(target=cluster.sync_gateways[2], db="db", name="abc_doc_pusher", password="password", channels=["ABC"])
    abc_doc_pusher.add_docs(num_docs)

    # Create access doc pusher and grant access Seth to ABC channel
    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[2], db="db", name="access_doc_pusher", password="password", channels=["access"])
    access_doc_pusher.add_doc(doc_id="access_doc", content={"grant_access": "true"})

    # Allow docs to backfill
    time.sleep(5)

    verify_changes(seth, expected_num_docs=num_docs, expected_num_revisions=0, expected_docs=abc_doc_pusher.cache)

    # Remove seth from ABC
    access_doc_pusher.update_doc(doc_id="access_doc", content={"grant_access": "false"})

    # Push more ABC docs
    abc_doc_pusher.add_docs(num_docs)

    time.sleep(10)

    # Verify seth sees no abc_docs
    verify_changes(seth, expected_num_docs=0, expected_num_revisions=0, expected_docs={})


@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf",
    [
        ("sync_gateway_custom_sync_channel_sanity_di.json"),
        ("sync_gateway_custom_sync_channel_sanity_cc.json")
    ],
    ids=["DI-1", "CC-2"]
)
def test_sync_channel_sanity(cluster, conf):

    num_docs_per_channel = 100
    channels = ["ABC", "NBC", "CBS"]

    log.info("Using conf: {}".format(conf))

    mode = cluster.reset(config=conf)
    admin = Admin(cluster.sync_gateways[2])

    doc_pushers = []
    doc_pusher_caches = []
    # Push some ABC docs
    for channel in channels:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[2], db="db", name="{}_doc_pusher".format(channel), password="password", channels=[channel])
        doc_pusher.add_docs(num_docs_per_channel, bulk=True)

        doc_pushers.append(doc_pusher)
        doc_pusher_caches.append(doc_pusher.cache)

    # Verfy that none of the doc_pushers get docs. They should all be redirected by the sync function
    verify_changes(doc_pushers, expected_num_docs=0, expected_num_revisions=0, expected_docs={})

    subscriber = admin.register_user(target=cluster.sync_gateways[2], db="db", name="subscriber", password="password", channels=["tv_station_channel"])

    # Allow docs to backfill
    time.sleep(5)

    # subscriber should recieve all docs
    all_docs = {k: v for cache in doc_pusher_caches for k, v in cache.items()}
    verify_changes(subscriber, expected_num_docs=len(channels) * num_docs_per_channel, expected_num_revisions=0, expected_docs=all_docs)

    # update subscribers cache so the user knows what docs to update
    subscriber.cache = all_docs
    subscriber.update_docs(num_revs_per_doc=1)

    # Allow docs to backfill
    time.sleep(5)

    # Verify the doc are back in the repective ABC, NBC, CBS channels
    # HACK: Ignoring rev_id verification due to the fact that the doc was updated the the subscriber user and not the
    # doc_pusher
    for doc_pusher in doc_pushers:
        verify_changes(doc_pusher, expected_num_docs=num_docs_per_channel, expected_num_revisions=1, expected_docs=doc_pusher.cache, ignore_rev_ids=True)

    # Verify that all docs have been flaged with _removed = true in changes feed for subscriber
    verify_docs_removed(subscriber, expected_num_docs=len(all_docs.items()), expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)

    # TODO Push more docs to channel and make sure they do not show up in the users changes feed.


@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf",
    [
        ("sync_gateway_custom_sync_role_sanity_di.json"),
        ("sync_gateway_custom_sync_role_sanity_cc.json")
    ],
    ids=["DI-1", "CC-2"]
)
def test_sync_role_sanity(cluster, conf):

    num_docs_per_channel = 100
    tv_channels = ["ABC", "NBC", "CBS"]

    log.info("Using conf: {}".format(conf))

    mode = cluster.reset(config=conf)

    admin = Admin(cluster.sync_gateways[2])
    admin.create_role(db="db", name="tv_stations", channels=tv_channels)

    seth = admin.register_user(target=cluster.sync_gateways[2], db="db", name="seth", password="password")

    doc_pushers = []
    doc_pusher_caches = []
    # Push some ABC docs
    for tv_channel in tv_channels:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[2], db="db", name="{}_doc_pusher".format(tv_channel), password="password", channels=[tv_channel])
        doc_pusher.add_docs(num_docs_per_channel, bulk=True)

        doc_pushers.append(doc_pusher)
        doc_pusher_caches.append(doc_pusher.cache)

    # Before role access grant
    verify_changes(seth, expected_num_docs=0, expected_num_revisions=0, expected_docs={})

    # Create access doc pusher and grant access Seth to ABC channel
    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[2], db="db", name="access_doc_pusher", password="password", channels=["access"])
    access_doc_pusher.add_doc(doc_id="access_doc", content={"grant_access": "true"})

    # Allow docs to backfill
    time.sleep(5)

    all_tv_docs = {k: v for cache in doc_pusher_caches for k, v in cache.items()}
    verify_changes(seth, expected_num_docs=num_docs_per_channel * len(tv_channels), expected_num_revisions=0, expected_docs=all_tv_docs)

    # Remove seth from tv_stations role
    access_doc_pusher.update_doc(doc_id="access_doc", content={"grant_access": "false"})

    # Allow docs to backfill
    time.sleep(5)

    # Verify seth sees no tv_stations channel docs
    verify_changes(seth, expected_num_docs=0, expected_num_revisions=0, expected_docs={})

    # Push more ABC docs
    for doc_pusher in doc_pushers:
        doc_pusher.add_docs(num_docs_per_channel, bulk=True)

    # Allow docs to backfill
    time.sleep(5)

    # Verify seth sees no tv_stations channel docs
    verify_changes(seth, expected_num_docs=0, expected_num_revisions=0, expected_docs={})

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf",
    [
        ("sync_gateway_custom_sync_one_di.json"),
        ("sync_gateway_custom_sync_one_cc.json")
    ],
    ids=["DI-1", "CC-2"]
)
def test_sync_sanity(cluster, conf):

    log.info("Using conf: {}".format(conf))

    mode = cluster.reset(config=conf)

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    number_of_docs_per_pusher = 5000

    admin = Admin(cluster.sync_gateways[0])

    dj_0 = admin.register_user(target=cluster.sync_gateways[0], db="db", name="dj_0", password="password")
    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="access_doc_pusher", password="password")

    # Grant dj_0 access to KDWB channel via sync before docs are pushed
    access_doc_pusher.add_doc("access_doc", content="access")

    kdwb_caches = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True,)
        if doc_pusher.name == "KDWB_doc_pusher":
            kdwb_caches.append(doc_pusher.cache)

    # Build global doc_id, rev dict for all docs from all KDWB caches
    kdwb_docs = {k: v for cache in kdwb_caches for k, v in cache.items()}

    # wait for changes
    time.sleep(5)

    # Make sure dj_0 sees KDWB docs in _changes feed
    verify_changes(dj_0, expected_num_docs=number_of_docs_per_pusher, expected_num_revisions=0, expected_docs=kdwb_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf",
    [
        ("sync_gateway_custom_sync_one_di.json"),
        ("sync_gateway_custom_sync_one_cc.json")
    ],
    ids=["DI-1", "CC-2"]
)
def test_sync_sanity_backfill(cluster, conf):

    log.info("Using conf: {}".format(conf))

    mode = cluster.reset(config=conf)

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    number_of_docs_per_pusher = 5000

    admin = Admin(cluster.sync_gateways[0])

    dj_0 = admin.register_user(target=cluster.sync_gateways[0], db="db", name="dj_0", password="password")

    kdwb_caches = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True)
        if doc_pusher.name == "KDWB_doc_pusher":
            kdwb_caches.append(doc_pusher.cache)

    access_doc_pusher = admin.register_user(target=cluster.sync_gateways[0], db="db", name="access_doc_pusher", password="password")

    # Grant dj_0 access to KDWB channel via sync after docs are pushed
    access_doc_pusher.add_doc("access_doc", content="access")

    # Build global doc_id, rev dict for all docs from all KDWB caches
    kdwb_docs = {k: v for cache in kdwb_caches for k, v in cache.items()}

    # wait for changes
    time.sleep(5)

    verify_changes(dj_0, expected_num_docs=number_of_docs_per_pusher, expected_num_revisions=0, expected_docs=kdwb_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)


@pytest.mark.sanity
@pytest.mark.parametrize(
    "conf",
    [
        ("sync_gateway_custom_sync_require_roles_di.json"),
        ("sync_gateway_custom_sync_require_roles_cc.json")
    ],
    ids=["DI-1", "CC-2"]
)
def test_sync_require_roles(cluster, conf):

    log.info("Using conf: {}".format(conf))

    mode = cluster.reset(config=conf)

    radio_stations = ["KMOW", "HWOD", "KDWB"]
    tv_stations = ["ABC", "CBS", "NBC"]

    number_of_djs = 10
    number_of_vjs = 10

    number_of_docs_per_pusher = 100

    admin = Admin(cluster.sync_gateways[2])

    admin.create_role("db", name="radio_stations", channels=radio_stations)
    admin.create_role("db", name="tv_stations", channels=tv_stations)

    djs = admin.register_bulk_users(target=cluster.sync_gateways[2], db="db", name_prefix="dj", number=number_of_djs, password="password", roles=["radio_stations"])
    vjs = admin.register_bulk_users(target=cluster.sync_gateways[2], db="db", name_prefix="vj", number=number_of_vjs, password="password", roles=["tv_stations"])

    mogul = admin.register_user(target=cluster.sync_gateways[2], db="db", name="mogul", password="password", roles=["tv_stations", "radio_stations"])

    radio_doc_caches = []
    for radio_station in radio_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[2], db="db", name="{}_doc_pusher".format(radio_station), password="password", channels=[radio_station], roles=["radio_stations"])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True)
        radio_doc_caches.append(doc_pusher.cache)

    expected_num_radio_docs = len(radio_stations) * number_of_docs_per_pusher

    # All docs that have been pushed with the "radio_stations" role
    all_radio_docs = {k: v for cache in radio_doc_caches for k, v in cache.items()}

    tv_doc_caches = []
    for tv_station in tv_stations:
        doc_pusher = admin.register_user(target=cluster.sync_gateways[2], db="db", name="{}_doc_pusher".format(tv_station), password="password", channels=[tv_station], roles=["tv_stations"])
        doc_pusher.add_docs(number_of_docs_per_pusher, bulk=True)
        tv_doc_caches.append(doc_pusher.cache)

    expected_num_tv_docs = len(tv_stations) * number_of_docs_per_pusher

    # All docs that have been pushed with the "tv_stations" role
    all_tv_docs = {k: v for cache in tv_doc_caches for k, v in cache.items()}

    # Read only users
    radio_channels_no_roles_user = admin.register_user(target=cluster.sync_gateways[2], db="db", name="bad_radio_user", password="password", channels=radio_stations)
    tv_channel_no_roles_user = admin.register_user(target=cluster.sync_gateways[2], db="db", name="bad_tv_user", password="password", channels=tv_stations)

    # Should not be allowed
    radio_channels_no_roles_user.add_docs(13, name_prefix="bad_doc")
    tv_channel_no_roles_user.add_docs(26, name_prefix="bad_doc")

    read_only_user_caches = [radio_channels_no_roles_user.cache, tv_channel_no_roles_user.cache]
    read_only_user_docs = {k: v for cache in read_only_user_caches for k, v in cache.items()}

    # Dictionary should be empty if they were blocked from pushing docs
    assert len(read_only_user_docs.items()) == 0

    # Should recieve docs from radio_channels
    verify_changes(radio_channels_no_roles_user, expected_num_docs=expected_num_radio_docs, expected_num_revisions=0, expected_docs=all_radio_docs)

    # Should recieve docs from tv_channels
    verify_changes(tv_channel_no_roles_user, expected_num_docs=expected_num_tv_docs, expected_num_revisions=0, expected_docs=all_tv_docs)

    # verify all djs with the 'radio_stations' role get the docs with radio station channels
    verify_changes(djs, expected_num_docs=expected_num_radio_docs, expected_num_revisions=0, expected_docs=all_radio_docs)

    # verify all djs with the 'radio_stations' role get the docs with radio station channels
    verify_changes(vjs, expected_num_docs=expected_num_tv_docs, expected_num_revisions=0, expected_docs=all_tv_docs)

    # Verify mogul gets docs for all the channels associated with the radio_stations + tv_stations roles
    all_doc_caches = list(radio_doc_caches)
    all_doc_caches.extend(tv_doc_caches)
    all_docs = {k: v for cache in all_doc_caches for k, v in cache.items()}

    for k, v in all_docs.items():
        assert not k.startswith("bad_doc")

    verify_changes(mogul, expected_num_docs=expected_num_radio_docs + expected_num_tv_docs, expected_num_revisions=0, expected_docs=all_docs)

    # Verify all sync_gateways are running
    errors = cluster.verify_alive(mode)
    assert(len(errors) == 0)
