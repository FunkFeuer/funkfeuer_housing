from flask_security import UserMixin, RoleMixin
from sqlalchemy_utils import EmailType
from datetime import datetime

from ..model import db

class ClassProperty(object):
    def __init__(self, func):
        self.func = func
    def __get__(self, inst, cls):
        return self.func(cls)

roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode(32), unique=True)
    description = db.Column(db.Unicode(255))

    groups_details = ['admin']
    groups_view = ['admin', 'system']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']

    def __str__(self):
        return self.name

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.Unicode(48), nullable=False)
    last_name = db.Column(db.Unicode(48), nullable=False)
    company_name = db.Column(db.Unicode(48))
    street = db.Column(db.Unicode(127), nullable=False)
    zip = db.Column(db.Unicode(16), nullable=False)
    town = db.Column(db.Unicode(32), nullable=False)
    country = db.Column(db.Unicode(32))
    email = db.Column(db.Unicode(64), nullable=False) #, unique=True)
    phone = db.Column(db.Unicode(32))
    sepa_iban = db.Column(db.Unicode(32), unique=True)
    sepa_mandate = db.Column(db.Unicode(32), unique=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    mailinglist = db.Column(db.Boolean(), nullable=False, default=True)

    password = db.Column(db.Unicode(255))
    active = db.Column(db.Boolean(), nullable=False)
    confirmed_at = db.Column(db.DateTime())
    last_login = db.Column(db.DateTime())
    keycard = db.Column(db.String)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    @property
    def address(self):
        addr = "%s\n%s %s\n%s" % (self.street, self.zip, self.town, self.country) # state
        if(self.company_name):
            return ("%s\n%s %s\n\n%s" % (self.company_name, self.first_name, self.last_name, addr))
        return ("%s %s\n\n%s" % (self.first_name, self.last_name, addr))

    @property
    def name(self):
        if(self.company_name):
            return "%s %s / %s" % (self.first_name, self.last_name, self.company_name)
        return "%s %s" % (self.first_name, self.last_name)

    form_columns = ('first_name', 'last_name', 'company_name', 'active', 'mailinglist', 'street', 'zip', 'town', 'country', 'email', 'phone', 'keycard')

    column_default_sort = ('id', False)
    column_filters = ('active','first_name','last_name', 'company_name', 'street')
    column_list = ('active', 'first_name', 'last_name', 'company_name', 'email', 'street', 'zip', 'town', 'keycard')
    column_searchable_list = ( 'id', 'first_name', 'last_name', 'company_name', 'email', 'street', 'zip')
    groups_view = ['admin', 'system']
    groups_create = ['admin' 'system']
    groups_edit = ['admin', 'system']
    groups_delete = ['system']

    @classmethod
    def byID(self, id):
        return self.query.filter(self.id==int(id)).first()

    def __str__(self):
        if(self.company_name):
            return "%s %s, %s (%s)" % (self.first_name, self.last_name, self.company_name, self.id)
        return "%s %s (%s)" % (self.first_name, self.last_name, self.id)

