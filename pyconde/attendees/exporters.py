# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.core.urlresolvers import reverse

from dateutil.rrule import DAILY, rrule

from ..conference.models import current_conference


LOG = logging.getLogger('pyconde.attendees')


class PurchaseExporter(object):
    """
    This exporter takes an pyconde.attendees.Purchase object and exports it,
    including related tickets and payment information as Python dict. This dict
    is intended to be usable by pyinvoice.
    """

    def __init__(self, purchase):
        self.purchase = purchase

    def export(self):
        return self._export(self.purchase)

    def _export(self, purchase):
        from .models import Ticket, VenueTicket
        result = {
            'id': purchase.full_invoice_number,
            'pk': purchase.pk,
            'tickets': [],
            'total': purchase.payment_total,
            'currency': 'EUR',
            'status': purchase.state,
            'comments': purchase.comments,
            'date_added': purchase.date_added.replace(microsecond=0),
            'payment_address': {
                'email': purchase.email,
                'first_name': purchase.first_name,
                'last_name': purchase.last_name,
                'company': purchase.company_name,
                'address_line': purchase.street,
                'postal_code': purchase.zip_code,
                'country': purchase.country,
                'city': purchase.city,
                'vat_id': purchase.vat_id,
            },
            'payment_info': {
                'method': purchase.payment_method,
                'transaction_id': purchase.payment_transaction
            }
        }

        for ticket in Ticket.objects.filter(purchase=purchase).all():
            ticket_data = {
                'pk': ticket.pk,
                'title': ticket.invoice_item_title,
                'voucher': None,
                'type': {
                    'product_number': ticket.ticket_type.product_number,
                    'name': ticket.ticket_type.name,
                    'pk': ticket.ticket_type.pk
                },
                'price': ticket.ticket_type.fee
            }
            try:
                if ticket.venueticket.voucher is not None:
                    ticket_data['voucher'] = ticket.venueticket.voucher.code
            except VenueTicket.DoesNotExist:
                pass
            result['tickets'].append(ticket_data)
        return result


class BadgeExporter(object):

    def __init__(self, tickets, base_url=None, indent=settings.DEBUG):
        from django.contrib.sites.models import Site
        self.tickets = tickets
        self.indent = indent
        if base_url is None:
            self.base_url = 'http://%s' % Site.objects.get_current().domain
        else:
            self.base_url = base_url
        self._data = None

    @property
    def json(self):
        import json
        data = self.export()
        return json.dumps(data, indent=self.indent)

    def export(self):
        if getattr(self, '_data', None) is None:
            self._data = self._export(self.tickets)
        return self._data

    def _export(self, tickets):
        from collections import defaultdict
        from .models import VenueTicket
        from ..schedule.models import Session

        result = []
        sessions = Session.objects.select_related('speaker', 'kind') \
                                  .prefetch_related('additional_speakers') \
                                  .all()
        speaker_involvements = defaultdict(set)
        all_trainings = Session.objects.order_by('start', 'location__order') \
                                       .filter(released=True,
                                               kind__slug='training') \
                                       .values_list('id', 'start')
        trainings_pk_index = {
            pk: (idx, start.date().isoformat())
            for idx, (pk, start)
            in enumerate(all_trainings, 1)
        }
        for session in sessions:
            speaker_involvements[session.speaker.pk].add(session.kind.slug)
            for add_s in session.additional_speakers.all():
                speaker_involvements[add_s.id].add(session.kind.slug)

        for ticket in tickets.order_by('last_name', 'first_name'):
            if not isinstance(ticket, VenueTicket):
                LOG.warn('Ticket %d is of type %s. Skipping' % (
                    ticket.pk, ticket.__class__.__name__))
                continue
            purchase = ticket.purchase
            if purchase.state != 'payment_received':
                LOG.warn('%s %d belongs to purchase %s (%d) which has not been paid. Skipping' % (
                    ticket.__class__.__name__, ticket.pk, purchase.full_invoice_number, purchase.id))
                continue
            user = ticket.user
            badge = {
                'id': ticket.id,
                'uid': user and user.id or None,
                'name': '%s %s' % (ticket.first_name, ticket.last_name),
                'organization': ticket.organisation or purchase.company_name or user and user.organisation or None,
                'tshirt': ticket.shirtsize_id and ticket.shirtsize.size or None,
                'tags': None,  # set below
                'sponsor': None,  # set below
                'days': None,  # Only whole-conference tickets are sold online
                'status': None,  # set below
                'trainings': None,
            }
            days = None
            if ticket.ticket_type.valid_on:
                days = [ticket.ticket_type.valid_on.isoformat()]
            else:
                dtstart = current_conference().start_date
                until = current_conference().end_date
                days = [d.date().isoformat() for d in rrule(DAILY, dtstart=dtstart, until=until)]
            badge['days'] = days
            status_keys = set()
            if ticket.sponsor_id and ticket.sponsor.active:
                sponsor = ticket.sponsor
                badge['sponsor'] = {
                    'name': sponsor.name,
                    'level': sponsor.level.name,
                    'website': sponsor.external_url
                }
                status_keys.add('sponsor')

            if user:
                status_keys |= set(user.badge_status.values_list('slug', flat=True).all())

                speaker = user.speaker_profile
                if 'talk' in speaker_involvements[speaker.id]:
                    status_keys.add('speaker')
                if 'training' in speaker_involvements[speaker.id]:
                    status_keys.add('trainer')
                if 'keynote' in speaker_involvements[speaker.id]:
                    status_keys.add('keynote')

                tags = [t.name for t in user.tags.all()]
                if tags:
                    badge['tags'] = tags

                trainings = user.sessions_attending.filter(kind__slug='training').all()
                if trainings:
                    attendings = defaultdict(list)
                    for t in trainings:
                        index, start = trainings_pk_index[t.id]
                        attendings[start].append(index)
                    badge['trainings'] = attendings
            from pdb import set_trace; set_trace()
            if status_keys:
                badge['status'] = list(status_keys)

            result.append(badge)
        return result

    def _user_url(self, user):
        if user:
            if '{uid}' in self.base_url:
                return self.base_url.format(uid=user.id)
            else:
                self.base_url + reverse('account_profile', kwargs={'uid': user.id})
        return None
