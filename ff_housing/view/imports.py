import csv
from flask_security.utils import encrypt_password
from dateutil import parser
import ipaddress

from .. import model, app, user_datastore, utils
from ..model import db


packagemap = {
    '1' : {'id':1, 'billing_period': 1,  'quantity': 1}, # Serverhousing
    '3' : {'id':7, 'billing_period': 1,  'quantity': 1}, # Serverhousing Micro Old 12
    '4' : {'id':1, 'billing_period': 6,  'quantity': 1}, # 6 Monate Serverhousing
    '10': {'id':4, 'billing_period': 1,  'quantity': 2}, # 100W Power Upgrade
    '14': {'id':2, 'billing_period': 1,  'quantity': 1}, # Serverhousing Micro
    '15': {'id':1, 'billing_period': 12, 'quantity': 1}, # 1 Jahr Serverhousing
    '17': {'id':5, 'billing_period': 1,  'quantity': 1}, # VServer
    '19': {'id':2, 'billing_period': 6,  'quantity': 1}, # 6 Monate Serverhousing Micro
    '20': {'id':6, 'billing_period': 1,  'quantity': 1}, # VServer normal
    '22': {'id':4, 'billing_period': 1,  'quantity': 3}, # 150W Power Upgrade
    '23': {'id':5, 'billing_period': 1,  'quantity': 1}, # Vserver mini
    '26': {'id':2, 'billing_period': 12,  'quantity': 1}, # Serverhousing Micro 1 Jahr
    '27': {'id':4, 'billing_period': 1,  'quantity': 1}, # 50W Power Upgrade
    '28': {'id':8, 'billing_period': 12, 'quantity': 1}, # 1 Jahr Serverhousing Micro Old
    '29': {'id':4, 'billing_period': 1,  'quantity': 27}, # 1350W Power Upgrade
}

#"id","created_at","changed_at","type","name","description","amount","tax","billing_period"
#1,"2017-01-01",,"housing","Serverhousing","Serverhousing Normal",40.00,0.00,1
#2,"2017-01-01",,"housing","Serverhousing Micro","Serverhousing Micro",19.00,0.00,1
#3,"2017-01-01",,"housing","Serverhousing Embedded","Embedded Device Serverhousing",5.00,0.00,12
#4,"2017-01-01",,"upgrade","Power Upgrade 50W","Serverhousing 5W Power Upgrade",6.00,0.00,1
#5,"2017-01-01",,"vserver","VServer mini","Serverhousing",9.00,0.00,1
#6,"2017-01-01",,"vserver","VServer normal","Serverhousing",19.00,0.00,1
#7,"2017-01-01",,"housing","(old) Serverhousing Micro 12","Serverhousing  Micro Old 12",12.00,0.00,1
#8,"2017-01-01",,"housing","(old) Serverhousing Micro 15","Serverhousing  Micro Old 15",15.00,0.00,1

#{'packagegroupid': '1', 'billing_period': 1, 'description': 'Serverhousing', 'price': '40.00'}
#{'packagegroupid': '3', 'billing_period': 1, 'description': 'Serverhousing Micro Old 12', 'price': '12.00'}
#{'packagegroupid': '4', 'billing_period': 6, 'description': '6 Monate Serverhousing', 'price': '240.00'}
#{'packagegroupid': '10', 'billing_period': 1, 'description': '100W Power Upgrade', 'price': '10.00'}
#{'packagegroupid': '14', 'billing_period': 1, 'description': 'Serverhousing Micro', 'price': '19.00'}
#{'packagegroupid': '15', 'billing_period': 12, 'description': '1 Jahr Serverhousing', 'price': '480.00'}
#{'packagegroupid': '17', 'billing_period': 1, 'description': 'VServer', 'price': '9.00'}
#{'packagegroupid': '19', 'billing_period': 6, 'description': '6 Monate Serverhousing Micro', 'price': '114.00'}
#{'packagegroupid': '20', 'billing_period': 1, 'description': 'VServer normal', 'price': '19.00'}
#{'packagegroupid': '22', 'billing_period': 1, 'description': '150W Power Upgrade', 'price': '18.00'}
#{'packagegroupid': '23', 'billing_period': 1, 'description': 'Vserver mini', 'price': '9.00'}
#{'packagegroupid': '26', 'billing_period': 12, 'description': 'Serverhousing Micro 1 Jahr', 'price': '228.00'}
#{'packagegroupid': '27', 'billing_period': 1, 'description': '50W Power Upgrade', 'price': '6.00'}
#{'packagegroupid': '28', 'billing_period': 12, 'description': '1 Jahr Serverhousing Micro Old', 'price': '180.00'}
#{'packagegroupid': '29', 'billing_period': 1, 'description': '1350W Power Upgrade', 'price': '162.00'}

