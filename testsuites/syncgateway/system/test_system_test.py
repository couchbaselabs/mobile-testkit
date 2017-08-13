import json
import random
import time

from concurrent.futures import ProcessPoolExecutor, as_completed
from couchbase.bucket import Bucket
from requests import Session
from requests.exceptions import HTTPError

from keywords import couchbaseserver, document
from keywords.ClusterKeywords import ClusterKeywords
from keywords.MobileRestClient import MobileRestClient
from keywords.SyncGateway import sync_gateway_config_path_for_mode, SyncGateway
from keywords.utils import log_info
from libraries.testkit.cluster import Cluster

# Set the default value to 404 - view not created yet
SG_VIEWS = {
    'sync_gateway_access': ["access"],
    'sync_gateway_access_vbseq': ["access_vbseq"],
    'sync_gateway_channels': ["channels"],
    'sync_gateway_role_access': ["role_access"],
    'sync_gateway_role_access_vbseq': ["role_access_vbseq"],
    'sync_housekeeping': [
        "all_bits",
        "all_docs",
        "import",
        "old_revs",
        "principals",
        "sessions",
        "tombstones"
    ]
}


USER_TYPES = ['shared_channel_user', 'unique_channel_user', 'filtered_channel_user', 'filtered_doc_ids_user']
USER_PASSWORD = 'password'


