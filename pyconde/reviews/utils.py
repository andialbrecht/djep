import tablib
import logging
import re

from django.contrib.auth import get_user_model, models as auth_models
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from pyconde.conference import models as conference_models
from pyconde.accounts import utils as account_utils

EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

logger = logging.getLogger(__name__)


def get_review_permission():
    from .models import Review
    review_ct = ContentType.objects.get_for_model(Review)
    return auth_models.Permission.objects.get(content_type_id=review_ct.pk, codename='add_review')


def can_review_proposal(user, proposal=None, reset_cache=False):
    cache_key = 'reviewer_pks'
    reviewer_pks = cache.get(cache_key)
    if user.is_anonymous() or not hasattr(user, 'pk'):
        return False
    if reset_cache or reviewer_pks is None:
        perm = get_review_permission()
        reviewer_pks = set(u['pk'] for u in get_user_model().objects.filter(Q(is_superuser=True) | Q(user_permissions=perm) | Q(groups__permissions=perm)).values('pk'))
        cache.set(cache_key, reviewer_pks)
        logger.debug("reviewer_pks cache has been rebuilt")
    return user.pk in reviewer_pks


def can_participate_in_review(user, proposal):
    if can_review_proposal(user, proposal):
        return True
    if is_proposal_author(user, proposal):
        return True
    return False


def can_see_proposal_author(user):
    if (
        conference_models.current_conference() is not None and
        not conference_models.current_conference().anonymize_proposal_author
    ):
        return True
    if user.has_perm('proposals.see_proposal_author'):
        return True
    return False


def has_valid_mailaddr(user):
    mail = user.email
    return mail and EMAIL_REGEX.match(mail)


def is_proposal_author(user, proposal):
    if not hasattr(user, 'speaker_profile'):
        return False
    if user.speaker_profile == proposal.speaker or user.speaker_profile in proposal.additional_speakers.all():
        return True
    return False


def merge_comments_and_versions(comments, versions):
    def _comparator(a, b):
        return cmp(a.pub_date, b.pub_date)
    return sorted(list(comments) + list(versions), cmp=_comparator)


def get_people_to_notify(proposal, current_user=None):
    """
    Generates a set of all users that are somehow related to the given proposal.
    If a current_user is specified, this user will NOT be included in this set.
    """
    people_to_notify = set()
    people_to_notify.update([u.author for u in proposal.comments.select_related('author')])
    people_to_notify.update([review.user for review in proposal.reviews.all().select_related('user')])
    people_to_notify.add(proposal.speaker.user)
    people_to_notify.update([s.user for s in proposal.additional_speakers.all()])
    if current_user:
        people_to_notify.remove(current_user)
    return people_to_notify


def send_comment_notification(comment, notify_author=False):
    """
    Send a comment notification mail to all users related to the comment's
    proposal except for the author of the comment unless notify_author=True
    is passed.
    """
    proposal = comment.proposal
    current_user = comment.author
    if notify_author:
        current_user = None
    # WARNING: We cannot use `can_see_proposal_author` here, because we
    #          write a BCC mail to all involved reviewers and there will
    #          probably be at least one not allowed to see the author
    hide_author = conference_models.current_conference().anonymize_proposal_author and\
        is_proposal_author(comment.author, proposal)
    body = render_to_string('reviews/emails/comment_notification.txt', {
        'comment': comment,
        'proposal': proposal,
        'hide_author': hide_author,
        'site': Site.objects.get_current(),
        'proposal_url': reverse('reviews-proposal-details', kwargs={'pk': proposal.pk}),
    })
    if hide_author:
        subject = _("[REVIEW] The author has commented on \"%(title)s\"")
    else:
        subject = _("[REVIEW] %(author)s commented on \"%(title)s\"")
    msg = EmailMessage(subject=subject % {
            'author': account_utils.get_display_name(comment.author),
            'title': proposal.title},
        bcc=[u.email for u in get_people_to_notify(proposal, current_user)
             if has_valid_mailaddr(u)],
        body=body)
    msg.send()


def send_proposal_update_notification(version, notify_author=False):
    """
    Send a version notification mail to all users related to the version's
    proposal except for the author of the version unless notify_author=True
    is passed.
    """
    proposal = version.original
    current_user = version.creator
    if notify_author:
        current_user = None
    # WARNING: We cannot use `can_see_proposal_author` here, because we
    #          write a BCC mail to all involved reviewers and there will
    #          probably be at least one not allowed to see the author
    hide_author = conference_models.current_conference().anonymize_proposal_author and\
        is_proposal_author(current_user, proposal)
    body = render_to_string('reviews/emails/version_notification.txt', {
        'version': version,
        'proposal': proposal,
        'hide_author': hide_author,
        'site': Site.objects.get_current(),
        'proposal_url': reverse('reviews-proposal-details', kwargs={'pk': proposal.pk}),
    })
    if hide_author:
        subject = _("[REVIEW] The author updated %(title)s")
    else:
        subject = _("[REVIEW] %(author)s updated %(title)s")
    msg = EmailMessage(subject=subject % {
            'author': account_utils.get_display_name(version.creator),
            'title': proposal.title},
        bcc=[u.email for u in get_people_to_notify(proposal, current_user)],
        body=body)
    msg.send()


def create_reviews_export(queryset):
    data = tablib.Dataset(headers=['Proposal-ID', 'Title', 'Review-ID', 'User-ID', 'Username', 'Rating'])
    for review in queryset.select_related('user', 'proposal'):
        data.append((review.proposal.pk, review.proposal.title, review.pk, review.user.pk, review.user.username, review.rating))
    return data


def create_proposal_score_export(queryset=None):
    """
    By default exports all proposals with their latest title (and original
    title), final score etc. to a tablib dataset.
    """
    from . import models

    def _format_cospeaker(s):
        """
        Format the speaker's name for secondary speaker export and removes
        our separator characters to avoid confusion.
        """
        return unicode(s).replace("|", " ")

    if queryset is None:
        queryset = models.ProposalMetaData.objects\
            .select_related('proposal', 'proposal__speaker',
                'latest_proposalversion', 'latest_proposalversion__track',
                'latest_proposalversion__audience_level',
                'latest_proposalversion__duration')\
            .order_by('-score')
    data = tablib.Dataset(headers=['ID', 'Title', 'OriginalTitle', 'SpeakerUsername',
        'SpeakerName', 'CoSpeakers', 'AudienceLevel', 'Duration', 'Track', 'Score',
        'NumReviews'])
    for md in queryset:
        title = md.proposal.title
        duration = md.proposal.duration
        audience_level = md.proposal.audience_level
        track = md.proposal.track
        cospeakers = []
        if md.latest_proposalversion:
            title = md.latest_proposalversion.title
            duration = md.latest_proposalversion.duration
            track = md.latest_proposalversion.track
            audience_level = md.latest_proposalversion.audience_level
            cospeakers = [_format_cospeaker(s) for s in md.latest_proposalversion.additional_speakers.all()]
        else:
            cospeakers = [_format_cospeaker(s) for s in md.proposal.additional_speakers.all()]
        data.append((
            md.proposal.pk,
            title,
            md.proposal.title,
            md.proposal.speaker.user.username,
            unicode(md.proposal.speaker) if md.proposal.speaker else "",
            u"|".join(cospeakers),
            unicode(audience_level) if audience_level else "",
            unicode(duration) if duration else "",
            unicode(track) if track else "",
            md.score,
            md.num_reviews
            ))
    return data
