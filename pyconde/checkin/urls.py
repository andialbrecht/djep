# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url, patterns


urlpatterns = patterns(
    'pyconde.checkin.views',

    url(r'^purchase/$', 'purchase_view', name='checkin_purchase'),
    url(r'^purchase/(?P<pk>\d+)/$', 'purchase_detail_view', name='checkin_purchase_detail'),
    url(r'^purchase/(?P<pk>\d+)/badges/$', 'purchase_badges_view', name='checkin_purchase_badges'),
    url(r'^purchase/(?P<pk>\d+)/invoice/$', 'purchase_invoice_view',
        name='checkin_purchase_invoice'),
    url(r'^purchase/(?P<pk>\d+)/(?P<new_state>[^/]+)/$', 'purchase_update_state',
        name='checkin_purchase_state'),
    url(r'^ticket/(?P<pk>\d+)/badge/$', 'ticket_badge_view', name='checkin_ticket_badge'),
    url(r'^ticket/(?P<pk>\d+)/edit/$', 'ticket_update_view', name='checkin_ticket_update'),

    url(r'^search/$', 'search_view', name='checkin_search'),
)
