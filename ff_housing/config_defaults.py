# Create dummy secrey key so we can use sessions
SECRET_KEY = '123456790'

# Create in-memory database
DATABASE_FILE = '/tmp/sample_db.sqlite'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DATABASE_FILE
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = True

# Flask-Security config
#SECURITY_URL_PREFIX = "/"
SECURITY_PASSWORD_HASH = "pbkdf2_sha512"
SECURITY_PASSWORD_SALT = "gaph5zoh7Eiphoh4ha4oeveiTh4ru8ii"

# Flask-Security URLs, overridden because they don't put a / at the end
SECURITY_LOGIN_URL = "/login/"
SECURITY_LOGOUT_URL = "/logout/"
SECURITY_REGISTER_URL = "/register/"
SECURITY_RESET_URL = "/lostpass/"

SECURITY_RECOVERABLE = True
SECURITY_CHANGEABLE = True
SECURITY_EMAIL_SENDER = "billing@funkfeuer.at"

SECURITY_POST_LOGIN_VIEW = "/"
SECURITY_POST_LOGOUT_VIEW = "/"
SECURITY_POST_REGISTER_VIEW = "/"

# Flask-Security features
SECURITY_REGISTERABLE = False
SECURITY_SEND_REGISTER_EMAIL = False


FF_HOUSING_FILES_DIR = "./files/"
FF_HOUSING_INVOICES_BCC = "root@localhost"

MAIL_SUPPRESS_SEND = True
MAIL_DEFAULT_SENDER = "FunkFeuer <root@localhost>"
MAIL_SERVER = "localhost"
