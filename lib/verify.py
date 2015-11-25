
def verify_change_with_filter(doc_name_pattern):
    pass


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

    if type(users) is not list:
        users = list(users)

    if type(expected_docs) is not dict:
        raise Exception("Make sure 'expected_docs' is a dictionary")

    for user in users:

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
        changes_doc_ids = [result["id"] for result in changes_result]

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
            if expected_num_revisions != int(rev_id_prefix):
                errors["unexpected_rev_id_prefix"] += 1

            # Check number of expected updates matched the updates on the _changes doc
            if expected_num_revisions != result["updates"]:
                errors["unexpected_num_updates"] += 1

        print(" -> |{0}| expected (num_docs: {1} num_updates: {2}) _changes (num_docs: {3} updates: {4})".format(
            user.name,
            expected_num_docs,
            expected_num_revisions,
            len(changes_doc_ids),
            changes_results[0]["updates"]
        ))

        # Print any error that may have occured
        error_count = 0
        for key, val in errors.items():
            if val != 0:
                print("<!> VERIFY ERROR - name: {}: occurences: {}".format(key, val))
                error_count += 1

        assert error_count == 0
