from ff_housing import app, mail, manager, model, db

from flask import Response
import json, re
from dateutil.parser import parse
from datetime import datetime

class PaymentsImporter():
    class ErstePaymentImport():
        class InconsistentUser(Exception):
            pass
        def __init__(self, payment_data, dryrun, job):
            self.payment_date = None
            self.payment_partner = None
            self.payment_iban = None
            self.payment_value = None
            self.payment_value_str = None
            self.payment_currency = None
            self.payment_reference = None
            self.payment_referenceNum = None
            self.payment_note = None
            self.payment_type = 'money transfer'

            self.found = {}
            self.found_weak = True
            self.user = None
            self.bounce = False
            self.imported = False
            self.ignored = False
            self.dryrun = dryrun
            self.job = job

            self.error = False
            self.error_msg = ''

            if self.parse(payment_data):
                self.findIBAN()
                self.findIP()
                self.findUserID()
                self.parseNoteOverride()
                self.process()

        def parse(self, data):
            try:
                self.payment_date = parse(data['booking'])
                self.payment_date_str = self.payment_date.strftime("%d.%m.%Y %H:%M")
                self.payment_partner = data['partnerName']
                self.payment_iban = data['partnerAccount']['iban']
                self.payment_currency = data['amount']['currency']
                self.payment_value = (data['amount']['value'] / 10 ** int(data['amount']['precision']))
                self.payment_value_str = "%.2f %s" % (self.payment_value, self.payment_currency)
                self.payment_reference = data['reference']
                self.payment_referenceNum = data['referenceNumber']
                self.payment_note = data['note']

            except KeyError as e:
                self.error = True
                self.error_msg = "ERROR: missing JSON data: %s" % e
                return False
            if self.payment_currency != "EUR":
                self.error = True
                self.error_msg = "ERROR: Currency not EUR (%s)" % self.payment_currency
                return False
            return True

        def process(self):
            if self.error:
                return False
            self.checkImported()

            try:
                for f in [['uid', 'User-ID'],['iban', 'IBAN'],['ip', 'IP']]:
                    if f[0] in self.found:
                        self._compare_found(self.found[f[0]], f[1])
            except self.InconsistentUser as e:
                self.error_msg += str(e)
                self.found = None
                self.error = True
                return False

            if self.user and self.checkUser():
                if self.payment_value < 0:
                    self.bounce = True
                    self.error_msg += "BOUNCED"
                self.do_import()

        def _compare_found(self, comp, src):
            if self.user is None and comp:
                self.user = comp
            elif self.user and comp and self.user is not comp:
                raise self.InconsistentUser("not matching: %s " % src)

        def findIBAN(self):
            user = model.User.query.filter_by(sepa_iban=self.payment_iban).first()
            if user:
                self.found_weak = False
                self.found['iban'] = user

        def findIP(self):
            for ip in re.findall('(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})', self.payment_reference):
                ip = model.IP.query.filter(model.IP.ip_address.like(ip+"/_%")).first()
                if ip and ip.server:
                    if 'ip' not in self.found:
                        self.found['ip'] = ip.server.billing_c
                    else:
                        if self.found['ip'] != ip.server.billing_c:
                            self.error = True
                            self.error_msg += "found multiple IPs with different User!"
                            return False

        def findUserID(self):
            m = re.search(r"Housing-k(\d+)", self.payment_reference)
            if m:
                self.found_weak = False
                self.found['uid'] = model.User.byID(int(m.group(1)))
                print(self.found, m)

        def parseNoteOverride(self):
            if self.payment_note == "ignore":
                self.found = []
                self.error_msg = "ignored by Note"
            elif self.payment_note:
                m = re.match(r"k(\d+)", self.payment_note)
                if m:
                    self.found_weak = False
                    self.user = model.User.byID(int(m.group(1)))
                    self.error_msg += "forced by Note"

        def checkImported(self):
            if model.Payment.query.filter_by(reference=self.payment_referenceNum).first():
                self.ignored = True
                self.user = None

        def checkUser(self):
            # check if user is billing_c of any servers
            if len(self.user.contracts) <= 0 :
                self.error = True
                self.error_msg = "User is not a billing contact of any server."
                return False
            return True

        def do_import(self):
            if self.error or self.ignored:
                return False
            self.imported = True

            if not self.dryrun:
                payment = model.Payment(
                                        contact = self.user,
                                        amount = self.payment_value,
                                        date    = self.payment_date,
                                        reference = self.payment_referenceNum,
                                        job     = self.job,
                                        detail  = self.payment_reference,
                                        payment_type = self.payment_type)
                db.session.add(payment)

        def formatList(self):
            # ['Partner', 'Date', 'Value', 'Reference', 'Note', 'Imported']
            return [
                self.user,
                self.payment_partner,
                self.payment_date_str,
                self.payment_value_str,
                self.payment_reference,
                self.error_msg
                ]

    # /class ErstePaymentImport

    def __init__(self, file, job=None):
        self.file = file
        self.payments = []
        self.job = job


    def readfile(self):
        return json.load(self.file.stream)

    def importResponse(self, view, dryrun=True):
        try:
            data = self.readfile()
            self.processPayments(data, dryrun)
        except json.JSONDecodeError as e:
            return view.render(template='admin/error.html',
                               header='Error Parsing JSON',
                               msg=str(e))
        tables = []
        return view.render(template='admin/payment_import_list.html',
                        tables=self.gen_view_tables())

    def processPayments(self, payments, dryrun):
        for p in payments:
            self.payments.append(self.ErstePaymentImport(p, dryrun=dryrun, job=self.job))
        if not dryrun:
            db.session.commit()


    def gen_view_tables(self):
        p_imported = []
        p_error = []
        p_ignored = []
        p_unknown = []

        for p in self.payments:
            if p.imported:
                if p.bounce:
                    p_imported.append({
                    'columns': [
                            p.user,
                            p.payment_partner,
                            p.payment_date_str,
                            p.payment_value_str,
                            p.payment_reference,
                            p.error_msg
                            ],
                    'class': 'danger'
                        })
                elif p.found_weak:
                    p_imported.append({
                    'columns': [
                            p.user,
                            p.payment_partner,
                            p.payment_date_str,
                            p.payment_value_str,
                            p.payment_reference,
                            p.error_msg
                            ],
                    'class': 'warning small'
                        })
                else:
                    p_imported.append({
                    'columns': [
                            p.user,
                            p.payment_partner,
                            p.payment_date_str,
                            p.payment_value_str,
                            p.payment_reference,
                            p.error_msg
                            ],
                    'class': 'success small'
                        })
            elif p.error:
                p_error.append({
                'columns': [
                            p.user,
                            p.payment_partner,
                            p.payment_date_str,
                            p.payment_value_str,
                            p.payment_reference,
                            p.error_msg
                            ],
                'class': 'danger small'
                    })
            elif p.ignored:
                p_ignored.append({
                    'columns': [
                            p.user,
                            p.payment_partner,
                            p.payment_date_str,
                            p.payment_value_str,
                            p.payment_reference
                            ],
                    'class': 'info small'
                        })
            else:
                p_unknown.append({
                    'columns': [
                            p.payment_partner,
                            p.payment_date_str,
                            p.payment_value_str,
                            p.payment_reference,
                            p.payment_iban,
                            p.error_msg
                            ],
                    'class': 'warning small'
                        })

        return (
                {
                'header': 'Payments with errors:',
                'table_header': ['User', 'Partner', 'Date', 'Value', 'Reference', 'Error'],
                'rows': p_error
                }, {
                'header': 'Unknown Payments:',
                'lead' : 'You can re-import your data at any time, already imported payments will be ignored..',
                'table_header': ['Partner', 'Date', 'Value', 'Reference', 'IBAN', 'Error'],
                'rows': p_unknown
                }, {
                'header': 'Imported Payments:',
                'lead' : 'Payments only matched by IP are marked orange, please check.',
                'table_header': ['Imported User', 'Partner', 'Date', 'Value', 'Reference', 'Note'],
                'rows': p_imported
                }, {
                'header': 'Ignored Payments:',
                'lead': 'The following payments have already been imported.',
                'table_header': ['User', 'Partner', 'Date', 'Value', 'Reference'],
                'rows': p_ignored
                }
            )