def test_system_test(params_from_base_test_setup):

    cluster_config = params_from_base_test_setup['cluster_config']
    mode = params_from_base_test_setup['mode']

    # Scenario parameters
    server_seed_docs = int(params_from_base_test_setup['server_seed_docs'])
    max_docs = int(params_from_base_test_setup['max_docs'])
    num_users = int(params_from_base_test_setup['num_users'])

    # Create paramters
    create_batch_size = int(params_from_base_test_setup['create_batch_size'])
    create_delay = float(params_from_base_test_setup['create_delay'])

    # Update parameters
    update_runtime_sec = int(params_from_base_test_setup['update_runtime_sec'])
    update_batch_size = int(params_from_base_test_setup['update_batch_size'])
    update_docs_percentage = float(params_from_base_test_setup['update_docs_percentage'])
    update_delay = float(params_from_base_test_setup['update_delay'])

    # Changes parameters
    changes_delay = float(params_from_base_test_setup['changes_delay'])
    changes_limit = int(params_from_base_test_setup['changes_limit'])

    changes_terminator_doc_id = 'terminator'

    docs_per_user = max_docs / num_users
    docs_per_user_per_update = int(update_docs_percentage * docs_per_user)

    log_info('Running System Test #1')
    log_info('> server_seed_docs          = {}'.format(server_seed_docs))
    log_info('> max_docs                  = {}'.format(max_docs))
    log_info('> num_users                 = {}'.format(num_users))
    log_info('> docs_per_user             = {}'.format(docs_per_user))
    log_info('> create_batch_size         = {}'.format(create_batch_size))
    log_info('> create_delay              = {}'.format(create_delay))
    log_info('> update_batch_size         = {}'.format(update_batch_size))
    log_info('> update_docs_percentage    = {}'.format(update_docs_percentage))
    log_info('> docs_per_user_per_update  = {}'.format(docs_per_user_per_update))
    log_info('> update_delay              = {}'.format(update_delay))
    log_info('> update_runtime_sec        = {}'.format(update_runtime_sec))
    log_info('> changes_delay             = {}'.format(changes_delay))
    log_info('> changes_limit             = {}'.format(changes_limit))
    log_info('> changes_terminator_doc_id = {}'.format(changes_terminator_doc_id))

    # Validate
    # Server docs should be a multiple of 1000 for batching purposes
    if server_seed_docs % 1000 != 0:
        raise ValueError('server_seed_docs must be divisible by 1000')

    # Number of docs should be equally divisible by number of users
    if max_docs % num_users != 0:
        raise ValueError('max_docs must be divisible by number_of_users')

    # Number of docs per user (max_docs / num_users) should be equally
    # divisible by the batch size for easier computation
    if docs_per_user % create_batch_size != 0:
        raise ValueError('docs_per_user ({}) must be devisible by create_batch_size ({})'.format(
            docs_per_user,
            create_batch_size
        ))

    # We want an even distributed of users per type
    if num_users % len(USER_TYPES) != 0:
        raise ValueError("'num_users' should be a multiple of 4")

    # Make sure that the 'update_batch_size' is complatible with
    # then number of users per type
    num_users_per_type = num_users / len(USER_TYPES)
    if update_batch_size > num_users_per_type:
        raise ValueError("'batch_size' cannot be larger than number of users per type")

    if num_users_per_type % update_batch_size != 0:
        raise ValueError("'update_batch_size' ({}) should be a multiple of number_users_per_type ({})".format(
            update_batch_size,
            num_users_per_type
        ))

    sg_conf_name = 'sync_gateway_default'
    sg_conf = sync_gateway_config_path_for_mode(sg_conf_name, mode)

    # Reset cluster state
    c = Cluster(config=cluster_config)
    c.reset(sg_config_path=sg_conf)

    cluster_helper = ClusterKeywords()
    topology = cluster_helper.get_cluster_topology(cluster_config)

    cbs_url = topology['couchbase_servers'][0]
    cbs_admin_url = cbs_url.replace('8091', '8092')
    cb_server = couchbaseserver.CouchbaseServer(cbs_url)
    bucket_name = "data-bucket"

    cbs_ip = cb_server.host

    headers = {'Content-Type': 'application/json'}
    cbs_session = Session()
    cbs_session.headers = headers
    cbs_session.auth = ('Administrator', 'password')

    log_info('Seeding {} with {} docs'.format(cbs_ip, server_seed_docs))
    sdk_client = Bucket('couchbase://{}/{}'.format(cbs_ip, bucket_name), password='password', timeout=300)

    # Stop SG before loading the server
    lb_url = topology['sync_gateways'][0]['public']
    sg_admin_url = topology['sync_gateways'][0]['admin']
    sg_db = 'db'

    sg_helper = SyncGateway()
    sg_helper.stop_sync_gateways(cluster_config=cluster_config)

    # Scenario Actions
    delete_views(cbs_session, cbs_admin_url, bucket_name)
    load_bucket(sdk_client, server_seed_docs)
    sg_helper.start_sync_gateways(cluster_config, config=sg_conf)
    wait_for_view_creation(cbs_session, cbs_admin_url, bucket_name)

    # Start concurrent creation of docs (max docs / num users)
    # Each user will add batch_size number of docs via bulk docs and sleep for 'create_delay'
    # Once a user has added number of expected docs 'docs_per_user', it will terminate.
    log_info('------------------------------------------')
    log_info('START concurrent user / doc creation')
    log_info('------------------------------------------')
    users = create_docs(
        sg_admin_url=sg_admin_url,
        sg_url=lb_url,
        sg_db=sg_db,
        num_users=num_users,
        number_docs_per_user=docs_per_user,
        create_batch_size=create_batch_size,
        create_delay=create_delay
    )
    assert len(users) == num_users
    log_info('------------------------------------------')
    log_info('END concurrent user / doc creation')
    log_info('------------------------------------------')

    # Start termination task
    with ProcessPoolExecutor(max_workers=10) as term_ex:
        terminator_task = term_ex.submit(
            start_terminator,
            lb_url,
            sg_db,
            users,
            update_runtime_sec,
            changes_terminator_doc_id,
            sg_admin_url
        )

    # Start changes processing
    with ProcessPoolExecutor(max_workers=num_users) as pex:
        # Start changes feeds in background process
        changes_workers_task = pex.submit(
            start_changes_processing,
            lb_url,
            sg_db,
            users,
            changes_delay,
            changes_limit,
            changes_terminator_doc_id
        )

        log_info('------------------------------------------')
        log_info('START concurrent updates')
        log_info('------------------------------------------')
        # Start concurrent updates of update
        # Update batch size is the number of users that will concurrently update all of their docs
        users = update_docs(
            sg_url=lb_url,
            sg_db=sg_db,
            users=users,
            update_runtime_sec=update_runtime_sec,
            batch_size=update_batch_size,
            docs_per_user_per_update=docs_per_user_per_update,
            update_delay=update_delay,
            terminator_doc_id=changes_terminator_doc_id
        )

        all_user_channels = []
        for k, v in users.items():
            log_info('User ({}) updated docs {} times!'.format(k, v['updates']))
            all_user_channels.append(k)

        log_info('------------------------------------------')
        log_info('END concurrent updates')
        log_info('------------------------------------------')

        # Block on changes completion
        try:
            log_info("Waiting for the changes_workers_task to complete")
            users = changes_workers_task.result()
            # Print the summary of the system test
            print_summary(users)
        except:
            if changes_workers_task.running():
                changes_workers_task.cancel()

        # TODO: Validated expected changes


