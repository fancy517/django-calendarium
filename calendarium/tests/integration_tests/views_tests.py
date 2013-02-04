"""Tests for the views of the ``calendarium`` app."""
# ! Never use the timezone now, import calendarium.utils.now instead always
# inaccuracy on microsecond base can negatively influence your tests
# from django.utils.timezone import now
from django.utils.timezone import timedelta
from django.test import TestCase

from django_libs.tests.factories import UserFactory
from django_libs.tests.mixins import ViewTestMixin

from calendarium.models import Event
from calendarium.tests.factories import EventFactory, GroupFactory, RuleFactory
from calendarium.utils import now


class MonthViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``MonthView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_month'

    def get_view_kwargs(self):
        return {'year': self.year, 'month': self.month}

    def setUp(self):
        self.year = now().year
        self.month = now().month

    def test_view(self):
        """Test for the ``MonthView`` view class."""
        # regular call
        resp = self.is_callable()
        self.assertEqual(
            resp.template_name[0], 'calendarium/calendar_month.html', msg=(
                'Returned the wrong template.'))
        self.is_callable(method='POST', data={'next': True})
        self.is_callable(method='POST', data={'previous': True})
        self.is_callable(method='POST', data={'today': True})

        # AJAX call
        resp = self.client.get(
            self.get_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(
            resp.template_name[0], 'calendarium/partials/calendar_month.html',
            msg=('Returned the wrong template for AJAX request.'))

        # called with wrong values
        self.is_not_callable(kwargs={'year': 2000, 'month': 15})


class WeekViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``WeekView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_week'

    def get_view_kwargs(self):
        return {'year': self.year, 'week': self.week}

    def setUp(self):
        self.year = now().year
        # current week number
        self.week = now().date().isocalendar()[1]

    def test_view(self):
        """Tests for the ``WeekView`` view class."""
        resp = self.is_callable()
        self.assertEqual(
            resp.template_name[0], 'calendarium/calendar_week.html', msg=(
                'Returned the wrong template.'))
        self.is_callable(method='POST', data={'next': True})
        self.is_callable(method='POST', data={'previous': True})
        self.is_callable(method='POST', data={'today': True})

        resp = self.client.get(
            self.get_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(
            resp.template_name[0], 'calendarium/partials/calendar_week.html',
            msg=('Returned the wrong template for AJAX request.'))
        self.is_not_callable(kwargs={'year': self.year, 'week': '60'})


class DayViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``DayView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_day'

    def get_view_kwargs(self):
        return {'year': self.year, 'month': self.month, 'day': self.day}

    def setUp(self):
        self.year = 2001
        self.month = 2
        self.day = 15

    def test_view(self):
        """Tests for the ``DayView`` view class."""
        resp = self.is_callable()
        self.assertEqual(
            resp.template_name[0], 'calendarium/calendar_day.html', msg=(
                'Returned the wrong template.'))
        self.is_callable(method='POST', data={'next': True})
        self.is_callable(method='POST', data={'previous': True})
        self.is_callable(method='POST', data={'today': True})

        resp = self.client.get(
            self.get_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(
            resp.template_name[0], 'calendarium/partials/calendar_day.html',
            msg=('Returned the wrong template for AJAX request.'))
        self.is_not_callable(kwargs={'year': self.year, 'month': '14',
                                     'day': self.day})


class EventUpdateViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``EventUpdateView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_event_update'

    def get_view_kwargs(self):
        return {'pk': self.event.pk}

    def setUp(self):
        self.event = EventFactory()
        self.user = UserFactory()
        self.group = GroupFactory()
        self.user.groups.add(self.group)


    def test_view(self):
        self.should_be_callable_when_authenticated(self.user)


class EventCreateViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``EventCreateView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_event_create'

    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory()
        self.user.groups.add(self.group)

    def test_view(self):
        self.should_be_callable_when_authenticated(self.user)
        self.is_callable(data={'delete': True})
        self.assertEqual(Event.objects.all().count(), 0)


class EventDetailViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``EventDetailView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_event_detail'

    def get_view_kwargs(self):
        return {'pk': self.event.pk}

    def setUp(self):
        self.event = EventFactory()

    def test_view(self):
        self.is_callable()


class OccurrenceViewTestCaseMixin(object):
    """Mixin to avoid repeating code for the Occurrence views."""
    longMessage = True

    def get_view_kwargs(self):
        return {
            'pk': self.event.pk,
            'year': self.event.start.date().year,
            'month': self.event.start.date().month,
            'day': self.event.start.date().day,
        }

    def setUp(self):
        self.rule = RuleFactory(name='daily')
        self.start = now() - timedelta(days=1)
        self.end = now() + timedelta(days=5)
        self.event = EventFactory(
            rule=self.rule, end_recurring_period=now() + timedelta(days=2))

    def test_view(self):
        # regular test with a valid request
        self.is_callable()


class OccurrenceDeleteViewTestCase(
        OccurrenceViewTestCaseMixin, ViewTestMixin, TestCase):
    """Tests for the ``OccurrenceDeleteView`` view class."""
    def get_view_name(self):
        return 'calendar_occurrence_delete'


class OccurrenceDetailViewTestCase(
        OccurrenceViewTestCaseMixin, ViewTestMixin, TestCase):
    """Tests for the ``OccurrenceDetailView`` view class."""
    def get_view_name(self):
        return 'calendar_occurrence_detail'


class OccurrenceUpdateViewTestCase(
        OccurrenceViewTestCaseMixin, ViewTestMixin, TestCase):
    """Tests for the ``OccurrenceUpdateView`` view class."""
    def get_view_name(self):
        return 'calendar_occurrence_update'
