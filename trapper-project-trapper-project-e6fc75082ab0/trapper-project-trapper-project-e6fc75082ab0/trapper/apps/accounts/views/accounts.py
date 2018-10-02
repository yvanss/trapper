# -*- coding: utf-8 -*-
"""
Module contains logic related to rendering pages related to user profile
like own profile form, password change or dashboard that is displayed
after user is logged in
"""
from __future__ import unicode_literals

import os
import datetime
from djcelery.models import TaskState, TaskMeta

from django.views import generic
from django.shortcuts import render, get_object_or_404, redirect
from django.core.urlresolvers import reverse, reverse_lazy
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.utils import timezone

from trapper.apps.accounts.models import (
    UserProfile, UserTask, UserDataPackage
)
from trapper.apps.accounts.forms import (
    UserProfileForm, UserProfilePasswordChangeForm,
    UserProfileSetTimezoneForm
)
from trapper.apps.messaging.models import Message
from trapper.apps.common.views import LoginRequiredMixin
from trapper.apps.storage.models import Collection
from trapper.apps.research.models import ResearchProject
from trapper.apps.research.taxonomy import ResearchProjectRoleType
from trapper.apps.media_classification.models import ClassificationProject
from trapper.apps.media_classification.taxonomy import ClassificationProjectRoleLevels
from trapper.apps.accounts.taxonomy import StateSettings
from trapper.apps.dashboard.models import DashboardButton
from trapper.celery_app import app
from trapper.apps.sendfile.views import BaseServeFileView


class MainIndexView(generic.TemplateView):
    """Display welcome message for anonymous users or redirect to
    dashboard"""
    template_name = 'index.html'

    def dispatch(self, request, *args, **kwargs):
        """If user is logged in then redirect to dashboard, otherwise show
        index page for non-logged in users"""
        if request.user.is_authenticated():
            response = redirect(
                reverse_lazy('accounts:dashboard')
            )
        else:
            response = super(
                MainIndexView, self
            ).dispatch(request, *args, **kwargs)
        return response

view_index = MainIndexView.as_view()


class ForumView(LoginRequiredMixin, generic.TemplateView):
    """"""
    template_name = 'forum.html'

view_forum = ForumView.as_view()