def start_terminator(lb_url, sg_db, users, update_runtime_sec, changes_terminator_doc_id, sg_admin_url):
    with ProcessPoolExecutor(max_workers=2) as term_ex:
        term_future = term_ex.submit(
            terminate,
            lb_url,
            sg_db,
            users,
            update_runtime_sec,
            changes_terminator_doc_id,
            sg_admin_url
        )

        # Block on termination task
        log_info("Waiting for the terminator_task to complete")
        for tfuture in as_completed(term_future):
            tfuture.result()


def terminate(lb_url, sg_db, users, update_runtime_sec, changes_terminator_doc_id, sg_admin_url):
    start = time.time()
    log_info('Starting Terminator at : {}'.format(start))
    while True:
        elapsed_sec = time.time() - start
        if elapsed_sec > update_runtime_sec:
            log_info('Terminator: Runtime limit reached. Exiting ...')
            # Broadcast termination doc to all users
            terminator_channel = 'terminator'
            send_changes_termination_doc(lb_url, sg_db, users, changes_terminator_doc_id, terminator_channel)
            # Overwrite each users channels with 'terminator' so their changes feed will backfill with the termination doc
            grant_users_access(users, [terminator_channel], sg_admin_url, sg_db)
            return
        else:
            time.sleep(5)


def print_summary(users):
    """ Pretty print user results for simulation """
    log_info('------------------------------------------')
    log_info('Summary')
    log_info('------------------------------------------')
    for user_name, value in users.items():
        num_user_docs = len(value['doc_ids'])
        log_info('-> {} added: {} docs'.format(user_name, num_user_docs))

        # _doc_ids filter only works with normal changes feed
        if not user_name.startswith('filtered_doc_ids'):
            log_info('  - CHANGES {} (normal), {} (longpoll), {} (continous)'.format(
                len(value['normal']),
                len(value['longpoll']),
                len(value['continuous'])
            ))
        else:
            log_info('  - CHANGES {} (normal)'.format(
                len(value['normal'])
            ))


def grant_users_access(users, channels, sg_admin_url, sg_db):
    sg_client = MobileRestClient()
    for username in users:
        sg_client.update_user(url=sg_admin_url, db=sg_db, name=username, password=USER_PASSWORD, channels=channels)


def send_changes_termination_doc(sg_url, sg_db, users, terminator_doc_id, terminator_channel):
    sg_client = MobileRestClient()

    random_user_id = random.choice(users.keys())
    random_user = users[random_user_id]
    log_info('Sending changes termination doc for all users')
    doc = {'_id': terminator_doc_id, 'channels': [terminator_channel]}
    sg_client.add_doc(url=sg_url, db=sg_db, doc=doc, auth=random_user['auth'])


def start_polling_changes_worker(sg_url, sg_db, user_name, user_auth, changes_delay, changes_limit, terminator_doc_id, feed, channels_filtered, doc_ids_filtered):
    sg_client = MobileRestClient()
    since = 0
    latest_changes = {}
    found_terminator = False

    # Pass a channel filter to changes request if filtered is true
    filter_type = None
    filter_channels = None
    filter_doc_ids = None

    if channels_filtered:
        filter_type = 'sync_gateway/bychannel'
        filter_channels = ['even', 'terminator']

    elif doc_ids_filtered:
        filter_type = '_doc_ids'
        filter_doc_ids = ['terminator']

    while True:

        # If terminator doc is found, terminate the polling loop
        if found_terminator:
            log_info('Found terminator ({}, {})'.format(user_name, feed))
            return user_name, latest_changes

        log_info('_changes ({}) for ({}) since: {}'.format(feed, user_name, since))
        changes = sg_client.get_changes(
            url=sg_url,
            db=sg_db,
            since=since,
            auth=user_auth,
            feed=feed,
            limit=changes_limit,
            filter_type=filter_type,
            filter_channels=filter_channels,
            filter_doc_ids=filter_doc_ids
        )

        # A termination doc was processed, exit on the next loop
        for change in changes['results']:
            if change['id'] == terminator_doc_id:
                found_terminator = True
            else:
                # Add latest rev to to latest_changes map
                if len(change['changes']) >= 1:
                    latest_changes[change['id']] = change['changes'][0]['rev']
                else:
                    latest_changes[change['id']] = ''

        since = changes['last_seq']
        time.sleep(changes_delay)


