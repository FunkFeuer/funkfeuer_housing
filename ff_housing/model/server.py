from sqlalchemy.orm import validates
from sqlalchemy import event

from ..model import db, User, Contract, insert_set_created_c
import ipaddress, re


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
    id = db.Column(db.Integer(), db.ForeignKey(Contract.id), primary_key=True)
    servertype_id = db.Column(db.Integer(), db.ForeignKey(ServerType.id, ondelete='RESTRICT'))
    servertype = db.relationship(ServerType, backref='servers')
    active = db.Column(db.Boolean(), nullable=False, default=True)
    name = db.Column(db.Unicode(48))
    description = db.Column(db.Unicode(255))
    location = db.Column(db.Unicode(48))
    admin_c_id = db.Column(db.Integer(), db.ForeignKey(User.id, ondelete='RESTRICT'), nullable=False)
    admin_c = db.relationship(User, backref='servers')

    groups_view = ['admin']
    groups_create = ['admin']
    groups_edit = ['admin']
    groups_delete = ['admin']
    column_list = ('id','active', 'admin_c', 'ips', 'location', 'servertype', 'created_at')
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

class PowerOutlet(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    outlet = db.Column(db.Unicode(32), unique=True, nullable=False)
    active = db.Column(db.Boolean(), default=True, nullable=False)
    server_id = db.Column(db.Integer(), db.ForeignKey(Server.id, ondelete="SET NULL"))
    server = db.relationship(Server, backref='outlets')

    groups_view = ['admin']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']

    def __str__(self):
        return str("Outlet %d" % (self.outlet))

class IP(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    type_id = db.Column(db.Integer(), db.ForeignKey(IPType.id, ondelete='RESTRICT'), nullable=False)
    type = db.relationship(IPType, backref='ips')
    switchport_id = db.Column(db.Integer(), db.ForeignKey(SwitchPort.id, ondelete="SET NULL"))
    switchport = db.relationship(SwitchPort, backref='ips')
    active = db.Column(db.Boolean(), default=True, nullable=False)
    ip_address = db.Column(db.String(48), unique=True, nullable = False)
    routed_subnet = db.Column(db.String(48), default=None, unique=True, nullable = True)
    gateway = db.Column(db.String(45))
    rdns = db.Column(db.String(255))
    server_id = db.Column(db.Integer(), db.ForeignKey(Server.id, ondelete="SET NULL"))
    server = db.relationship(Server, backref='ips')

    monitoring = db.Column(db.Boolean(), default=False, nullable=False)

    form_columns = ('type','ip_address', 'gateway', 'rdns', 'routed_subnet', 'monitoring')
    column_searchable_list = ( 'ip_address', 'rdns')
    column_filters = ('type', 'active', 'ip_address', 'server_id')

    @property
    def ip(self):
        return ipaddress.ip_interface(self.ip_address).ip

    @property
    def netmask(self):
        if self.family == 6:
            return ipaddress.ip_interface(self.ip_address).with_prefixlen.split('/')[1]
        else:
            return ipaddress.ip_interface(self.ip_address).with_netmask.split('/')[1]

    @property
    def family(self):
        return ipaddress.ip_interface(self.ip_address).version

    @validates('ip_address')
    def validate_ip_address(self, key, value):
        assert value != ''
        return str(ipaddress.ip_interface(value))

    @validates('routed_subnet')
    def validate_routed_subnet(self, key, value):
        if value == '' or value == None:
            return None
        if not ipaddress.ip_network(value).version == self.family:
            raise Exception( "Subnet IP version does not match IP Address." )
        return str(ipaddress.ip_network(value))

    @validates('rdns')
    def validate_rdns(self, key, value):
        if value is None:
            return value
        hostname = value.rstrip('.')
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if not all(allowed.match(x) for x in hostname.split(".")):
            raise Exception( "Reverse DNS record is invalid." )
        return str(hostname)

    groups_details = ['admin']
    groups_view = ['admin']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']

    def __str__(self):
        if self.routed_subnet is not None:
            return "%s (via %s)" % (self.routed_subnet, self.ip)
        return str(self.ip)

from flask_security import current_user

class Subnet_rDNS(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    subnet_id = db.Column(db.Integer(), db.ForeignKey(IP.id, ondelete="CASCADE"))
    subnet = db.relationship(IP, backref='subnet_rdns')
    ip_address = db.Column(db.String(48), unique=True, nullable = False)
    rdns = db.Column(db.String(255))

    monitoring = db.Column(db.Boolean(), default=False, nullable=False)

    form_columns = ('subnet','ip_address', 'rdns', 'monitoring')
    column_searchable_list = ( 'ip_address', 'rdns')
    column_filters = ('rdns', 'ip_address', 'subnet')

    @property
    def ip(self):
        return ipaddress.ip_address(self.ip_address)

    @property
    def ip_subnet(self):
        return self.subnet.routed_subnet

    @property
    def family(self):
        return self.subnet.family

    @validates('subnet')
    def validate_subnet(self, key, value):
        if current_user and not bool(set(self.groups_edit) & set(current_user.roles)):
            if value.server.admin_c is not current_user:
                raise Exception( "Not allowed." )
        if value.routed_subnet is None or value.routed_subnet is '':
            raise Exception( "Upstream IP does not have a routed subnet." )
        return value

    @validates('ip_address')
    def validate_ip_address(self, key, value):
        assert value != ''
        if not ipaddress.ip_address(value) in ipaddress.ip_network(self.ip_subnet):
            raise Exception( "IP Address is not in selected subnet (%s)" % self.ip_subnet )
        return str(ipaddress.ip_address(value))

    @validates('rdns')
    def validate_rdns(self, key, value):
        if value is None:
            return value
        hostname = value.rstrip('.')
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if not all(allowed.match(x) for x in hostname.split(".")):
            raise Exception( "Reverse DNS record is invalid." )
        return str(hostname)

    groups_details = ['admin']
    groups_view = ['admin']
    groups_create = ['system']
    groups_edit = ['system']
    groups_delete = ['system']

    def __str__(self):
        return str(self.ip_address)
