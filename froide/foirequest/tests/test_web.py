from __future__ import with_statement

from django.test import TestCase
from django.core.urlresolvers import reverse

from publicbody.models import PublicBody, PublicBodyTopic, Jurisdiction
from foirequest.models import FoiRequest


class WebTest(TestCase):
    fixtures = ['auth_profile.json', 'publicbody.json', 'foirequest.json']

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_request(self):
        response = self.client.get(reverse('foirequest-make_request'))
        self.assertEqual(response.status_code, 200)

    def test_request_to(self):
        p = PublicBody.objects.all()[0]
        response = self.client.get(reverse('foirequest-make_request',
            kwargs={'public_body': p.slug}))
        self.assertEqual(response.status_code, 200)

    def test_list_requests(self):
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        for urlpart, status in FoiRequest.STATUS_URLS:
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": urlpart}))
            self.assertEqual(response.status_code, 200)

        for topic in PublicBodyTopic.objects.all():
            response = self.client.get(reverse('foirequest-list',
                kwargs={"topic": topic.slug}))
            self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('foirequest-list_not_foi'))
        self.assertEqual(response.status_code, 200)

    def test_list_jurisdiction_requests(self):
        juris = Jurisdiction.objects.all()[0]
        response = self.client.get(reverse('foirequest-list'),
                kwargs={'jurisdiction': juris.slug})
        self.assertEqual(response.status_code, 200)
        for urlpart, status in FoiRequest.STATUS_URLS:
            response = self.client.get(reverse('foirequest-list',
                kwargs={"status": urlpart, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

        for topic in PublicBodyTopic.objects.all():
            response = self.client.get(reverse('foirequest-list',
                kwargs={"topic": topic.slug, 'jurisdiction': juris.slug}))
            self.assertEqual(response.status_code, 200)

    def test_tagged_requests(self):
        response = self.client.get(reverse('foirequest-list', kwargs={"tag": "awesome"}))
        self.assertEqual(response.status_code, 404)
        req = FoiRequest.published.all()[0]
        req.tags.add('awesome')
        req.save()
        response = self.client.get(reverse('foirequest-list', kwargs={"tag": "awesome"}))
        self.assertEqual(response.status_code, 200)
        self.assertIn(req.title, response.content.decode('utf-8'))

    def test_list_no_identical(self):
        reqs = FoiRequest.published.all()
        req1 = reqs[0]
        req2 = reqs[1]
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(req1.title, response.content.decode('utf-8'))
        self.assertIn(req2.title, response.content.decode('utf-8'))
        req1.same_as = req2
        req1.save()
        req2.same_as_count = 1
        req2.save()
        response = self.client.get(reverse('foirequest-list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(req1.title, response.content.decode('utf-8'))
        self.assertIn(req2.title, response.content.decode('utf-8'))

    def test_show_request(self):
        req = FoiRequest.objects.all()[0]
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug + "-garbage"}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        req.visibility = 1
        req.save()
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 403)
        self.client.login(username="sw", password="froide")
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)

    def test_feed(self):
        response = self.client.get(reverse('foirequest-feed_latest'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-feed_latest_atom'))
        self.assertEqual(response.status_code, 200)
        req = FoiRequest.objects.all()[0]
        response = self.client.get(reverse('foirequest-feed_atom',
            kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('foirequest-feed',
            kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
