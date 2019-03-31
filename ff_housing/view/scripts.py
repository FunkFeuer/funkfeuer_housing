import warnings
warnings.filterwarnings("ignore", module="psycopg2")

from .. import app, manager, model, utils
from ..controller import accounting

from sqlalchemy.sql.expression import func

@manager.command
def build_uml(file='schema.png'):
    '''write model relation graph to schema.png'''
    from sqlalchemy_schemadisplay import create_uml_graph
    from sqlalchemy.orm import class_mapper

    mappers = []
    for attr in dir(model):
        if attr[0] == '_': continue
        try:
            cls = getattr(model, attr)
            mappers.append(class_mapper(cls))
        except:
            pass
    create_uml_graph(mappers,
        show_operations=False,
        show_multiplicity_one=False # some people like to see the ones, some don't
    ).write_png(file)


@manager.command
def auto_close_servers():
    '''set servers without assigned IPs to inactive'''
    for c in model.Server.query.filter(model.Server.active==True):
        if(len(c.ips) == 0):
            c.active = False;
    model.db.session.commit()

@manager.command
def bill_contact(id):
    '''bill all contracts of user'''
    accounting.bill_contact(model.User.byID(id))
    model.db.session.commit()

@manager.command
def bill_contract(id):
    '''bill specific contract'''
    accounting.bill_contract(model.Contract.byID(id))
    model.db.session.commit()

@manager.command
def send_invoice(invoice):
    '''send specific invoice by db-id'''
    accounting.send_invoice(model.Invoice.query.filter_by(id=int(invoice)).first())
    model.db.session.commit()

@manager.command
def billing_bill_all():
    '''BILLING: bill all contacts/contracts'''
    accounting.bill_all()
    model.db.session.commit()

@manager.command
def billing_send_all():
    '''BILLING: send all unsent invoices'''
    accounting.send_unsent_invoices()
    model.db.session.commit()

@manager.command
def all_billing_users():
    '''all users (as CSV) with actively billed contract-packages (billing_active)'''
    print('"id","email","name"')
    for u in model.User.query.order_by(model.User.id.asc()).all():
        if u.billing_active:
            print('%s,"%s","%s"' % (u.id, u.email, u.name,))
