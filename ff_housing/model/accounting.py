from ..model import db, User, insert_set_created_c
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select, func, event, inspect
from sqlalchemy.orm import validates
from datetime import datetime, date
import werkzeug.exceptions as exceptions
from wtforms.fields import TextAreaField

from ff_housing import app

_payment_types = db.Enum('SEPA-DD', 'money transfer', 'cash_payment', name='payment_types')

class Job(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    type = db.Column(db.Unicode(32))
    note = db.Column(db.Unicode(255))
    started = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    finished = db.Column(db.DateTime())
    user_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='SET NULL'))
    user = db.relationship(User, foreign_keys=[user_id])

    groups_view = ['billing']
    groups_details = ['billing']

    def __str__(self):
        return str(self.id)


class Invoice(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    address = db.Column(db.UnicodeText(255), nullable=False)
    contact_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='RESTRICT'), nullable=False)
    contact = db.relationship(User, foreign_keys=[contact_id], backref='invoices')
    created_c_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='RESTRICT'))
    created_c = db.relationship(User, foreign_keys=[created_c_id])
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    cancelled = db.Column(db.Boolean(), nullable=False, default=False)
    exported = db.Column(db.Boolean(), nullable=False, default=False)
    exported_id = db.Column(db.Unicode(35), nullable=True, default=None)
    payment_type = db.Column(_payment_types)
    sent_on = db.Column(db.DateTime(), default=None)
    job_id = db.Column(db.Integer(), db.ForeignKey(Job.id, ondelete='RESTRICT'), nullable=True)
    job = db.relationship(Job, foreign_keys=[job_id], backref='invoices')

    @property
    def number(self):
        return "AR%02d%05d" % (self.created_at.year % 100, self.id)

    def __str__(self):
        if self.cancelled:
            return "Invoice %s for %s (cancelled)" % (self.number, self.contact)
        return "Invoice %s for %s" % (self.number, self.contact)

    @property
    def path(self):
        return '%s/invoices/%s.pdf' % (app.config.get('FF_HOUSING_FILES_DIR', './files/').rstrip('/'), self.number)

    @property
    def sent(self):
        return (self.sent_on != None)

    @property
    def sort_date(self):
        return self.created_at

    @hybrid_property
    def amount(self):
        return sum([item.amount for item in self.items])

    @amount.expression
    def amount(cls):
        return select([func.sum(InvoiceItem.amount)]).\
                where(InvoiceItem.invoice_id==cls.id).\
                label('total_amount')

    @validates('exported_id')
    def validate_exported_id(self, key, value):
        if value is '':
            return None
        return value

    form_columns = ('contact','address', 'payment_type', 'sent_on')
    column_list = ('number', 'contact', 'amount', 'payment_type', 'created_at', 'sent', 'cancelled')
    column_searchable_list = ( 'id', 'contact.first_name', 'contact.last_name', 'contact.company_name')
    column_filters = ('id', 'payment_type', 'contact_id', 'amount', 'created_at', 'job_id')
    groups_view = ['billing']
    groups_create = ['billing']
    groups_edit = ['billing']
    groups_details = ['billing']
    inline_models = ('InvoiceItem',)

event.listen(Invoice, 'before_insert', insert_set_created_c)

@event.listens_for(Invoice, 'before_insert')
def Invoice_before_insert(mapper, connection, target):
    target.created_at = datetime.utcnow()
    target.address = target.contact.address

#@event.listens_for(Invoice, 'before_update')
def Invoice_before_update(mapper, connection, target):
    # prevent update if invoice has already been generated.
    if(inspect(target).attrs['sent_on'].history.deleted != None and
        inspect(target).attrs['sent_on'].history.deleted != [None]):
        raise exceptions.Forbidden()


