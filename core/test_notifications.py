from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase

from accounts.models import User
from core.context_processors import sgp_globals
from core.models import Notification


class NotificationVisibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('notification@example.invalid', nom='Test', prenom='User')
        self.other = User.objects.create_user('other@example.invalid', nom='Other', prenom='User')

    def context_for(self, user):
        request = RequestFactory().get('/')
        request.user = user
        return sgp_globals(request)

    def test_personal_and_global_unread_notifications_exclude_private_and_read(self):
        personal = Notification.objects.create(user=self.user, titre='Personnel', message='Message personnel')
        global_notice = Notification.objects.create(titre='Global', message='Message commun')
        Notification.objects.create(user=self.other, titre='Confidentiel', message='Message autre utilisateur')
        Notification.objects.create(user=self.user, titre='Lu', message='Ancien message', is_read=True)
        context = self.context_for(self.user)
        self.assertEqual(context['sgp_unread_count'], 2)
        self.assertEqual({item.pk for item in context['sgp_notifications']}, {personal.pk, global_notice.pk})

    def test_display_limit_keeps_total_count_and_anonymous_user_sees_none(self):
        Notification.objects.bulk_create([
            Notification(titre=f'Global {i}', message='Message commun') for i in range(10)
        ])
        context = self.context_for(self.user)
        self.assertEqual(context['sgp_unread_count'], 10)
        self.assertEqual(len(context['sgp_notifications']), 8)
        anonymous_context = self.context_for(AnonymousUser())
        self.assertEqual(anonymous_context['sgp_notifications'], [])
        self.assertEqual(anonymous_context['sgp_unread_count'], 0)
