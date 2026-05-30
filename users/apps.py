from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        from common.queue.runner import start_background_consumer_once

        start_background_consumer_once()