def start_continuous_changes_worker(sg_url, sg_db, user_name, user_auth, terminator_doc_id, channels_filtered):

    sg_client = MobileRestClient()

    latest_changes = {}

    # Pass a channel filter to changes request if filtered is true
    filter_type = None
    filter_channels = None

    if channels_filtered:
        filter_type = 'sync_gateway/bychannel'
        filter_channels = ['even', 'terminator']

    log_info('_changes (continuous) for ({}) since: 0'.format(user_name))
    stream = sg_client.stream_continuous_changes(
        sg_url,
        sg_db,
        since=0,
        auth=user_auth,
        filter_type=filter_type,
        filter_channels=filter_channels
    )

    for line in stream.iter_lines():

        # filter out keep-alive new lines
        if line:
            decoded_line = line.decode('utf-8')
            change = json.loads(decoded_line)

            if change['id'] == terminator_doc_id:
                log_info('Found terminator ({}, continuous)'.format(user_name))
                return user_name, latest_changes

            else:
                if len(change['changes']) >= 1:
                    latest_changes[change['id']] = change['changes'][0]['rev']
                else:
                    latest_changes[change['id']] = ''


def start_changes_processing(sg_url, sg_db, users, changes_delay, changes_limit, terminator_doc_id):

    # Make sure there are enough workers for 3 changes feed types for each user
    workers = len(users) * 3

    with ProcessPoolExecutor(max_workers=workers) as changes_pex:

        # Start 3 changes feed types for each user:
        #  - looping normal
        #  - looping longpoll
        #  - continuous
        # For 'filtered_channel_user' users:
        #  - Apply a syncgateway/bychannel filter to the changes feed
        # For 'filtered_doc_ids_user' users:
        #  - Apply a _doc_ids filter to the normal changes feed (limitation of the filter type)

        normal_changes_tasks = []
        longpoll_changes_tasks = []
        continuous_changes_tasks = []

        for user_key, user_val in users.items():

            channels_filtered = False
            doc_ids_filtered = False
            if user_key.startswith('filtered_channel'):
                channels_filtered = True
            elif user_key.startswith('filtered_doc_ids'):
                doc_ids_filtered = True

            # Start a looping normal changes feed for user
            normal_changes_tasks.append(
                changes_pex.submit(
                    start_polling_changes_worker,
                    sg_url,
                    sg_db,
                    user_key,
                    user_val['auth'],
                    changes_delay,
                    changes_limit,
                    terminator_doc_id,
                    "normal",
                    channels_filtered,
                    doc_ids_filtered
                )
            )

            # Start a looping longpoll changes feed for user
            if not doc_ids_filtered:
                longpoll_changes_tasks.append(
                    changes_pex.submit(
                        start_polling_changes_worker,
                        sg_url,
                        sg_db,
                        user_key,
                        user_val['auth'],
                        changes_delay,
                        changes_limit,
                        terminator_doc_id,
                        "longpoll",
                        channels_filtered,
                        False
                    )
                )

            # Start continuous changes feed for each user
            if not doc_ids_filtered:
                continuous_changes_tasks.append(
                    changes_pex.submit(
                        start_continuous_changes_worker,
                        sg_url,
                        sg_db,
                        user_key,
                        user_val['auth'],
                        terminator_doc_id,
                        channels_filtered
                    )
                )

        # Block on termination of "normal" changes feeds
        for changes_task in as_completed(normal_changes_tasks):
            user_name, latest_change = changes_task.result()
            users[user_name]['normal'] = latest_change

        # Block on termination of "longpoll" changes feeds
        for changes_task in as_completed(longpoll_changes_tasks):
            user_name, latest_change = changes_task.result()
            users[user_name]['longpoll'] = latest_change

        # Block on termination of "continuous" changes feeds
        for changes_task in as_completed(continuous_changes_tasks):
            user_name, latest_change = changes_task.result()
            users[user_name]['continuous'] = latest_change

    return users


def create_user_names(num_users):
    """ Takes a number of users and returns a list of usernames """

    num_per_type = num_users / len(USER_TYPES)
    user_names = []

    for user_type in USER_TYPES:
        for i in range(num_per_type):
            user_names.append('{}_{}'.format(user_type, i))

    return user_names


