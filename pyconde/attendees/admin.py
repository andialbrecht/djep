# -* coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import ugettext, ugettext_lazy as _
from django.utils.timezone import now

from . import settings as app_settings
from . import tasks
from . import utils
from .exporters import BadgeExporter
from .models import Purchase, SupportTicket, VenueTicket, TicketType, Voucher, VoucherType, \
                    TShirtSize, SIMCardTicket, DietaryPreference


def export_tickets(modeladmin, request, queryset):
    return HttpResponse(utils.create_tickets_export(queryset).csv, mimetype='text/csv')
export_tickets.short_description = _("Export as CSV")


def export_badges(modeladmin, request, queryset):
    base_url = 'https://' if request.is_secure() else 'http://'
    exporter = BadgeExporter(queryset, base_url=base_url + request.get_host())
    return HttpResponse(exporter.json, mimetype='application/json')


class TicketTypeAdmin(admin.ModelAdmin):
    list_display = ('product_number', '__unicode__', 'conference',
                    'fee', 'is_active', 'tutorial_ticket', 'purchases_count',
                    'max_purchases', 'date_valid_from', 'date_valid_to')
    list_display_links = ('product_number', '__unicode__')
    list_filter = ('is_active', 'conference')

    class Media(object):
        js = ('assets/js/admin.attendees.js',)

admin.site.register(TicketType, TicketTypeAdmin)


class ShirtSizeAdmin(admin.ModelAdmin):
    list_display = ('size', 'sort')

admin.site.register(TShirtSize, ShirtSizeAdmin)


class VoucherTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'conference')
    list_filter = ('conference',)

admin.site.register(VoucherType, VoucherTypeAdmin)


class VoucherAdmin(admin.ModelAdmin):
    list_display = ('pk', 'code', 'is_used', 'type', 'remarks', 'date_valid')
    list_filter = ('is_used', 'type')
    search_fields = ('code', 'remarks')

admin.site.register(Voucher, VoucherAdmin)


class TicketInline(admin.TabularInline):
    extra = 0


class SupportTicketInline(TicketInline):
    model = SupportTicket


class VenueTicketInline(TicketInline):
    model = VenueTicket


class SIMCardTicketInline(TicketInline):
    model = SIMCardTicket


