import os
import concurrent.futures

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
import django.db.utils

from filmdemocracy.democracy.models import FilmDb, FilmDbTranslation


MAX_CONNECTIONS = 32


class Command(BaseCommand):
    help = 'Feed the database with the films translations located in /local'

    FILMS_TRANSLATIONS_FILE = os.path.join(os.getenv('MAIN_DIR', '.'), 'local/films_info/title_translations.tsv')
    REGION_TRANSLATION_CODES = ['es']
    LANGUAGE_TRANSLATION_CODES = {'es': ['\\N']}

    def update_film_translations_info(self, imdb_id, title, language, updatedb=False, dryrun=False, verbose=False, overwrite=False):
        if verbose:
            self.stdout.write(f'    Found "{language}" translation for film "{imdb_id}": {title}')
        if dryrun:
            return None
        elif updatedb:
            try:
                filmdb = FilmDb.objects.get(imdb_id=imdb_id)
                filmdbtrans, created = FilmDbTranslation.objects.get_or_create(imdb_id=imdb_id, language_code=language)
                if created or overwrite:
                    try:
                        filmdbtrans.title = title
                        filmdbtrans.save()
                        return imdb_id
                    except django.db.utils.DataError as e:
                        self.stdout.write(f'    ***FAILED: uploading film translation "{imdb_id}" with "DataError" exception: {e}')
                        filmdbtrans.delete()
                        return None
                    except Exception as e:
                        self.stdout.write(f'    ***FAILED: uploading film translation "{imdb_id}" with UNKNOWN exception: {e}')
                        filmdbtrans.delete()
                        return None
            except FilmDb.DoesNotExist as e:
                self.stdout.write(f'    ***FAILED: filmdb "{imdb_id}" DoesNotExist: {e}')

    def get_list_of_films_in_db(self):
        self.stdout.write(f'  Getting list of films in db...')
        filmdbs_ids = FilmDb.objects.all().values_list('imdb_id', flat=True)
        self.stdout.write(f'  Number of films found in db: {len(filmdbs_ids)}')
        return filmdbs_ids

    def process_translations_file(self, process_options):
        filmdbs_ids = self.get_list_of_films_in_db()
        translations_file_path = self.FILMS_TRANSLATIONS_FILE
        self.stdout.write(f'  Processing translations file: {os.path.basename(translations_file_path)}')
        translations_df = pd.read_csv(translations_file_path, sep='\t', usecols=['titleId', 'title', 'region', 'language'])
        self.process_translations_df(translations_df, filmdbs_ids, process_options)

    def process_translations_df(self, translations_df, filmdbs_ids, process_options):
        translations_df = translations_df.replace({'titleId': r'^tt'}, {'titleId': ''}, regex=True)
        translations_df["titleId"] = translations_df["titleId"].str.zfill(8)
        titles_df_ids = translations_df["titleId"].unique().tolist()
        self.stdout.write(f'    Number of titles in df: {len(translations_df.index)}')
        self.stdout.write(f'    Number of unique titles in df: {len(titles_df_ids)}')
        common_film_ids = list(set.intersection(set(titles_df_ids), set(filmdbs_ids)))
        self.stdout.write(f'    Number of objects in df and database: {len(common_film_ids)}')
        translations_df = translations_df[translations_df['titleId'].isin(common_film_ids)]
        translations_df["region"] = translations_df["region"].str.lower()
        translations_df = translations_df[translations_df['region'].isin(self.REGION_TRANSLATION_CODES)]
        self.stdout.write(f'    Number of titles in translations_df: {len(translations_df.index)}')
        film_translations = []
        processed_translations = 0
        updated_translations = 0
        translations_groups = translations_df.groupby(['titleId'])
        for imdb_id, group in translations_groups:
            film_titles = group['title'].tolist()
            film_regions = group['region'].tolist()
            film_languages = group['language'].tolist()
            for language in self.REGION_TRANSLATION_CODES:
                film_titles_list = []
                for i in range(0, len(film_titles)):
                    if film_regions[i] == language and film_languages[i] in self.LANGUAGE_TRANSLATION_CODES[language]:
                        film_titles_list.append(film_titles[i])
                main_title = None
                if film_titles_list:
                    film_titles_list = list(set(film_titles_list))
                    for film_title in film_titles_list:
                        if not main_title:
                            main_title = film_title
                        else:
                            main_title += f' ({film_title})'
                if main_title:
                    film_translations.append((imdb_id, main_title, language))
        self.stdout.write(f'    Creating translations models...')
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONNECTIONS) as executor:
            future_result = (executor.submit(self.update_film_translations_info, imdb_id, title, language, **process_options)
                             for imdb_id, title, language in film_translations)
            for i, future in enumerate(concurrent.futures.as_completed(future_result)):
                imdb_id = future.result()
                processed_translations += 1
                if imdb_id:
                    updated_translations += 1
        self.stdout.write(f'    OK: Number of processed translations: {processed_translations} ({updated_translations} updated)')

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
        # FilmDbTranslation.objects.all().delete()
        self.process_translations_file(process_options)
        self.stdout.write(f'  OK')
