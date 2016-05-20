# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import decimal
import uuid
import os
import string

from email.utils import formataddr

from django.contrib.contenttypes import models as content_models
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.conf import settings as django_settings
from django.db import models
from django.db.models import Q
from django.utils.encoding import force_text
from django.utils.timezone import now
from django.utils.translation import ugettext, ugettext_lazy as _

from . import settings
from .validators import during_conference


PURCHASE_STATES = (
    ('incomplete', _('Purchase incomplete')),
    ('new', _('new')),
    ('invoice_created', _('invoice created')),
    ('payment_received', _('payment received')),
    ('canceled', _('canceled'))
)

PAYMENT_METHOD_CHOICES = (
    ('invoice', _('Invoice')),
    ('creditcard', _('Credit card')),
    ('elv', _('ELV')),
)

GENDER_CHOICES = (
    ('female', _('female')),
    ('male', _('male')),
)


def limit_ticket_types():
    """
    This returns a Q usable for limit_choice_to restrictions that only
    includes subclasses of Ticket and Ticket itself.

    TODO: Once djep works on Django 1.7, this should be updated to act as
          callable Q generator.
    """
    return (Q(app_label='attendees', model='ticket') |
        Q(app_label='attendees', model='venueticket') |
        Q(app_label='attendees', model='supportticket') |
        Q(app_label='attendees', model='simcardticket'))


class VoucherTypeManager(models.Manager):
    pass


class VoucherType(models.Model):
    conference = models.ForeignKey(
        "conference.Conference", verbose_name="conference", null=True,
        on_delete=models.PROTECT)
    name = models.CharField(_('voucher type'), max_length=50)

    objects = VoucherTypeManager()

    def __unicode__(self):
        return self.name

    class Meta(object):
        verbose_name = _('voucher type')
        verbose_name_plural = _('voucher types')


class VoucherManager(models.Manager):
    def valid(self):
        return self.filter(date_valid__gte=now(), is_used=False)


class Voucher(models.Model):
    code = models.CharField(
        _('Code'), max_length=12, blank=True,
        help_text=_('Can be left blank, code will be created when you save.'))
    remarks = models.CharField(_('Remarks'), max_length=254, blank=True)
    date_valid = models.DateTimeField(
        _('Date (valid)'), blank=False,
        help_text=_('The voucher is valid until this date'))
    is_used = models.BooleanField(_('Is used'), default=False)
    type = models.ForeignKey('VoucherType', verbose_name=_('voucher type'),
                             null=True)

    objects = VoucherManager()

    class Meta:
        verbose_name = _('Voucher')
        verbose_name_plural = _('Vouchers')

    def __unicode__(self):
        return '%s %s' % (ugettext('Voucher'), self.code)

    def save(self, *args, **kwargs):
        if len(self.code) < 1:
            self.code = str(uuid.uuid4())[-12:]
        super(Voucher, self).save(*args, **kwargs)


class TicketTypeManager(models.Manager):

    def available(self):
        return self.filter(date_valid_from__lte=now(),
                           date_valid_to__gte=now(), is_active=True)

    def get_next_product_number(self):
        """Returns the next product number."""
        if self.count() > 0:
            last = self.aggregate(models.Max('product_number'))
            return last['product_number__max'] + 1
        else:
            return settings.PRODUCT_NUMBER_START

    def filter_ondesk(self):
        vt_ct = content_models.ContentType.objects.get_for_model(VenueTicket)
        return self.get_queryset().filter(is_on_desk_active=True,
                                          content_type=vt_ct,
                                          date_valid_from__lte=now(),
                                          date_valid_to__gte=now(),
                                          )


