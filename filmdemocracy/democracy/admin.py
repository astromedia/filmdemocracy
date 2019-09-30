from django.contrib import admin

from filmdemocracy.democracy.models import Film, Vote


class VoteInLine(admin.TabularInline):
    model = Vote
    extra = 0


class FilmAdmin(admin.ModelAdmin):
    fieldsets = [
        (
            'General info',
            {'fields': ['proposed_by', 'seen']}
        ),
        (
            'Internet databases information',
            {'fields': ['imdb_id']}
        ),
        (
            'Date information',
            {
                'fields': ['seen_date'],
                'classes': ['collapse']
            }
        ),
    ]
    inlines = [VoteInLine]
    list_display = ('id', 'proposed_by', 'pub_datetime', 'seen')
    list_filter = ['proposed_by', 'seen']


admin.site.register(Film, FilmAdmin)
