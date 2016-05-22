import os

from email.utils import parseaddr
from configurations import Configuration, values

import dj_database_url


ugettext = lambda s: s


class Base(Configuration):
    """
    The are correct settings that are primarily targeted at the production
    system but allow (where appriate) easy overrides either via subclassing
    or environment variables.
    """

    ###########################################################################
    #
    # General settings
    #
    TEXT_HTML_SANITIZE = True
    TEXT_ADDITIONAL_TAGS = ['object', 'param']
    TEXT_ADDITIONAL_PROTOCOLS = ['rtmp']

    PROJECT_NAME = 'pyconde'

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    ADMINS = values.ListValue([], converter=parseaddr)

    ALLOWED_HOSTS = values.ListValue(['localhost', '127.0.0.1'])

    @property
    def MANAGERS(self):
        return self.ADMINS

    EMAIL_HOST = values.Value()
    EMAIL_PORT = values.Value()
    EMAIL_HOST_USER = values.Value()
    EMAIL_HOST_PASSWORD = values.Value()
    EMAIL_USE_TLS = values.BooleanValue(True)
    EMAIL_USE_SSL = values.BooleanValue(False)

    DEFAULT_FROM_EMAIL = values.EmailValue('info@euroscipy.org')

    SERVER_EMAIL = values.EmailValue('info@euroscipy.org')

    SUPPORT_EMAIL = values.EmailValue('info@euroscipy.org')

    TIME_ZONE = 'Europe/Berlin'

    LANGUAGE_CODE = 'en'

    SECRET_KEY = values.SecretValue()

    EMAIL_SUBJECT_PREFIX = values.Value('[EuroSciPy 2016] ')

    USE_I18N = True

    USE_L10N = True

    SITE_ID = values.IntegerValue(1)

    CONFERENCE_ID = values.IntegerValue(1)

    LANGUAGES = (
        #('de', ugettext('German')),
        ('en', ugettext('English')),
    )
    INTERNAL_IPS = ('127.0.0.1',)

    ROOT_URLCONF = values.Value('%s.urls' % PROJECT_NAME)

    SCRIPT_NAME = values.Value()

    USE_X_FORWARDED_HOST = values.BooleanValue(False)

    INSTALLED_APPS = [
        # Skins
        # 'pyconde.skins.ep14',
        # 'pyconde.skins.default',
        'pyconde.skins.euroscipy2016',
        'djangocms_admin_style',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.messages',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.staticfiles',
        'markup_deprecated',

        # django allauth for account creation and managing
        'allauth',
        'allauth.account',
        'allauth.socialaccount',

        'sortedm2m',
        'crispy_forms',
        'easy_thumbnails',
        'compressor',

        # Custom apps 1
        'pyconde.core',
        'pyconde.accounts',  # pyconde.accounts musst before cms

        'djangocms_text_ckeditor',  # must be before 'cms'!
        'cms',
        'treebeard',
        'mptt',
        'menus',
        'sekizai',
        'taggit',
        'haystack',
        'tinymce',  # If you want tinymce, add it in the settings.py file.
        'django_gravatar',
        'gunicorn',
        'statici18n',

        'djangocms_inherit',
        'djangocms_googlemap',
        'djangocms_link',
        'djangocms_snippet',
        #'cms.plugins.twitter',
        #'cms.plugins.text',
        'djangocms_style',
        #'cmsplugin_news',
        'djangocms_picture',
        'pyconde.testimonials',

        # Symposion apps
        'pyconde.conference',
        'pyconde.speakers',
        'pyconde.proposals',
        'pyconde.sponsorship',


        # Custom apps 2
        'pyconde.attendees',
        'pyconde.events',
        'pyconde.reviews',
        'pyconde.schedule',
        'pyconde.search',
        'pyconde.helpers',
        'pyconde.checkin',
        'pyconde.lightningtalks',
    ]

    MIDDLEWARE_CLASSES = [
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'cms.middleware.page.CurrentPageMiddleware',
        'cms.middleware.user.CurrentUserMiddleware',
        'cms.middleware.toolbar.ToolbarMiddleware',
        'cms.middleware.language.LanguageCookieMiddleware',
    ]

    TEMPLATES = [
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [os.path.join(BASE_DIR, 'templates'), ],
            'APP_DIRS': True,
            'OPTIONS': {
                'debug': True,
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.media',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                    'sekizai.context_processors.sekizai',
                    'pyconde.conference.context_processors.current_conference',
                    'pyconde.reviews.context_processors.review_roles',
                ],
                # Beware before activating this! Grappelli has problems with admin
                # inlines and the template backend option 'string_if_invalid'.
                'string_if_invalid': values.Value('', environ_name='TEMPLATE_STRING_IF_INVALID'),
            },
        },
    ]

    DATABASES = {
        'default': dj_database_url.config(
            default='postgres://djep:djep@localhost/djep',
            env='DEFAULT_DATABASE_URL'
        )
    }
    # Number of seconds database connections should persist for
    DATABASES['default']['CONN_MAX_AGE'] = 600

    FIXTURE_DIRS = (
        os.path.join(BASE_DIR, 'fixtures'),
    )

    # TODO: As soon as we move to foundation use
    # https://pypi.python.org/pypi/crispy-forms-foundation
    CRISPY_TEMPLATE_PACK = 'bootstrap3'

    # If the project uses Less.js, use the inline-JavaScript renderer in
    # debug mode.
    LESS_USE_DYNAMIC_IN_DEBUG = True

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True
    }

    SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

    AUTH_USER_MODEL = 'accounts.User'

    ###########################################################################
    #
    # Debug settings
    #
    DEBUG = values.BooleanValue(False)

    DEBUG_TOOLBAR_CONFIG = {'INTERCEPT_REDIRECTS': False}

    @property
    def THUMBNAIL_DEBUG(self):
        return self.DEBUG

    ###########################################################################
    #
    # File settings
    #
    MEDIA_ROOT = values.Value()

    STATIC_ROOT = values.Value()

    MEDIA_URL = values.Value('/site_media/')

    MEDIA_OPTIPNG_PATH = values.Value('optipng')

    MEDIA_JPEGOPTIM_PATH = values.Value('jpegoptim')

    STATIC_URL = values.Value('/static_media/')

    STATICFILES_FINDERS = Configuration.STATICFILES_FINDERS + (
        'compressor.finders.CompressorFinder',
    )

    STATICFILES_DIRS = values.ListValue()

    STATICI18N_ROOT = os.path.join(BASE_DIR, PROJECT_NAME, "core", "static")

    COMPRESS_CSS_FILTERS = (
        'compressor.filters.css_default.CssAbsoluteFilter',
        'compressor.filters.cssmin.CSSMinFilter',
    )

    THUMBNAIL_PROCESSORS = (
        'easy_thumbnails.processors.colorspace',
        'easy_thumbnails.processors.autocrop',
        'easy_thumbnails.processors.filters',
    )
    THUMBNAIL_SIZE = 100

    CHILDREN_DATA_DISABLED = True

    ###########################################################################
    #
    # CMS Settings
    #
    CMS_PERMISSION = values.BooleanValue(False)

    CMS_TEMPLATES = (
        ('cms/default.html', ugettext('Default template')),
        ('cms/start.html', ugettext('Start page template')),
        ('cms/page_templates/fullpage.html', ugettext('Full page width (schedule, ...)')),
    )

    # Docs at https://django-cms.readthedocs.org/en/develop/getting_started/configuration.html#cms-languages
    CMS_LANGUAGES = {
        1: [
            {
                'code': 'en',
                'name': ugettext('English'),
                'public': True,
            },
            #{
            #    'code': 'de',
            #    'name': ugettext('German'),
            #    'public': True,
            #},
        ],
        'default': {
            'fallbacks': ['en', 'de'],
            'hide_untranslated': False,
        }
    }

    WYM_TOOLS = ",\n".join([
        "{'name': 'Bold', 'title': 'Strong', 'css': 'wym_tools_strong'}",
        "{'name': 'Italic', 'title': 'Emphasis', 'css': 'wym_tools_emphasis'}",
        "{'name': 'Superscript', 'title': 'Superscript', 'css': 'wym_tools_superscript'}",
        "{'name': 'Subscript', 'title': 'Subscript', 'css': 'wym_tools_subscript'}",
        "{'name': 'InsertOrderedList', 'title': 'Ordered_List', 'css': 'wym_tools_ordered_list'}",
        "{'name': 'InsertUnorderedList', 'title': 'Unordered_List', 'css': 'wym_tools_unordered_list'}",
        "{'name': 'Indent', 'title': 'Indent', 'css': 'wym_tools_indent'}",
        "{'name': 'Outdent', 'title': 'Outdent', 'css': 'wym_tools_outdent'}",
        "{'name': 'Undo', 'title': 'Undo', 'css': 'wym_tools_undo'}",
        "{'name': 'Redo', 'title': 'Redo', 'css': 'wym_tools_redo'}",
        "{'name': 'Paste', 'title': 'Paste_From_Word', 'css': 'wym_tools_paste'}",
        "{'name': 'ToggleHtml', 'title': 'HTML', 'css': 'wym_tools_html'}",
        "{'name': 'CreateLink', 'title': 'Link', 'css': 'wym_tools_link'}",
        "{'name': 'Unlink', 'title': 'Unlink', 'css': 'wym_tools_unlink'}",
        "{'name': 'InsertImage', 'title': 'Image', 'css': 'wym_tools_image'}",
        "{'name': 'InsertTable', 'title': 'Table', 'css': 'wym_tools_table'}",
        "{'name': 'Preview', 'title': 'Preview', 'css': 'wym_tools_preview'}",
    ])

    TINYMCE_DEFAULT_CONFIG = {
        'theme': 'advanced',
        'relative_urls': False,
        'theme_advanced_resizing': True,
        'theme_advanced_buttons1_add': 'forecolor,backcolor',
        'style_formats': [
            {'title': u'Heading 2 (alternative)', 'block': 'h2', 'classes': 'alt'},
            {'title': u'Heading 3 (alternative)', 'block': 'h3', 'classes': 'alt'},
        ]
    }

    CMSPLUGIN_NEWS_FEED_TITLE = u'EuroPython 2014 News'

    CMSPLUGIN_NEWS_FEED_DESCRIPTION = u'News from EuroPython 2014'

    SCHEDULE_ATTENDING_POSSIBLE = values.ListValue(['training'])
    SCHEDULE_CACHE_SCHEDULE = values.BooleanValue(True)
    SCHEDULE_CACHE_TIMEOUT = values.IntegerValue(300)

    ###########################################################################
    #
    # Account settings
    #
    AVATAR_MIN_DIMENSION = values.TupleValue(converter=int)
    AVATAR_MAX_DIMENSION = values.TupleValue(converter=int)

    ###########################################################################
    #
    # Proposal and schedule settings
    #
    ATTENDEES_PRODUCT_NUMBER_START = 1000

    PROPOSALS_SUPPORT_ADDITIONAL_SPEAKERS = True

    MAX_CHECKOUT_DURATION = 1800  # 30 minutes

    # This configures the form that is used for each proposal type identified
    # by their respective slug.
    PROPOSALS_TYPED_SUBMISSION_FORMS = {
        'training': 'pyconde.proposals.forms.TrainingSubmissionForm',
        'talk': 'pyconde.proposals.forms.TalkSubmissionForm',
        'poster': 'pyconde.proposals.forms.PosterSubmissionForm',
    }

    # These languages should be available when making a session proposal.
    PROPOSAL_LANGUAGES = (
        #('de', ugettext('German')),
        ('en', ugettext('English')),
    )

    # This setting defines the language that should be pre-selected in the
    # proposal submission form.
    PROPOSAL_DEFAULT_LANGUAGE = 'en'

    ###########################################################################
    #
    # Review settings
    #
    REVIEWER_APPLICATION_OPEN = values.BooleanValue(False)

    ###########################################################################
    #
    # Search configuration
    #    If no other search backend is specified, Whoosh is used to make the setup
    #    as simple as possible. In production we will be using a Lucene-based
    #    backend like SOLR or ElasticSearch.

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(BASE_DIR, 'whoosh_index'),
            'STORAGE': 'file',
            'INCLUDE_SPELLING': True,
            'BATCH_SIZE': 100,
        }
    }

    ###########################################################################
    #
    # Auth settings
    #
    LOGIN_ERROR_URL = values.Value('/accounts/login/')

    LOGIN_REDIRECT_URL = values.Value('/accounts/profile/')

    LOGOUT_REDIRECT_URL = values.Value('/')

    ACCOUNT_ADAPTER = values.Value('pyconde.skins.euroscipy2016.adapter.EuroSciPy2016Adapter')

    ###########################################################################
    #
    # allauth settings
    #
    ACCOUNT_AUTHENTICATION_METHOD = 'username'
    ACCOUNT_EMAIL_REQUIRED = True
    ACCOUNT_EMAIL_VERIFICATION = values.Value('mandatory')
    ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX
    ACCOUNT_SIGNUP_FORM_CLASS = 'pyconde.accounts.forms.SignUpForm'

    ###########################################################################
    #
    # Payment settings
    #
    PAYMILL_PRIVATE_KEY = values.Value()

    PAYMILL_PUBLIC_KEY = values.Value()

    PAYMILL_TRANSACTION_DESCRIPTION = values.Value('EuroPython 2014: Purchase ID {purchase_pk}')

    PAYMENT_METHODS = values.ListValue(['invoice', 'creditcard'])

    PAYMENT_REMINDER_DUE_DATE_OFFSET = values.Value(14)

    PAYMENT_REMINDER_LATEST_DUE_DATE = values.Value('')

    PURCHASE_TERMS_OF_USE_URL = values.Value("https://ep2014.europython.eu/en/registration/terms-conditions/")

    PURCHASE_INVOICE_DISABLE_RENDERING = values.BooleanValue(True)
    # List of emails to be notified when a purchase has been made. PDF is send
    # to these addresses, too.
    PURCHASE_INVOICE_EXPORT_RECIPIENTS = values.ListValue([])

    PURCHASE_INVOICE_FONT_CONFIG = values.DictValue({'de': {}, 'en': {}})

    PURCHASE_INVOICE_FONT_ROOT = values.Value()  # absolute path on the filesystem

    PURCHASE_INVOICE_NUMBER_FORMAT = values.Value('INVOICE-{0:d}')

    PURCHASE_INVOICE_ROOT = values.Value()  # absolute path on the filesystem

    PURCHASE_INVOICE_TEMPLATE_PATH = values.Value()  # absolute path to invoice template

    # Mapping from logo name (key, e.g. 'logo' or 'vbb') to the image file path
    ATTENDEES_BADGE_LOGOS = values.DictValue({})

    CACHES = values.DictValue({
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'localhost:6379:0',
            'OPTIONS': {
                'PARSER_CLASS': 'redis.connection.HiredisParser'
            },
        },
    })

    BROKER_URL = values.Value('redis://localhost:6379/0')

    LOCALE_PATHS = (
        os.path.join(BASE_DIR, PROJECT_NAME, 'locale'),
    )

    # Default settings for statici18n
    STATICI18N_OUTPUT_DIR = 'jsi18n'
    STATICI18N_DOMAIN = 'djangojs'
    STATICI18N_FILENAME_FUNCTION = 'statici18n.utils.default_filename'

    THUMBNAIL_ALIASES = {
        '': {
            'avatar': {'size': (300, 300), 'crop': True},
        },
    }

    ACCOUNTS_FALLBACK_TO_GRAVATAR = True