class TicketType(models.Model):
    conference = models.ForeignKey(
        "conference.Conference", verbose_name="conference", null=True,
        on_delete=models.PROTECT)
    product_number = models.IntegerField(
        _('Product number'), blank=True,
        help_text=_('Will be created when you save the first time.'))

    name = models.CharField(_('Name'), max_length=50)
    fee = models.FloatField(_('Fee'), default=0)

    max_purchases = models.PositiveIntegerField(
        _('Max. purchases'),
        default=0, help_text=_('0 means no limit'))

    is_active = models.BooleanField(_('Is active'), default=False)
    is_on_desk_active = models.BooleanField(_('Allow on desk purchase'), default=False)

    date_valid_from = models.DateTimeField(_('Sale start'), blank=False)
    date_valid_to = models.DateTimeField(_('Sale end'), blank=False)

    valid_on = models.DateField(_('Valid on'), blank=True, null=True,
        validators=[during_conference])

    vouchertype_needed = models.ForeignKey('VoucherType', null=True, blank=True,
        verbose_name=_('voucher type needed'))
    tutorial_ticket = models.BooleanField(_('Tutorial ticket'), default=False)

    remarks = models.TextField(_('Remarks'), blank=True)

    # Various settings for making tickets editable
    allow_editing = models.NullBooleanField(_('Allow editing'))
    editable_fields = models.TextField(_('Editable fields'), blank=True)
    editable_until = models.DateTimeField(_('Editable until'), blank=True, null=True)

    prevent_invoice = models.BooleanField(_("Conditionally prevent invoice to user"),
        default=False, blank=True,
        help_text=_('If checked, a purchase, that contains only tickets of '
                    'ticket types where this is checked, will not be send to '
                    'the user. This can be useful for e.g. sponsor tickets'))

    content_type = models.ForeignKey(
        content_models.ContentType, blank=False,
        limit_choices_to=limit_ticket_types(),
        verbose_name=_('Ticket to generate'))

    objects = TicketTypeManager()

    class Meta:
        ordering = ('tutorial_ticket', 'product_number', 'vouchertype_needed',)
        verbose_name = _('Ticket type')
        verbose_name_plural = _('Ticket type')
        unique_together = [('product_number', 'conference')]

    def __unicode__(self):
        return '%s (%.2f EUR)' % (self.name, self.fee)

    def get_editable_fields(self):
        if self.editable_fields:
            return filter(bool, map(string.strip, self.editable_fields.split(",")))
        return []

    def get_readonly_fields(self):
        return [f for f in self.content_type.model_class().get_fields() if f not in self.get_editable_fields()]

    @property
    def purchases_count(self):
        # Ignore incomplete purchases.
        return self.ticket_set.filter(ticket_type=self).exclude(
            purchase__state='incomplete').count()

    @property
    def available_tickets(self):
        """
        Returns a number of still purchasable tickets or None if there is no
        limit.
        """
        if self.max_purchases < 1:
            return None
        else:
            available_tickets = self.max_purchases - self.purchases_count
            return available_tickets if available_tickets > 0 else 0

    def save(self, *args, **kwargs):
        if not self.pk:
            self.product_number = TicketType.objects.get_next_product_number()
        super(TicketType, self).save(*args, **kwargs)

    def clean(self):
        self.clean_editable_fields()

    def clean_editable_fields(self):
        val = self.editable_fields
        if self.content_type is None:
            return val
        ticket_cls = self.content_type.model_class()
        found_field_names = set(filter(bool, map(string.strip, val.split(","))))
        allowed_field_names = ticket_cls.get_fields()
        invalid_field_names = found_field_names - allowed_field_names
        if invalid_field_names:
            raise ValidationError(_("Invalid editable fields specified: %s") % u", ".join(invalid_field_names))
        return val

    @property
    def tax(self):
        return self.fee - (self.fee / 1.19)

    @property
    def fee_without_tax(self):
        return self.fee - self.tax


class PurchaseManager(models.Manager):
    def get_exportable_purchases(self):
        return self.filter(exported=False)


