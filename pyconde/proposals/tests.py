import datetime
import urllib
from datetime import timedelta

from django.test import TestCase
from django.forms.models import model_to_dict
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from pyconde.conference.test_utils import ConferenceTestingMixin
from pyconde.conference import models as conference_models
from pyconde.speakers import models as speakers_models

from . import models
from . import forms
from . import validators
from . import utils


class SubmissionTests(ConferenceTestingMixin, TestCase):
    def setUp(self):
        self.create_test_conference()
        self.user = get_user_model().objects.create_user(
            'test', 'test@test.com',
            'testpassword')
        speakers_models.Speaker.objects.all().delete()
        self.speaker = speakers_models.Speaker(user=self.user)
        self.speaker.save()

        self.now = datetime.datetime.now()

    def tearDown(self):
        self.destroy_all_test_conferences()

    def test_with_open_sessionkind(self):
        """
        Tests that a proposal can be submitted with an open sessionkind
        """
        proposal = models.Proposal(
            conference=self.conference,
            title="Proposal",
            description="DESCRIPTION",
            abstract="ABSTRACT",
            speaker=self.speaker,
            kind=self.kind,
            audience_level=self.audience_level,
            duration=self.duration,
            track=self.track
        )
        data = model_to_dict(proposal)
        data['agree_to_terms'] = True
        form = forms.ProposalSubmissionForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        now = datetime.datetime.now()
        self.kind.start_date = now - datetime.timedelta(1)
        self.kind.end_date = now + datetime.timedelta(1)
        self.kind.save()

        data = model_to_dict(proposal)
        data['agree_to_terms'] = True
        form = forms.ProposalSubmissionForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_with_closed_sessionkind(self):
        proposal = models.Proposal(
            conference=self.conference,
            title="Proposal",
            description="DESCRIPTION",
            abstract="ABSTRACT",
            speaker=self.speaker,
            kind=self.kind,
            audience_level=self.audience_level,
            duration=self.duration,
            track=self.track
        )
        self.kind.start_date = self.now - timedelta(2)
        self.kind.end_date = self.now - timedelta(1)
        self.kind.closed = None
        self.kind.save()
        form = forms.ProposalSubmissionForm(data=model_to_dict(proposal))
        self.assertFalse(form.is_valid())

        self.kind.start_date = None
        self.kind.end_date = None
        self.kind.closed = True
        self.kind.save()
        form = forms.ProposalSubmissionForm(data=model_to_dict(proposal))
        self.assertFalse(form.is_valid(), form.errors)


class MaxWordsValidatorTests(TestCase):
    def test_too_long(self):
        v = validators.MaxWordsValidator(3)
        self.assertRaises(ValidationError, v, "this is a bit too long")

    def test_ok_with_signs(self):
        v = validators.MaxWordsValidator(3)
        v("hi! hello... world!")

    def test_ok(self):
        v = validators.MaxWordsValidator(2)
        v("hello world!")

    def test_ok_with_whitespaces(self):
        v = validators.MaxWordsValidator(2)
        v("hello    \n   \t world!")


class ListUserProposalsViewTests(ConferenceTestingMixin, TestCase):
    def setUp(self):
        self.create_test_conference('')
        self.create_test_conference('other_')

        self.user = get_user_model().objects.create_user(
            'test', 'test@test.com',
            'testpassword'
        )
        speakers_models.Speaker.objects.all().delete()
        self.speaker = speakers_models.Speaker(user=self.user)
        self.speaker.save()

        self.now = datetime.datetime.now()

    def tearDown(self):
        self.destroy_all_test_conferences()
        self.user.delete()

    def test_current_conf_only(self):
        """
        This view should only list proposals made for the current conference.
        """
        # In this case the user has made two proposals: One for the current
        # conference, one for another one also managed within the same
        # database. Only the one for the current conference should be listed
        # here.
        previous_proposal = models.Proposal(
            conference=self.other_conference,
            title="Proposal",
            description="DESCRIPTION",
            abstract="ABSTRACT",
            speaker=self.speaker,
            kind=self.other_kind,
            audience_level=self.other_audience_level,
            duration=self.other_duration,
            track=self.other_track
        )
        previous_proposal.save()

        current_proposal = models.Proposal(
            conference=self.conference,
            title="Proposal",
            description="DESCRIPTION",
            abstract="ABSTRACT",
            speaker=self.speaker,
            kind=self.kind,
            audience_level=self.audience_level,
            duration=self.duration,
            track=self.track
        )
        current_proposal.save()

        with self.settings(CONFERENCE_ID=self.conference.pk):
            self.client.login(username=self.user.username,
                              password='testpassword')
            ctx = self.client.get('/en/proposals/mine/').context
            self.assertEqual([current_proposal], list(ctx['proposals']))

        with self.settings(CONFERENCE_ID=self.other_conference.pk):
            self.client.login(username=self.user.username,
                              password='testpassword')
            resp = self.client.get('/en/proposals/mine/')
            self.assertEqual([previous_proposal], list(resp.context['proposals']))

    def test_login_required(self):
        """
        This list should only be available to logged in users.
        """
        self.client.logout()
        self.assertRedirects(
            self.client.get('/en/proposals/mine/', follow=True),
            '/en/accounts/login/?next=%2Fen%2Fproposals%2Fmine%2F')


