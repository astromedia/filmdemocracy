import uuid

from django.db import models

from filmdemocracy.registration.models import User
from filmdemocracy.democracy.models import Club


class ChatClubPost(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_sender = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)

    def __str__(self):
        return f'{self.club}|{self.user_sender}|{self.created_datetime}|{self.text}'


class ChatClubInfo(models.Model):
    """ Created together with the associated the club """

    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    last_post = models.ForeignKey(ChatClubPost, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.club}|{self.last_post.created_datetime}'


class ChatUsersPost(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_sender = models.ForeignKey(User, related_name='user_sender', on_delete=models.CASCADE)
    user_receiver = models.ForeignKey(User, related_name='user_receiver', on_delete=models.CASCADE)
    edited = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)
    text = models.CharField(max_length=5000)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)
    last_updated_datetime = models.DateTimeField('last updated datetime', auto_now=True)

    def __str__(self):
        return f'{self.user_sender}|{self.user_receiver}|{self.created_datetime}|{self.text}'


class ChatUsersInfo(models.Model):

    user = models.ForeignKey(User, related_name='chat_user', on_delete=models.CASCADE)
    user_known = models.ForeignKey(User, related_name='chat_user_known', on_delete=models.CASCADE)
    last_post = models.ForeignKey(ChatUsersPost, on_delete=models.SET_NULL, null=True)
    created_datetime = models.DateTimeField('created datetime', auto_now_add=True)

    def __str__(self):
        return f'{self.user}|{self.user_known}|{self.last_post.created_datetime}'
