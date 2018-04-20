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
    for c in model.Server.query.filter(model.Server.active==True):
        if(len(c.ips) == 0):
            c.active = False;
    model.db.session.commit()

@manager.command
def ip_find_server(ip):
    '''find Server by IP'''
    print(utils.ip_find_server(ip))

@manager.command
def server_by_id(id):
    print(model.Server.byID(id))

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
def generate_invoice(id):
    accounting.generate_invoice(model.Invoice.query.filter_by(id=int(id)).first())
    model.db.session.commit()

@manager.command
def send_invoice(invoice):
    accounting.send_invoice(model.Invoice.query.filter_by(id=int(invoice)).first())
    model.db.session.commit()

@manager.command
def import_legacy(dir='data/'):
    '''import legacy redeemer & cwISPy csv dumps'''
    from .imports import import_packages, import_redeemer_csv, import_cwispy_csv
    import_redeemer_csv(dir)
    import_packages(dir)
    import_cwispy_csv(dir)
    auto_close_servers()

@manager.command
def bill_all():
    '''BILLING: bill all contacts/contracts'''
    accounting.bill_all()
    model.db.session.commit()

@manager.command
def generate_all_invoices():
    for i in model.Invoice.query.filter_by(sent_on=None):
        print("%s, %s for %s" % (i, str(i.amount), i.contact.email) )
        accounting.generate_invoice(i)
    model.db.session.commit()

@manager.command
def send_unsent_invoices():
    '''BILLING: send all unsent invoices'''
    accounting.send_unsent_invoices()
    model.db.session.commit()