class SubmitProposalViewTests(TestCase):
    def test_login_required(self):
        self.client.logout()
        self.assertRedirects(
            self.client.get('/en/proposals/submit/', follow=True),
            '/en/accounts/login/?next=%2Fen%2Fproposals%2Fsubmit%2F')


class SubmitTypedProposalViewTests(TestCase):
    def test_login_required(self):
        self.client.logout()
        resp = self.client.get('/en/proposals/submit/testkind/', follow=True)
        self.assertRedirects(
            resp,
            '/en/accounts/login/?next=%2Fen%2Fproposals%2Fsubmit%2Ftestkind%2F')


class EditProposalViewTests(TestCase):
    def test_login_required(self):
        self.client.logout()
        self.assertRedirects(
            self.client.get('/en/proposals/edit/123/', follow=True),
            '/en/accounts/login/?next=%2Fen%2Fproposals%2Fedit%2F123%2F')


class CancelProposalViewTests(TestCase):
    def test_login_required(self):
        self.client.logout()
        self.assertRedirects(
            self.client.get('/en/proposals/cancel/123/', follow=True),
            '/en/accounts/login/?next=%2Fen%2Fproposals%2Fcancel%2F123%2F')


class LeaveProposalViewTests(TestCase):
    def test_login_required(self):
        self.client.logout()
        self.assertRedirects(
            self.client.get('/en/proposals/leave/123/', follow=True),
            '/en/accounts/login/?next=%2Fen%2Fproposals%2Fleave%2F123%2F')


class TimeslotModelTests(ConferenceTestingMixin, TestCase):
    def setUp(self):
        self.create_test_conference()

    def tearDown(self):
        self.destroy_all_test_conferences()

    def test_uniqueness(self):
        """
        Ensure uniqueness of a timeslot per day.
        """
        section = conference_models.Section(
            conference=self.conference, name="Test section")
        section.save()
        today = datetime.datetime.now().date()
        ts1 = models.TimeSlot(date=today, slot=1, section=section)
        ts1.save()
        ts2 = models.TimeSlot(date=today, slot=2, section=section)
        ts2.save()
        ts1_again = models.TimeSlot(date=today, slot=1, section=section)
        with self.assertRaises(Exception):
            ts1_again.clear()


class DateRangeTests(TestCase):
    def test_simple_daterange(self):
        start = datetime.date(2013, 3, 15)
        end = datetime.date(2013, 3, 18)
        range_ = list(utils.get_date_range(start, end))
        self.assertEquals(4, len(range_))
        self.assertEquals(datetime.date(2013, 3, 15), range_[0])
        self.assertEquals(datetime.date(2013, 3, 16), range_[1])
        self.assertEquals(datetime.date(2013, 3, 17), range_[2])
        self.assertEquals(datetime.date(2013, 3, 18), range_[3])

    def test_oneday_daterange(self):
        start = datetime.date(2013, 3, 15)
        end = datetime.date(2013, 3, 15)
        range_ = list(utils.get_date_range(start, end))
        self.assertEquals(1, len(range_))
        self.assertEquals(datetime.date(2013, 3, 15), range_[0])

    def test_invalid_daterange(self):
        start = datetime.date(2013, 03, 15)
        end = datetime.date(2013, 03, 14)
        with self.assertRaises(ValueError):
            list(utils.get_date_range(start, end))
