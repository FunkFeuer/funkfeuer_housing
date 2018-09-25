from flask_security import UserMixin, RoleMixin
from datetime import datetime, date
from sqlalchemy.orm import validates
from stdnum import iban

from ..model import db
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select, func

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
    groups_create = [ ]
    groups_edit = [ ]
    groups_delete = [ ]

    column_list = ('name', 'description', 'users')
    column_details_list =  ('name', 'description', 'users')

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
    sepa_mandate_id = db.Column(db.Unicode(32), unique=True)
    sepa_mandate_date = db.Column(db.Date(), default=None)
    sepa_mandate_first = db.Column(db.Boolean(), nullable=False, default=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    mailinglist = db.Column(db.Boolean(), nullable=False, default=True)

    password = db.Column(db.Unicode(255))
    active = db.Column(db.Boolean(), nullable=False)
    confirmed_at = db.Column(db.DateTime())
    last_login = db.Column(db.DateTime())
    keycard = db.Column(db.String)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users'))

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

    @property
    def billing_active(self):
        return self.billing_active_at()

    def billing_active_at(self, atdate=date.today()):
        for c in self.contracts:
            if c.billing_active_at(atdate):
                return True
        return False

    @validates('sepa_iban', 'sepa_mandate_id', 'sepa_mandate_date')
    def validate_sepa_mandate(self, key, value):
        if value == '' or value is None:
            self.sepa_mandate_first = True
            value = None

        if key == 'sepa_iban' and value:
            return iban.validate(value)

        if key == 'sepa_mandate_date':
            if value is None and self.sepa_mandate_id is not None:
                raise Exception( "SEPA mandate date must be set for a SEPA mandate." )
            elif value is not None and self.sepa_mandate_id is None:
                raise Exception( "SEPA mandate ID must be set for a SEPA mandate." )
            elif value is not None and self.sepa_iban is None:
                raise Exception( "IBAN must be set for a SEPA mandate." )
            elif value and value > date.today():
                raise Exception( "SEPA Mandate Date must not be in the future." )
        return value

    @property
    def has_sepa_mandate(self):
        if self.sepa_iban and self.sepa_mandate_id and self.sepa_mandate_date:
            return True
        return False

    @hybrid_property
    def balance(self):
        from .accounting import Invoice, Payment
        return sum([payment.amount for payment in self.payments]) - \
                    sum([invoice.amount for invoice in self.invoices])

    @balance.expression
    def balance(cls):
        from .accounting import Invoice, Payment
        return select([func.sum(Payment.amount - Invoice.amount)]).\
                where(Payment.contact_id==cls.id ).\
                where(Invoice.contact_id==cls.id ).\
                where(Invoice.sent_on is not None ).\
                label('total_amount'),

    form_columns = ('first_name', 'last_name', 'company_name', 'active', 'mailinglist', 'street', 'zip', 'town', 'country', 'email', 'phone', 'keycard')

    column_default_sort = ('id', False)
    column_filters = ('active','first_name','last_name', 'company_name', 'street')
    column_list = ('id', 'active', 'billing_active', 'first_name', 'last_name', 'company_name', 'servers')
    column_searchable_list = ( 'id', 'first_name', 'last_name', 'company_name', 'email', 'street')
    groups_view = ['admin', 'system']
    groups_create = ['admin', 'system']
    groups_edit = ['admin', 'system']
    groups_delete = ['system']

    @classmethod
    def byID(self, id):
        return self.query.filter(self.id==int(id)).first()

    def __str__(self):
        if(self.company_name):
            return "%s %s, %s (%s)" % (self.first_name, self.last_name, self.company_name, self.id)
        return "%s %s (%s)" % (self.first_name, self.last_name, self.id)

