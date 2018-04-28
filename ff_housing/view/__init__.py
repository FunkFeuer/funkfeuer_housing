from flask_admin.contrib import sqla
from flask_admin.base import BaseView, expose
from flask_admin import tools
from flask_admin.form import SecureForm
from flask import url_for, redirect, render_template, request, abort, send_file
from flask_security import current_user
from flask_admin.model.template import LinkRowAction
from flask_admin.model.helpers import get_mdict_item_or_list
from os.path import isfile

import ff_housing.model as model

from .scripts import *
from .imports import *


# Create customized model view class
class AdminView(sqla.ModelView):
    form_base_class = SecureForm

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('user'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))




class ACLView(sqla.ModelView):
    form_base_class = SecureForm

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if hasattr(self.model, 'groups_view'):
            return bool(set(self.model.groups_view) & set(current_user.roles))
        return False

    def _handle_view(self, name, **kwargs):
        self._refresh_cache()
        if not self.is_accessible():
            if current_user.is_authenticated:
                abort(403)
            else:
                return redirect(url_for('security.login', next=request.url))
        return super(sqla.ModelView, self)._handle_view(name, **kwargs)

    @property
    def can_edit(self):
        if hasattr(self.model, 'groups_edit') and current_user:
            return bool(set(self.model.groups_edit) & set(current_user.roles))
        return False

    @property
    def can_delete(self):
        if hasattr(self.model, 'groups_delete') and current_user:
            return bool(set(self.model.groups_delete) & set(current_user.roles))
        return False

    @property
    def can_create(self):
        if hasattr(self.model, 'groups_create') and current_user:
            return bool(set(self.model.groups_create) & set(current_user.roles))
        return False

    @property
    def can_view_details(self):
        if hasattr(self.model, 'groups_details') and current_user:
            return bool(set(self.model.groups_details) & set(current_user.roles))
        return False

    @property
    def column_list(self):
        if hasattr(self.model, 'column_list'):
            return self.model.column_list
        return None

    @property
    def column_details_list(self):
        if hasattr(self.model, 'column_details_list'):
            return self.model.column_details_list
        return None

    @property
    def form_columns(self):
        if hasattr(self.model, 'form_columns'):
            return self.model.form_columns
        return None

    @property
    def form_excluded_columns(self):
        if hasattr(self.model, 'form_excluded_columns'):
            return self.model.form_excluded_columns
        return None

    @property
    def form_rules(self):
        if hasattr(self.model, 'form_rules'):
            return self.model.form_rules
        return None

    @property
    def column_filters(self):
        if hasattr(self.model, 'column_filters'):
            return self.model.column_filters
        return None

    @property
    def column_searchable_list(self):
        if hasattr(self.model, 'column_searchable_list'):
            return self.model.column_searchable_list
        return None

    @property
    def column_default_sort(self):
        if hasattr(self.model, 'column_default_sort'):
            return self.model.column_default_sort
        return None

    @property
    def form_overrides(self):
        if hasattr(self.model, 'form_overrides'):
            return self.model.form_overrides
        return None

    @property
    def inline_models(self):
        if hasattr(self.model, 'inline_models'):
            return self.model.inline_models
        return None

    page_size = 100


class AdminInvoiceView(ACLView):
    inline_models = (model.InvoiceItem,)

    column_extra_row_actions = [
        LinkRowAction('glyphicon glyphicon-print', 'generate/?id={row_id}')
        ]

    @expose('/generate/', methods=('POST','GET'))
    def generate_view(self):
        """
            Invoice download view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not  self.can_view_details:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
    
        if id:
            invoice = self.get_one(id)

            if invoice is None:
                flash(gettext('Invoice does not exist.'), 'error')
                return redirect(return_url)

            if len(invoice.items) == 0:
                flash(gettext('Invoice has no Items, will not create empty invoice.'), 'error')
                return redirect(return_url)

            if not invoice.sent and not invoice.exported:
                # (re-)generate invoice if it was not sent and not exported
                from ff_housing.controller.accounting import generate_invoice
                generate_invoice(invoice)

            if invoice.path and isfile(invoice.path):
                res = send_file(invoice.path)
                res.headers['Content-Disposition'] = 'inline;filename*=%s.pdf' % invoice.number
                return res
            else:
                flash(gettext('File does not exist.'), 'error')

        return redirect(return_url)

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        """
            restrict edit on invoices, that have not been sent.
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_edit:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        invoice = self.get_one(id)

        if invoice is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)

        if invoice.sent:
            flash(gettext('Invoice has already been sent and cannot be edited.'), 'error')
            return redirect(return_url)

        return super(AdminInvoiceView, self).edit_view()


