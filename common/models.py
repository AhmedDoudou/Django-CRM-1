import arrow
import binascii
import datetime
import os
import time
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from phonenumber_field.modelfields import PhoneNumberField
from common.templatetags.common_tags import (
    is_document_file_image,
    is_document_file_audio,
    is_document_file_video,
    is_document_file_pdf,
    is_document_file_code,
    is_document_file_text,
    is_document_file_sheet,
    is_document_file_zip,
)
from common.utils import COUNTRIES, ROLES
from django.utils import timezone


def img_url(self, filename):
    hash_ = int(time.time())
    return "%s/%s/%s" % ("profile_pics", hash_, filename)


class Address(models.Model):
    address_line = models.CharField(
        _("Address"), max_length=255, blank=True, null=True
    )
    street = models.CharField(
        _("Street"), max_length=55, blank=True, null=True)
    city = models.CharField(_("City"), max_length=255, blank=True, null=True)
    state = models.CharField(_("State"), max_length=255, blank=True, null=True)
    postcode = models.CharField(
        _("Post/Zip-code"), max_length=64, blank=True, null=True
    )
    country = models.CharField(
        max_length=3, choices=COUNTRIES, blank=True, null=True)

    def __str__(self):
        return self.city if self.city else ""

    def get_complete_address(self):
        address = ""
        if self.address_line:
            address += self.address_line
        if self.street:
            if address:
                address += ", " + self.street
            else:
                address += self.street
        if self.city:
            if address:
                address += ", " + self.city
            else:
                address += self.city
        if self.state:
            if address:
                address += ", " + self.state
            else:
                address += self.state
        if self.postcode:
            if address:
                address += ", " + self.postcode
            else:
                address += self.postcode
        if self.country:
            if address:
                address += ", " + self.get_country_display()
            else:
                address += self.get_country_display()
        return address


