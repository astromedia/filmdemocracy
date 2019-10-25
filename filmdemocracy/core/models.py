import uuid

from django.db import models

from filmdemocracy.democracy.models import Club
from filmdemocracy.registration.models import User


class Notification(models.Model):

    SIGNUP = 'signup'
    JOINED = 'joined'
    PROMOTED = 'promoted'
    LEFT = 'left'
    ADDED_FILM = 'addedfilm'
    SEEN_FILM = 'seenfilm'
    ORGAN_MEET = 'organmeet'
    COMM_FILM = 'commfilm'
    COMM_COMM = 'commcomm'
    KICKED = 'kicked'
    ABANDONED = 'abandoned'
    INVITED = 'invited'

    notification_choices = (
        (SIGNUP, 'User created account'),
        (JOINED, 'Member joined the club'),
        (PROMOTED, 'Member promoted to admin'),
        (LEFT, "Member left the club"),
        (ADDED_FILM, 'Member added new film'),
        (SEEN_FILM, "Member marked film as seen by club"),
        (ORGAN_MEET, "Member organized a new club meeting"),
        (COMM_FILM, "Member commented in film proposed by user"),
        (COMM_COMM, 'Member commented in film commented by user'),
        (KICKED, 'Member kicked other member from club'),
        (ABANDONED, 'Club admin deleted account'),
        (INVITED, 'User invited to join club'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=9, choices=notification_choices)
    activator = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='active_member')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, related_name='club')
    object_id = models.UUIDField(null=True)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recipient')
    read = models.BooleanField('notification read', default=False)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)

    def __str__(self):
        return f"{self.activator.username}|{self.club}|{self.type}|{self.created_datetime}|{self.recipient.username}"
