# -*- coding: utf-8 -*-
"""
Forms used for managing user profile:

* update profile
* change password
"""
from __future__ import unicode_literals

from django import forms

from captcha.fields import ReCaptchaField
from crispy_forms.layout import Layout, Fieldset, HTML
from django.contrib.auth.forms import PasswordChangeForm
from timezone_field import TimeZoneFormField

from trapper.apps.accounts.models import UserProfile
from trapper.apps.research.models import ResearchProject
from trapper.apps.research.taxonomy import ResearchProjectRoleType
from trapper.apps.media_classification.models import ClassificationProject
from trapper.apps.media_classification.taxonomy import ClassificationProjectRoleLevels
from trapper.apps.common.forms import BaseCrispyModelForm, CrispyFormMixin
from trapper.apps.common.widgets import DisabledTextInput


class TrapperSignupForm(forms.Form):
    """Add a captcha field to a standard allauth signup form"""
    captcha = ReCaptchaField()

    def signup(self, request, user):
        """ Required, or else it throws deprecation warnings """
        pass


class UserProfileForm(BaseCrispyModelForm):
    """Form used to update user profile"""

    email = forms.EmailField(
        max_length=255, required=False, widget=DisabledTextInput()
    )
    username = forms.CharField(
        max_length=255, required=False, widget=DisabledTextInput()
    )
    first_name = forms.CharField(max_length=255, required=False)
    last_name = forms.CharField(max_length=255, required=False)

    class Meta:
        model = UserProfile
        exclude = ['user']

    def get_avatar(self):
        """Prepare img tag containing user avatar"""
        username = self.initial.get('username', None)
        avatar_image = self.initial.get('avatar_image', None)
        if username and avatar_image:
            html = (
                '<div class="form-group"><img src="{url}" alt="{user}" '\
                'class="img-thumbnail avatar-big"></div>'.format(
                    url=avatar_image,
                    user=username
                )
            )
        else:
            html = ''
        return HTML(html)

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'email',
                'username',
                'first_name',
                'last_name',
                'institution',
                'about_me',
                'system_notifications',
                'avatar',
                self.get_avatar(),
                ),
            )

    def save(self, commit=True):
        """
        Handle updating :class:accounts.UserProfile
        :param commit: if set to True then changes are saved to database
        :return: `:class:accounts.UserProfile`
        """
        user_fields = ['first_name', 'last_name']
        instance = super(UserProfileForm, self).save(commit=True)
        user = instance.user
        for field in user_fields:
            setattr(user, field, self.cleaned_data.get(field, None))
            user.save()
        return instance


class UserProfilePasswordChangeForm(CrispyFormMixin, PasswordChangeForm):
    """Form used to change user password"""

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'old_password',
                'new_password1',
                'new_password2',
            ),
        )


class UserProfileSetTimezoneForm(CrispyFormMixin, forms.Form):
    timezone = TimeZoneFormField(
        help_text='Set your working timezone',
    )


class AdminSetUserRolesForm(forms.Form):

    _selected_action = forms.CharField(
        widget=forms.MultipleHiddenInput
    )
    rproject = forms.ModelMultipleChoiceField(
        queryset=ResearchProject.objects.all(),
        required=False
    )
    rproject_role = forms.ChoiceField(
        choices=ResearchProjectRoleType.CHOICES,
        required=False, initial=3
    )
    cproject = forms.ModelMultipleChoiceField(
        queryset=ClassificationProject.objects.all(),
        required=False
    )
    cproject_role = forms.ChoiceField(
        choices=ClassificationProjectRoleLevels.CHOICES,
        required=False, initial=3
    )
    activate_all = forms.BooleanField(required=False)


class AdminMailUsersForm(forms.Form):

    _selected_action = forms.CharField(
        widget=forms.MultipleHiddenInput
    )
    subject = forms.CharField(
        widget=forms.TextInput(
            attrs={'maxlength':150, 'class':'vTextField'}
        )
    )
    text = forms.CharField(
        widget=forms.Textarea()
    )