class Org(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    user_limit = models.IntegerField(default=5)
    country = models.CharField(
        max_length=3, choices=COUNTRIES, blank=True, null=True)


class User(AbstractBaseUser, PermissionsMixin):
    file_prepend = "users/profile_pics"
    username = models.CharField(max_length=100, null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    alternate_email = models.EmailField(max_length=255, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(("date joined"), auto_now_add=True)
    profile_pic = models.FileField(
        max_length=1000, upload_to=img_url, null=True, blank=True
    )
    skype_ID = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def get_short_name(self):
        return self.username

    def documents(self):
        return self.document_uploaded.all()

    def get_full_name(self):
        full_name = None
        if self.first_name or self.last_name:
            full_name = self.first_name + " " + self.last_name
        elif self.username:
            full_name = self.username
        else:
            full_name = self.email
        return full_name

    @property
    def created_on_arrow(self):
        return arrow.get(self.date_joined).humanize()

    class Meta:
        ordering = ["-is_active"]

    def __str__(self):
        return self.email


class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    org = models.ForeignKey(
        Org, null=True, on_delete=models.CASCADE, blank=True)
    phone = PhoneNumberField(null=True, unique=True)
    alternate_phone = PhoneNumberField(null=True)
    address = models.ForeignKey(
        Address,
        related_name="adress_users",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    role = models.CharField(max_length=50, choices=ROLES, default="USER")
    has_sales_access = models.BooleanField(default=False)
    has_marketing_access = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_organization_admin = models.BooleanField(default=False)
    date_of_joining = models.DateField(null=True, blank=True)
    activation_key = models.CharField(max_length=150, null=True, blank=True)
    key_expires = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("user", "org"),)

    def save(self, *args, **kwargs):
        """ by default the expiration time is set to 2 hours """
        self.key_expires = timezone.now() + datetime.timedelta(hours=2)
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.is_organization_admin


class Comment(models.Model):
    case = models.ForeignKey(
        "cases.Case",
        blank=True,
        null=True,
        related_name="cases",
        on_delete=models.CASCADE,
    )
    comment = models.CharField(max_length=255)
    commented_on = models.DateTimeField(auto_now_add=True)
    commented_by = models.ForeignKey(
        Profile, on_delete=models.CASCADE, blank=True, null=True
    )
    account = models.ForeignKey(
        "accounts.Account",
        blank=True,
        null=True,
        related_name="accounts_comments",
        on_delete=models.CASCADE,
    )
    lead = models.ForeignKey(
        "leads.Lead",
        blank=True,
        null=True,
        related_name="leads_comments",
        on_delete=models.CASCADE,
    )
    opportunity = models.ForeignKey(
        "opportunity.Opportunity",
        blank=True,
        null=True,
        related_name="opportunity_comments",
        on_delete=models.CASCADE,
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        blank=True,
        null=True,
        related_name="contact_comments",
        on_delete=models.CASCADE,
    )
    profile = models.ForeignKey(
        "Profile",
        blank=True,
        null=True,
        related_name="user_comments",
        on_delete=models.CASCADE,
    )

    task = models.ForeignKey(
        "tasks.Task",
        blank=True,
        null=True,
        related_name="tasks_comments",
        on_delete=models.CASCADE,
    )

    invoice = models.ForeignKey(
        "invoices.Invoice",
        blank=True,
        null=True,
        related_name="invoice_comments",
        on_delete=models.CASCADE,
    )

    event = models.ForeignKey(
        "events.Event",
        blank=True,
        null=True,
        related_name="events_comments",
        on_delete=models.CASCADE,
    )

    def get_files(self):
        return Comment_Files.objects.filter(comment_id=self)

    @property
    def commented_on_arrow(self):
        return arrow.get(self.commented_on).humanize()


class Comment_Files(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    updated_on = models.DateTimeField(auto_now_add=True)
    comment_file = models.FileField(
        "File", upload_to="comment_files", null=True)

    def get_file_name(self):
        if self.comment_file:
            return self.comment_file.path.split("/")[-1]

        return None


class Attachments(models.Model):
    created_by = models.ForeignKey(
        Profile,
        related_name="attachment_created_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    file_name = models.CharField(max_length=60)
    created_on = models.DateTimeField(_("Created on"), auto_now_add=True)
    attachment = models.FileField(
        max_length=1001, upload_to="attachments/%Y/%m/")
    lead = models.ForeignKey(
        "leads.Lead",
        null=True,
        blank=True,
        related_name="lead_attachment",
        on_delete=models.CASCADE,
    )
    account = models.ForeignKey(
        "accounts.Account",
        null=True,
        blank=True,
        related_name="account_attachment",
        on_delete=models.CASCADE,
    )
    contact = models.ForeignKey(
        "contacts.Contact",
        on_delete=models.CASCADE,
        related_name="contact_attachment",
        blank=True,
        null=True,
    )
    opportunity = models.ForeignKey(
        "opportunity.Opportunity",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="opportunity_attachment",
    )
    case = models.ForeignKey(
        "cases.Case",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="case_attachment",
    )

    task = models.ForeignKey(
        "tasks.Task",
        blank=True,
        null=True,
        related_name="tasks_attachment",
        on_delete=models.CASCADE,
    )

    invoice = models.ForeignKey(
        "invoices.Invoice",
        blank=True,
        null=True,
        related_name="invoice_attachment",
        on_delete=models.CASCADE,
    )
    event = models.ForeignKey(
        "events.Event",
        blank=True,
        null=True,
        related_name="events_attachment",
        on_delete=models.CASCADE,
    )

    def file_type(self):
        name_ext_list = self.attachment.url.split(".")
        if len(name_ext_list) > 1:
            ext = name_ext_list[int(len(name_ext_list) - 1)]
            if is_document_file_audio(ext):
                return ("audio", "fa fa-file-audio")
            if is_document_file_video(ext):
                return ("video", "fa fa-file-video")
            if is_document_file_image(ext):
                return ("image", "fa fa-file-image")
            if is_document_file_pdf(ext):
                return ("pdf", "fa fa-file-pdf")
            if is_document_file_code(ext):
                return ("code", "fa fa-file-code")
            if is_document_file_text(ext):
                return ("text", "fa fa-file-alt")
            if is_document_file_sheet(ext):
                return ("sheet", "fa fa-file-excel")
            if is_document_file_zip(ext):
                return ("zip", "fa fa-file-archive")
            return ("file", "fa fa-file")
        return ("file", "fa fa-file")

    def get_file_type_display(self):
        if self.attachment:
            return self.file_type()[1]
        return None

    @property
    def created_on_arrow(self):
        return arrow.get(self.created_on).humanize()


def document_path(self, filename):
    hash_ = int(time.time())
    return "%s/%s/%s" % ("docs", hash_, filename)


class Document(models.Model):

    DOCUMENT_STATUS_CHOICE = (("active", "active"), ("inactive", "inactive"))

    title = models.TextField(blank=True, null=True)
    document_file = models.FileField(upload_to=document_path, max_length=5000)
    created_by = models.ForeignKey(
        Profile,
        related_name="document_uploaded",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        choices=DOCUMENT_STATUS_CHOICE, max_length=64, default="active"
    )
    shared_to = models.ManyToManyField(
        Profile, related_name="document_shared_to")
    teams = models.ManyToManyField(
        "teams.Teams", related_name="document_teams")
    org = models.ForeignKey(
        Org, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ("-created_on",)

    def __str__(self):
        return self.title

    def file_type(self):
        name_ext_list = self.document_file.url.split(".")
        if len(name_ext_list) > 1:
            ext = name_ext_list[int(len(name_ext_list) - 1)]
            if is_document_file_audio(ext):
                return ("audio", "fa fa-file-audio")
            if is_document_file_video(ext):
                return ("video", "fa fa-file-video")
            if is_document_file_image(ext):
                return ("image", "fa fa-file-image")
            if is_document_file_pdf(ext):
                return ("pdf", "fa fa-file-pdf")
            if is_document_file_code(ext):
                return ("code", "fa fa-file-code")
            if is_document_file_text(ext):
                return ("text", "fa fa-file-alt")
            if is_document_file_sheet(ext):
                return ("sheet", "fa fa-file-excel")
            if is_document_file_zip(ext):
                return ("zip", "fa fa-file-archive")
            return ("file", "fa fa-file")
        return ("file", "fa fa-file")

    @property
    def get_team_users(self):
        team_user_ids = list(self.teams.values_list("users__id", flat=True))
        return Profile.objects.filter(id__in=team_user_ids)

    @property
    def get_team_and_assigned_users(self):
        team_user_ids = list(self.teams.values_list("users__id", flat=True))
        assigned_user_ids = list(self.shared_to.values_list("id", flat=True))
        user_ids = team_user_ids + assigned_user_ids
        return Profile.objects.filter(id__in=user_ids)

    @property
    def get_assigned_users_not_in_teams(self):
        team_user_ids = list(self.teams.values_list("users__id", flat=True))
        assigned_user_ids = list(self.shared_to.values_list("id", flat=True))
        user_ids = set(assigned_user_ids) - set(team_user_ids)
        return Profile.objects.filter(id__in=list(user_ids))

    @property
    def created_on_arrow(self):
        return arrow.get(self.created_on).humanize()


def generate_key():
    return binascii.hexlify(os.urandom(8)).decode()


class APISettings(models.Model):
    title = models.TextField()
    apikey = models.CharField(max_length=16, blank=True)
    website = models.URLField(max_length=255, null=True)
    lead_assigned_to = models.ManyToManyField(
        Profile, related_name="lead_assignee_users")
    tags = models.ManyToManyField("accounts.Tags", blank=True)
    created_by = models.ForeignKey(
        Profile,
        related_name="settings_created_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    org = models.ForeignKey(
        Org, blank=True, on_delete=models.SET_NULL, null=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_on",)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.apikey or self.apikey is None or self.apikey == "":
            self.apikey = generate_key()
        super().save(*args, **kwargs)


class Google(models.Model):
    profile = models.ForeignKey(
        Profile, related_name="google", null=True, on_delete=models.CASCADE)
    google_id = models.CharField(max_length=200, null=True)
    google_url = models.TextField(null=True)
    verified_email = models.CharField(max_length=200, null=True)
    family_name = models.CharField(max_length=200, null=True)
    name = models.CharField(max_length=200, null=True)
    gender = models.CharField(max_length=10, null=True)
    dob = models.CharField(max_length=50, null=True)
    given_name = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True, db_index=True)

    def __str__(self):
        return self.email
