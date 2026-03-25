from Fusion.settings import *
import os

BASE_DIR_LOCAL = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = 'test_secret_key_12345'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR_LOCAL, 'test_db.sqlite3'),
    }
}