class Purchase(models.Model):
    conference = models.ForeignKey(
        "conference.Conference", verbose_name="conference", null=True,
        on_delete=models.PROTECT)
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True,
        verbose_name=_('User'))

    # Address in purchase because a user maybe wants to different invoices.
    company_name = models.CharField(_('Company'), max_length=100, blank=True)
    first_name = models.CharField(_('First name'), max_length=250)
    last_name = models.CharField(_('Last name'), max_length=250)
    email = models.EmailField(_('E-mail'))

    street = models.CharField(_('Street and house number'), max_length=100)
    zip_code = models.CharField(_('Zip code'), max_length=20)
    city = models.CharField(_('City'), max_length=100)
    country = models.CharField(_('Country'), max_length=100)
    vat_id = models.CharField(_('VAT-ID'), max_length=16, blank=True)

    date_added = models.DateTimeField(
        _('Date (added)'), blank=False, default=now)
    state = models.CharField(
        _('Status'), max_length=25, choices=PURCHASE_STATES,
        default=PURCHASE_STATES[0][0], blank=False)

    comments = models.TextField(_('Comments'), blank=True)

    payment_method = models.CharField(_('Payment method'), max_length=20,
                                      choices=PAYMENT_METHOD_CHOICES,
                                      default='invoice')
    payment_transaction = models.CharField(_('Transaction ID'), max_length=255,
                                           blank=True)
    payment_total = models.FloatField(_('Payment total'),
                                      blank=True, null=True)

    exported = models.BooleanField(_('Exported'), default=False)

    # Invoicing fields
    invoice_number = models.IntegerField(_('Invoice number'), null=True,
                                         blank=True)
    invoice_filename = models.CharField(_('Invoice filename'), null=True,
                                        blank=True, max_length=255)

    objects = PurchaseManager()

    class Meta:
        verbose_name = _('Purchase')
        verbose_name_plural = _('Purchases')

    def subtotal(self, tickets=None):
        return self.calculate_payment_total() - self.payment_tax

    def calculate_payment_total(self, tickets=None):
        # TODO: Externalize this into a utils method to be usable "offline"
        # TODO Maybe it's necessary to add VAT to payment_total.
        # TKO: Nope: in 2013 at least all ticket prices have been including VAT
        # However this may be different if people from foreign countries purchase
        # a ticket because then no VAT may be added (depends on country...)
        # so remains TODO for EuroPython
        fee_sum = 0.0
        if tickets is None:
            fee_sum = self.ticket_set.aggregate(models.Sum('ticket_type__fee'))
            return fee_sum['ticket_type__fee__sum']
        else:
            for ticket in tickets:
                fee_sum += ticket.ticket_type.fee
            return fee_sum

    @property
    def payment_total_in_cents(self):
        return int(decimal.Decimal(self.payment_total) * 100)

    @property
    def payment_fee(self):
        return self.payment_total / 1.19

    @property
    def payment_tax(self):
        return self.payment_total - (self.payment_total / 1.19)

    @property
    def full_invoice_number(self):
        if self.invoice_number is None:
            return None
        return settings.INVOICE_NUMBER_FORMAT.format(str(self.invoice_number).zfill(4))

    @property
    def invoice_filepath(self):
        if self.invoice_filename:
            return os.path.join(settings.INVOICE_ROOT, self.invoice_filename)
        return None

    @property
    def email_receiver(self):
        name = "%s %s" % (self.first_name, self.last_name)
        return formataddr((name, self.email))

    @property
    def send_invoice_to_user(self):
        if (
            self.payment_total == 0.0 and
            self.payment_method == 'invoice' and
            self.ticket_set.exclude(ticket_type__prevent_invoice=True).count() == 0
        ):
            return False
        return True

    def __unicode__(self):
        return '%s - %s' % (self.pk, self.get_state_display())


class TShirtSize(models.Model):
    conference = models.ForeignKey(
        "conference.Conference", verbose_name="conference", null=True,
        on_delete=models.PROTECT)
    size = models.CharField(max_length=100, verbose_name=_('Size'))
    sort = models.IntegerField(default=999, verbose_name=_('Sort order'))

    class Meta:
        verbose_name = _('T-Shirt size')
        verbose_name_plural = _('T-Shirt sizes')
        ordering = ('sort',)

    def __unicode__(self):
        return self.size


class TicketManager(models.Manager):

    def only_valid(self):
        return self.get_queryset().filter(canceled=False,
                                          purchase__state='payment_received')

    def get_active_user_tickets(self, user):
        """
        This returns all tickets that belong to a certain user, meaning that
        they were purchased by the user and not assigned to a different user
        or purchased by someone else and then assigned to the user.

        Only tickets from completed purchases are listed here.
        """
        return self.select_related('user')\
                   .filter(
                       Q(Q(purchase__user=user) & Q(user__isnull=True))
                       | Q(user=user)
                       )\
                   .filter(purchase__state='payment_received')