class InvoiceItem(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    invoice_id = db.Column(db.Integer(), db.ForeignKey(Invoice.id, ondelete="CASCADE"), nullable=False)
    invoice = db.relationship(Invoice, backref='items')
    title = db.Column(db.Unicode(64))
    detail = db.Column(db.Unicode(255))
    unit_price = db.Column(db.Numeric(precision=10, scale=2, decimal_return_scale=2), nullable=False)
    quantity = db.Column(db.Integer(), default=1)

    @hybrid_property
    def amount(self):
        return self.unit_price * self.quantity

    @amount.expression
    def amount(cls):
        return cls.unit_price * cls.quantity

    groups_view = ['billing']
    groups_create = ['billing']
    groups_details = ['billing']

#@event.listens_for(InvoiceItem, 'before_update')
def InvoiceItem_before_update(mapper, connection, target):
    # prevent update if invoice has already been generated.
    if(inspect(target.invoice).attrs['sent_on'].history.deleted != None and \
        inspect(target.invoice).attrs['sent_on'].history.deleted != [None]):
        raise exceptions.Forbidden()

class Payment(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    contact_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='RESTRICT'), nullable=False)
    contact = db.relationship(User, backref='payments')
    date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    payment_type = db.Column(_payment_types)
    amount = db.Column(db.Numeric(precision=10, scale=2, decimal_return_scale=2))
    detail = db.Column(db.Unicode(255))
    reference = db.Column(db.String(128))
    job_id = db.Column(db.Integer(), db.ForeignKey(Job.id, ondelete='RESTRICT'), nullable=True)
    job = db.relationship(Job, foreign_keys=[job_id], backref='payments')

    groups_view = ['billing']
    groups_create = ['billing']
    groups_edit = ['billing']
    groups_details = ['billing']
    column_list = ('date', 'amount', 'contact', 'detail', 'job')
    column_default_sort = ('date', True)
    form_excluded_columns = ('created_at', 'changed_at')
    column_filters = ('id', 'payment_type', 'contact_id', 'amount', 'created_at', 'job_id', 'reference')

    @property
    def sort_date(self):
        return self.date

    def __str__(self):
        if self.amount < 0:
            return 'Payment %s from %s (failed) ' % (self.id, self.date.date())
        return 'Payment %s from %s ' % (self.id, self.date.date())

class Contract(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    billing_c_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='RESTRICT'), nullable=False)
    billing_c = db.relationship(User, backref='contracts', foreign_keys=[billing_c_id])
    created_c_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='RESTRICT'))
    created_c = db.relationship(User, backref='created_contracts', foreign_keys=[created_c_id])
    closed = db.Column(db.Boolean(), nullable=False, default=False)
    payment_type = db.Column(_payment_types)
    contracttype = db.Column(db.String(50))
    contract_state = db.Column(db.Enum('draft', 'sent', 'accepted', 'declined', 'closed', name='contract_state'), default='draft')

    __mapper_args__ = {
        'polymorphic_identity':'billable',
        'polymorphic_on': contracttype
    }

    def needs_billing(self, billdate=date.today()):
        if(self.closed):
            return False
        for p in self.packages:
            if p.needs_billing(billdate):
                return True
        return False

    form_excluded_columns = ('created_at', 'changed_at', 'created_c', 'contracttype')
    column_list = ('id', 'billing_c', 'created_at', 'changed_at')
    column_searchable_list = ('id',  'billing_c.first_name', 'billing_c.last_name', 'billing_c.company_name')
    column_default_sort = ('id', False)

    groups_view = ['billing']
    groups_edit = ['billing']
    groups_create = ['billing']
    groups_details = ['billing']

    @classmethod
    def byID(self, id):
        return self.query.filter(self.id==int(id)).first()

    def __str__(self):
        return 'c'+str(self.id)

event.listen(Contract, 'before_insert', insert_set_created_c)


class Package(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    type = db.Column(db.String(50))
    name = db.Column(db.Unicode(32))
    description = db.Column(db.Unicode(255))
    amount = db.Column(db.Numeric(precision=10, scale=2, decimal_return_scale=2))
    tax = db.Column(db.Numeric(precision=10, scale=2, decimal_return_scale=2))
    billing_period = db.Column(db.Integer(), default=1)

    def __str__(self):
        return str(self.name)

    form_columns = ('type', 'name', 'description', 'amount', 'billing_period')
    column_list = ('type', 'name', 'description', 'amount', 'billing_period')
    groups_view = ['admin', 'billing']
    groups_edit = ['billing']
    groups_create = ['billing']
    groups_details = ['billing']


class ContractPackage(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    contract_id = db.Column(db.Integer(), db.ForeignKey(Contract.id), nullable=False)
    package_id = db.Column(db.Integer(), db.ForeignKey(Package.id, ondelete='RESTRICT'), nullable=False)
    contract = db.relationship(Contract, backref='packages')
    package = db.relationship(Package, backref='contracts')
    quantity = db.Column(db.Integer(), default=1, nullable=False)
    
    active = db.Column(db.Boolean(), default=True, nullable=False )
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    opened_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime(), default=None)
    last_billed = db.Column(db.Date())
    billed_until = db.Column(db.Date())
    billing_period = db.Column(db.Integer(), default=None)

    def needs_billing(self, billdate=date.today()):
        if self.active and self.opened_at.date() <= billdate:
            if self.billed_until and self.billed_until > billdate:
                return False
            if self.closed_at and self.billed_until and self.closed_at <= self.billed_until:
                return False
            else:
                return True
        return False

    @property
    def amount(self):
        return self.package.amount

    @validates('billing_period')
    def validate_billing_period(self, key, value):
        if value == '' or value is None:
            return self.package.billing_period
        return value

    groups_view = ['admin', 'billing']
    groups_edit = ['billing']
    groups_create = ['billing']
    groups_details = ['billing']

    def __str__(self):
        return "%s (%s)" % (self.package.name, self.contract)
