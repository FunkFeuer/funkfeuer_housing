import os
from flask import Flask, url_for, redirect, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
import flask_admin
from flask_admin.contrib import sqla
from flask_admin import helpers as admin_helpers
from flask_admin.base import expose

from flask_script import Manager
from flask_mail import Mail
from flask_migrate import Migrate, MigrateCommand

# Create Flask application
app = Flask(__name__)

app.config.from_pyfile('config_defaults.py')

if(os.environ.get('CONFIG')):
    app.config.from_pyfile(os.environ.get('CONFIG'))
else:
    try:
        app.config.from_pyfile('/etc/funkfeuer-housing/config.py')
    except FileNotFoundError:
        print('WARNING: for production you should create /etc/funkfeuer-housing/config.py')
        print('  or set the CONFIG environment variable.')
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
    'FunkFeuer Housing',
    base_template='my_master.html',
    template_mode='bootstrap3',
    index_view=flask_admin.AdminIndexView(
        name='Home',
        url='/'
    )
)

# Add model views
admin.add_view(view.UserEditView(model.User, db.session, endpoint="profile", menu_icon_type='glyph', menu_icon_value='glyphicon-user'))
admin.add_view(view.UserServerView(model.Server, db.session, category='Server', endpoint="server", menu_icon_type='glyph', menu_icon_value='glyphicon-tasks'))
admin.add_view(view.PowerOuletUserView(model.PowerOutlet, db.session, category='Server', name='Power Outlets', endpoint="power",  menu_icon_type='glyph', menu_icon_value='glyphicon-flash'))
admin.add_view(view.UserIPView(model.IP, db.session, endpoint="ip", category='IPs / rDNS', name='IPs / rDNS', menu_icon_type='glyph', menu_icon_value='glyphicon-globe'))
admin.add_view(view.UserSubnetRDNSView(model.Subnet_rDNS, db.session, endpoint="subnet_rdns", category='IPs / rDNS', name='Subnet rDNS', menu_icon_type='glyph', menu_icon_value='glyphicon-list'))

# Admin Views
admin.add_view(view.AdminServerView(model.Server, db.session, category='Admin', name='Servers', endpoint="admin/servers"))
admin.add_view(view.AdminUserView(model.User, db.session, category='Admin', name='Users', endpoint="admin/users"))

admin.add_view(view.AdminInvoiceView(model.Invoice, db.session, category='Billing', endpoint="admin/invoices"))
admin.add_view(view.ACLView(model.Payment, db.session, category='Billing', endpoint="admin/payments"))
admin.add_view(view.SepaExportView(model.Invoice, db.session, category='Billing', name='SEPA Export', endpoint="admin/sepa-export", menu_icon_type='glyph',  menu_icon_value='glyphicon-open'))
admin.add_view(view.PaymentImportView(name='Import Payments', category='Billing', endpoint='billing/import_payments', menu_icon_type='glyph',  menu_icon_value='glyphicon-save'))

admin.add_view(view.ACLView(model.Package, db.session, category='System', endpoint="admin/packages"))
admin.add_view(view.ACLView(model.IP, db.session, category='System', name='IPs', endpoint="admin/ips"))
admin.add_view(view.ACLView(model.Subnet_rDNS, db.session, category='System', name='Subnet rDNS', endpoint="admin/subnet_rdns"))
admin.add_view(view.PowerOuletAdminView(model.PowerOutlet, db.session, category='System', name='Power Outlets', endpoint="admin/power"))
admin.add_view(view.ACLView(model.Role, db.session, category='System', name='Roles', endpoint="admin/roles"))
admin.add_view(view.ACLView(model.ServerType, db.session, category='System', name='Server Types', endpoint="admin/servertypes"))

from ff_housing.view.whois import WhoisView
WhoisView.register_view(app, "/api/whois")

from ff_housing.view.rdns import rdnsView
rdnsView.register_view(app, "/api/rdns")

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

