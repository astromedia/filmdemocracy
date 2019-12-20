import json
import glob
import os
import tarfile
from pprint import pprint
import ntpath

from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.democracy.models import FilmDb


class Command(BaseCommand):
    help = 'Feed the database with the films jsons located in /local'

    # FILMS_JSONS_DUMPS_DIR = '/code/local/films_jsons_dumps'
    FILMS_JSONS_DUMPS_DIR = './local/films_jsons_dumps'
    FILMS_JSONS_CRASH_DIR = './local/films_jsons_crash'

    @staticmethod
    def get_film_data_from_film_json(film_id, film_json):
        if 'Error' in film_json:
            return None
        else:
            film_dict = {
                'Title': film_json['Title'],
                'imdbRating': film_json['imdbRating'],
                'Metascore': film_json['Metascore'],
                'Year': int(film_json['Year'][0:4]),
                'Director': film_json['Director'],
                'Writer': film_json['Writer'],
                'Actors': film_json['Actors'],
                'Poster': film_json['Poster'],
                'Runtime': film_json['Runtime'],
                'Language': film_json['Language'],
                'Rated': film_json['Rated'],
                'Country': film_json['Country'],
                'Plot': film_json['Plot'],
            }
            return film_dict

    @staticmethod
    def update_filmdb_info(film_id, film_dict):
        filmdb, created = FilmDb.objects.get_or_create(imdb_id=str(film_id).zfill(8))
        if created:
            try:
                filmdb.title = film_dict['Title']
                filmdb.imdb_rating = film_dict['imdbRating']
                filmdb.metascore = film_dict['Metascore']
                filmdb.year = film_dict['Year']
                filmdb.director = film_dict['Director']
                filmdb.writer = film_dict['Writer']
                filmdb.actors = film_dict['Actors']
                filmdb.poster_url = film_dict['Poster']
                filmdb.duration = film_dict['Runtime']
                filmdb.language = film_dict['Language']
                filmdb.rated = film_dict['Rated']
                filmdb.country = film_dict['Country']
                filmdb.plot = film_dict['Plot']
                filmdb.save()
            except KeyError:
                filmdb.delete()
            except django.db.utils.DataError:
                self.stdout.write(f"***FAILED: uploading {film_id} with film_dict:\n")
                pprint(film_dict)
                filmdb.delete()

    def print_film_info(self, film_id, film_dict):
        try:
            self.stdout.write(f"")
            self.stdout.write(f"    Title: {film_dict['Title']}")
            self.stdout.write(f"    imdbRating: {film_dict['imdbRating']}")
            self.stdout.write(f"    Metascore: {film_dict['Metascore']}")
            self.stdout.write(f"    Year: {int(film_dict['Year'][0:4])}")
            self.stdout.write(f"    Director: {film_dict['Director']}")
            self.stdout.write(f"    Writer: {film_dict['Writer']}")
            self.stdout.write(f"    Actors: {film_dict['Actors']}")
            self.stdout.write(f"    Poster: {film_dict['Poster']}")
            self.stdout.write(f"    Runtime: {film_dict['Runtime']}")
            self.stdout.write(f"    Language: {film_dict['Language']}")
            self.stdout.write(f"    Rated: {film_dict['Rated']}")
            self.stdout.write(f"    Country: {film_dict['Country']}")
            self.stdout.write(f"    Plot: {film_dict['Plot']}")
            self.stdout.write(f"")
        except KeyError:
            self.stdout.write(f"***FAILED: printing {film_id} with film_dict:\n")
            pprint(film_dict)

    def process_films_in_dump_tar(self, dump_tar_path, dryrun=False, verbose=False, copycrashed=False):
        self.stdout.write(f'    Checking film jsons in dump tar.gz file: {dump_tar_path}')
        tar = tarfile.open(dump_tar_path, "r:gz")
        films_jsons_files = tar.getmembers()
        self.stdout.write(f'    Number of film jsons detected: {len(films_jsons_files)}')
        for film_json_file in films_jsons_files:
            film_id = film_json_file.name.split('.')[0]
            if verbose:
                self.stdout.write(f'  Processing film json: {film_id}')
            f = tar.extractfile(film_json_file)

            try:
                film_json = json.loads(f.read())
            except:
                self.stdout.write(f'    ***FAILED: reading film json: {film_id}')
                if copycrashed:
                    tar.extract(film_json_file, self.FILMS_JSONS_CRASH_DIR)
                continue

            try:
                film_dict = self.get_film_data_from_film_json(film_id, film_json)
                if film_dict is None and copycrashed:
                    tar.extract(film_json_file, self.FILMS_JSONS_CRASH_DIR)
            except:
                self.stdout.write(f"    ***FAILED: parsing film {film_id} with film_json:\n")
                pprint(film_json)
                if copycrashed:
                    tar.extract(film_json_file, self.FILMS_JSONS_CRASH_DIR)
                continue

            if verbose:
                self.print_film_info(film_id, film_dict)
            if not dryrun:
                self.update_filmdb_info(film_id, film_json)

    def process_dump_files(self, dryrun=False, verbose=False, copycrashed=False):
        dump_files_dir = self.FILMS_JSONS_DUMPS_DIR
        dump_files = glob.glob(os.path.join(dump_files_dir, '*.tar.gz'))
        self.stdout.write(f'  Number of dump file detected: {len(dump_files)}')
        for dump_file in sorted(dump_files):
            self.stdout.write(f'  Processing dump file: {os.path.basename(dump_file)}')
            self.process_films_in_dump_tar(dump_file, dryrun, verbose, copycrashed)

    def add_arguments(self, parser):
        parser.add_argument('--dryrun', action='store_true', help='Dry run')
        parser.add_argument('--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--copycrashed', action='store_true', help='Verbose output')

    def handle(self, *args, **options):
        self.stdout.write(f'Feeding local film jsons to database:')
        self.process_dump_files(options['dryrun'], options['verbose'], options['copycrashed'])
        self.stdout.write(f'  OK')
