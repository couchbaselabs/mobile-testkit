
from lib.user import User


def verify_same_docs(expected_num_docs, doc_dict_one, doc_dict_two):

    # assert each dictionary is of expected length
    assert len(doc_dict_one) == expected_num_docs
    assert len(doc_dict_two) == expected_num_docs

    # get doc ids
    ids_one = doc_dict_one.keys()
    ids_two = doc_dict_two.keys()

    # Check keys of the dictionary are the same
    assert set(ids_one) == set(ids_two)

    # Compare _revs from each dictionary
    for k in ids_one:
        assert doc_dict_one[k] == doc_dict_two[k]

    print(" -> doc_dict_one == doc_dict_two expected (num_docs: {})".format(expected_num_docs))


def verify_changes(users, expected_num_docs, expected_num_revisions, expected_docs):

    # When users create or update a doc on sync_gateway, the response of the REST call
    # is stored in the users cache. 'expected_docs' is a scenario level dictionary created
    # from the combination of these user caches. This is used to create expected results
    # when comparing against the changes feed for each user.

    errors = {
        "unexpected_changes_length": 0,
        "invalid_expected_docs_length": 0,
        "duplicate_expected_ids": 0,
        "duplicate_changes_doc_ids": 0,
        "expected_doc_ids_differ_from_changes_doc_ids": 0,
        "invalid_rev_id": 0,
        "unexpected_rev_id_prefix": 0,
        "unexpected_num_updates": 0
    }

    if type(users) is list:
        user_list = users
    else:
        # Allow a single user to be passed
        user_list = list()
        user_list.append(users)

    if type(expected_docs) is not dict:
        raise Exception("Make sure 'expected_docs' is a dictionary")

    for user in user_list:

        changes = user.get_changes(include_docs=True)
        results = changes["results"]

        changes_results = list()
        for result in results:
            changes_result = dict()
            if not result["id"].startswith("_user"):
                changes_result["id"] = result["doc"]["_id"]
                changes_result["rev"] = result["doc"]["_rev"]
                changes_result["updates"] = result["doc"]["updates"]
                changes_results.append(changes_result)

        # Check expected_num_docs matches number of changes results
        if expected_num_docs != len(changes_results):
            errors["unexpected_changes_length"] += 1

        # Check number of expected num docs matched number of expected doc ids
        if expected_num_docs != len(expected_docs):
            errors["invalid_expected_docs_length"] += 1

        # Get ids from expected docs
        expected_doc_ids = expected_docs.keys()

        # Assert there are no duplicates in expected doc ids
        if len(expected_doc_ids) != len(set(expected_doc_ids)):
            errors["duplicate_expected_ids"] += 1

        # Get ids from all changes results
        changes_doc_ids = [result["id"] for result in changes_results]

        # Assert there are no duplicates in changes doc ids
        if len(changes_doc_ids) != len(set(changes_doc_ids)):
            errors["duplicate_changes_doc_ids"] += 1

        # Assert the expected doc ids and changes doc ids are the same
        if set(expected_doc_ids) != set(changes_doc_ids):
            errors["expected_doc_ids_differ_from_changes_doc_ids"] += 1

        for result in changes_results:
            # Compare revision number for id
            if expected_docs[result["id"]] != result["rev"]:
                errors["invalid_rev_id"] += 1

            # IMPORTANT - This assumes that no conflicts are created via new_edits in the doc PUT
            # Assert that the revision id prefix matches the number of expected revisions
            rev_id_prefix = result["rev"].split("-")[0]

            # rev-id prefix will be 1 when document is created
            # For any non-conflicting update, it will be incremented by one
            if expected_num_revisions != int(rev_id_prefix) - 1:
                errors["unexpected_rev_id_prefix"] += 1

            # Check number of expected updates matched the updates on the _changes doc
            if expected_num_revisions != result["updates"]:
                errors["unexpected_num_updates"] += 1

        # Allow printing updates even if changes feed length is 0
        if len(changes_results) == 0:
            updates = 0
        else:
            updates = changes_results[0]["updates"]

        print(" -> |{0}| expected (num_docs: {1} num_revisions: {2}) _changes (num_docs: {3} updates: {4})".format(
            user.name,
            expected_num_docs,
            expected_num_revisions,
            len(changes_doc_ids),
            updates
        ))

        # Print any error that may have occured
        error_count = 0
        for key, val in errors.items():
            if val != 0:
                print("<!> VERIFY ERROR - name: {}: occurences: {}".format(key, val))
                error_count += 1

        assert error_count == 0
