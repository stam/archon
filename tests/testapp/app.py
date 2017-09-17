from archon.app import create_app
from .models import *  # noqa

app, db = create_app()