class Ticket(models.Model):
    purchase = models.ForeignKey(Purchase)
    ticket_type = models.ForeignKey(TicketType, verbose_name=_('Ticket type'))
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True,
        blank=True, related_name='%(app_label)s_%(class)s_tickets')

    date_added = models.DateTimeField(
        _('Date (added)'), blank=False, default=now)

    canceled = models.BooleanField(_('Canceled'), default=False, blank=True)

    objects = TicketManager()

    management_fields = ()

    def __init__(self, *args, **kwargs):
        obj = super(Ticket, self).__init__(*args, **kwargs)
        self.related_data = {}
        return obj

    class Meta:
        ordering = ('ticket_type__tutorial_ticket',
                    'ticket_type__product_number')

    @property
    def invoice_item_title(self):
        if self.real_ticket is None:
            return self.ticket_type.name
        return self.real_ticket.invoice_item_title

    @property
    def real_ticket(self):
        real_ticket = getattr(self, '_real_ticket', None)
        if real_ticket is None:
            try:
                real_ticket = getattr(self, self.ticket_type.content_type.model)
                self._real_ticket = real_ticket
            except ObjectDoesNotExist:
                # We need try-except here, because there is no other way to
                # check for the sub ticket class
                pass
        return real_ticket

    def save_related_data(self):
        """
        This helper method stores all the data inside the related_data object
        as if they were m2m relations that had not been persisted yet.
        """
        for key, values in self.related_data.items():
            attr = getattr(self, key)
            attr.clear()
            for value in values:
                attr.add(value)

    def can_be_edited_by(self, user, current_time=None):
        if current_time is None:
            current_time = now()
        if self.ticket_type.allow_editing is False:
            return False
        if not self.ticket_type.conference.tickets_editable and self.ticket_type.allow_editing is None:
            return False
        if self.user == user or (self.purchase.user == user and self.user is None):
            if self.ticket_type.editable_until is not None and self.ticket_type.editable_until < current_time:
                return False
            if self.ticket_type.conference.tickets_editable_until is not None and self.ticket_type.conference.tickets_editable_until < current_time:
                return False
            return True
        return False

    @classmethod
    def get_fields(cls):
        """
        Returns all fieldnames that are special to this ticket type.
        """
        local_fields = set(cls._meta.get_all_field_names())
        original_fields = set(Ticket._meta.get_all_field_names())
        return local_fields - original_fields - set(['ticket_ptr']) - set(cls.management_fields)


class SupportTicket(Ticket):

    objects = TicketManager()

    class Meta:
        verbose_name = _('Support Ticket')
        verbose_name_plural = _('Support Tickets')

    def __unicode__(self):
        return u'%s - %s' % (ugettext('Support'), self.ticket_type)

    @property
    def invoice_item_title(self):
        return force_text('“%s”' % self.ticket_type.name)


class VenueTicket(Ticket):
    first_name = models.CharField(_('First name'), max_length=250, blank=True)
    last_name = models.CharField(_('Last name'), max_length=250, blank=True)
    organisation = models.CharField(
        _('Organization'), max_length=100, blank=True)

    shirtsize = models.ForeignKey(TShirtSize, blank=True, null=True,
                                  verbose_name=_('Desired T-Shirt size'))
    dietary_preferences = models.ManyToManyField('DietaryPreference',
        verbose_name=_('Dietary preferences'), blank=True)

    sponsor = models.ForeignKey('sponsorship.Sponsor', null=True, blank=True,
        verbose_name=_('Sponsor'))
    voucher = models.ForeignKey(
        'Voucher', verbose_name=_('Voucher'), blank=True, null=True)

    management_fields = ('sponsor', 'voucher',)

    objects = TicketManager()

    class Meta:
        verbose_name = _('Conference Ticket')
        verbose_name_plural = _('Conference Tickets')

    def __unicode__(self):
        return u'%s %s - %s' % (self.first_name, self.last_name,
                                self.ticket_type)

    @property
    def invoice_item_title(self):
        return force_text('“%s” Ticket for:<br /><i>%s %s</i>' %
            (self.ticket_type.name, self.first_name, self.last_name))


class DietaryPreference(models.Model):
    name = models.CharField('Name', unique=True, max_length=30)

    def __unicode__(self):
        return ugettext(self.name)


class SIMCardTicket(Ticket):
    first_name = models.CharField(_('First name'), max_length=250, blank=False)
    last_name = models.CharField(_('Last name'), max_length=250, blank=False)

    date_of_birth = models.DateField(_('Date of birth'))
    gender = models.CharField(_('Gender'), max_length=6, choices=GENDER_CHOICES)

    hotel_name = models.CharField(
        _('Host'), max_length=100, blank=True,
        help_text=_('Name of your hotel or host for your stay.'))
    email = models.EmailField(_('E-mail'), blank=False)

    street = models.CharField(_('Street and house number of host'), max_length=100)
    zip_code = models.CharField(_('Zip code of host'), max_length=20)
    city = models.CharField(_('City of host'), max_length=100)
    country = models.CharField(_('Country of host'), max_length=100)

    phone = models.CharField(
        _('Host phone number'), max_length=100, blank=False,
        help_text=_('Please supply the phone number of your hotel or host.'))

    sim_id = models.CharField(
        _('IMSI'), max_length=20, blank=True,
        help_text=_('The IMSI of the SIM Card associated with this account.'))

    objects = TicketManager()

    class Meta:
        verbose_name = _('SIM Card')
        verbose_name_plural = _('SIM Cards')

    def __unicode__(self):
        return u'%s %s - SIM %s' % (self.first_name, self.last_name, self.sim_id)

    @property
    def invoice_item_title(self):
        return force_text('SIM Card for:<br /><i>%s %s</i>' %
            (self.first_name, self.last_name))
