from django.apps import AppConfig


class Stock_mangementConfig(AppConfig):
    # name = 'Stock_mangement'
    name = 'WAMSApp'

    def ready(self):
        import WAMSApp.signals  # noqa