from .track import register_track_handlers
from .list_untrack import register_list_untrack_handlers


def register_all_handlers(app):
    register_track_handlers(app)
    register_list_untrack_handlers(app)