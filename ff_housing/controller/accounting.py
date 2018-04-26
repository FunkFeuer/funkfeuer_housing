from ff_housing import app, mail, manager, model, db
from flask_mail import Message
from datetime import datetime, date
from dateutil.relativedelta import *
from dateutil.rrule import *

from ff_housing.utils import daysofmonth
from sqlalchemy.sql.expression import func

def bill_all():
    job = model.Job(
        type = 'billing',
        note = 'bill_all',
        started = datetime.utcnow() )

    db.session.add(job)
    for contact in db.session.query(model.User):
        bill_contact(contact, job)

    job.finished = datetime.utcnow()
    db.session.commit()

def bill_contact(contact, job=None):
    invoice = None
    for c in model.Contract.query.filter_by(closed=False, billing_c=contact):
        if c.needs_billing():
            invoice = invoice if (invoice != None) else \
                model.Invoice(contact = c.billing_c, payment_type=c.payment_type, job=job)
            bill_contract(c, invoice)

    if (invoice != None):
        db.session.commit()


def bill_contract(c, invoice = None):
    if(c.needs_billing() == False):
        return False
    invoice = invoice if (invoice != None) else \
    model.Invoice(contact = c.billing_c, payment_type=c.payment_type)
    print("\n%s: %s" % (c.billing_c, c.payment_type))

    db.session.add(invoice)

    for package in c.packages:
        if package.needs_billing():
            bill_package(package, invoice)
    db.session.commit()

def bill_package(package, invoice):
    if(package.needs_billing() == False):
        return False
    amount = 0
    # next_billed - the span of this invoice element.
    next_billed = package.billed_until+relativedelta(months=+package.billing_period)
    if (next_billed <= date.today()+relativedelta(days=-30)):
        print ("!! something fishy here: package %s next_billed (%s) is in the past!" % (package, next_billed))
        return False

    # TODO: only bill until closed_date if closed_date

    # we iterate over a list of montly dates between billed_until and next_billed
    last_date = package.billed_until
    for next_date in list(rrule(MONTHLY, dtstart=package.billed_until, until=next_billed, bymonthday=package.billed_until.day)):
        next_date = next_date.date()
        if last_date == next_date:
            continue;

        if (last_date.day == next_date.day):
            # full month
            amount += package.amount
        elif (int(next_date.month) != int(last_date.month)):
            # days between two months
            fraction_of_month = (daysofmonth(last_date) - last_date.day) / daysofmonth(last_date) + \
                (next_date.day / daysofmonth(next_date))
            amount += package.amount * fraction_of_month
        else:
            # days in same month
            fraction_of_month = (next_date.day - last_date.day) / daysofmonth(next_date)
            amount += package.amount * fraction_of_month
        last_date = next_date

    print("\t%d * %s: %s - %s \t%f" % (package.quantity, package, package.billed_until, next_billed+relativedelta(days=-1), amount*package.quantity))

    db.session.add(model.InvoiceItem(
        invoice = invoice,
        title = str(package),
        detail = "%s - %s" % (package.billed_until, next_billed+relativedelta(days=-1)),
        unit_price = amount,
        quantity = package.quantity
    ))

    package.last_billed = date.today()
    package.billed_until = next_billed


def generate_invoice(invoice):
    from jinja2.loaders import FileSystemLoader
    from latex.jinja2 import make_env
    from latex import build_pdf
    import os

    if(len(invoice.items) == 0):
        # skip invoices without items
        return

    # TODO: MWST

    env = make_env(loader=FileSystemLoader('ff_housing/templates/latex/'))
    tpl = env.get_template('invoice.tex')
    
    pdf = build_pdf(tpl.render(invoice=invoice, templatedir=os.getcwd()+'/ff_housing/templates/latex/'))
    path = '%sinvoices/%s.pdf' % (app.config.get('FF_HOUSING_FILES_DIR', './files/'), invoice.number)
    pdf.save_to(path)
    invoice.path = path
    return(path)

def send_invoice(invoice):
    from jinja2.loaders import FileSystemLoader
    from jinja2 import Environment

    if(len(invoice.items) == 0):
        # skip invoices without items
        return

    msg = Message("Funkfeuer Housing Rechnung %s" % invoice.number,
                  recipients=[invoice.contact.email],
                  bcc=[app.config.get('FF_HOUSING_INVOICES_BCC')]
                  )

    print("sending %s to %s" % (invoice, invoice.contact.email) )

    env = Environment(loader=FileSystemLoader('ff_housing/templates/mail/'))
    tpl = env.get_template('invoice.txt')
    msg.body = tpl.render(invoice=invoice)

    generate_invoice(invoice)
    with app.open_resource(".%s" % invoice.path) as fp:
        msg.attach("%s.pdf" % invoice.number, "application/pdf", fp.read())

    mail.send(msg)
    invoice.sent_on = datetime.utcnow()
    model.db.session.commit()

def send_unsent_invoices():
    for i in model.Invoice.query.filter_by(sent_on=None):
        send_invoice(i)
