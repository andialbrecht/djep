# -*- coding: UTF-8 -*-
from django import forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, ButtonHolder, Submit, HTML, Fieldset

from taggit.utils import edit_string_for_tags

from . import models
from pyconde.proposals import forms as proposal_forms
from pyconde.conference import models as conference_models


class UpdateProposalForm(forms.ModelForm):

    class Meta(object):
        model = models.ProposalVersion
        fields = [
            'title', 'description', 'abstract', 'duration', 'track', 'audience_level', 'tags'
        ]

    def __init__(self, *args, **kwargs):
        super(UpdateProposalForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.layout = Layout(
            Fieldset(_('General'),
                Field('title', autofocus='autofocus'),
                Field('description'),
                Field('abstract'),
                ),
            Fieldset(_('Details'),
                Field('duration'),
                Field('track'),
                Field('audience_level'),
                Field('tags'),
                ),
            ButtonHolder(Submit('save', "Speichern", css_class="btn-primary"))
            )

    def save(self, commit=True):
        instance = super(UpdateProposalForm, self).save(False)
        self.customize_save(instance)
        if commit:
            instance.save()
        return instance

    def customize_save(self, instance):
        """
        This is executed right after the initial save step to enforce
        some values no matter what was previously assigned to this form.
        """
        pass

    @classmethod
    def init_from_proposal(cls, proposal):
        # Right now this code smells a bit esp. with regards to tags
        form = cls(initial={
            'title': proposal.title,
            'description': proposal.description,
            'abstract': proposal.abstract,
            'tags': edit_string_for_tags(proposal.tags.all()),
            'speaker': proposal.speaker,
            'additional_speakers': proposal.additional_speakers.all(),
            'track': proposal.track,
            'duration': proposal.duration,
            'audience_level': proposal.audience_level,
            })
        return form


class UpdateTalkProposalForm(UpdateProposalForm):
    def __init__(self, *args, **kwargs):
        super(UpdateTalkProposalForm, self).__init__(*args, **kwargs)
        proposal_forms.TalkSubmissionForm().customize_fields(form=self)


class UpdateTutorialProposalForm(UpdateProposalForm):
    class Meta(object):
        model = models.ProposalVersion
        fields = ['title', 'description', 'abstract', 'audience_level', 'tags']

    def __init__(self, *args, **kwargs):
        super(UpdateTutorialProposalForm, self).__init__(*args, **kwargs)
        proposal_forms.TutorialSubmissionForm().customize_fields(form=self)
        self.helper.layout = Layout(
            Fieldset(_('General'),
                Field('title', autofocus='autofocus'),
                Field('description'),
                Field('abstract'),
                ),
            Fieldset(_('Details'),
                Field('audience_level'),
                Field('tags'),
                ),
            ButtonHolder(Submit('save', "Speichern", css_class="btn-primary"))
            )

    def customize_save(self, instance):
        instance.duration = conference_models.SessionDuration.current_objects.get(slug='tutorial')


class CommentForm(forms.ModelForm):
    class Meta(object):
        model = models.Comment
        fields = ['content']

    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('content'),
            ButtonHolder(Submit('comment', "Kommentar abschicken", css_class='btn btn-primary'))
            )


class ReviewForm(forms.ModelForm):
    class Meta(object):
        model = models.Review
        fields = ['rating', 'summary']

    def __init__(self, *args, **kwargs):
        super(ReviewForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('rating'), Field('summary'),
            ButtonHolder(Submit('save', "Review abgeben", css_class='btn-primary')))


class UpdateReviewForm(ReviewForm):
    def __init__(self, *args, **kwargs):
        super(UpdateReviewForm, self).__init__(*args, **kwargs)
        self.helper.layout = Layout(
            Field('rating'), Field('summary'),
            ButtonHolder(
                HTML(u"""<a href="{0}">Löschen</a>""".format(
                    reverse('reviews-delete-review',
                        kwargs={'pk': kwargs.get('instance').proposal.pk}))),
                Submit('save', "Änderungen speichern", css_class='btn-primary')
                )
            )
