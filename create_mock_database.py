import random
import requests

from filmdemocracy.registration.models import User
from filmdemocracy.democracy.models import Film


names = ['Pablo', 'Naranjo', 'Timi', 'Carla', 'Ricardo', 'Txan', 'Juanra', 'Andrea']

for name in names:
    User.objects.create_user(
        name,
        f'{name.lower()}@gmail.com',
        f'pass'
    )

imdb_ids = [
    'tt0111161',
    'tt0071562',
    'tt0468569'
]

user_creator = User.objects.filter(email='pablo@gmail.com')[0]
OMDB_API_KEY = '4b213d96'

for imdb_id in imdb_ids:

    new_id = random.choice(range(1, 999999))

    omdb_api_url = f'http://www.omdbapi.com/?i={imdb_id}' \
        f'&apikey={OMDB_API_KEY}'
    response = requests.get(omdb_api_url)
    omdb_data = response.json()
    Film.objects.create(
        id=new_id,
        imdb_id=imdb_id,
        proposed_by=user_creator,
        title=omdb_data['Title'],
        director=omdb_data['Director'],
        writer=omdb_data['Writer'],
        actors=omdb_data['Actors'],
        poster_url=omdb_data['Poster'],
        year=omdb_data['Year'],
        duration=int(omdb_data['Runtime'].replace('min', '')),
        language=omdb_data['Language'],
        rated=omdb_data['Rated'],
        country=omdb_data['Country'],
        plot=omdb_data['Plot'],
    )
