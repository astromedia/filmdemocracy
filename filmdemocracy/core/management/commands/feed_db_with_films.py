from django.core.management.base import BaseCommand

from filmdemocracy.democracy.models import FilmDb, FilmDbTranslation
from filmdemocracy.utils.mongodb_manager import MongoDBManager
from filmdemocracy.utils.films_dbs_manager import FilmsDBsManager
from filmdemocracy.secrets import MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD


class Command(BaseCommand):

    help = 'Feed the database with the info stored in the mongodb'
    
    def __init__(self, **kwargs):
        self.dbs_manager = None
        self.test_film_ids = [
            '00038650',
            '00047478',
            '00050083',
            '00060196',
            '00068646',
            '00071562',
            '00073486',
            '00080684',
            '00099685',
            '00102926',
            '00108052',
            '00109830',
            '00110912',
            '00111161',
            '00114369',
            '00118799',
            '00120737',
            '00133093',
            '00137523',
            '00167260',
            '00167261',
            '00317248',
            '00468569',
            '01375666',
            '07286456',
        ]
        super().__init__(**kwargs)

    def process_mongodb_films(self, ok_film_ids, **options):
        films_count = 0
        for imdb_id in ok_film_ids:
            film_info = self.dbs_manager.mongodb.get_film(imdb_id)
            assert imdb_id == film_info['imdb_id']
            if options['verbose']:
                self.stdout.write(f"film info {imdb_id=}: {film_info=}")
            film_data = film_info['data']
            if options['verbose']:
                self.stdout.write(f"film data {imdb_id=}: {film_data=}")
            film_dict = self.dbs_manager.parse_film_data(film_data)
            if options['verbose']:
                self.stdout.write(f"film dict {imdb_id=}: {film_dict=}")
            assert film_dict is not None
            if not self.dbs_manager.film_quality_check(film_dict):
                continue
            films_count += 1
            if (film_basics := film_info.get('basics')) and options['verbose']:
                self.stdout.write(f'film basics {imdb_id=}: {film_basics=}')
            if (film_translations := film_info.get('translations')) and options['verbose']:
                self.stdout.write(f'film translations {imdb_id=}: {film_translations=}')
            if options['dryrun']:
                continue
            self.dbs_manager.update_film_data_info(imdb_id, film_dict, overwrite=options['overwrite'])
            if film_basics:
                self.dbs_manager.update_film_basics_info(imdb_id, film_basics, overwrite=options['overwrite'])
            if film_translations:
                self.dbs_manager.update_film_translations_info(imdb_id, film_translations, overwrite=options['overwrite'])
        self.stdout.write(f'  Number of films processed: {films_count}')

    def clean_old_films(self, ok_film_ids, postgres_film_ids, **options):
        films_count = 0
        old_film_ids = set(postgres_film_ids) - set(ok_film_ids)
        self.stdout.write(f'  Found {films_count} old films')
        for imdb_id in list(old_film_ids):
            if options['verbose']:
                self.stdout.write(f'  Deleting old film {imdb_id=}')
            if options['dryrun']:
                continue
            self.dbs_manager.delete_film_from_db(imdb_id)
            films_count += 1
        self.stdout.write(f'  Number of films deleted: {films_count}')

    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--test', action='store_true', help='Only insert test films')
        parser.add_argument('--reset', action='store_true', help='Reset postgres films database')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite if film exists')
        parser.add_argument('--dryrun', action='store_true', help='Dry run')

    def handle(self, *args, **options):
        self.stdout.write('Feeding the database with the info stored in the mongodb')
        self.dbs_manager = FilmsDBsManager(
            mongodb_url='mongodb:27017',
            mongodb_username=MONGO_INITDB_ROOT_USERNAME,
            mongodb_password=MONGO_INITDB_ROOT_PASSWORD,
            verbose=options['verbose']
            )
        if options['reset']:
            self.dbs_manager.delete_all_films()
            self.dbs_manager.delete_all_films_translations()
        if options['test']:
            ok_film_ids = self.test_film_ids
        else:
            ok_film_ids = self.dbs_manager.get_film_ids_in_mongodb(status='OK')
        postgres_film_ids = self.dbs_manager.get_film_ids_in_postgresdb()
        self.stdout.write(f'{options=}')
        self.process_mongodb_films(ok_film_ids, **options)
        self.clean_old_films(ok_film_ids, postgres_film_ids, **options)
        self.stdout.write('  OK')
