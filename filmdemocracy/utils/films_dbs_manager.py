from pprint import pprint

import django.db.utils

from filmdemocracy.democracy.models import FilmDb, FilmDbTranslation
from filmdemocracy.utils.mongodb_manager import MongoDBManager
from filmdemocracy.settings import MIN_IMDB_VOTES, MAIN_LANGUAGE, PRIMARY_LANGUAGE, ORIGINAL_LANGUAGE


class FilmsDBsManager:

    def __init__(self, mongodb_url=None, mongodb_username=None, mongodb_password=None, verbose=False):

        self.mongodb = MongoDBManager(
            mongodb_url=mongodb_url,
            db_name='filmdemocracy', 
            collection_name='films',
            username=mongodb_username,
            password=mongodb_password,
            )
        self.verbose = verbose
        self.popularity_check_date = 2020

    def get_film_ids_in_mongodb(self, status='OK'):
        print(f'  Getting list of film ids with {status=} in mongodb...')
        film_ids = self.mongodb.get_film_ids(status=status)
        print(f'  Number of films found: {len(film_ids)}')
        return film_ids

    def get_film_ids_in_postgresdb(self):
        print('  Getting list of film ids in postgresdb...')
        film_ids = FilmDb.objects.all().values_list('imdb_id', flat=True)
        print(f'  Number of films found: {len(film_ids)}')
        return film_ids

    def delete_all_films(self):
        FilmDb.objects.all().delete()

    def delete_all_films_translations(self):
        FilmDbTranslation.objects.all().delete()

    @staticmethod
    def parse_film_data(film_data):
        year_str = str(film_data['Year'])
        if '–' in year_str:
            year_str = year_str.split('–')[0]
        year_int = int(year_str[0:4])
        if not film_data['imdbVotes']:
            imdb_votes = 0
        else:
            imdb_votes = int(film_data['imdbVotes'].replace(',', ''))
        film_dict = {
            'Type': film_data['Type'],
            'Title': film_data['Title'],
            'imdbRating': film_data['imdbRating'],
            'imdbVotes': imdb_votes,
            'Metascore': film_data['Metascore'],
            'Year': year_int,
            'Director': film_data['Director'],
            'Writer': film_data['Writer'],
            'Actors': film_data['Actors'],
            'Poster': film_data['Poster'],
            'Runtime': film_data['Runtime'],
            'Language': film_data['Language'],
            'Rated': film_data['Rated'],
            'Country': film_data['Country'],
            'Plot': film_data['Plot'],
        }
        return film_dict

    def film_quality_check(self, film_dict):
        type_check = film_dict['Type'] == 'movie'
        content_check = film_dict['Director'] and film_dict['Poster'] and film_dict['Title']
        popularity_check = int(film_dict['imdbVotes']) >= MIN_IMDB_VOTES and int(film_dict['Year']) < 2020
        if type_check and content_check and popularity_check:
            return True
        return False

    def update_film_data_info(self, imdb_id, film_dict, overwrite=False):
        if self.film_quality_check(film_dict):
            filmdb, created = FilmDb.objects.get_or_create(imdb_id=imdb_id)
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
                    # Create main language translation
                    filmdbtrans, _ = FilmDbTranslation.objects.get_or_create(imdb_id=imdb_id, language_code=MAIN_LANGUAGE)
                    filmdbtrans.title = film_dict['Title']
                    filmdbtrans.save()
                except KeyError as exc:
                    pprint(film_dict)
                    filmdb.delete()
                    raise(f'***FAILED: uploading film "{imdb_id=}" with "KeyError" exception: {exc}')
                except django.db.utils.DataError as exc:
                    pprint(film_dict)
                    filmdb.delete()
                    raise(f'***FAILED: uploading film "{imdb_id=}" with "DataError" exception: {exc}')
                except Exception as exc:
                    pprint(film_dict)
                    filmdb.delete()
                    raise(f'***FAILED: uploading film "{imdb_id=}" with UNKNOWN exception: {exc}')

    def update_film_basics_info(self, imdb_id, film_basics, overwrite=False):
        primary = film_basics['primaryTitle']
        original = film_basics['originalTitle']
        is_adult = film_basics['isAdult']
        try:
            filmdb = FilmDb.objects.get(imdb_id=imdb_id)
            if filmdb.title != primary and self.verbose:
                print(f'Film "{imdb_id}" title mismatch: title: "{filmdb.title}"')
                print(f'                               primary: "{primary}"')
                print(f'                              original: "{original}"')
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
                except django.db.utils.DataError as exc:
                    pprint(film_basics)
                    raise f'***FAILED: updating film basics "{imdb_id=}" with "DataError" exception: {exc}'
                except Exception as exc:
                    pprint(film_basics)
                    raise f'***FAILED: updating film basics "{imdb_id=}" with UNKNOWN exception: {exc}'
        except FilmDb.DoesNotExist as exc:
            raise f'***FAILED: filmdb "{imdb_id=}" DoesNotExist: {exc}'

    def update_film_translations_info(self, imdb_id, film_translations, overwrite=False):
        codes = []
        for film_translation in film_translations:
            code = film_translation['code']
            if code in codes:
                continue
            codes.append(code)
            title = film_translation['title']
            if self.verbose:
                print(f'Found {code=} translation for film {imdb_id=}: {title}')
            try:
                _ = FilmDb.objects.get(imdb_id=imdb_id)
                filmdbtrans, created = FilmDbTranslation.objects.get_or_create(imdb_id=imdb_id, language_code=code)
                if created or overwrite:
                    try:
                        filmdbtrans.title = title
                        filmdbtrans.save()
                    except django.db.utils.DataError as exc:
                        filmdbtrans.delete()
                        raise f'***FAILED: uploading film translation "{imdb_id=}" with "DataError" exception: {exc}'
                    except Exception as exc:
                        filmdbtrans.delete()
                        raise f'***FAILED: uploading film translation "{imdb_id=}" with UNKNOWN exception: {exc}'
            except FilmDb.DoesNotExist as exc:
                raise f'***FAILED: filmdb "{imdb_id=}" DoesNotExist: {exc}'

    def delete_film_from_db(self, imdb_id):
        try:
            FilmDb.objects.get(imdb_id=imdb_id).delete()
            FilmDbTranslation.objects.filter(imdb_id=imdb_id).delete()  # Not needed because of cascade delete?
            print(f'Cleaned film "{imdb_id=}" from db')
        except FilmDb.DoesNotExist:
            pass