class MineProfileView(LoginRequiredMixin, generic.View):
    """Handle currently logged in user profile:
    * update user details
    * change password
    """
    profile_form_class = UserProfileForm
    password_form_class = UserProfilePasswordChangeForm
    set_timezone_form_class = UserProfileSetTimezoneForm

    @staticmethod
    def response_redirect():
        """Redirect back to user profile"""
        return redirect(reverse('accounts:mine_profile'))

    def response_render(self, context):
        """Render forms with given context"""
        return render(self.request, 'accounts/mine_profile.html', context)

    def get_profile(self):
        """Get currently logged user UserProfile instance"""
        return get_object_or_404(UserProfile, user__pk=self.request.user.pk)

    def profile_initial(self, instance):
        """Profile form is combination of AccountProfile and User model
        and it's required to initialize User related data
        """
        user = self.request.user
        initial = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar_image': instance.avatar_url,
        }
        return initial

    def get(self, request, *args, **kwargs):
        """Prepare form instances and redner them"""
        instance = self.get_profile()
        context = {
            'profile_form': self.profile_form_class(
                instance=instance,
                initial=self.profile_initial(instance=instance)
            ),
            'password_form': self.password_form_class(user=request.user),
            'timezone_form': self.set_timezone_form_class(
                initial={
                    'timezone': str(timezone.get_current_timezone())
                }
            )
        }
        return self.response_render(context=context)

    def process_update_profile(self):
        """If UserProfile was submitted then process data and update
        user profile"""
        data = self.request.POST
        instance = self.get_profile()

        form = self.profile_form_class(
            data, files=self.request.FILES, instance=instance
        )
        if form.is_valid():
            form.save()
            messages.add_message(
                self.request,
                messages.SUCCESS,
                'Your profile has been updated'
            )
            response = self.response_redirect()
        else:
            context = {
                'profile_form': form,
                'password_form': self.password_form_class(
                    user=self.request.user,
                ),
                'timezone_form': self.set_timezone_form_class()
            }
            messages.add_message(
                self.request,
                messages.ERROR,
                'Some errors occurred while updating your profile'
            )
            response = self.response_render(context=context)
        return response

    def process_change_password(self):
        """If change password form was sent then work with password"""
        data = self.request.POST
        form = self.password_form_class(self.request.user, data)

        if form.is_valid():
            form.save()
            messages.add_message(
                self.request,
                messages.SUCCESS,
                'Your password has been updated'
            )
            response = self.response_redirect()
        else:
            instance = self.get_profile()
            context = {
                'profile_form': self.profile_form_class(
                    instance=instance,
                    initial=self.profile_initial(instance=instance)
                ),
                'password_form': form,
                'timezone_form': self.set_timezone_form_class()
            }
            messages.add_message(
                self.request,
                messages.ERROR,
                'Some errors occurred while updating your password'
            )
            response = self.response_render(context=context)
        return response

    def process_set_timezone(self):
        """If set timezone form was sent then process it"""
        data = self.request.POST
        form = self.set_timezone_form_class(data)

        if form.is_valid():
            self.request.session['django_timezone'] = str(form.cleaned_data['timezone'])
            messages.add_message(
                self.request,
                messages.SUCCESS,
                'You have successfully set your working timezone'
            )
            response = self.response_redirect()
        else:
            instance = self.get_profile()
            context = {
                'profile_form': self.profile_form_class(
                    instance=instance,
                    initial=self.profile_initial(instance=instance)
                ),
                'password_form': self.password_form_class(
                    user=self.request.user,
                ),
                'timezone_form': form
            }
            messages.add_message(
                self.request,
                messages.ERROR,
                'Some errors occurred while setting your working timezone'
            )
            response = self.response_render(context=context)
        return response

    def post(self, request, *args, **kwargs):
        """Determine what action should be taken and run it"""
        if 'update-profile' in request.POST:
            response = self.process_update_profile()
        elif 'change-password' in request.POST:
            response = self.process_change_password()
        elif 'set-timezone' in request.POST:
            response = self.process_set_timezone()
        else:
            response = self.response_redirect()
        return response


view_mine_profile = MineProfileView.as_view()


class UserProfileView(generic.TemplateView):
    """Display profile of given username"""
    template_name = 'accounts/user_profile.html'

    @staticmethod
    def get_profile(username):
        """Get currently logged user UserProfile instance"""
        return get_object_or_404(UserProfile, user__username=username)

    def get_context_data(self, **kwargs):
        """Update context with profile information"""
        context = super(UserProfileView, self).get_context_data(**kwargs)
        username = kwargs.get('username', None)
        context['profile'] = self.get_profile(username=username)
        return context

view_user_profile = UserProfileView.as_view()


