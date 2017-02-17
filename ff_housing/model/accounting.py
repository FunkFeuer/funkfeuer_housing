from ..model import db, Contact, User
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select, func, event
# automatic billing - job id
from datetime import datetime, date

class Job(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    description = db.Column(db.Unicode(255))
    started = db.Column(db.DateTime(), nullable=False)
    finished = db.Column(db.DateTime())

    groups_view = ['admin', 'billing']
    groups_details = ['billing']

    def __str__(self):
        return str(self.id)


class Invoice(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    address = db.Column(db.Unicode(255), nullable=False)
    contact_id = db.Column(db.Integer(), db.ForeignKey(Contact.id, ondelete='RESTRICT'), nullable=False)
    contact = db.relationship(Contact, backref='invoices')
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    path = db.Column(db.String(64))
    sent_on = db.Column(db.DateTime(), default=None)

    @property
    def number(self):
        return "AR%08d" % self.id

    @property
    def sent(self):
        return (self.sent_on != None)

    @hybrid_property
    def amount(self):
        return sum([item.amount for item in self.items])

    @amount.expression
    def amount(cls):
        return select([func.sum(InvoiceItem.amount)]).\
                where(InvoiceItem.invoice_id==cls.id).\
                label('total_amount')

    form_columns = ('contact',)
    column_list = ('number', 'contact', 'amount', 'created_at', 'sent')
    groups_view = ['billing']
    groups_create = ['billing']
    groups_details = ['billing']

def Invoice_before_insert(mapper, connection, target):
    created_at = datetime.utcnow
    target.address = target.contact.address

# associate the listener function with SomeClass,
# to execute during the "before_insert" hook
event.listen(Invoice, 'before_insert', Invoice_before_insert)


class InvoiceItem(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    invoice_id = db.Column(db.Integer(), db.ForeignKey(Invoice.id), nullable=False)
    invoice = db.relationship(Invoice, backref='items')
    title = db.Column(db.Unicode(32))
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


class Payment(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    contact_id = db.Column(db.Integer(), db.ForeignKey(Contact.id, ondelete='RESTRICT'), nullable=False)
    contact = db.relationship(Contact, backref='payments')
    date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    paymenttype = db.Column(db.Unicode(32))
    amount = db.Column(db.Numeric(precision=10, scale=2, decimal_return_scale=2))
    detail = db.Column(db.Unicode(255))
    reference = db.Column(db.String(128))

    groups_view = ['billing']
    groups_create = ['billing']
    groups_details = ['billing']


class Contract(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    billing_c_id = db.Column(db.Integer(), db.ForeignKey(Contact.id, ondelete='RESTRICT'), nullable=False)
    billing_c = db.relationship(Contact, backref='contracts', foreign_keys=[billing_c_id])
    created_c_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='RESTRICT'))
    created_c = db.relationship(User, backref='created_contracts', foreign_keys=[created_c_id])
    closed = db.Column(db.Boolean(), nullable=False, default=False)
    payment_type = db.Column(db.Enum('SEPA-DD', 'money transfer', 'cash_payment', name='payment_types'))
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

    #form_columns = ('billing_c', 'contracttype')
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
    quantity = db.Column(db.Integer(), default=1)
    
    active = db.Column(db.Boolean(), default=True, nullable=False )
    created_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    changed_at = db.Column(db.DateTime(), onupdate=datetime.utcnow)
    opened_at = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime(), default=None)
    last_billed = db.Column(db.Date())
    billed_until = db.Column(db.Date())
    billing_period = db.Column(db.Integer(), default=1)

    def needs_billing(self, billdate=date.today()):
        if (self.active and self.billed_until <= billdate):
            return True
        return False

    @property
    def amount(self):
        return self.package.amount

    #column_list = ('contract', 'package', 'last_billed', 'billed_until', 'billing_period')
    groups_view = ['admin', 'billing']
    groups_edit = ['billing']
    groups_create = ['billing']
    groups_details = ['billing']

    def __str__(self):
        return "%s (%s)" % (self.package.name, self.contract)
