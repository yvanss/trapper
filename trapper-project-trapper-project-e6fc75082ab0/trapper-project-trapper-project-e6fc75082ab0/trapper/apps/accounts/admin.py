# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.

Admin is used to activate or deactivate accounts
"""

from django.contrib import admin
from django.contrib.auth.models import Permission, ContentType
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.core.mail import send_mail

from trapper.apps.accounts.models import UserProfile, UserTask
from trapper.apps.accounts.forms import AdminSetUserRolesForm, AdminMailUsersForm
from trapper.apps.research.models import ResearchProjectRole
from trapper.apps.media_classification.models import ClassificationProjectRole

User = get_user_model()


class TrapperUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'is_staff', 'is_active', 'date_joined', 'last_login'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active', 'last_login')
    actions = ['set_user_roles_action', 'mail_users_action']

    def set_user_roles_action(self, request, queryset):
        if 'do_action' in request.POST:
            form = AdminSetUserRolesForm(request.POST)
            if form.is_valid():
                rprojects = form.cleaned_data['rproject']
                rproject_role = form.cleaned_data['rproject_role']
                cprojects = form.cleaned_data['cproject']
                cproject_role = form.cleaned_data['cproject_role']
                activate_all = form.cleaned_data['activate_all']
                for user in queryset:
                    if activate_all and not user.is_active:
                        user.is_active = True
                        user.save()
                    for rp in rprojects:
                        rpr, created = ResearchProjectRole.objects.get_or_create(
                            user=user, project=rp, 
                            defaults={'name': int(rproject_role)}
                        )
                        if not created:
                            rpr.name = int(rproject_role)
                            rpr.save()
                    for cp in cprojects:
                        cpr, created = ClassificationProjectRole.objects.get_or_create(
                            user=user, classification_project=cp, 
                            defaults={'name': int(cproject_role)}
                        )
                        if not created:
                            cpr.name = int(cproject_role)
                            cpr.save()
                self.message_user(request, 'You have successfully set all the selected user roles.', level=25)
                return
        else:
            form = AdminSetUserRolesForm(
                initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)}
            )

        return render(request, 'admin/accounts/action_set_user_roles.html',
            {'title': u'Set user roles',
             'objects': queryset,
             'form': form})
    set_user_roles_action.short_description = u'Set roles for selected users'

    def mail_users_action(self, request, queryset):
        if 'do_action' in request.POST:
            form = AdminMailUsersForm(request.POST)
            if form.is_valid():
                subject = form.cleaned_data['subject']
                text = form.cleaned_data['text']
                for user in queryset:
                    if user.userprofile.system_notifications:
                        send_mail(
                            subject=subject,
                            message=text,
                            from_email=None,
                            recipient_list=[user.email,],
                            fail_silently=True
                        )

                self.message_user(
                    request, 
                    'You have successfully send an email to selected users.', 
                    level=25
                )
                return
        else:
            form = AdminMailUsersForm(
                initial={'_selected_action': request.POST.getlist(admin.ACTION_CHECKBOX_NAME)}
            )

        return render(request, 'admin/accounts/action_mail_users.html',
            {'title': u'Send an email',
             'objects': queryset,
             'form': form})
    mail_users_action.short_description = u'Send an email to selected users'


admin.site.register(User, TrapperUserAdmin)
admin.site.register(UserProfile)
admin.site.register(UserTask)
admin.site.register(Permission)
admin.site.register(ContentType)
