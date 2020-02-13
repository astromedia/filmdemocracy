import os
import concurrent.futures

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.democracy.models import FilmDb, FilmDbTranslation


MAX_CONNECTIONS = 32
PRIMARY_LANGUAGE = 'PRI'
ORIGINAL_LANGUAGE = 'ORI'


class Command(BaseCommand):
    help = 'Feed the database with the films basics located in /local'

    FILMS_BASICS_FILE = os.path.join(os.getenv('MAIN_DIR', '.'), 'local/films_info/title_basics.tsv')

    def update_film_basics_info(self, imdb_id, primary, original, is_adult, updatedb=False, dryrun=False, verbose=False, overwrite=False):
        if verbose:
            self.stdout.write(f'    Processing film "{imdb_id}" (adult: {is_adult}): "{primary}" | "{original}"')
        if dryrun:
            return None
        elif updatedb:
            try:
                filmdb = FilmDb.objects.get(imdb_id=imdb_id)
                if filmdb.title != primary and verbose:
                    self.stdout.write(f'    Film "{imdb_id}" title mismatch: title: "{filmdb.title}"')
                    self.stdout.write(f'                                   primary: "{primary}"')
                    self.stdout.write(f'                                  original: "{original}"')
                filmdbtrans_pri, created_pri = FilmDbTranslation.objects.get_or_create(imdb_id=imdb_id, language_code=PRIMARY_LANGUAGE)
                filmdbtrans_ori, created_ori = FilmDbTranslation.objects.get_or_create(imdb_id=imdb_id, language_code=ORIGINAL_LANGUAGE)
                if created_pri or created_ori or overwrite:
                    try:
                        filmdb.original_title = original
                        filmdb.adult_film = True if is_adult else False
                        filmdb.save()
                        filmdbtrans_pri.title = primary
                        filmdbtrans_pri.save()
                        filmdbtrans_ori.title = original
                        filmdbtrans_ori.save()
                        return imdb_id
                    except django.db.utils.DataError as e:
                        self.stdout.write(f'    ***FAILED: updating film basics "{imdb_id}" with "DataError" exception: {e}')
                        return None
                    except Exception as e:
                        self.stdout.write(f'    ***FAILED: updating film basics "{imdb_id}" with UNKNOWN exception: {e}')
                        return None
            except FilmDb.DoesNotExist as e:
                self.stdout.write(f'    ***FAILED: filmdb "{imdb_id}" DoesNotExist: {e}')

    def get_list_of_films_in_db(self):
        self.stdout.write(f'  Getting list of films in db...')
        filmdbs_ids = FilmDb.objects.all().values_list('imdb_id', flat=True)
        self.stdout.write(f'  Number of FilmDb objects found in db: {len(filmdbs_ids)}')
        filmdbstrans_ids = FilmDbTranslation.objects.all().values_list('imdb_id', flat=True)
        self.stdout.write(f'  Number of FilmDbTranslation objects found in db: {len(filmdbstrans_ids)}')
        return filmdbs_ids

    def process_basics_file(self, process_options):
        filmdbs_ids = self.get_list_of_films_in_db()
        basics_file_path = self.FILMS_BASICS_FILE
        self.stdout.write(f'  Processing basics file: {os.path.basename(basics_file_path)}')
        basics_df = pd.read_csv(basics_file_path, sep='\t', usecols=['tconst', 'primaryTitle', 'originalTitle', 'isAdult'])
        self.process_basics_df(basics_df, filmdbs_ids, process_options)

    def process_basics_df(self, basics_df, filmdbs_ids, process_options):
        basics_df = basics_df.replace({'tconst': r'^tt'}, {'tconst': ''}, regex=True)
        basics_df["tconst"] = basics_df["tconst"].str.zfill(8)
        titles_df_ids = basics_df["tconst"].unique().tolist()
        self.stdout.write(f'    Number of titles in df: {len(basics_df.index)}')
        self.stdout.write(f'    Number of unique titles in df: {len(titles_df_ids)}')
        common_film_ids = list(set.intersection(set(titles_df_ids), set(filmdbs_ids)))
        self.stdout.write(f'    Number of objects in df and database: {len(common_film_ids)}')
        basics_df = basics_df[basics_df['tconst'].isin(common_film_ids)]
        self.stdout.write(f'    Number of titles in basics_df: {len(basics_df.index)}')
        film_basics = []
        processed_films = 0
        updated_films = 0
        for index, film_row in basics_df.iterrows():
            imdb_id = film_row['tconst']
            primary = film_row['primaryTitle']
            original = film_row['originalTitle']
            is_adult = film_row['isAdult']
            film_basics.append((imdb_id, primary, original, is_adult))
        self.stdout.write(f'    Updating {len(film_basics)} filmdb models...')
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONNECTIONS) as executor:
            future_result = (executor.submit(self.update_film_basics_info, imdb_id, primary, original, is_adult, **process_options)
                             for imdb_id, primary, original, is_adult in film_basics)
            for i, future in enumerate(concurrent.futures.as_completed(future_result)):
                film_id = future.result()
                processed_films += 1
                if film_id:
                    updated_films += 1
        self.stdout.write(f'    OK: Number of processed basics: {processed_films} ({updated_films} updated)')

    def add_arguments(self, parser):
        parser.add_argument('--dryrun', action='store_true', help='Dry run')
        parser.add_argument('--verbose', action='store_true', help='Verbose output')
        parser.add_argument('--updatedb', action='store_true', help='Add or delete film db objects')
        parser.add_argument('--overwrite', action='store_true', help='Overwrite film db objects')

    def handle(self, *args, **options):
        self.stdout.write(f'Feeding local film jsons to database:')
        process_options = {
            'dryrun': options['dryrun'],
            'updatedb': options['updatedb'],
            'overwrite': options['overwrite'],
            'verbose': options['verbose'],
        }
        if not process_options['dryrun'] and not process_options['updatedb']:
            self.stdout.write(f'Must select either "--dryrun" or "--updatedb"')
            raise
        if process_options['dryrun'] and process_options['updatedb']:
            self.stdout.write(f'Invalid command combination: "--dryrun" and "--updatedb"')
            raise
        if not process_options['updatedb'] and process_options['overwrite']:
            self.stdout.write(f'Invalid command combination: "--overwrite" without "--updatedb"')
            raise
        self.process_basics_file(process_options)
        self.stdout.write(f'  OK')
