from flask_admin.contrib import sqla
from flask_admin.base import BaseView, expose
from flask_admin.form import SecureForm
from flask_admin.actions import action
from datetime import datetime

from flask import flash, Response
from flask_security import current_user
from flask_admin.model.template import LinkRowAction
from sqlalchemy.sql.expression import func

from ff_housing.controller import SepaExport

class SepaExportView(sqla.ModelView):

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if current_user.has_role('billing'):
            return True
        return False

#    column_extra_row_actions = [
#        LinkRowAction('glyphicon glyphicon-print', 'generate/?id={row_id}')
#        ]

    can_create = False
    can_edit = False
    can_delete = False
    column_default_sort = ('id', True)
    column_list = ('number', 'job', 'created_at', 'contact', 'amount', 'sent', 'contact.has_sepa_mandate')
    column_filters = ('job.id', 'contact.id', 'amount', 'created_at')
    page_size = 200

    def get_query(self):
        return super(SepaExportView, self).get_query().filter(self.model.sent_on != None,
                                                                                                self.model.exported == False,
                                                                                                self.model.payment_type == 'SEPA-DD')
	
    def get_count_query(self):
        return self.session.query(func.count('*')).filter(self.model.sent_on != None,
                                                                                    self.model.exported == False,
                                                                                    self.model.payment_type == 'SEPA-DD')


    @action('export', 'Export', 'Are you sure you want export selected Invoices?')
    def action_export(self, ids):
        try:
            sepa = SepaExport()
            invoices = self.model.query.filter(self.model.id.in_(ids))
            sepa.add_invoices(invoices.all())

            resp = Response(sepa.export(), mimetype="application/xml")
            resp.headers['Content-Disposition'] = 'attachment;filename*=sepa_export_%s.xml' % sepa.msg_id
            return resp

        except Exception as ex:
            raise
            flash(str(ex), 'error')

 
