import os
import datetime
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'h4hjbt-$4vx3%yvk3t+i)s0)%v$thnnyk4+i&w=lpfiyvi$e-l'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'auditlog',
    'WAMSApp',
    'storages',
    'django_extensions',
    'corsheaders'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
]

ROOT_URLCONF = 'WAMS.urls'

DATA_UPLOAD_MAX_MEMORY_SIZE = 10242880

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'WAMS.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
"""


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'wamstest',
        'USER': 'nisarg',
        'PASSWORD': 'nisargtike',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE =  'Asia/Kolkata'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# STATIC_URL = '/static/'
# STATIC_ROOT = 'static/'

# MEDIA_URL = '/files/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'files')


AWS_ACCESS_KEY_ID = 'AKIA5NL25NAZB4FJDK65'
AWS_SECRET_ACCESS_KEY = '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'
AWS_STORAGE_BUCKET_NAME = 'wig-wams-s3-bucket'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
#AWS_DEFAULT_ACL = None

DEFAULT_FILE_STORAGE = 'WAMSApp.storage_backends.MediaStorage'
MEDIA_URL = "https://%s/" % AWS_S3_CUSTOM_DOMAIN

# Userid: tikenisarg@gmail.com
# Acces Key ID: AKIA5NL25NAZB4FJDK65
# Secret access key: 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
# Password: {t-yUSBZwt8J


# Log Conf
if not os.path.exists('log'):
    os.makedirs('log')

APP_LOG_FILENAME = os.path.join(BASE_DIR, 'log/app.log')

LOGFILE_SIZE = 20 * 1024 * 1024
LOGFILE_COUNT = 5
LOGFILE_APP = 'WAMSApp'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)s] %(message)s",
            'datefmt' : "%d-%b-%Y %H:%M:%S"
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler'
        },
        'applog': {
            'level':'INFO',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': APP_LOG_FILENAME,
            'maxBytes': LOGFILE_SIZE,
            'backupCount': LOGFILE_COUNT,
            'formatter': 'standard',
        }
    },
    'loggers': {
        LOGFILE_APP: {
            'handlers': ['applog'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
}

# CORS_ORIGIN_WHITELIST = (
#     'http://127.0.0.1:3000',
# )

JWT_AUTH = {
    'JWT_RESPONSE_PAYLOAD_HANDLER': 'WAMSApp.utils.my_jwt_response_handler',
    'JWT_EXPIRATION_DELTA': datetime.timedelta(seconds=1800),
}

CORS_ORIGIN_ALLOW_ALL = True

FILE_UPLOAD_HANDLERS = [
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
]