class DashboardView(LoginRequiredMixin, generic.TemplateView):
    """Summarize most important data in single a page - dashboard"""

    template_name = 'accounts/dashboard.html'

    def get_messages(self):
        """Get list of first settings.MESSAGE_COUNT messages """
        inbox_messages = Message.objects.filter(
            user_to=self.request.user
        ).select_related(
            'user_from', 'user_from__userprofile'
        )[:settings.MESSAGES_COUNT]
        return inbox_messages

    def get_data_packages(self):
        """Get user's data packages"""
        return UserDataPackage.objects.filter(user=self.request.user)

    def get_classification_projects(self):
        """Get classification projects that current user can access"""
        return ClassificationProject.objects.get_accessible(
            user=self.request.user, crowdsourcing=False
        ).order_by('-date_created')[:5]

    def get_research_projects(self):
        """Get research projects that current user can access"""
        return ResearchProject.objects.get_accessible(
            user=self.request.user,
            role_levels=ResearchProjectRoleType.ANY
        ).order_by('-date_created')[:5]

    @staticmethod
    def _clean_task_name(name):
        """Clean name of task displayed in dashboard from function
        that is passed to celery.
        By default functions start with **celery_**
        All _ and - are converted into spaces to prettify displayed name
        """
        name = name.split('.')[-1].replace(
            '_', ' '
        ).replace(
            '-', ' '
        ).replace('celery', '').strip().capitalize()
        return name

    def get_celery_tasks(self):
        """Get current celery tasks for currently logged in user"""
        user = self.request.user
        # get user tasks ids
        tasks_ids = UserTask.objects.filter(user=user).values_list(
            'task_id', flat=True
        )
        exclude_tasks = [
            'trapper.apps.storage.tasks.celery_update_thumbnails',
        ]
        # get task states
        tasks = TaskState.objects.filter(
            task_id__in=tasks_ids
        ).exclude(name__in=exclude_tasks)
        # get task metas
        metas = TaskMeta.objects.filter(task_id__in=tasks_ids)
        metas = [(k.task_id, k.result) for k in metas]
        metas = dict(metas)

        for task in tasks:
            task.dashboard_name = self._clean_task_name(name=task.name)
            runtime = task.runtime or 0
            task.dashboard_end = (
                task.tstamp + datetime.timedelta(seconds=runtime)
            )
            task.dashboard_status = StateSettings.STATE_MAP[task.state]
            try:
                task.result = metas[task.task_id]
            except KeyError:
                task.result = ''

        return tasks

    @staticmethod
    def get_dashboard_buttons():
        """Get list of dashboard buttons that will be displayed"""
        return DashboardButton.objects.all()

    def get_context_data(self, **kwargs):
        """
        Prepare context that contain detail data for each box in dashboard
        """
        user = self.request.user
        profile = user.userprofile
        return {
            'profile': profile,
            'inbox_messages': self.get_messages(),
            'classification_projects': self.get_classification_projects(),
            'data_packages': self.get_data_packages(),
            'research_projects': self.get_research_projects(),
            'celery_tasks': self.get_celery_tasks(),
            'buttons': self.get_dashboard_buttons()
        }

view_dashbord = DashboardView.as_view()


class CeleryTaskCancelView(generic.View):
    """
    Manage celery tasks from dashboard.
    For now only cancel task is handled
    """

    def post(self, request, *args, **kwargs):
        """If user has any task that can be stoppable, then calling this
        method will stop it and return to dashboard with proper message"""
        lookup = u"'username': '{name}'".format(
            name=self.request.user.username
        )
        task_id = request.POST.get('task_id', None)

        if task_id:
            try:
                task = TaskState.objects.get(
                    kwargs__icontains=lookup,
                    state__in=StateSettings.STOPPABLE,
                    task_id=task_id
                )
            except TaskState.DoesNotExist:
                messages.error(
                    request=request,
                    message=(
                        'There is no stoppable task with id {task_id}'.format(
                            task_id=task_id
                        )
                    )
                )
            else:
                app.control.revoke(task.task_id)
                messages.success(
                    request=request,
                    message='Task {task_id} has been stopped'.format(
                        task_id=task.task_id
                    )
                )
        else:
            messages.error(
                request=request,
                message='Stopping task failed. Incorrect task id'
            )

        return HttpResponseRedirect(reverse('accounts:dashboard'))


view_celery_task_cancel = CeleryTaskCancelView.as_view()


class UserDataPackageDeleteView(generic.View):
    """TODO: change it a POST delete view
    """

    def get(self, *args, **kwargs):
        pk = kwargs.get('pk', None)
        package = get_object_or_404(UserDataPackage, pk=pk)
        if package.can_delete(self.request.user):
            package.delete()
            messages.success(
                request=self.request,
                message='Data package has been successfully deleted.'
            )
            return HttpResponseRedirect(reverse('accounts:dashboard'))
        else:
            return HttpResponseForbidden()


view_data_package_delete = UserDataPackageDeleteView.as_view()


class DataPackageSendfileMediaView(BaseServeFileView):

    authenticated_only = True

    def access_granted(self, package):
        response = self.serve_file(package.package.name, root=settings.EXTERNAL_MEDIA_URL)
        response["Content-Disposition"] = "attachment; filename={0}".format(
            package.filename()
        )
        return response

    def access_revoked(self):
        return HttpResponseForbidden

    def get(self, *args, **kwargs):
        pk = kwargs.get('pk', None)
        if not (pk):
            raise Http404
        user = self.request.user

        package = get_object_or_404(UserDataPackage, pk=pk)
        if package.user == user:
            response = self.access_granted(
                package
            )
        else:
            response = self.access_revoked()
        return response

view_data_package_sendfile_media = DataPackageSendfileMediaView.as_view()