class AdminContractView(ACLView):
    inline_models = (model.ContractPackage,)

class AdminUserView(ACLView):
    def _refresh_cache(self):
        if not current_user:
            self._list_columns = ()
            return
        super(ACLView, self)._refresh_cache()

    @property
    def form_columns(self):
        if hasattr(self.model, 'form_columns'):
            cols = list(self.model.form_columns)
            if current_user and 'billing' in current_user.roles:
                cols.append('sepa_iban')
                cols.append('sepa_mandate')
            if current_user and 'system' in current_user.roles:
                cols.append('roles')
            return cols
        return None




class ServerIPQueryAjaxModelLoader(sqla.ajax.QueryAjaxModelLoader):
    def get_list(self, query, offset=0, limit=20):
        filters = list(
            field.ilike(u'%%%s%%' % query) for field in self._cached_fields
        )
        filters.append(model.IP.server == None)
        return (
            db.session.query(model.IP)
            .filter(*filters)
            .all()
        )

class AdminServerView(AdminContractView):
    form_ajax_refs = {
        'ips': ServerIPQueryAjaxModelLoader('ips', db.session, model.IP, fields=['ip_address'], page_size=10)
    }


from flask import (current_app, request, redirect, flash, abort, json,
                   Response, get_flashed_messages, stream_with_context)
from flask_admin.helpers import (get_form_data, validate_form_on_submit,
                                 get_redirect_target, flash_errors)
from flask_admin.form import BaseForm, FormOpts, rules, Select2Widget
from flask_admin.babel import gettext


class UserView(sqla.ModelView):
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        return True

class UserEditView(UserView):
    form_base_class = SecureForm
    edit_template = "profile.html"
    can_delete = False
    can_create = False
    can_view_details = False

    def edit_view(self):
        pass
    def create_view(self):
        pass
    def details_view(self):
        pass
    def delete_view(self):
        pass
    def ajax_update(self):
        pass

    def is_accessible(self):
        if current_user.is_active and current_user.is_authenticated:
            return True
        return False

    form_columns = ('first_name', 'last_name', 'company_name', 'street', 'zip', 'town', 'country', 'phone')

    @expose('/', methods=('GET', 'POST'))
    def index_view(self):
        """
            Edit model view
        """
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_edit:
            return redirect(return_url)

        id = current_user.id

        if id is None:
            return redirect(return_url)

        model = self.get_one([str(id)])

        if model is None:
            flash(gettext('Record does not exist.'), 'error')
            return redirect(return_url)

        form = self.edit_form(obj=model)
        if not hasattr(form, '_validated_ruleset') or not form._validated_ruleset:
            self._validate_form_instance(ruleset=self._form_edit_rules, form=form)

        if self.validate_form(form):
            if self.update_model(form, model):
                flash(gettext('Record was successfully saved.'), 'success')
                if '_continue_editing' in request.form:
                    return redirect(request.url)
                else:
                    # save button
                    return redirect(self.get_save_return_url(model, is_created=False))

        if request.method == 'GET' or form.errors:
            self.on_form_prefill(form, id)

        form_opts = FormOpts(widget_args=self.form_widget_args,
                             form_rules=self._form_edit_rules)

        if self.edit_modal and request.args.get('modal'):
            template = self.edit_modal_template
        else:
            template = self.edit_template

        return self.render(template,
                           model=model,
                           form=form,
                           form_opts=form_opts,
                           return_url=return_url)

