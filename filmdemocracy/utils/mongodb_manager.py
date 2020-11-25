import pymongo


class MongoDBManager:

    def __init__(self, mongodb_url=None, db_name=None, collection_name=None, username=None, password=None):

        self.mongodb_url = mongodb_url
        self.db_name = db_name
        self.collection_name = collection_name
        self.key_name = 'imdb_id'
        self.mongodb_id = '_id'
        self.film_status_codes = ['OK', 'Error', 'Incomplete', 'Pending']

        self.client = pymongo.MongoClient(mongodb_url, username=username, password=password)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]

        if not self.test_index_exists():
            self.collection.create_index([(self.key_name, pymongo.ASCENDING)], background=True, unique=True)

    def test_index_exists(self):
        index_info = self.collection.index_information()
        for item in index_info:
            index_spec = index_info[item]
            if 'key' in index_spec:
                for index_tuple in index_spec['key']:
                    if index_tuple[0] == self.key_name:
                        return True
        return False

    def get_db_status(self):
        return self.db.command("serverStatus")

    def get_film(self, key):
        return self.collection.find_one({self.key_name: key}, {'_id': 0})

    def get_film_status(self, key):
        return self.get_film(key)['status']

    def get_film_data(self, key):
        return self.get_film(key)['data']

    def get_film_basics(self, key):
        return self.get_film(key).get('basics', {})

    def get_film_translations(self, key):
        return self.get_film(key).get('translations', [])

    def update_film(self, key, film_update, upsert=False):
        self.collection.update_one({self.key_name: key}, film_update, upsert=upsert)

    def delete_film(self, key):
        self.collection.delete_one({self.key_name: key})

    def delete_films(self, key_list):
        self.collection.remove({self.key_name: {'$in': key_list}})

    def count_films(self, status=None):
        if status:
            return self.collection.count_documents({'status': status})
        else:
            return self.collection.count_documents({})

    def get_films_cursor(self, status=None):
        if status:
            return self.collection.find({'status': status}, {'_id': 0})
        else:
            return self.collection.find({}, {'_id': 0})

    def get_film_ids(self, status=None):
        if status:
            cursor = self.collection.find({'status': status}, {'_id': 0, self.key_name: 1})
        else:
            cursor = self.collection.find({}, {'_id': 0, self.key_name: 1})
        return [film[self.key_name] for film in cursor]

    def get_film_ids_sorted_by_update_date(self, status=None, order='ascending', limit=None):
        assert order in ['ascending', 'descending']
        if status:
            cursor = self.collection.find({'status': status}, {'_id': 0, self.key_name: 1, 'updated': 1})
        else:
            cursor = self.collection.find({}, {'_id': 0, self.key_name: 1, 'updated': 1})
        if order == 'ascending':
            cursor = cursor.sort('updated', pymongo.ASCENDING)
        elif order == 'descending':
            cursor = cursor.sort('updated', pymongo.DESCENDING)
        if limit:
            cursor = cursor.limit(limit)
        return [film[self.key_name] for film in cursor]

    def get_status_stats(self):
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
        result = list(self.collection.aggregate(pipeline))
        return {row['_id']: row['count'] for row in result}

    def get_type_stats(self):
        pipeline = [
            {"$unwind": "$data"},
            {"$group": {"_id": "$data.Type", "count": {"$sum": 1}}}
            ]
        result = list(self.collection.aggregate(pipeline))
        return {row['_id']: row['count'] for row in result}

    def unset_film_basics_info(self):
        self.collection.update({}, {"$unset": {'basics': 1}}, multi=True)

    def unset_film_translations_info(self):
        self.collection.update({}, {"$unset": {'translations': 1}}, multi=True)

    def destroy_collection(self):
        return self.db.drop_collection(self.collection_name)

    def destroy_database(self):
        return self.client.drop_database(self.db_name)
