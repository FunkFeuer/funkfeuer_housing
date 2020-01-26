from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
from sepaxml.utils import get_rand_string
from sepaxml import SepaDD

from flask_security import current_user

from ff_housing import app, model, db

def make_id(number, name):
    name = re.sub(r'[^a-zA-Z0-9]', '', name)
    name = "%s-%s" % (number, name)
    r = get_rand_string(12)
    if len(name) > 22:
        name = name[:22]
    return name + "-" + r


class SepaExport:
    def __init__(self):
        self.invoices = []
        self.config = {
            "name": app.config.get('SEPADD_CREDITOR_NAME'),
            "IBAN": app.config.get('SEPADD_CREDITOR_IBAN'),
            "BIC": app.config.get('SEPADD_CREDITOR_BIC'),
            "batch": app.config.get('SEPADD_BATCH'),
            "creditor_id": app.config.get('SEPADD_CREDITOR_ID'),
            "currency": app.config.get('SEPADD_CURRENCY'),
            "instrument": app.config.get('SEPADD_INSTRUMENT')
        }
        self.sepa = SepaDD(self.config, schema=app.config.get('SEPADD_SCHEMA'))

    def __len__(self):
        return len(self.invoices)

    def add_invoice(self, invoice):
        if(len(invoice.items) == 0):
        # skip invoices without items
            return

        if not invoice.sent:
            raise Exception( "%s has not yet been sent." % invoice.number )
        if invoice.cancelled:
            raise Exception( "%s has been cancelled." % invoice.number )
        if not invoice.contact.has_sepa_mandate:
            raise Exception( "%s: No sepa mandate for %s" % (invoice.number, invoice.contact))
        if invoice.payment_type != 'SEPA-DD':
            raise Exception( "%s Payment Type is not SEPA-DD" % invoice.number )

        if self.sepa.check_payment(self._gen_payment(invoice)):
            self.invoices.append(invoice)

    def _gen_payment(self, invoice):
        if  invoice.contact.sepa_mandate_first:
            payment_type = "FRST"
            collection_date = date.today() + timedelta(days=+5)
        else:
            payment_type = "RCUR"
            collection_date = date.today() + timedelta(days=+3)

        payment = {
            "name": invoice.contact.name,
            "IBAN": invoice.contact.sepa_iban,
            "mandate_id": invoice.contact.sepa_mandate_id,
            "mandate_date": invoice.contact.sepa_mandate_date,
            "amount": int(invoice.amount * 100),
            "type": payment_type,  # FRST,RCUR,OOFF,FNAL
            "collection_date": collection_date,
            "endtoend_id": invoice.exported_id,
            "description": "Funkfeuer %s%d %s" % (app.config.get('BILLING_REFERENCE_UID_PREFIX'),
                                                                            invoice.contact.id, invoice.number)
        }
        return payment

    def add_invoices(self, invoices):
        for invoice in invoices:
            self.add_invoice(invoice)

    @property
    def msg_id(self):
        return self.sepa.msg_id

    def export(self):
        if len(self.invoices) < 1:
            raise Exception("no invoices to export")

        for invoice in self.invoices:
            if invoice.exported_id is None:
                invoice.exported_id = make_id(invoice.number, app.config.get('SEPADD_CREDITOR_NAME'))
                invoice.exported = True

            self.sepa.add_payment(self._gen_payment(invoice))
            if invoice.contact.sepa_mandate_first:
               invoice.contact.sepa_mandate_first = False

        export = self.sepa.export()

        db.session.add(model.Job(
            type = 'sepa_export',
            note = self.msg_id,
            user = current_user,
            started = datetime.utcnow(),
            finished = datetime.utcnow()
        ))
        db.session.commit()

        return export