class Dev(Base):
    """
    These settings are intended for the locaton development environment.
    """

    DEBUG = values.BooleanValue(True)

    COMPRESS_ENABLED = values.BooleanValue(False)

    EMAIL_HOST = 'localhost'

    EMAIL_PORT = 1025

    MEDIA_ROOT = os.path.join(Base.BASE_DIR, 'site_media')

    STATIC_ROOT = os.path.join(Base.BASE_DIR, 'deployed_static_media')

    DEBUG_TOOLBAR_PATCH_SETTINGS = False

    INSTALLED_APPS = Base.INSTALLED_APPS + [
        'debug_toolbar',
        'django_extensions',
    ]

    MIDDLEWARE_CLASSES = [
        'debug_toolbar.middleware.DebugToolbarMiddleware'
    ] + Base.MIDDLEWARE_CLASSES

    PURCHASE_INVOICE_ROOT = os.path.join(Base.BASE_DIR, 'invoices')

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(levelname)s  %(module)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple'
            }
        },
        'loggers': {
            '': {
                'handlers': ['console'],
            },
        }
    }

    # SCHEDULE_CACHE_SCHEDULE = False
    SCHEDULE_CACHE_TIMEOUT = 60


class Testing(Dev):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
        },
    }

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

    SECRET_KEY = "testing_secret_key"
    FIXTURE_DIRS = (os.path.join(Base.BASE_DIR, 'fixtures'),)

    CELERY_ALWAYS_EAGER = True
    CELERY_ACCEPT_CONTENT = ['json']
    PURCHASE_INVOICE_DISABLE_RENDERING = True


class Staging(Base):
    INSTALLED_APPS = Base.INSTALLED_APPS + [
        'raven.contrib.django.raven_compat',
    ]
    RAVEN_CONFIG = values.DictValue()


class Production(Base):
    pass

#    INSTALLED_APPS = Base.INSTALLED_APPS + [
#        'raven.contrib.django.raven_compat',
#    ]
#    RAVEN_CONFIG = values.DictValue()
