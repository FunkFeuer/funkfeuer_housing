import os
from flask import Flask, url_for, redirect, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask_security.utils import encrypt_password
import flask_admin
from flask_admin.contrib import sqla
from flask_admin import helpers as admin_helpers
from flask_admin.base import expose

from flask_script import Manager
from flask_mail import Mail
from flask.ext.migrate import Migrate, MigrateCommand

# Create Flask application
app = Flask(__name__)

app.config.from_pyfile('../config_debug.py')
app.config.from_pyfile('../config.py', silent=True)


from .model import db
import ff_housing.model as model

user_datastore = SQLAlchemyUserDatastore(db, model.User, model.Role)
security = Security(app, user_datastore)
manager = Manager(app)
mail = Mail(app)

migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

import ff_housing.view as view


admin = flask_admin.Admin(
    app,
    'Funkfeuer Housing',
    base_template='my_master.html',
    template_mode='bootstrap3',
    index_view=flask_admin.AdminIndexView(
        name='Home',
        url='/'
    )
)

# Add model views
admin.add_view(view.UserEditView(model.User, db.session, endpoint="profile"))

# admin.add_view(view.UserServerView(model.Server, db.session, name='My Servers', endpoint="servers", menu_icon_type='glyph', menu_icon_value='glyphicon-tasks'))
admin.add_view(view.ContractView(model.Server, db.session, category='Admin', name='Servers'))
admin.add_view(view.ACLView(model.IP, db.session, category='Admin', name='IPs'))
admin.add_view(view.ACLView(model.User, db.session, category='Admin', name='Users'))
admin.add_view(view.ACLView(model.Contact, db.session, category='Admin', name='Contacts'))

admin.add_view(view.ContractView(model.Contract, db.session, category='Billing'))
admin.add_view(view.InvoiceView(model.Invoice, db.session, category='Billing'))
admin.add_view(view.ACLView(model.Payment, db.session, category='Billing'))
admin.add_view(view.ACLView(model.Package, db.session, category='Billing'))


# define a context processor for merging flask-admin's template context into the
# flask-security views.
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )


def build_sample_db():
    """
    Populate a small db with some example entries.
    """
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if os.path.exists(database_path):
        return
    
    import string
    import random
    import ipaddress

    db.drop_all()
    db.create_all()

    with app.app_context():
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
        db.session.commit()


        user_datastore.create_user(
            login='system',
            first_name='System',
            email='system',
            password=encrypt_password('system'),
            roles=[system_role, admin_role],
            last_name="",
            street="",
            zip="",
            town="",
            country="",
            active=True
        )

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
        user_datastore.create_user(
            login='billing',
            first_name='Billing',
            email='billing',
            password=encrypt_password('user'),
            roles=[billing_role],
            last_name="",
            street="",
            zip="",
            town="",
            country="",
            active=True
        )
        user_datastore.create_user(
            login='user',
            first_name='User',
            email='user',
            password=encrypt_password('user'),
            roles=[user_role],
            last_name="",
            street="",
            zip="",
            town="",
            country="",
            active=True
        )

        first_names = [
            'Harry', 'Amelia', 'Oliver', 'Jack', 'Isabella', 'Charlie', 'Sophie', 'Mia'
        ]
        last_names = [
            'Brown', 'Smith', 'Patel', 'Jones', 'Williams', 'Johnson', 'Taylor', 'Thomas'
        ]

        for i in range(len(first_names)):
            tmp_email = first_names[i].lower() + "." + last_names[i].lower() + "@example.com"
            tmp_pass = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(10))
            user_datastore.create_user(
                login=str(i+1),
                first_name=first_names[i],
                last_name=last_names[i],
                email=tmp_email,
                password=encrypt_password(str(i+1)),
                roles=[user_role],
                street="",
                zip="",
                town="",
                country="",
                active=True
            )
        
        iptype_public = model.IPType(name='public', description="public subnets")
        db.session.add(iptype_public)
        db.session.add(model.IPType(name='FF management', description="core management subnet"))
        db.session.add(model.IPType(name='ipmi', description="IPMI/KVM management subnet"))
        
        db.session.add(model.ServerType(name='Server (Tower)', description=''))
        db.session.add(model.ServerType(name='Server (Rack)', description=''))
        db.session.add(model.ServerType(name='Embedded Server', description=''))
        db.session.add(model.ServerType(name='VM (wirt3)', description=''))
        db.session.add(model.ServerType(name='VM (deepthought)', description=''))
        db.session.add(model.ServerType(name='VM (vogsphere)', description=''))
        
        
        for host in ipaddress.ip_network('193.238.157.0/25').hosts():
            db.session.add(model.IP(ip_address="%s/25" % host, family=4 , type=iptype_public))
        
        db.session.add(model.SwitchPort(switch='core', port="A1"))
        db.session.add(model.SwitchPort(switch='core', port="A2"))
        db.session.add(model.SwitchPort(switch='core', port="A3"))
        db.session.add(model.SwitchPort(switch='core', port="A4"))
        
        db.session.add(model.Package(type='serverhousing', name='Serverhousing Normal', description='150W', amount=40.00, billing_period=1))
        db.session.add(model.Package(type='serverhousing', name='Serverhousing Mini', description='45W', amount=19.00, billing_period=1))
        
        db.session.commit()
    return
