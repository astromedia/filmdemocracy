import random
import requests

from filmdemocracy.registration.models import User
from filmdemocracy.socialclub.models import Club
from filmdemocracy.democracy.models import Film


names = [
    'Pablo',
    'Naranjo',
    'Timi',
    'Carla',
    'Ricardo',
    'Txan',
    'Juanra',
    'Andrea',
    'Diego',
    'Cris',
    'Javi 1',
    'Javi 2',
    'Jose',
    'Pedro',
    'Elias',
    'Marta',
    'Vega',
]

for name in names:
    User.objects.create_user(
        name,
        f'{name.lower()}@gmail.com',
        f'pass'
    )

user_creator = User.objects.filter(email='pablo@gmail.com')[0]

club_names = [
    'CCM',
    'Trabajo',
]


lore_100 = "Lorem ipsum dolor sit amet consectetur adipiscing elit, " \
           "praesent sem sed tristique tincidunt sociis."

mock_club_description = "## A sample club description written in markdown" \
                        "\r\n" \
                        "\r\n---" \
                        "\r\n" \
                        "\r\n#### Point 1: Here is some text. " \
                        "\r\nHello world, I'm a cinema club... " \
                        "\r\n" \
                        "\r\n#### Point 2: And here is a list to consider: " \
                        "\r\n1. Item #1" \
                        "\r\n2. Item #2" \
                        "\r\n3. Item #3" \
                        "\r\n" \
                        "\r\n#### Point 3: And here is an unordered list to consider:" \
                        "\r\n- Item 1" \
                        "\r\n- Item 2" \
                        "\r\n- Item 3"


for club_name in club_names:
    club = Club.objects.create(
        id=random.choice(range(1, 99999)),
        name=club_name,
        short_description=lore_100,
        club_description=mock_club_description,
    )
    club.admin_users.add(user_creator)
    club.users.add(user_creator)
    for name in random.sample(names[1:], 12):
        user = User.objects.filter(email=f'{name.lower()}@gmail.com')[0]
        club.users.add(user)
    club.save()


# imdb_ids = [
#     'tt0111161',
#     'tt0071562',
#     'tt0468569'
# ]
#
#
# OMDB_API_KEY = '4b213d96'
#
# for imdb_id in imdb_ids:
#
#     new_id = random.choice(range(1, 999999))
#
#     omdb_api_url = f'http://www.omdbapi.com/?i={imdb_id}' \
#         f'&apikey={OMDB_API_KEY}'
#     response = requests.get(omdb_api_url)
#     omdb_data = response.json()
#     Film.objects.create(
#         id=new_id,
#         imdb_id=imdb_id,
#         proposed_by=user_creator,
#         title=omdb_data['Title'],
#         director=omdb_data['Director'],
#         writer=omdb_data['Writer'],
#         actors=omdb_data['Actors'],
#         poster_url=omdb_data['Poster'],
#         year=omdb_data['Year'],
#         duration=int(omdb_data['Runtime'].replace('min', '')),
#         language=omdb_data['Language'],
#         rated=omdb_data['Rated'],
#         country=omdb_data['Country'],
#         plot=omdb_data['Plot'],
#     )
