from .. import app, manager, model, utils
from ..controller import accounting

from sqlalchemy.sql.expression import func

@manager.command
def bill_contracts():
    app.config['SQLALCHEMY_ECHO'] = False
    accounting.bill_contracts()


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
    app.config['SQLALCHEMY_ECHO'] = False
    print(utils.ip_find_server(ip))

@manager.command
def server_by_id(id):
    app.config['SQLALCHEMY_ECHO'] = False
    print(model.Server.byID(id))

@manager.command
def contract_bill(id):
    app.config['SQLALCHEMY_ECHO'] = False
    accounting.bill_contract(model.Contract.byID(id))


@manager.command
def import_legacy(dir='data/'):
    '''import legacy redeemer & cwISPy csv dumps'''
    from .imports import import_packages, import_redeemer_csv, import_cwispy_csv
    app.config['SQLALCHEMY_ECHO'] = False
    import_redeemer_csv(dir)
    import_packages(dir)
    import_cwispy_csv(dir)
    
