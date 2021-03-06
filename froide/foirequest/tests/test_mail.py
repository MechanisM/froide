# -*- coding: utf-8 -*-
from __future__ import with_statement

from django.test import TestCase
from django.core import mail
from django.conf import settings
from django.utils.translation import ugettext as _

from froide.foirequest.tasks import _process_mail
from foirequest.models import FoiRequest


class MailTest(TestCase):
    fixtures = ['auth_profile.json', 'publicbody.json', "foirequest.json"]

    def test_working(self):
        with file("foirequest/tests/test_mail_01.txt") as f:
            _process_mail(f.read())
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)

    def test_working_with_attachment(self):
        with file("foirequest/tests/test_mail_02.txt") as f:
            _process_mail(f.read())
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        messages = request.foimessage_set.all()
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1].subject, u"Fwd: Informationsfreiheitsgesetz des Bundes, Antragsvordruck für Open Data")
        self.assertEqual(len(messages[1].attachments), 1)
        self.assertEqual(messages[1].attachments[0].name, u"TI  - IFG-Antrag, Vordruck.docx")

    def test_wrong_address(self):
        request = FoiRequest.objects.get_by_secret_mail("sw+yurpykc1hr@fragdenstaat.de")
        request.delete()
        mail.outbox = []
        with file("foirequest/tests/test_mail_01.txt") as f:
            _process_mail(f.read())
        self.assertEqual(len(mail.outbox), len(settings.MANAGERS))
        self.assertTrue(all([_('Unknown FoI-Mail Recipient') in m.subject for m in mail.outbox]))
        recipients = [m.to[0] for m in mail.outbox]
        for manager in settings.MANAGERS:
            self.assertIn(manager[1], recipients)
