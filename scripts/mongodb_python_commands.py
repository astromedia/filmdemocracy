import json
import glob
import os
import ntpath
import concurrent.futures
import requests
import tarfile
import time
import re
import shutil
from pprint import pprint
import random

from filmdemocracy.utils.mongodb_manager import MongoDBManager
from filmdemocracy.secrets import MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD


def main():

    # init service:

    mongodb_url='mongodb://localhost:27017/'
    mongodb = MongoDBManager(
        mongodb_url=mongodb_url,
        db_name='filmdemocracy',
        collection_name='films',
        # username=MONGO_INITDB_ROOT_USERNAME,
        # password=MONGO_INITDB_ROOT_PASSWORD,
        )

    # commands:

    # mongodb.destroy_database()
    # mongodb.unset_film_basics_info()
    # mongodb.unset_film_translations_info()
    # print(mongodb.count_films())
    # print(mongodb.count_films(status='OK'))
    # print(mongodb.get_film_ids(status='KO'))
    # pprint(mongodb.get_film('00000211'))
    # pprint(mongodb.get_film(str(random.randint(0, 1e7)).zfill(8)))
    # pprint(mongodb.get_status_stats())
    # pprint(mongodb.get_film_ids_sorted_by_update_date(status='Error', order='ascending', limit=20))
    # pprint(mongodb.get_type_stats())


if __name__ == '__main__':
    main()
