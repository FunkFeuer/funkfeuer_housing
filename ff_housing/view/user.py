from flask_admin.contrib import sqla
from flask_admin.base import expose
from flask_security import current_user

from flask import (current_app, request, redirect, flash, abort, json,
                   Response, get_flashed_messages, stream_with_context)
from flask_admin.helpers import (get_form_data, validate_form_on_submit,
                                 get_redirect_target, flash_errors)
from flask_admin.form import SecureForm, FormOpts, Select2Widget
from flask_admin.babel import gettext

from sqlalchemy.sql.expression import func
from flask_admin.model.helpers import get_mdict_item_or_list
import ff_housing.model as model

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
