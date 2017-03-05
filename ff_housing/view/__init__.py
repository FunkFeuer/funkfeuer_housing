from flask_admin.contrib import sqla
from flask_admin.base import BaseView, expose
from flask_admin import tools
from flask import url_for, redirect, render_template, request, abort
from flask_security import current_user
import ff_housing.model as model


from .scripts import *
from .imports import *


class UserServerView(sqla.ModelView):
    def get_query(self):
        from app.model import Server
        return super(UserServerView, self).get_query().filter(Server.admin_c_id == current_user.id)



# Create customized model view class
#@expose(url='/admin')
class AdminView(sqla.ModelView):

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

class AdminUserView(AdminView):
    column_display_pk = True
    column_hide_backrefs = False
    column_list = ('id', 'active', 'first_name', 'last_name', 'company_name', 'servers')
    
    @property
    def can_edit(self):
        return current_user.has_role('superuser')
    
    @property
    def can_delete(self):
        return current_user.has_role('superuser')
    
    @property
    def can_create(self):
        return current_user.has_role('superuser')



class ACLView(sqla.ModelView):
    
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        if hasattr(self.model, 'groups_view'):
            return bool(set(self.model.groups_view) & set(current_user.roles))
        return False

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            if current_user.is_authenticated:
                abort(403)
            else:
                return redirect(url_for('security.login', next=request.url))
    
    @property
    def can_edit(self):
        if hasattr(self.model, 'groups_edit'):
            return bool(set(self.model.groups_edit) & set(current_user.roles))
        return False
    
    @property
    def can_delete(self):
        if hasattr(self.model, 'groups_delete'):
            return bool(set(self.model.groups_delete) & set(current_user.roles))
        return False
    
    @property
    def can_create(self):
        if hasattr(self.model, 'groups_create'):
            return bool(set(self.model.groups_create) & set(current_user.roles))
        return False
    
    @property
    def can_view_details(self):
        if hasattr(self.model, 'groups_details'):
            return bool(set(self.model.groups_details) & set(current_user.roles))
        return False
    
    @property
    def column_list(self):
        if hasattr(self.model, 'column_list'):
            return self.model.column_list
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
    def inline_models(self):
        if hasattr(self.model, 'inline_models'):
            return self.model.inline_models
        return None

    page_size = 100


class ACLUserView(ACLView):
    column_list = ('id', 'active', 'first_name', 'last_name', 'company_name', 'servers')
    
class InvoiceView(ACLView):
    inline_models = (model.InvoiceItem,)

class ContractView(ACLView):
    inline_models = (model.ContractPackage,)



from flask import (current_app, request, redirect, flash, abort, json,
                   Response, get_flashed_messages, stream_with_context)
from flask_admin.helpers import (get_form_data, validate_form_on_submit,
                                 get_redirect_target, flash_errors)
from flask_admin.form import BaseForm, FormOpts, rules
from flask_admin.babel import gettext




class UserEditView(sqla.ModelView):
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
    