def add_user_docs(client, sg_url, sg_db, user_name, user_auth, channels, number_docs_per_user, batch_size, create_delay):

    doc_ids = []
    docs_pushed = 0
    batch_count = 0

    # Even filtered users should add docs with ['even'] channel
    # Odd filtered users should add docs with ['odd'] channel
    if user_name.startswith('filtered_channel_user'):
        # The split below will result in the following format ['filtered', 'channel', 'user', '2']
        user_name_parts = user_name.split('_')
        user_index = int(user_name_parts[3])
        if user_index % 2 == 0:
            channels = ['even']
        else:
            channels = ['odd']

    while docs_pushed < number_docs_per_user:

        # Create batch of docs
        docs = document.create_docs(
            doc_id_prefix='{}-{}'.format(user_name, batch_count),
            number=batch_size,
            prop_generator=document.doc_1k,
            channels=channels
        )

        # Add batch of docs
        log_info('User ({}) adding {} docs.'.format(user_name, number_docs_per_user))
        docs = client.add_bulk_docs(sg_url, sg_db, docs, auth=user_auth)
        batch_doc_ids = [doc['id'] for doc in docs]
        doc_ids.extend(batch_doc_ids)

        docs_pushed += batch_size
        batch_count += 1
        # Sleep 'create_delay' second before adding another batch
        time.sleep(create_delay)

    return doc_ids


def create_users_add_docs_task(user_name,
                               sg_admin_url,
                               sg_url,
                               sg_db,
                               number_docs_per_user,
                               batch_size,
                               create_delay):

    sg_client = MobileRestClient()

    # Create user
    if user_name.startswith('unique'):
        # Doc channel should be unique for each users
        channels = [user_name]
    elif user_name.startswith('shared'):
        # Doc channel should be shared for each doc with this user type
        channels = ['shared']
    elif user_name.startswith('filtered_channel'):
        channels = ['even', 'odd']
    elif user_name.startswith('filtered_doc_ids'):
        channels = ['terminator']
    else:
        raise ValueError('Unexpected user type: {}'.format(user_name))

    sg_client.create_user(
        url=sg_admin_url,
        db=sg_db,
        name=user_name,
        password=USER_PASSWORD,
        channels=channels
    )

    # Create session
    user_auth = sg_client.create_session(
        url=sg_admin_url,
        db=sg_db,
        name=user_name, password=USER_PASSWORD
    )

    # Start bulk doc creation
    doc_ids = add_user_docs(
        client=sg_client,
        sg_url=sg_url,
        sg_db=sg_db,
        user_name=user_name,
        user_auth=user_auth,
        channels=channels,
        number_docs_per_user=number_docs_per_user,
        batch_size=batch_size,
        create_delay=create_delay
    )

    return user_name, user_auth, doc_ids


def create_docs(sg_admin_url, sg_url, sg_db, num_users, number_docs_per_user, create_batch_size, create_delay):
    """ Concurrent creation of docs """

    users = {}

    start = time.time()
    log_info('Starting {} users to add {} docs per user'.format(num_users, number_docs_per_user))

    user_names = create_user_names(num_users)

    with ProcessPoolExecutor(max_workers=10) as pe:

        # Start concurrent create block
        futures = [pe.submit(
            create_users_add_docs_task,
            user_name=user_name,
            sg_admin_url=sg_admin_url,
            sg_url=sg_url,
            sg_db=sg_db,
            number_docs_per_user=number_docs_per_user,
            batch_size=create_batch_size,
            create_delay=create_delay
        ) for user_name in user_names]

        # Block until all futures are completed or return
        # exception in future.result()
        for future in as_completed(futures):
            username, auth, doc_ids = future.result()
            log_info('User ({}) done adding docs.'.format(username))

            # Add user to global dictionary
            users[username] = {
                'auth': auth,
                'doc_ids': doc_ids,
                'updates': 0
            }

    end = time.time() - start
    log_info('Doc creation of {} docs per user and delay: {}s took -> {}s'.format(
        number_docs_per_user, create_delay, end
    ))

    return users