def import_redeemer_csv(dir='data/'):
    '''import tab-seperated csvs from redeemer psql dumps'''
    
    with app.app_context():
        
        db.drop_all()
        db.create_all()
        
        system_role = model.Role(name='system')
        db.session.add(system_role)
        billing_role = model.Role(name='billing')
        db.session.add(billing_role)
        admin_role = model.Role(name='admin')
        db.session.add(admin_role)
        keymaster_role = model.Role(name='keymaster')
        db.session.add(keymaster_role)
        user_role = model.Role(name='user')
        db.session.add(user_role)
        
        db.session.add(model.ServerType(name='Server (Tower)', description=''))
        db.session.add(model.ServerType(name='Server (Rack)', description=''))
        db.session.add(model.ServerType(name='Embedded Server', description=''))
        db.session.add(model.ServerType(name='VM (wirt3)', description=''))
        db.session.add(model.ServerType(name='VM (deepthought)', description=''))
        db.session.add(model.ServerType(name='VM (vogsphere)', description=''))
        
        db.session.commit()
        
        with open(dir+'redeemer/customers.csv') as csvfile:
            reader = csv.DictReader(csvfile, dialect='excel-tab')
            for r in reader:
                r = {k: None if (v=='\\N') else v for k, v in r.items()}
                
                user_datastore.create_user(id=int(r['id']),
                        login=str(r['id']),
                        password='',
                        active=True,
                        confirmed_at=None,
                        last_login=None,
                        keycard=r['keycard'],
                        first_name=r['firstname'],
                        last_name=r['lastname'],
                        email=r['email'],
                        phone=r['phone'],
                        company_name=r['company'],
                        street=r['street'],
                        zip=r['zip'],
                        town=r['town'],
                        country=r['zip'])
            
            user_datastore.create_user(
                login='admin',
                first_name='Admin',
                email='admin',
                password=encrypt_password('admin'),
                roles=[admin_role, billing_role],
                last_name="Brown",
                street="Adminstreet 1",
                zip="1234",
                town="Admintown",
                country="Admincountry",
                active=True
            )
            db.session.commit()
        
        with open(dir+'redeemer/servers.csv') as csvfile:
            reader = csv.DictReader(csvfile, dialect='excel-tab')
            for r in reader:
                r = {k: None if (v=='\\N') else v for k, v in r.items()}
                
                db.session.add(model.Server(
                    id = int(r['id']),
                    name = 's'+str(r['id']),
                    description = '',
                    created_at = parser.parse(r['created']),
                    admin_c_id = int(r['id_customers']),
                    billing_c_id = int(r['id_customers']),
                    created_c_id = int(r['created_by']) if (r['created_by']) else None,
                    active = True,
                    closed = False
                    ))
                
            db.session.commit()
        
        
        iptype_public = model.IPType(name='public', description="public subnets")
        db.session.add(iptype_public)
        db.session.add(model.IPType(name='FF management', description="core management subnet"))
        db.session.add(model.IPType(name='ipmi', description="IPMI/KVM management subnet"))
        
        with open(dir+'redeemer/ips.csv') as csvfile:
            reader = csv.DictReader(csvfile, dialect='excel-tab')
            for r in reader:
                r = {k: None if (v=='\\N') else v for k, v in r.items()}
                
                db.session.add(model.IP(
                    id = int(r['id']),
                    type = iptype_public,
                    active = True,
                    is_subnet = False,
                    ip_address = r['ip'],
                    family = ipaddress.ip_interface(r['ip']).version,
                    gateway = r['gateway'],
                    rdns = r['reverse_dns'],
                    server_id = r['id_servers'],
                    monitoring = True if (r['nagios']=='t') else False
                    ))
                
            db.session.commit()