class UserServerView(UserView):
    form_base_class = SecureForm
    can_delete = False
    can_create = False
    can_view_details = True

    column_list = ('id', 'servertype', 'location', 'name', 'description', 'ips')
    column_details_list =  ('id', 'admin_c', 'billing_c', 'name', 'location', 'description', 'servertype', 'location', 'payment_type', 'ips', 'outlets')
    form_columns = ('name', 'location', 'description')
    column_sortable_list = ()

    def create_view(self):
        pass
    def delete_view(self):
        pass
    def ajax_update(self):
        pass

    def get_query(self):
        return super(UserServerView, self).get_query().filter(self.model.admin_c_id == current_user.id,
                                                                                                self.model.active == True)

    def get_count_query(self):
        return self.session.query(func.count('*')).filter(self.model.admin_c_id == current_user.id,
                                                                                    self.model.active == True)

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_edit:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        server = self.get_one(id)

        if server is None or server.admin_c_id is not current_user.id:
            flash(gettext('Server does not exist.'), 'error')
            return redirect(return_url)

        return super(UserServerView, self).edit_view()



class UserIPView(UserView):
    form_base_class = SecureForm
    can_delete = False
    can_create = False
    can_view_details = True

    column_list = ('server', 'server.name', 'ip', 'netmask', 'gateway', 'rdns', 'routed_subnet', 'type')
    column_default_sort = 'server.id'
    column_sortable_list = ()

    form_columns = ('server', 'rdns')
    form_extra_fields = {
        'server': sqla.fields.QuerySelectField(
            label='Server',
            query_factory=lambda: model.Server.query.filter(model.Server.admin_c_id == current_user.id,
                                                                                   model.Server.active == True),
            widget=Select2Widget()
        )
    }

    def create_view(self):
        pass
    def delete_view(self):
        pass
    def ajax_update(self):
        pass

    def get_query(self):
        return super(UserIPView, self).get_query().join(model.Server).filter(
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

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        return_url = get_redirect_target() or self.get_url('.index_view')

        if not self.can_edit:
            return redirect(return_url)

        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return redirect(return_url)

        ip = self.get_one(id)
        user = model.User.byID(current_user.id)

        if ip is None or user is None or ip.server.admin_c is not user:
            flash(gettext('IP does not exist.'), 'error')
            return redirect(return_url)

        return super(UserIPView, self).edit_view()


class UserSubnetRDNSView(UserView):
    form_base_class = SecureForm
    can_view_details = False
    column_editable_list = False

    column_list = ('ip_subnet', 'ip_address', 'rdns')
    column_default_sort = 'ip_address'
    column_sortable_list = ()

    form_columns = ('subnet', 'ip_address', 'rdns')
    form_extra_fields = {
        'subnet': sqla.fields.QuerySelectField(
            label='Subnet',
            query_factory=lambda: model.IP.query.join(model.Server).filter(
                    model.Server.admin_c_id == current_user.id,
                    model.Server.active == True,
                    model.IP.routed_subnet != None ),
            widget=Select2Widget()
        )
    }

    def get_query(self):
        return super(UserSubnetRDNSView, self).get_query().join(model.IP).join(model.Server).filter(
            model.Server.admin_c_id == current_user.id,
            model.Server.active == True,
            model.IP.active == True,
            model.IP.routed_subnet != None
        )

    def get_count_query(self):
        return self.session.query(func.count('*')).select_from(self.model).join(model.IP).join(model.Server).filter(
            model.Server.admin_c_id == current_user.id,
            model.Server.active == True,
            model.IP.active == True,
            model.IP.routed_subnet != None
        )

    @property
    def user_has_access(self):
        id = get_mdict_item_or_list(request.args, 'id')
        if id is None:
            return False
        entry = self.get_one(id)
        user = model.User.byID(current_user.id)
        if entry is None or user is None or entry.subnet.server.admin_c is not user:
            return False
        return True

    @expose('/new/', methods=('GET', 'POST'))
    def create_view(self):
        if not self.user_has_access:
            flash(gettext('Entry does not exist.'), 'error')
            return_url = get_redirect_target() or self.get_url('.index_view')
            return redirect(return_url)
        return super(UserSubnetRDNSView, self).create_view()

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        if not self.user_has_access:
            flash(gettext('Entry does not exist.'), 'error')
            return_url = get_redirect_target() or self.get_url('.index_view')
            return redirect(return_url)
        return super(UserSubnetRDNSView, self).delete_view()

    def ajax_update(self):
        pass

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        if not self.user_has_access:
            flash(gettext('Entry does not exist.'), 'error')
            return_url = get_redirect_target() or self.get_url('.index_view')
            return redirect(return_url)
        return super(UserSubnetRDNSView, self).edit_view()
