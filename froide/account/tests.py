import re
import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.core import mail

from publicbody.models import PublicBody
from foirequest.models import FoiRequest
from account.models import AccountManager


class AccountTest(TestCase):
    fixtures = ['auth_profile.json', 'publicbody.json', 'foirequest.json']

    def test_account_page(self):
        ok = self.client.login(username='sw', password='wrong')
        self.assertFalse(ok)
        ok = self.client.login(username='sw', password='froide')
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        self.client.logout()
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 302)
        self.client.get(reverse('account-login'))
        response = self.client.post(reverse('account-login'),
                {"email": "doesnt@exist.com",
                "password": "foobar"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('account-login'),
                {"email": "mail@stefanwehrmeyer.com",
                "password": "dummy"})
        self.assertEqual(response.status_code, 400)
        response = self.client.post(reverse('account-login'),
                {"email": "mail@stefanwehrmeyer.com",
                "password": "froide"})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('account-login'),
                {"email": "mail@stefanwehrmeyer.com",
                "password": "froide"})
        # already logged in, login again gives 302
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account-show'), response['location'])
        response = self.client.get(reverse('account-logout'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('account-login') + "?simple")
        self.assertIn("simple_base.html", map(lambda x: x.name,
                response.templates))
        response = self.client.post(reverse('account-login') + "?simple",
                {"email": "mail@stefanwehrmeyer.com",
                "password": "froide"})
        self.assertTrue(response.status_code, 302)
        self.assertIn("simple", response['location'])
        user = User.objects.get(email="mail@stefanwehrmeyer.com")
        user.is_active = False
        user.save()
        self.client.logout()
        response = self.client.post(reverse('account-login'),
                {"email": "mail@stefanwehrmeyer.com",
                "password": "froide"})
        # inactive users can't login
        self.assertEqual(response.status_code, 400)
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 302)

    def test_signup(self):
        mail.outbox = []
        post = {"first_name": "Horst",
                "last_name": "Porst",
                "terms": "on",
                "user_email": "horst.porst"}
        self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('account-signup'), post)
        self.assertTrue(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        self.client.logout()
        response = self.client.post(reverse('account-signup'), post)
        self.assertEqual(response.status_code, 400)
        post['user_email'] = 'horst.porst@example.com'
        response = self.client.post(reverse('account-signup'), post)
        self.assertTrue(response.status_code, 400)
        post['address'] = 'MyOwnPrivateStree 5\n31415 Pi-Ville'
        response = self.client.post(reverse('account-signup'), post)
        self.assertTrue(response.status_code, 302)
        user = User.objects.get(email=post['user_email'])
        self.assertEqual(user.first_name, post['first_name'])
        self.assertEqual(user.last_name, post['last_name'])
        profile = user.get_profile()
        self.assertEqual(profile.address, post['address'])
        self.assertEqual(mail.outbox[0].to[0], post['user_email'])

        # sign up with email that is not confirmed
        response = self.client.post(reverse('account-signup'), post)
        self.assertTrue(response.status_code, 400)

        # sign up with email that is confirmed
        message = mail.outbox[0]
        match = re.search('/%d/(\w+)/' % user.pk, message.body)
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': match.group(1)}))
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        response = self.client.post(reverse('account-signup'), post)
        self.assertTrue(response.status_code, 400)

    def test_confirmation_process(self):
        self.client.logout()
        user, password = AccountManager.create_user(first_name=u"Stefan",
                last_name=u"Wehrmeyer", user_email="sw@example.com",
                address=u"SomeRandomAddress\n11234 Bern", private=True)
        AccountManager(user).send_confirmation_mail(password=password)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        match = re.search('/%d/(\w+)/' % user.pk, message.body)
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': match.group(1)}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account-show'), response['Location'])
        response = self.client.get(response['Location'])
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': 'a' * 32}))
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': match.group(1)}))
        # user is already active, link does not exist
        self.assertEqual(response.status_code, 404)
        # deactivate user
        user = User.objects.get(pk=user.pk)
        user.is_active = False
        # set last_login back artificially so it's not the same
        # as in secret link
        user.last_login = user.last_login - datetime.timedelta(seconds=1)
        user.save()
        response = self.client.get(reverse('account-confirm',
                kwargs={'user_id': user.pk,
                'secret': match.group(1)}))
        # user is inactive, but link was already used
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('account-login'), response['Location'])

    def test_change_password(self):
        response = self.client.get(reverse('account-change_password'))
        self.assertEqual(response.status_code, 405)
        data = {"new_password1": "froide1",
                "new_password2": "froide2"}
        response = self.client.post(reverse('account-change_password'), data)
        self.assertEqual(response.status_code, 403)
        ok = self.client.login(username='sw', password='froide')
        response = self.client.post(reverse('account-change_password'), data)
        self.assertEqual(response.status_code, 400)
        data["new_password2"] = "froide1"
        response = self.client.post(reverse('account-change_password'), data)
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        ok = self.client.login(username='sw', password='froide')
        self.assertFalse(ok)
        ok = self.client.login(username='sw', password='froide1')
        self.assertTrue(ok)

    def test_send_reset_password_link(self):
        mail.outbox = []
        response = self.client.get(reverse('account-send_reset_password_link'))
        self.assertEqual(response.status_code, 405)
        ok = self.client.login(username='sw', password='froide')
        data = {"email": "unknown@example.com"}
        response = self.client.post(reverse('account-send_reset_password_link'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        self.client.logout()
        response = self.client.post(reverse('account-send_reset_password_link'), data)
        self.assertEqual(response.status_code, 400)
        data['email'] = 'mail@stefanwehrmeyer.com'
        response = self.client.post(reverse('account-send_reset_password_link'), data)
        self.assertEqual(response.status_code, 302)
        message = mail.outbox[0]
        match = re.search('/account/reset/([^/]+)/', message.body)
        uidb36, token = match.group(1).split("-", 1)
        response = self.client.get(reverse('account-password_reset_confirm',
            kwargs={"uidb36": uidb36, "token": "2y1-d0b8c8b186fdc63ccc6"}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])
        response = self.client.get(reverse('account-password_reset_confirm',
            kwargs={"uidb36": uidb36, "token": token}))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['validlink'])
        data = {"new_password1": "froide4",
                "new_password2": "froide4"}
        response = self.client.post(reverse('account-password_reset_confirm',
            kwargs={"uidb36": uidb36, "token": token}), data)
        self.assertEqual(response.status_code, 302)
        # we are already logged in after redirect
        # due to extra magic in wrapping view
        response = self.client.get(reverse('account-show'))
        self.assertEqual(response.status_code, 200)
        self.client.logout()
        ok = self.client.login(username='sw', password='froide4')
        self.assertTrue(ok)

    def test_private_name(self):
        user = User.objects.get(username="dummy")
        profile = user.get_profile()
        profile.private = True
        profile.save()
        self.client.login(username='dummy', password='froide')
        pb = PublicBody.objects.all()[0]
        post = {"subject": "Request - Private name",
                "body": "This is a test body",
                "public": "on",
                "law": pb.default_law.pk}
        response = self.client.post(reverse('foirequest-submit_request',
                kwargs={"public_body": pb.slug}), post)
        self.assertEqual(response.status_code, 302)
        req = FoiRequest.objects.filter(user=user, public_body=pb).order_by("-id")[0]
        self.client.logout()  # log out to remove Account link
        response = self.client.get(reverse('foirequest-show',
                kwargs={"slug": req.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(user.get_full_name().encode("utf-8"),
                response.content)
        self.assertNotIn(user.last_name.encode("utf-8"),
                response.content)

    def test_change_address(self):
        data = {}
        response = self.client.post(reverse('account-change_address'), data)
        self.assertEqual(response.status_code, 403)
        ok = self.client.login(username='sw', password='froide')
        self.assertTrue(ok)
        response = self.client.post(reverse('account-change_address'), data)
        self.assertEqual(response.status_code, 400)
        data["address"] = ""
        response = self.client.post(reverse('account-change_address'), data)
        self.assertEqual(response.status_code, 400)
        data["address"] = "Some Value"
        response = self.client.post(reverse('account-change_address'), data)
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='sw')
        profile = user.get_profile()
        self.assertEqual(profile.address, data['address'])

    def test_go(self):
        user = User.objects.get(username='dummy')
        other_user = User.objects.get(username='sw')
        # test url is not cached and does not cause 404
        test_url = reverse('foirequest-make_request')
        profile = user.get_profile()

        # Try logging in via link: success
        autologin = profile.get_autologin_url(test_url)
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], user)
        self.assertTrue(response.context['user'].is_authenticated())
        self.client.logout()

        # Try logging in via link: other user is authenticated
        ok = self.client.login(username='sw', password='froide')
        self.assertTrue(ok)
        autologin = profile.get_autologin_url(test_url)
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], other_user)
        self.assertTrue(response.context['user'].is_authenticated())
        self.client.logout()

        # Try logging in via link: user not active
        autologin = profile.get_autologin_url(test_url)
        user.is_active = False
        user.save()
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 404)
        response = self.client.get(test_url)
        self.assertTrue(response.context['user'].is_anonymous())

        # Try logging in via link: wrong user id
        autologin = reverse('account-go', kwargs=dict(
            user_id='80000', secret='a' * 32, url=test_url
        ))
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 404)
        response = self.client.get(test_url)
        self.assertTrue(response.context['user'].is_anonymous())
        user.is_active = True
        user.save()

        # Try logging in via link: wrong secret
        autologin = reverse('account-go', kwargs=dict(
            user_id=str(user.id), secret='a' * 32, url=test_url
        ))
        response = self.client.get(autologin)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(test_url)
        self.assertTrue(response.context['user'].is_anonymous())
