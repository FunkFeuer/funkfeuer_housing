from ff_housing import app, mail, manager, model, db

from flask_admin import BaseView, expose
from flask_security import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms.fields import BooleanField
from datetime import datetime

from ff_housing.controller import PaymentsImporter

class FileForm(FlaskForm):
    file = FileField(validators=[FileRequired()])
    checkbox = BooleanField(default=True, label="Dry Run")

class PaymentImportView(BaseView):
    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False
        return bool(set(['billing']) & set(current_user.roles))

    @expose('/', methods=('GET', 'POST'))
    def index(self):
        form = FileForm()

        if form.validate_on_submit():
            dryrun = form.checkbox.data
            job = None

            if not dryrun:
                job = model.Job(
                    type = 'billing',
                    note = 'payment_import',
                    user = current_user,
                    started = datetime.utcnow() )
                db.session.add(job)

            importer = PaymentsImporter(form.file.data, job)
            resp = importer.importResponse(view=self, dryrun=dryrun)

            if job:
                job.finished = datetime.utcnow()
                db.session.commit()
            return resp

        form.title = self.name
        form.submit_val = 'Import'
        lead = "ErsteBank JSON Upload"
        description = """Zahlungen können mit „ignore“ im Notizfeld des Bank-Interfaces
        ignoriert oder mit „k<UserID>“ direkt Personen zugewiesen werden."""

        return self.render('admin/file_import.html',
                           form=form, lead=lead, description=description)
