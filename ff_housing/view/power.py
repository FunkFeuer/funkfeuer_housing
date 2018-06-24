from flask_admin.contrib import sqla
from flask_admin.base import BaseView, expose
from flask_admin.form import SecureForm
from flask_admin.actions import action
from datetime import datetime

from flask import flash, Response
from flask_security import current_user
from flask_admin.model.template import LinkRowAction
from sqlalchemy.sql.expression import func

from . import ACLView
from .user import UserView

from ff_housing.controller import power
from ff_housing import model
import json

from flask_admin.model.helpers import get_mdict_item_or_list
from flask import url_for, redirect, render_template, request, abort, send_file
from flask_admin.helpers import (get_form_data, validate_form_on_submit,
                                 get_redirect_target, flash_errors)

from wtforms import validators, PasswordField, HiddenField
from flask_security.utils import verify_password

class PowerForm(SecureForm):
    status = HiddenField('', validators=[validators.DataRequired()])
    password = PasswordField('Password', validators=[validators.DataRequired()])

class PowerOuletView():
    def _can_view(self, outlet):
        if outlet.server and outlet.server.admin_c == current_user:
            return True
        if self.can_edit:
            return True
        return False

    def _can_switch(self, outlet):
        if outlet.server and outlet.server.admin_c == current_user:
            return outlet.switchable
        if self.can_edit and outlet.server is None:
            return outlet.switchable
        return False

    def _process_request(self, id, request):
        outlet = self.get_one(id)

        if request.method == 'POST' and current_user and self._can_switch(outlet):
            form = PowerForm(request.values)
            if form.validate() and verify_password(form.data['password'], current_user.password):
                if form.data['status'] == 'OFF':
                    power.set_power(outlet, False)
                elif form.data['status'] == 'ON':
                    power.set_power(outlet, True)
        return outlet

    @expose('/view/', methods=('GET', 'POST'))
    def status_view(self):
        return_url = get_redirect_target() or self.get_url('.index_view')
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        outlet = self._process_request(id, request)
        if not outlet:
            return None

        if not self._can_view(outlet):
            return redirect(return_url)

        status = power.get_status(outlet)

        if self._can_switch(outlet):
            form = PowerForm(status = status['powered'] and 'OFF' or 'ON')
        else:
            form = None

        return self.render(template = 'power_view.html',
                               outlet = outlet,
                               form = form,
                               status = status)

    @expose('/view/ajax', methods=('GET', 'POST'))
    def status_view_ajax(self):
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect( get_redirect_target() or self.get_url('.index_view'))
        outlet = self._process_request(id, request)
        status = power.get_status(outlet)
        return Response(json.dumps(status), mimetype="application/json")


class PowerOuletAdminView(ACLView, PowerOuletView):
    page_size = 200

    column_extra_row_actions = [
        LinkRowAction('glyphicon glyphicon-eye-open', 'view/?id={row_id}')
        ]

class PowerOuletUserView(UserView, PowerOuletView):
    form_base_class = SecureForm
    can_delete = False
    can_create = False
    can_edit = False
    can_view_details = False

    column_extra_row_actions = [
        LinkRowAction('glyphicon glyphicon-eye-open', 'view/?id={row_id}')
        ]

    column_list = ('server', 'outlet')
    column_sortable_list = ()

    def create_view(self):
        pass
    def delete_view(self):
        pass
    def ajax_update(self):
        pass

    def get_query(self):
        return super(UserView, self).get_query().join(model.Server).filter(
                model.Server.admin_c_id == current_user.id,
                model.Server.active == True,
                self.model.active == True
            )

    def get_count_query(self):
        return self.session.query(func.count('*')).select_from(self.model).join(model.Server).filter(
            model.Server.admin_c_id == current_user.id,
            model.Server.active == True,
            self.model.active == True
        )

    def edit_view(self):
        pass