def update_docs_task(users, user_type, user_index, sg_url, sg_db, docs_per_user_per_update, terminator_doc_id):

    user_name = '{}_{}'.format(user_type, user_index)

    # Get a random value to determin the update method
    # ~ 90% ops bulk, 10% ops single
    rand = random.random()
    if rand <= 0.90:
        update_method = 'bulk_docs'
    else:
        update_method = 'put'

    sg_client = MobileRestClient()

    # Get a random user
    current_user_auth = users[user_name]['auth']
    current_user_doc_ids = list(users[user_name]['doc_ids'])

    if terminator_doc_id in current_user_doc_ids:
        log_info('Found terminator ({})'.format(user_name))
        return user_name

    # Get a random subset of docs to update
    user_docs_subset_to_update = []
    for _ in range(docs_per_user_per_update):
        random_doc_id = random.choice(current_user_doc_ids)
        user_docs_subset_to_update.append(random_doc_id)
        current_user_doc_ids.remove(random_doc_id)

    log_info('Updating {} docs, method ({}) number of updates: {} ({})'.format(
        len(user_docs_subset_to_update),
        update_method,
        users[user_name]['updates'],
        user_name
    ))

    # Update the user's docs
    if update_method == 'bulk_docs':
        # Get docs for that user
        user_docs, errors = sg_client.get_bulk_docs(url=sg_url, db=sg_db, doc_ids=user_docs_subset_to_update, auth=current_user_auth)
        assert len(errors) == 0

        # Update the 'updates' property
        for doc in user_docs:
            doc['updates'] += 1

        # Add the docs via build_docs
        sg_client.add_bulk_docs(url=sg_url, db=sg_db, docs=user_docs, auth=current_user_auth)

    else:

        # Do a single GET / PUT for each of the user docs
        for doc_id in current_user_doc_ids:
            doc = sg_client.get_doc(url=sg_url, db=sg_db, doc_id=doc_id, auth=current_user_auth)
            doc['updates'] += 1
            sg_client.put_doc(url=sg_url, db=sg_db, doc_id=doc_id, doc_body=doc, rev=doc['_rev'], auth=current_user_auth)

    return user_name


def update_docs(sg_url, sg_db, users, update_runtime_sec, batch_size, docs_per_user_per_update, update_delay, terminator_doc_id):

    log_info('Updating {} doc/user per update'.format(docs_per_user_per_update))
    log_info('Starting updates with batch size (concurrent users updating): {} and delay: {}s'.format(
        batch_size,
        update_delay
    ))
    log_info('Continue to update for {}s'.format(update_runtime_sec))

    num_users_per_type = len(users) / len(USER_TYPES)
    current_user_index = 0
    sg_client = MobileRestClient()
    random_user_id = random.choice(users.keys())
    random_user = users[random_user_id]

    while True:
        all_docs = sg_client.get_all_docs(url=sg_url, db=sg_db, auth=random_user['auth'], logr=False)
        for doc in all_docs['rows']:
            if doc['id'] == terminator_doc_id:
                return users

        all_docs = None

        with ProcessPoolExecutor(max_workers=batch_size) as pe:

            # Pick out batch size users from each user type
            # and update all of the users docs.
            # For example if batch_size == num_users_per_type,
            # All users would update the docs
            for user_type in USER_TYPES:
                update_futures = [pe.submit(
                    update_docs_task,
                    users,
                    user_type,
                    current_user_index + i,
                    sg_url,
                    sg_db,
                    docs_per_user_per_update,
                    terminator_doc_id
                ) for i in range(batch_size)]

            # Block until all update_futures are completed or return
            # exception in future.result()
            for future in as_completed(update_futures):
                # Increment updates
                user = future.result()
                users[user]['updates'] += 1
                log_info('Completed updates ({})'.format(user))

        current_user_index = (current_user_index + batch_size) % num_users_per_type
        time.sleep(update_delay)


def delete_views(cbs_session, cbs_admin_url, bucket_name):
    """ Deletes all SG Views from Couchbase Server
    """

    # Delete the SG views before seeding the server
    # We want to see how long does it take for SG views to get created
    for view in SG_VIEWS:
        log_info('Deleting view: {}'.format(view))
        try:
            resp = cbs_session.delete('{}/{}/_design/{}'.format(cbs_admin_url, bucket_name, view))
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 404:
                log_info('View already deleted: {}'.format(view))
            else:
                raise


def load_bucket(sdk_client, server_seed_docs):
    # Seed the server with server_seed_docs number of docs
    num_batches = server_seed_docs / 1000
    count = 0
    for batch_num in range(num_batches):
        docs = {'doc_{}_{}'.format(batch_num, i): {'foo': 'bar'} for i in range(1000)}
        sdk_client.upsert_multi(docs)
        count += 1000
        log_info('Created {} total docs ...'.format(count))


def wait_for_view_creation(cbs_session, cbs_admin_url, bucket_name):
    # Wait for the views to be ready
    # TODO: Add this to couchbase_server.py
    start = time.time()
    for view in SG_VIEWS:
        for index in SG_VIEWS[view]:
            log_info('Waiting for view {}/{} to be finished'.format(view, index))
            resp = cbs_session.get('{}/{}/_design/{}/_view/{}?stale=false'.format(cbs_admin_url, bucket_name, view, index))
            resp.raise_for_status()
    end = time.time()
    log_info('Views creation took {} seconds'.format(end - start))
