from flask_security import UserMixin, RoleMixin
from sqlalchemy_utils import EmailType
from datetime import datetime

from ..model import db


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


class Contact(db.Model):
    __tablename__ = 'contact'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.Unicode(48), nullable=False)
    last_name = db.Column(db.Unicode(48), nullable=False)
    company_name = db.Column(db.Unicode(48))
    street = db.Column(db.Unicode(127), nullable=False)
    zip = db.Column(db.Unicode(16), nullable=False)
    town = db.Column(db.Unicode(32), nullable=False)
#    state = db.Column(db.Unicode(32), nullable=False)
    country = db.Column(db.Unicode(32), nullable=False)
    email = db.Column(EmailType, nullable=False)
    phone = db.Column(db.Unicode(32))
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    type = db.Column(db.String(32))
    __mapper_args__ = {
        'polymorphic_identity': 'contact',
        'polymorphic_on': type
    }
    
    @property
    def address(self):
        addr = "%s\n%s %s\n%s" % (self.street, self.zip, self.town, self.country) # state
        if(self.company_name):
            return ("%s\n%s %s\n\n%s" % (self.company_name, self.first_name, self.last_name, addr))
        return ("%s %s\n\n%s" % (self.first_name, self.last_name, addr))
    
    column_list = ('type', 'first_name', 'last_name', 'company_name', 'email', 'street', 'zip', 'town')
    groups_view = ['admin']
    groups_create = ['admin']
    groups_edit = ['admin']
    groups_delete = ['admin']
    column_searchable_list = ('first_name','last_name', 'company_name', 'email', 'street')
    column_filters = ('first_name','last_name', 'company_name', 'street')
    column_default_sort = ('id', False)

    def __str__(self):
        if(self.company_name):
            return self.company_name
        return "%s %s" % (self.first_name, self.last_name)

class User(Contact, UserMixin):
    id = db.Column(db.Integer(), db.ForeignKey(Contact.id), primary_key=True)
    login = db.Column(db.Unicode(32), unique=True, nullable=False)
    password = db.Column(db.Unicode(255))
    active = db.Column(db.Boolean(), nullable=False)
    confirmed_at = db.Column(db.DateTime())
    last_login = db.Column(db.DateTime())
    keycard = db.Column(db.String)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))
    __mapper_args__ = {
        'polymorphic_identity':'user',
    }

    column_default_sort = ('id', False)
    column_filters = ('active','login','first_name','last_name', 'company_name', 'street')
    column_list = ('active','login', 'first_name', 'last_name', 'company_name', 'email', 'street', 'zip', 'town', 'keycard')
    groups_view = ['admin']
    groups_create = ['admin']
    groups_edit = ['admin']
    groups_delete = ['admin']

    def __str__(self):
        if(self.company_name):
            return "%s %s, %s (%s)" % (self.first_name, self.last_name, self.company_name, self.login)
        return "%s %s (%s)" % (self.first_name, self.last_name, self.login)
