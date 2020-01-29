import json
import glob
import os
import tarfile
from pprint import pformat
import concurrent.futures
import pickle
import time

from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.democracy.models import FilmDb, FilmDbTranslation


MAX_CONNECTIONS = 32
MIN_IMDB_VOTES = 20
MAIN_LANGUAGE = 'en'


class Command(BaseCommand):
    help = 'Feed the database with the films jsons located in /local'

    FILMS_JSONS_DUMPS_DIR = os.path.join(os.getenv('MAIN_DIR', '.'), 'local/films_jsons_dumps')
    FILMS_JSONS_DEAD_FILMS_FILE = os.path.join(os.getenv('MAIN_DIR', '.'), 'local/films_jsons_crash.pkl')

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
    def include_film_in_db_test(film_dict):
        if (film_dict['Type'] != 'movie' or
                film_dict['Director'] == 'N/A' or
                film_dict['Poster'] == 'N/A' or
                film_dict['Title'] == 'N/A' or
                (film_dict['imdbVotes'] < MIN_IMDB_VOTES and film_dict['Year'] < 2019) or
                'X' in film_dict['Rated']):
            return False
        else:
            return True

    def update_filmdb_info(self, film_id, film_dict, overwrite=False, cleandb=False, onlycleandb=False):
        include_film_in_db = self.include_film_in_db_test(film_dict)
        if include_film_in_db and not onlycleandb:
            filmdb, created = FilmDb.objects.get_or_create(imdb_id=film_id)
            if created or overwrite:
                try:
                    FilmDbTranslation.objects.get_or_create(imdb_id=film_id, filmdb=filmdb, title=film_dict['Title'], language_code=MAIN_LANGUAGE)
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
                    return None
                except KeyError as e:
                    self.stdout.write(f'    ***FAILED: uploading film "{film_id}" with "KeyError" exception: {e}')
                    self.print_film_info(film_dict)
                    filmdb.delete()
                    return film_id
                except django.db.utils.DataError as e:
                    self.stdout.write(f'    ***FAILED: uploading film "{film_id}" with "DataError" exception: {e}')
                    self.print_film_info(film_dict)
                    filmdb.delete()
                    return film_id
                except Exception as e:
                    self.stdout.write(f'    ***FAILED: uploading film "{film_id}" with UNKNOWN exception: {e}')
                    self.print_film_info(film_dict)
                    filmdb.delete()
                    return film_id
        elif not include_film_in_db and (cleandb or onlycleandb):
            self.delete_film_from_db(film_id)
            return None

    def delete_film_from_db(self, film_id):
        try:
            filmdb = FilmDb.objects.get(imdb_id=film_id)
            filmdb.delete()
            self.stdout.write(f'    Cleaned film "{film_id}" from db')
        except FilmDb.DoesNotExist:
            pass

    def print_film_info(self, film_dict):
        self.stdout.write(f"\n{pformat(film_dict)}\n")

    def print_film_info_verbose(self, film_dict):
        self.stdout.write(f"{film_dict['Type']}")

    def process_film_json_file(self, film_id, film_json, updatedb=False, dryrun=False, verbose=False, overwrite=False, cleandb=False, onlycleandb=False):
        # 1) Extract film json
        try:
            assert self.test_film_json_is_valid(film_json)
        except Exception as e:
            # self.stdout.write(f'    ***FAILED: not valid film json for film "{film_id}"')
            if updatedb and (cleandb or onlycleandb):
                self.delete_film_from_db(film_id)
            return film_id
        # 2) Extract film data from film json
        try:
            film_dict = self.parse_film_data_from_film_json(film_json)
            assert film_dict is not None
        except Exception as e:
            self.stdout.write(f'    ***FAILED: parsing film json for film "{film_id}" with exception: {e}')
            self.stdout.write(f"\n{pformat(film_json)}\n")
            if updatedb and (cleandb or onlycleandb):
                self.delete_film_from_db(film_id)
            return film_id
        # 3) Print film dict
        if verbose:
            self.print_film_info_verbose(film_dict)
        # 4) Pass or update db with film dict
        if dryrun:
            return None
        elif updatedb:
            return self.update_filmdb_info(film_id, film_dict, overwrite, cleandb, onlycleandb)

    def process_films_in_dump_tar(self, dump_tar_path, process_options):
        tar_films_count = 0
        fs = []
        dump_tar_dead_films = []
        self.stdout.write(f'    Checking film jsons in dump tar.gz file: {dump_tar_path}')
        tar = tarfile.open(dump_tar_path, "r:gz")
        films_jsons_tar_files = tar.getmembers()
        self.stdout.write(f'    Number of film jsons detected: {len(films_jsons_tar_files)}')
        for film_json_tar_file in films_jsons_tar_files:
            tar_films_count += 1
            film_id = str(film_json_tar_file.name.split('.')[0]).zfill(8)
            # self.stdout.write(f'  Processing film json: {film_id}')
            f = tar.extractfile(film_json_tar_file)
            try:
                film_json = json.loads(f.read())
                fs.append((film_id, film_json))
            except Exception as e:
                # self.stdout.write(f'    ***FAILED: processing film json for film "{film_id}" with exception: {e}')
                dump_tar_dead_films.append(film_id)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONNECTIONS) as executor:
            future_result = (executor.submit(self.process_film_json_file, film_id, film_json, **process_options)
                             for film_id, film_json in fs)
            for i, future in enumerate(concurrent.futures.as_completed(future_result)):
                film_id = future.result()
                if film_id:
                    dump_tar_dead_films.append(film_id)
        return tar_films_count, dump_tar_dead_films

    def process_dump_files(self, process_options):
        films_count = 0
        dead_films = []
        dump_files_dir = self.FILMS_JSONS_DUMPS_DIR
        dump_files = glob.glob(os.path.join(dump_files_dir, '*.tar.gz'))
        self.stdout.write(f'  Number of dump file detected: {len(dump_files)}')
        for dump_file in sorted(dump_files):
            self.stdout.write(f'  Processing dump file: {os.path.basename(dump_file)}')
            tar_films_count, dump_tar_dead_films = self.process_films_in_dump_tar(dump_file, process_options)
            films_count += tar_films_count
            dead_films += dump_tar_dead_films
            time.sleep(180)
        self.stdout.write(f'  Number of films processed: {films_count}')
        self.stdout.write(f'  Number of dead films found: {len(dead_films)}')
        with open(self.FILMS_JSONS_DEAD_FILMS_FILE, 'wb') as f:
            pickle.dump(dead_films, f)

    def add_arguments(self, parser):
        parser.add_argument('--dryrun', action='store_true', help='Dry run')
        parser.add_argument('--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--updatedb', action='store_true', help='Add or delete film db objects')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite film db objects')
        parser.add_argument('--cleandb', action='store_true', help='Delete deprecated film db objects')
        parser.add_argument('--onlycleandb', action='store_true', help='Only delete deprecated film db objects')

    def handle(self, *args, **options):
        self.stdout.write(f'Feeding local film jsons to database:')
        process_options = {
            'dryrun': options['dryrun'],
            'updatedb': options['updatedb'],
            'overwrite': options['overwrite'],
            'cleandb': options['cleandb'],
            'onlycleandb': options['onlycleandb'],
            'verbose': options['verbose'],
        }
        if not process_options['dryrun'] and not process_options['updatedb']:
            self.stdout.write(f'Must select either "--dryrun" or "--updatedb"')
            raise
        if process_options['dryrun'] and process_options['updatedb']:
            self.stdout.write(f'Invalid command combination: "--dryrun" and "--updatedb"')
            raise
        if not process_options['updatedb'] and (process_options['overwrite'] or process_options['cleandb'] or process_options['onlycleandb']):
            self.stdout.write(f'Invalid command combination: "--overwrite" and/or "--onlycleandb" and/or "--cleandb" without "--updatedb"')
            raise
        self.process_dump_files(process_options)
        self.stdout.write(f'  OK')
