"""Views for the ``calendarium`` app."""
import calendar
from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.timezone import datetime, now, timedelta, utc
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    RedirectView,
    TemplateView,
    UpdateView,
)

from .constants import OCCURRENCE_DECISIONS
from .forms import OccurrenceForm
from .models import EventCategory, Event, Occurrence
from .utils import monday_of_week


class CategoryMixin(object):
    """Mixin to handle category filtering."""
    def dispatch(self, request, *args, **kwargs):
        if request.GET.get('category'):
            try:
                category_id = int(request.GET.get('category'))
            except ValueError:
                pass
            else:
                try:
                    self.category = EventCategory.objects.get(pk=category_id)
                except EventCategory.DoesNotExist:
                    pass
        return super(CategoryMixin, self).dispatch(request, *args, **kwargs)

    def get_category_context(self, **kwargs):
        context = {'categories': EventCategory.objects.all()}
        if hasattr(self, 'category'):
            context.update({'current_category': self.category})
        return context


class CalendariumRedirectView(RedirectView):
    """View to redirect to the current month view."""
    def get_redirect_url(self, **kwargs):
        return reverse('calendar_month', kwargs={'year': now().year,
                                                 'month': now().month})


class MonthView(CategoryMixin, TemplateView):
    """View to return all occurrences of an event for a whole month."""
    template_name = 'calendarium/calendar_month.html'

    def dispatch(self, request, *args, **kwargs):
        self.month = int(kwargs.get('month'))
        self.year = int(kwargs.get('year'))
        if self.month not in range(1, 13):
            raise Http404
        if request.method == 'POST':
            if request.POST.get('next'):
                new_date = datetime(self.year, self.month, 1) + timedelta(
                    days=31)
                return HttpResponseRedirect(reverse('calendar_month', kwargs={
                    'year': new_date.year, 'month': new_date.month}))
            elif request.POST.get('previous'):
                new_date = datetime(self.year, self.month, 1) - timedelta(
                    days=1)
                return HttpResponseRedirect(reverse('calendar_month', kwargs={
                    'year': new_date.year, 'month': new_date.month}))
            elif request.POST.get('today'):
                return HttpResponseRedirect(reverse('calendar_month', kwargs={
                    'year': now().year, 'month': now().month}))
        if request.is_ajax():
            self.template_name = 'calendarium/partials/calendar_month.html'
        return super(MonthView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = self.get_category_context()
        month = [[]]
        week = 0
        start = datetime(year=self.year, month=self.month, day=1, tzinfo=utc)
        end = datetime(
            year=self.year, month=self.month, day=1, tzinfo=utc
        ) + relativedelta(months=1)

        all_occurrences = Event.objects.get_occurrences(
            start, end, ctx.get('current_category'))
        for day in calendar.Calendar().itermonthdays(self.year, self.month):
            current = False
            if day:
                date = datetime(year=self.year, month=self.month, day=day,
                                tzinfo=utc)
                occurrences = filter(
                    lambda occ, date=date: occ.start.replace(
                        hour=0, minute=0, second=0, microsecond=0) == date,
                    all_occurrences)
                if date.date() == now().date():
                    current = True
            else:
                occurrences = []
            month[week].append((day, occurrences, current))
            if len(month[week]) == 7:
                month.append([])
                week += 1
        ctx.update({'month': month, 'date': date})
        return ctx


class WeekView(CategoryMixin, TemplateView):
    """View to return all occurrences of an event for one week."""
    template_name = 'calendarium/calendar_week.html'

    def dispatch(self, request, *args, **kwargs):
        self.week = int(kwargs.get('week'))
        self.year = int(kwargs.get('year'))
        if self.week not in range(1, 53):
            raise Http404
        if request.method == 'POST':
            if request.POST.get('next'):
                date = monday_of_week(self.year, self.week) + timedelta(days=7)
                return HttpResponseRedirect(reverse('calendar_week', kwargs={
                    'year': date.year, 'week': date.date().isocalendar()[1]}))
            elif request.POST.get('previous'):
                date = monday_of_week(self.year, self.week) - timedelta(days=7)
                return HttpResponseRedirect(reverse('calendar_week', kwargs={
                    'year': date.year, 'week': date.date().isocalendar()[1]}))
            elif request.POST.get('today'):
                return HttpResponseRedirect(reverse('calendar_week', kwargs={
                    'year': now().year,
                    'week': now().date().isocalendar()[1]}))
        if request.is_ajax():
            self.template_name = 'calendarium/partials/calendar_week.html'
        return super(WeekView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = self.get_category_context()
        date = monday_of_week(self.year, self.week)
        week = []
        day = 0
        start = date
        end = date + relativedelta(days=7)
        all_occurrences = Event.objects.get_occurrences(
            start, end, ctx.get('current_category'))
        while day < 7:
            current = False
            occurrences = filter(
                lambda occ, date=date: occ.start.replace(
                    hour=0, minute=0, second=0, microsecond=0) == date,
                all_occurrences)
            if date.date() == now().date():
                current = True
            week.append((date, occurrences, current))
            day += 1
            date = date + timedelta(days=1)
        ctx.update({'week': week, 'date': date, 'week_nr': self.week})
        return ctx


class DayView(CategoryMixin, TemplateView):
    """View to return all occurrences of an event for one day."""
    template_name = 'calendarium/calendar_day.html'

    def dispatch(self, request, *args, **kwargs):
        self.day = int(kwargs.get('day'))
        self.month = int(kwargs.get('month'))
        self.year = int(kwargs.get('year'))
        try:
            self.date = datetime(year=self.year, month=self.month,
                                 day=self.day, tzinfo=utc)
        except ValueError:
            raise Http404
        if request.method == 'POST':
            if request.POST.get('next'):
                date = self.date + timedelta(days=1)
                return HttpResponseRedirect(reverse('calendar_day', kwargs={
                    'year': date.year, 'month': date.month, 'day': date.day}))
            elif request.POST.get('previous'):
                date = self.date - timedelta(days=1)
                return HttpResponseRedirect(reverse('calendar_day', kwargs={
                    'year': date.year, 'month': date.month, 'day': date.day}))
            elif request.POST.get('today'):
                return HttpResponseRedirect(reverse('calendar_day', kwargs={
                    'year': now().year, 'month': now().month,
                    'day': now().day}))
        if request.is_ajax():
            self.template_name = 'calendarium/partials/calendar_day.html'
        return super(DayView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = self.get_category_context()
        occurrences = Event.objects.get_occurrences(
            self.date, self.date, ctx.get('current_category'))
        ctx.update({'date': self.date, 'occurrences': occurrences})
        return ctx


class EventDetailView(DetailView):
    """View to return information of an event."""
    model = Event


class EventMixin(object):
    """Mixin to handle event-related functions."""
    model = Event

    @method_decorator(permission_required('calendarium.add_event'))
    def dispatch(self, request, *args, **kwargs):
        return super(EventMixin, self).dispatch(request, *args, **kwargs)


class EventUpdateView(EventMixin, UpdateView):
    """View to update information of an event."""
    pass


class EventCreateView(EventMixin, CreateView):
    """View to create an event."""
    pass


class EventDeleteView(EventMixin, DeleteView):
    """View to delete an event."""
    pass


class OccurrenceViewMixin(object):
    """Mixin to avoid repeating code for the Occurrence view classes."""
    form_class = OccurrenceForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.event = Event.objects.get(pk=kwargs.get('pk'))
        except Event.DoesNotExist:
            raise Http404
        year = int(kwargs.get('year'))
        month = int(kwargs.get('month'))
        day = int(kwargs.get('day'))
        try:
            date = datetime(year, month, day, tzinfo=utc)
        except (TypeError, ValueError):
            raise Http404
        # this should retrieve the one single occurrence, that has a
        # matching start date
        try:
            occ = Occurrence.objects.get(
                start__year=year, start__month=month, start__day=day)
        except Occurrence.DoesNotExist:
            occ_gen = self.event.get_occurrences(self.event.start)
            occ = occ_gen.next()
            while occ.start.date() < date.date():
                occ = occ_gen.next()
        if occ.start.date() == date.date():
            self.occurrence = occ
        else:
            raise Http404
        self.object = occ
        return super(OccurrenceViewMixin, self).dispatch(
            request, *args, **kwargs)

    def get_object(self):
        return self.object

    def get_form_kwargs(self):
        kwargs = super(OccurrenceViewMixin, self).get_form_kwargs()
        kwargs.update({'initial': model_to_dict(self.object)})
        return kwargs


class OccurrenceDeleteView(OccurrenceViewMixin, DeleteView):
    """View to delete an occurrence of an event."""
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        decision = self.request.POST.get('decision')
        self.object.delete_period(decision)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, object):
        ctx = super(OccurrenceDeleteView, self).get_context_data()
        ctx.update({
            'decisions': OCCURRENCE_DECISIONS,
            'object': self.object
        })
        return ctx

    def get_success_url(self):
        return reverse('calendar_current_month')


class OccurrenceDetailView(OccurrenceViewMixin, DetailView):
    """View to show information of an occurrence of an event."""
    pass


class OccurrenceUpdateView(OccurrenceViewMixin, UpdateView):
    """View to edit an occurrence of an event."""
    pass
