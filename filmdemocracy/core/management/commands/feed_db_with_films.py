import json
import glob
import os
from pprint import pprint
import ntpath

from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.democracy.models import FilmDb


class Command(BaseCommand):
    help = 'Feeds the database with the films jsons located in /local'

    FILMS_JSONS_TEST_DIR = '/code/local/films_jsons_test'
    FILMS_JSONS_TMP_DIR = '/code/local/films_jsons_tmp'
    FILMS_JSONS_DUMPS_DIR = '/code/local/films_jsons_dumps'

    @staticmethod
    def load_film_json(file_path):
        film_json_id = str(int(os.path.splitext(ntpath.basename(file_path))[0])).zfill(7)
        with open(file_path) as json_file:
            film_json = json.load(json_file)
        return film_json_id, film_json

    @staticmethod
    def update_filmdb_info(film_json_id, film_json):
        filmdb, created = FilmDb.objects.get_or_create(imdb_id=film_json_id)
        if created:
            try:
                filmdb.title = film_json['Title']
                filmdb.year = int(film_json['Year'][0:4])
                filmdb.director = film_json['Director']
                filmdb.writer = film_json['Writer']
                filmdb.actors = film_json['Actors']
                filmdb.poster_url = film_json['Poster']
                filmdb.duration = film_json['Runtime']
                filmdb.language = film_json['Language']
                filmdb.rated = film_json['Rated']
                filmdb.country = film_json['Country']
                filmdb.plot = film_json['Plot']
                filmdb.save()
            except KeyError:
                filmdb.delete()
            except django.db.utils.DataError:
                pprint(film_json)
                filmdb.delete()

    def process_films_jsons(self, test=False):
        if test:
            films_jsons_dir = self.FILMS_JSONS_TEST_DIR
        else:
            films_jsons_dir = self.FILMS_JSONS_TMP_DIR
        self.stdout.write(f'  Checking film jsons in directory: {films_jsons_dir}')
        films_jsons_files = glob.glob(os.path.join(films_jsons_dir, '*.json'))
        self.stdout.write(f'  Number of film jsons detected: {len(films_jsons_files)}')
        for film_json_file in films_jsons_files:
            self.stdout.write(f'  Processing film json: {film_json_file}')
            film_json_id, film_json = self.load_film_json(film_json_file)
            self.update_filmdb_info(film_json_id, film_json)

    def add_arguments(self, parser):
        parser.add_argument('--test', action='store_true', help='Feed only test films')

    def handle(self, *args, **options):
        self.stdout.write(f'Feeding local film jsons to database:')
        self.process_films_jsons(options['test'])
        self.stdout.write(f'  OK')