def import_packages(dir):
    with open(dir+'packages.csv') as csvfile:
        for r in csv.DictReader(csvfile):
            r = {k: None if (v=='') else v for k, v in r.items()}
            r['created_at'] = parser.parse(r['created_at'])
            db.session.add(model.Package(**r))
        db.session.commit()


def import_cwispy_csv(dir='data/'):
    import re
    
    custidmapper = {}
    packages = {}
    
    # insert new packages
    
    
    
    # load packages
    with open(dir+'cwispy/packagegroup.csv') as csvfile:
        for r in csv.DictReader(csvfile):
            r = {k: None if (v=='') else v for k, v in r.items()}
            del(r['charged'])
            del(r['tax'])
            packages[int(r['packagegroupid'])] = r
    
    
    with open(dir+'cwispy/customers.csv') as csvfile:

        print('### CUSTOMERS ###')
        for r in csv.DictReader(csvfile):
            r = {k: None if (v=='') else v for k, v in r.items()}
            
            if ( 'ccnumber' in r and r['ccnumber'] != None):
                custidmapper[r['customerid']] = int(r['ccnumber'])
                
                for c in model.Contact.query.filter(model.Contact.id==int(r['ccnumber'])):
                    if(c.first_name != r['first'] or c.last_name != r['last']):
                        print('!! different billing address:', c, '\t', r['first'], r['last'], r['company'])
        
        print('\n\n### ACCOUNTS ###')
        # read accounts
        with open(dir+'cwispy/accounts.csv') as csvfile:
            for r in csv.DictReader(csvfile):
                r = {k: None if (v=='') else v for k, v in r.items()}
                r = {k: None if (v=='0000-00-00') else v for k, v in r.items()}
                
                server = None
                
                if (r['status'] == 'Closed'):
                    continue
                
                
                if (r['domain']):
                    # try to get server ID from package name
                    m = re.match('s(\d+)', r['domain'])
                    if(m):
                        server = model.Server.byID(m.group(1))
                    else:
                        # no server ID found, get through IP
                        m = re.search('(\d+\.\d+\.\d+\.\d+)', r['domain'])
                        if(m):
                            server = utils.ip_find_server(m.group(1))
                
                
                if not server:
                    print("!! could not find Server:", \
                        model.Contact.query.filter(model.Contact.id==custidmapper[r['customerid']]).one(), \
                        "\t", r['customerid'], \
                        packages[int(r['packagegroupid'])]['description'], \
                        r['dateopened'], \
                        r['status'], \
                        r['domain'], \
                        r['lastdatebilled'], \
                        r['nextdatebilled'])
                    continue
                
                
                # import accounts to DB
                print("# account:", \
                        model.Contact.query.filter(model.Contact.id==custidmapper[r['customerid']]).one(), \
                        "\t",
                        r['domain'])
                db.session.add(model.ContractPackage(
                    contract = server,
                    package_id = packagemap[r['packagegroupid']]['id'],
                    quantity = packagemap[r['packagegroupid']]['quantity'],
                    active = True,
                    created_at = parser.parse(r['dateopened']) if r['dateopened'] else None,
                    opened_at = parser.parse(r['dateopened'])  if r['dateopened'] else None,
                    last_billed = parser.parse(r['lastdatebilled']) if (r['lastdatebilled']) else None,
                    billed_until = parser.parse(r['nextdatebilled']),
                    billing_period = packagemap[r['packagegroupid']]['billing_period']
                ))
            
            db.session.commit()
