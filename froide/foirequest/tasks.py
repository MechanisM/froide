import sys

from celery.task import task

from django.conf import settings
from django.utils import translation
from django.db import transaction

from foirequest.models import FoiRequest
from foirequest.foi_mail import _process_mail, _fetch_mail

@task
def process_mail(mail):
    translation.activate(settings.LANGUAGE_CODE)
    def run(mail_string):
        try:
            _process_mail(mail_string)
        except Exception:
            transaction.rollback()
            return sys.exc_info()
        else:
            transaction.commit()
            return None
    run = transaction.commit_manually(run)
    exc_info = run(mail)
    if exc_info is not None:
        from sentry.client.models import client
        client.create_from_exception(exc_info=exc_info, view="froide.foirequest.tasks.process_mail")

@task
def fetch_mail():
    for rfc_data in _fetch_mail():
        process_mail.delay(rfc_data)

@task
def detect_overdue():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_overdue():
        foirequest.set_overdue()

@task
def classification_reminder():
    translation.activate(settings.LANGUAGE_CODE)
    for foirequest in FoiRequest.objects.get_unclassified():
        foirequest.send_classification_reminder()

@task
def count_same_foirequests(instance_id):
    translation.activate(settings.LANGUAGE_CODE)
    try:
        req = FoiRequest.objects.get(id=instance_id)
        count = FoiRequest.objects.filter(same_as=req).count()
        req.same_as_count = count
        req.save()
    except FoiRequest.DoesNotExist:
        pass
