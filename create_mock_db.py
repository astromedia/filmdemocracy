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

lore_3 = "Lorem ipsum dolor sit amet consectetur adipiscing elit pharetra, " \
         "nulla cras curabitur class facilisi himenaeos. Lobortis penatibus" \
         " mi sem morbi sed nostra magna class proin euismod, tortor erat " \
         "conubia ligula montes pellentesque scelerisque malesuada mattis " \
         "at, facilisis parturient enim himenaeos suspendisse mus ad aptent " \
         "cras. Aenean tempus eleifend ut dapibus mi praesent quisque per" \
         " duis vivamus, phasellus sociis a nulla nostra mattis magnis " \
         "sollicitudin non scelerisque nam, himenaeos etiam sapien massa " \
         "risus torquent mus cras metus. Sollicitudin tempus penatibus " \
         "justo fusce urna vivamus pellentesque inceptos rutrum, tristique " \
         "faucibus dignissim platea potenti odio ullamcorper commodo eros, " \
         "facilisis duis feugiat litora velit class euismod et. " \
         "" \
         "Ante vulputate etiam litora sem vivamus tincidunt volutpat cum " \
         "vitae natoque, malesuada pellentesque duis curabitur non diam " \
         "libero magnis hac. Sodales faucibus tristique est curabitur " \
         "condimentum consequat ultrices cubilia id, porttitor viverra" \
         " tincidunt risus tortor lacus dictum rhoncus, tempus ridiculus " \
         "laoreet varius eros nisl sociosqu vitae. Tristique phasellus " \
         "taciti purus arcu ornare auctor viverra bibendum mauris pretium " \
         "praesent laoreet rhoncus, platea pharetra erat malesuada sapien" \
         " curae lectus neque facilisi id fringilla ante. Neque massa vel " \
         "ligula magnis torquent aliquet egestas non quisque primis, " \
         "phasellus mollis aliquam nibh ullamcorper mi hendrerit natoque " \
         "in, tempor at varius proin sagittis cras eros id curabitur." \
         "" \
         "Auctor placerat ultrices facilisi pulvinar sem nullam facilisis" \
         " pharetra turpis nisl feugiat, mauris netus sociis augue ante " \
         "senectus lectus velit curae. Vulputate sollicitudin lacinia " \
         "ultricies fermentum augue purus habitant id mi rutrum malesuada " \
         "dignissim, et vivamus parturient convallis fringilla cras vestibulum " \
         "euismod nibh tristique eleifend, odio curabitur cubilia ut quam " \
         "enim at gravida tortor magnis nullam."


for club_name in club_names:
    club = Club.objects.create(
        id=random.choice(range(1, 99999)),
        name=club_name,
        short_description=lore_100,
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
