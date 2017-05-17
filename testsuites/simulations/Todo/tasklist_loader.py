from __future__ import print_function

import uuid
from datetime import datetime
import time

from couchbase.bucket import Bucket

BUCKET_NAME = 'todo'
SDK_CLIENT = Bucket('couchbase://localhost/{}'.format(BUCKET_NAME), password='password')
USERS = ['user1', 'user2']


def load_lists():
    # Create a list for each user. List doc format below
    # sample key = 'user1.4280DE40-A452-4B09-B0D4-D756B0339521'
    # sample value = { 'name': 'User 1 List', 'owner': 'user1', 'type', 'task-list' }
    for user in USERS:
        list_doc_key = '{}.{}'.format(user, uuid.uuid4())
        list_doc_val = {
            'name': '{} SDK: {}'.format(user, time.time()),
            'owner': user,
            'type': 'task-list'
        }

        print('Creating list doc with key: {}, value: {}'.format(list_doc_key, list_doc_val))
        SDK_CLIENT.upsert(list_doc_key, list_doc_val)

        # Create a couple tasks for each user list
        # sample key = 'a7062d1c-339c-42e2-8aad-276528a3da3e'
        # sample value = {
        #    'complete': false,
        #    'createdAt': 1494982643250,
        #    'task': 'test task',
        #    'taskList': {
        #         'id': 'user2.94f1cd96-f771-48d2-85f1-1855cff0b614',
        #         'owner': 'user2'
        #     },
        #     'type': 'task'
        # }
        for i in range(5):
            list_task_key = str(uuid.uuid4())
            list_task_value = {
                'complete': False,
                'createdAt': str(datetime.utcnow()),
                'task': '{} Task {} from SDK'.format(user, i),
                'taskList': {
                    'id': list_doc_key,
                    'owner': user
                },
                'type': 'task'
            }
            SDK_CLIENT.upsert(list_task_key, list_task_value)


if __name__ == "__main__":
    load_lists()