class PurchaseAdmin(admin.ModelAdmin):
    list_display = (
        'full_invoice_number', 'pk', 'payment_total', 'first_name', 'last_name',
        'company_name', 'street', 'city', 'date_added', 'payment_method',
        'state', 'exported',
    )
    list_editable = ('state',)
    list_filter = ('state', 'date_added', 'payment_method', 'exported',)
    search_fields = ('invoice_number', 'first_name', 'last_name', 'email')
    inlines = (SupportTicketInline, VenueTicketInline, SIMCardTicketInline,)
    actions = ('send_payment_confirmation', 'export_and_send_invoices',
               'send_invoice_to_myself', 'send_invoice_to_customer',
               'send_payment_reminder', 'send_purchase_canceled',)

    def export_and_send_invoices(self, request, queryset):
        for purchase in queryset:
            if not purchase.exported:
                tasks.render_invoice.delay(purchase.pk)
            else:
                self.message_user(request,
                    _('Purchase %(invoice_number)s has already been exported. '
                      'Use “Send me a copy of the invoice” or “Send customer '
                      'a copy of the invoice” to mail the invoice.') % {
                        'invoice_number': purchase.full_invoice_number,
                    })
    export_and_send_invoices.short_description = _('Export invoice and send')

    def send_invoice_to_myself(self, request, queryset):
        recipients = (request.user.email,)  # Needs a tuple
        for purchase in queryset:
            if purchase.exported:
                tasks.send_invoice.delay(purchase.pk, recipients)
            else:
                self.message_user(request,
                    _('Purchase %(invoice_number)s has not been exported yet. '
                      'Use “Export invoice and send” to export the invoice '
                      'and send it to the customer.') % {
                        'invoice_number': purchase.full_invoice_number,
                    })
    send_invoice_to_myself.short_description = _('Send me a copy of the invoice')

    def send_invoice_to_customer(self, request, queryset):
        for purchase in queryset:
            if purchase.exported:
                tasks.send_invoice.delay(purchase.pk, (purchase.email_receiver,))
            else:
                self.message_user(request,
                    _('Purchase %(invoice_number)s has not been exported yet. '
                      'Use “Export invoice and send” to export the invoice '
                      'and send it to the customer.') % {
                        'invoice_number': purchase.full_invoice_number,
                    })
    send_invoice_to_customer.short_description = _('Send customer a copy of the invoice')

    def send_payment_confirmation(self, request, queryset):
        sent = 0
        for purchase in queryset.filter(
                state__in=('invoice_created', 'payment_received')):

            send_mail(ugettext('Payment receipt confirmation'),
                render_to_string('attendees/mail_payment_received.txt', {
                    'purchase': purchase,
                    'conference': purchase.conference
                }),
                settings.DEFAULT_FROM_EMAIL,
                [purchase.email_receiver, settings.DEFAULT_FROM_EMAIL],
                fail_silently=True
            )
            if purchase.state == 'invoice_created':
                purchase.state = 'payment_received'
                purchase.save()
            sent += 1

        if sent == 1:
            message_bit = _('1 mail was')
        else:
            message_bit = _('%s mails were') % sent

        self.message_user(request, ugettext('%s successfully sent.') % message_bit)
    send_payment_confirmation.short_description = _(
        'Send payment confirmation for selected %(verbose_name_plural)s')

    def send_payment_reminder(self, request, queryset):
        due_date = now() + datetime.timedelta(days=app_settings.REMINDER_DUE_DATE_OFFSET)

        # Remove everything not date related
        due_date = datetime.datetime(due_date.year, due_date.month, due_date.day)

        # Check that due date is not behind latest due date
        if app_settings.REMINDER_LATEST_DUE_DATE:
            latest_due_date = datetime.datetime.strptime(app_settings.REMINDER_LATEST_DUE_DATE, '%Y-%m-%d')
            if due_date > latest_due_date:
                due_date = latest_due_date

        for purchase in queryset.filter(state='invoice_created'):
            send_mail(ugettext('%(conference)s payment reminder' % {
                    'conference': purchase.conference.title,
                }),
                render_to_string('attendees/mail_payment_pending.txt', {
                    'purchase': purchase,
                    'conference': purchase.conference,
                    'due_date': due_date
                }),
                settings.DEFAULT_FROM_EMAIL,
                (purchase.email_receiver, request.user.email,),
                fail_silently=True
            )
            if purchase.exported:
                tasks.send_invoice.delay(purchase.pk, (purchase.email_receiver,))
            else:
                self.message_user(request,
                    _('Purchase %(invoice_number)s has not been exported yet. '
                      'Use “Export invoice and send” to export the invoice '
                      'and send it to the customer.') % {
                        'invoice_number': purchase.full_invoice_number,
                    })

    send_payment_reminder.short_description = _(
        'Send payment reminders for selected %(verbose_name_plural)s')

    def send_purchase_canceled(self, request, queryset):
        qs = queryset.filter(state__in=('invoice_created', 'payment_received')) \
                     .select_related('user')
        for purchase in qs.all():
            recipients = (purchase.email_receiver, request.user.email,)  # Needs a tuple
            tasks.cancel_purchase(purchase.id, recipients)

    send_purchase_canceled.short_description = _(
        'Cancel purchase and send cancelation notice for selected %(verbose_name_plural)s')

admin.site.register(Purchase, PurchaseAdmin)


class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'ticket_type', 'date_added', 'canceled')
    list_filter = ('ticket_type', 'date_added', 'purchase__state', 'canceled')
    search_fields = ('purchase__email', )
    actions = [export_tickets]

admin.site.register(SupportTicket, SupportTicketAdmin)


class VenueTicketAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'first_name', 'last_name', 'ticket_type',
                    'user', 'shirtsize', 'date_added', 'canceled')
    list_filter = ('ticket_type', 'date_added', 'purchase__state',
                   'dietary_preferences', 'canceled')
    search_fields = ('first_name', 'last_name', 'purchase__email',
                     'user__email')
    actions = [export_tickets, export_badges]
    raw_id_fields = ('user', 'purchase', 'voucher')

    def queryset(self, request):
        qs = super(VenueTicketAdmin, self).queryset(request)
        qs = qs.select_related('ticket_type', 'purchase', 'shirtsize')
        return qs

admin.site.register(VenueTicket, VenueTicketAdmin)


class SIMCardTicketAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'first_name', 'last_name', 'ticket_type',
                    'sim_id', 'date_added', 'canceled')
    list_filter = ('ticket_type', 'date_added', 'purchase__state', 'canceled')
    search_fields = ('first_name', 'last_name', 'purchase__email')
    actions = [export_tickets]

admin.site.register(SIMCardTicket, SIMCardTicketAdmin)


class DietaryPreferenceAdmin(admin.ModelAdmin):
    pass

admin.site.register(DietaryPreference, DietaryPreferenceAdmin)
