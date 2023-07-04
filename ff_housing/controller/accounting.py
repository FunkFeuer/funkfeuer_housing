import ff_housing
from ff_housing import app, mail, manager, model, db
from flask_mail import Message
from datetime import datetime, date
from dateutil.relativedelta import *
from dateutil.rrule import *
from os.path import dirname
from decimal import Decimal

from ff_housing.utils import daysofmonth
from sqlalchemy.sql.expression import func

from flask import flash

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
    if package.billed_until is not None:
        billed_until = package.billed_until
        billingmonthday = billed_until.day
        next_billed = billed_until + relativedelta(months=+package.billing_period)
    else:
        billed_until = package.opened_at.date()
        billingmonthday = app.config.get('FF_HOUSING_BILLING_DAY_DEFAULT', 25)
        next_billed = billed_until.replace(day=billingmonthday) + relativedelta(months=+package.billing_period)

    if package.closed_at and next_billed > package.closed_at.date():
        next_billed = package.closed_at.date()

    if (next_billed <= date.today()+relativedelta(days=-30)):
        print ("!! something fishy here: package %s next_billed (%s) is in the past!" % (package, next_billed))
        return False

    # we iterate over a list of montly dates between billed_until and next_billed, including both
    last_date = billed_until
    billing_dates = list(rrule(MONTHLY, dtstart=billed_until, until=next_billed, bymonthday=billingmonthday))
    billing_dates.append(next_billed)
    for next_date in billing_dates:
        if type(next_date) is datetime:
            next_date = next_date.date()

        if last_date == next_date:
            continue;

        if (last_date.day == next_date.day):
            # full month
            amount += package.amount
        elif (int(next_date.month) != int(last_date.month)):
            # days between two months
            fraction_of_month = Decimal(
                ( daysofmonth(last_date) - (last_date.day-1) ) / daysofmonth(last_date) \
                + ( (next_date.day-1) / daysofmonth(next_date) )
            )
            amount += package.amount * fraction_of_month
        else:
            # days in same month
            fraction_of_month = Decimal((next_date.day - last_date.day) / daysofmonth(next_date))
            amount += package.amount * fraction_of_month
        last_date = next_date
        amount = amount.quantize(Decimal('.01'))

    print("\t%d * %s: %s - %s \t%f" % (package.quantity, package, billed_until, next_billed+relativedelta(days=-1), amount*package.quantity))

    db.session.add(model.InvoiceItem(
        invoice = invoice,
        title = str(package),
        detail = "%s - %s" % (billed_until, next_billed+relativedelta(days=-1)),
        unit_price = amount,
        quantity = package.quantity
    ))

    package.last_billed = date.today()
    package.billed_until = next_billed


def generate_invoice(invoice):
    from jinja2.loaders import FileSystemLoader
    from latex.jinja2 import make_env
    from latex import build_pdf

    if(len(invoice.items) == 0):
        # skip invoices without items
        return

    latex_templates = '%s/templates/latex/' % dirname(ff_housing.__file__)
    env = make_env(loader=FileSystemLoader(latex_templates))
    tpl = env.get_template('invoice.tex')

    pdf = build_pdf(tpl.render(invoice=invoice, templatedir=latex_templates ))
    pdf.save_to(invoice.path)
    return(invoice.path)

def send_invoice(invoice):
    from jinja2.loaders import FileSystemLoader
    from jinja2 import Environment

    if invoice.cancelled or len(invoice.items) == 0:
        # skip invoices without items
        return

    msg = Message("FunkFeuer Housing Rechnung %s" % invoice.number,
                  recipients=[invoice.contact.email],
                  bcc=[app.config.get('FF_HOUSING_INVOICES_BCC')]
                  )

    print("sending %s to %s" % (invoice, invoice.contact.email) )

    mail_templates = '%s/templates/mail/' % dirname(ff_housing.__file__)
    env = Environment(loader=FileSystemLoader(mail_templates))
    tpl = env.get_template('invoice.txt')
    msg.body = tpl.render(invoice=invoice)

    generate_invoice(invoice)
    with open(invoice.path, mode='rb') as fp:
        msg.attach("%s.pdf" % invoice.number, "application/pdf", fp.read())

    mail.send(msg)
    invoice.sent_on = datetime.utcnow()
    model.db.session.commit()

def send_unsent_invoices():
    job = model.Job(
        type = 'billing',
        note = 'send_unsent_invoices',
        started = datetime.utcnow() )
    db.session.add(job)

    for i in model.Invoice.query.filter_by(sent_on=None):
        send_invoice(i)

    job.finished = datetime.utcnow()
    db.session.commit()


def cancel_invoice(invoice):
    if invoice.cancelled:
        return False

    if invoice.sent:
        # generate cancelation invoice
        cancelation = model.Invoice(contact = invoice.contact)
        db.session.add(cancelation)
        db.session.add(model.InvoiceItem(
            invoice = cancelation,
            title = 'Storno Rechnung %s' % invoice.number,
            detail = '',
            unit_price = -invoice.amount,
            quantity = 1
        ))
        invoice.cancelled = True
        flash('Created cancelation invoice.', 'warning')
    else:
        # balance invoice to 0
        db.session.add(model.InvoiceItem(
            invoice = invoice,
            title = 'Invoice cancelled',
            detail = '',
            unit_price = -invoice.amount,
            quantity = 1
        ))
        invoice.cancelled = True
        flash('Marked invoice as cancelled.', 'info')
    model.db.session.commit()
    return True
