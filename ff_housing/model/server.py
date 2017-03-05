from sqlalchemy.orm import validates
from sqlalchemy import event

from ..model import db, User, Contact, Contract, insert_set_created_c
import ipaddress


class ServerType(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode(32), nullable=False)
    description = db.Column(db.Unicode(255))
    
    groups_details = ['admin']
    groups_view = ['admin', 'system']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']
    
    def __str__(self):
        return str(self.name)

class Server(Contract):
    #id = db.Column(db.Integer(), primary_key=True)
    id = db.Column(db.Integer(), db.ForeignKey(Contract.id), primary_key=True)
    servertype_id = db.Column(db.Integer(), db.ForeignKey(ServerType.id, ondelete='RESTRICT'))
    servertype = db.relationship(ServerType, backref='servers')
    active = db.Column(db.Boolean(), nullable=False, default=True)
    name = db.Column(db.Unicode(48))
    description = db.Column(db.Unicode(255))
    location = db.Column(db.Unicode(48))
    admin_c_id = db.Column(db.Integer(), db.ForeignKey(Contact.id, ondelete='RESTRICT'), nullable=False)
    admin_c = db.relationship(Contact, backref='servers')
    server_state = db.Column(db.Enum('draft', 'sent', 'accepted', 'declined', 'closed', name='contract_state'), default='draft')
    
    groups_view = ['admin']
    groups_create = ['admin']
    groups_edit = ['admin']
    groups_delete = ['admin']
    column_list = ('id', 'admin_c', 'servertype', 'created_at', 'ips','active')
    column_searchable_list = ('id', 'admin_c.first_name', 'admin_c.last_name', 'admin_c.company_name', 
                              'name', 'location', 'billing_c.first_name', 'billing_c.last_name', 'billing_c.company_name', 'ips.ip_address')
    column_filters = ('active', 'created_at', 'admin_c')
    
    __mapper_args__ = {
        'polymorphic_identity':'server',
    }
    
    def __str__(self):
        return 's'+str(self.id)

event.listen(Server, 'before_insert', insert_set_created_c)

class IPType(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.Unicode(32), nullable=False)
    description = db.Column(db.Unicode(255))
    
    groups_details = ['admin']
    groups_view = ['admin', 'system']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']
    
    def __str__(self):
        return str(self.name)


class SwitchPort(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    switch = db.Column(db.Unicode(32))
    port = db.Column(db.Unicode(32))
    
    groups_view = ['admin']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']
    
    def __str__(self):
        return str("%s (%d)" % (self.switch, self.port))


class IP(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    type_id = db.Column(db.Integer(), db.ForeignKey(IPType.id, ondelete='RESTRICT'), nullable=False)
    type = db.relationship(IPType, backref='ips')
    switchport_id = db.Column(db.Integer(), db.ForeignKey(SwitchPort.id))
    switchport = db.relationship(SwitchPort, backref='ips')
    active = db.Column(db.Boolean(), default=True, nullable=False)
    is_subnet = db.Column(db.Boolean(), default=False, nullable=False)
    family = db.Column(db.Integer(), nullable=False)
    ip_address = db.Column(db.String(48), unique=True, nullable = False)
    gateway = db.Column(db.String(45))
    rdns = db.Column(db.String(255))
    server_id = db.Column(db.Integer(), db.ForeignKey(Server.id))
    server = db.relationship(Server, backref='ips')
    
    monitoring = db.Column(db.Boolean(), default=False, nullable=False)
    
    form_columns = ('type','ip_address', 'gateway', 'rdns', 'monitoring')
    column_searchable_list = ( 'ip_address', 'rdns')
    column_filters = ('type', 'active', 'ip_address', 'family')
    
    @validates('ip_address')
    def validate_ip_address(self, key, value):
        assert value != ''
        if self.is_subnet:
            return str(ipaddress.ip_network(value))
        else:
            return str(ipaddress.ip_interface(value))
    
    
    groups_details = ['admin']
    groups_view = ['admin']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']

    def __str__(self):
        return str(self.ip_address)

