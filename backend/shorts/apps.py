from django.apps import AppConfig


class ShortsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shorts'

    def ready(self):
        from shorts import job_store  # noqa: F401

        job_store.start_cleanup_thread()
