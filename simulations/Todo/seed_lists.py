from __future__ import print_function

import uuid
from datetime import datetime

from couchbase.bucket import Bucket

BUCKET_NAME = 'todo'
SDK_CLIENT = Bucket('couchbase://localhost/{}'.format(BUCKET_NAME), password='password')
USERS = ['user1', 'user2']


def seed_lists():
    add_list('user1', 'My Top 5 golang builtin', ['panic', 'append', 'copy', 'make', 'close'])
    add_list('user1', 'Smiths singles', ['Ask', 'Panic', 'How Soon is Now', 'Sheila Take a Bow'])
    add_list('user1', 'What To Do When Demo Laptop Crashes', ['Switch to backup', 'Realize there is no backup', 'Panic'])
    add_list('user2', 'Things the Guide Says Not To Do', ['Forget your towel', 'Panic'])
    add_list('user2', 'Sync Gateway 1.5 Closedown', ['Code Complete', 'QE Complete', 'Release DP'])


def add_list(user, name, tasks):

    # Create list
    list_id = user + '.' + name.replace(' ', '')
    list_body = {'name': name, 'owner': user, 'type': 'task-list'}
    print('Upserting list: {}'.format(list_id))
    SDK_CLIENT.upsert(list_id, list_body)

    # Create tasks for list
    for task_name in tasks:
        task_id = str(uuid.uuid4())
        task_body = {
            'complete': False,
            'createdAt': str(datetime.now()),
            'task': task_name,
            'taskList': {
                'id': list_id,
                'owner': user
            },
            'type': 'task'
        }
        SDK_CLIENT.upsert(task_id, task_body)


if __name__ == "__main__":
    seed_lists()
