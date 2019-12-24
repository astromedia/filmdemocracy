import json
import glob
import os
import tarfile
from pprint import pformat

from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.democracy.models import FilmDb


class Command(BaseCommand):
    help = 'Feed the database with the films jsons located in /local'

    FILMS_JSONS_DUMPS_DIR = '/code/local/films_jsons_dumps'
    FILMS_JSONS_CRASH_DIR = '/code/local/films_jsons_crash'

    @staticmethod
    def test_film_json_is_valid(film_json):
        if not film_json or 'Error' in film_json or ('Response' in film_json and film_json['Response'] == 'False'):
            return False
        else:
            return True

    @staticmethod
    def parse_film_data_from_film_json(film_json):
        year_str = str(film_json['Year'])
        if '–' in year_str:
            year_str = year_str.split('–')[0]
        year_int = int(year_str[0:4])
        if film_json['imdbVotes'] == "N/A":
            imdb_votes = 0
        else:
            imdb_votes = int(film_json['imdbVotes'].replace(',', ''))
        film_dict = {
            'Type': film_json['Type'],
            'Title': film_json['Title'],
            'imdbRating': film_json['imdbRating'],
            'imdbVotes': imdb_votes,
            'Metascore': film_json['Metascore'],
            'Year': year_int,
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
    def include_film_in_db(film_dict):
        if (film_dict['Type'] != 'movie' or
                film_dict['Director'] == 'N/A' or
                film_dict['Poster'] == 'N/A' or
                film_dict['Title'] == 'N/A' or
                film_dict['imdbVotes'] < 5):
            return False
        else:
            return True

    def update_filmdb_info(self, film_id, film_dict, overwrite=False, cleandb=False):
        if self.include_film_in_db(film_dict):
            filmdb, created = FilmDb.objects.get_or_create(imdb_id=str(film_id).zfill(8))
            if created or overwrite:
                try:
                    filmdb.title = film_dict['Title']
                    filmdb.imdb_rating = film_dict['imdbRating']
                    filmdb.imdb_votes = film_dict['imdbVotes']
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
                except django.db.utils.DataError as e:
                    self.stdout.write(f'    ***FAILED: uploading film "{film_id}" with "DataError" exception:\n\n{e}\n')
                    self.print_film_info(film_dict)
                    filmdb.delete()
                except Exception as e:
                    self.stdout.write(f'    ***FAILED: uploading film "{film_id}" with UNKNOWN exception:\n\n{e}\n')
                    self.print_film_info(film_dict)
                    filmdb.delete()
        elif not self.include_film_in_db(film_dict) and cleandb:
            try:
                filmdb = FilmDb.objects.get(imdb_id=str(film_id).zfill(8))
                filmdb.delete()
                # self.stdout.write(f'    Cleaned film "{film_id}" from db')
            except FilmDb.DoesNotExist:
                pass

    def print_film_info(self, film_dict):
        self.stdout.write(f"\n{pformat(film_dict)}\n")

    def print_film_info_verbose(self, film_dict):
        self.stdout.write(f"{film_dict['Type']}")

    def process_films_in_dump_tar(self, dump_tar_path, dryrun=False, verbose=False, copycrashed=False, overwrite=False, cleandb=False):
        self.stdout.write(f'    Checking film jsons in dump tar.gz file: {dump_tar_path}')
        tar = tarfile.open(dump_tar_path, "r:gz")
        films_jsons_files = tar.getmembers()
        self.stdout.write(f'    Number of film jsons detected: {len(films_jsons_files)}')
        for film_json_file in films_jsons_files:
            film_id = film_json_file.name.split('.')[0]
            # self.stdout.write(f'  Processing film json: {film_id}')
            f = tar.extractfile(film_json_file)
            # 1) Extract film json
            try:
                film_json = json.loads(f.read())
                assert self.test_film_json_is_valid(film_json)
            except Exception as e:
                self.stdout.write(f'    ***FAILED: processing film json for film "{film_id}" with exception:\n\n{e}\n')
                if copycrashed:
                    tar.extract(film_json_file, self.FILMS_JSONS_CRASH_DIR)
                continue
            # 2) Extract film data from film json
            try:
                film_dict = self.parse_film_data_from_film_json(film_json)
                assert film_dict is not None
            except Exception as e:
                self.stdout.write(f'    ***FAILED: parsing film json for film "{film_id}" with exception:\n\n{e}\n')
                self.stdout.write(f"\n{pformat(film_json)}\n")
                if copycrashed:
                    tar.extract(film_json_file, self.FILMS_JSONS_CRASH_DIR)
                continue
            # 3) Print or update db with film dict
            if verbose:
                self.print_film_info_verbose(film_dict)
            if not dryrun:
                self.update_filmdb_info(film_id, film_dict, overwrite, cleandb)

    def process_dump_files(self, process_options):
        dump_files_dir = self.FILMS_JSONS_DUMPS_DIR
        dump_files = glob.glob(os.path.join(dump_files_dir, '*.tar.gz'))
        self.stdout.write(f'  Number of dump file detected: {len(dump_files)}')
        for dump_file in sorted(dump_files):
            self.stdout.write(f'  Processing dump file: {os.path.basename(dump_file)}')
            self.process_films_in_dump_tar(dump_file, **process_options)

    def add_arguments(self, parser):
        parser.add_argument('--dryrun', action='store_true', help='Dry run')
        parser.add_argument('--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--copycrashed', action='store_true', help='Verbose output')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite film db info')
        parser.add_argument('--cleandb', action='store_true', help='Delete deprecated film db objects')

    def handle(self, *args, **options):
        self.stdout.write(f'Feeding local film jsons to database:')
        process_options = {
            'dryrun': options['dryrun'],
            'verbose': options['verbose'],
            'copycrashed': options['copycrashed'],
            'overwrite': options['overwrite'],
            'cleandb': options['cleandb'],
        }
        self.process_dump_files(process_options)
        self.stdout.write(f'  OK')
