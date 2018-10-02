# -*- coding: utf-8 -*-
"""
Views used to handle logic related to research project management in research
application
"""
from __future__ import unicode_literals

from django.conf import settings
from django.views import generic
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.core.urlresolvers import reverse
from django.core.mail import mail_admins

from braces.views import JSONResponseMixin, UserPassesTestMixin
from extra_views import (
    CreateWithInlinesView, UpdateWithInlinesView, NamedFormsetsMixin
)

from trapper.apps.research.models import (
    ResearchProject, ResearchProjectCollection
)
from trapper.apps.research.forms import (
    ResearchProjectForm, ProjectCollectionForm, ProjectRoleInline,
)
from trapper.apps.storage.models import Collection
from trapper.apps.common.views import LoginRequiredMixin, BaseDeleteView
from trapper.apps.storage.views.collection import CollectionGridContextMixin
from trapper.apps.media_classification.views.projects import (
    ClassificationProjectGridContextMixin
)
from trapper.apps.common.tools import parse_pks


class ResearchProjectGridContextMixin(object):
    """Mixin used with views that use any collection listing
    for changing list behaviour.
    This mixin can be used to:

    * tags used in filters
    """

    def get_resource_context(self, **kwargs):
        """Build resource context"""
        context = {
        }
        return context


class ResearchProjectListView(LoginRequiredMixin, generic.TemplateView):
    """View used for rendering template with research projects grid."""

    model = ResearchProject
    template_name = 'research/project_list.html'

    def get_context_data(self, **kwargs):
        """All we need to render base grid is:
        * Model name as title
        * Base context to build filters

        This view is not serving any data. Data is read using DRF API
        """
        research_project_context = {
            'data_url': reverse('research:api-research-project-list'),
            'keywords': ResearchProject.keywords.values_list('pk', 'name'),
            'model_name': 'research projects',
            'update_redirect': 'true',
        }
        return {
            'research_project_context': research_project_context
        }

view_research_project_list = ResearchProjectListView.as_view()


class ResearchProjectDetailView(
    UserPassesTestMixin,
    generic.DetailView,
    CollectionGridContextMixin,
    ClassificationProjectGridContextMixin
):
    """View used for rendering details of specified research project.

    Research projects are accessible to everyone, but anonymous users
    can see limited version of details

    This view uses

    * :class:`apps.storage.views.collection.CollectionGridContextMixin`
      for altering behaviour collection grid rendered in details
    * :class:`apps.media_classification.views.projects.ClassificationProjectGridContextMixin`
      for altering behaviour classification projects grid rendered in details
    """

    template_name = 'research/project_detail.html'
    model = ResearchProject
    raise_exception = True
    context_object_name = 'research_project'

    def test_func(self, user):
        """Details are available only if project is accepted"""
        return self.get_object().status

    def get_collection_delete_url(self, **kwargs):
        """Return standard url used for removing multiple collections"""
        return reverse('research:project_collection_delete_multiple')

    def get_collection_url(self, **kwargs):
        """Alter url for collections DRF API, to get only collections that
        belongs to research project and are accessible for currently logged in
        user"""
        research_project = kwargs.get('research_project')
        return '{url}?project={pk}'.format(
            url=reverse('research:api-research-project-collection-list'),
            pk=research_project.pk
        )

    def get_classification_project_url(self, **kwargs):
        """Return standard url used for classification project list limited
        to those, which are related to given research project"""
        research_project = kwargs.get('research_project')
        return '{url}?research_project={pk}'.format(
            url=reverse(
                'media_classification:api-classification-project-list'
            ),
            pk=research_project.pk
        )

    def get_context_data(self, **kwargs):
        """
        Alter context data used for research projects details:

        * for collection context:

            * hide add research project
            * hide filter research project
            * set collection primary key field
            * hide collection delete action
            * hide collection update action

        * for classification project:

            * hide research project column in grid
            * hide classification project delete action
            * hide classification project update action
        """
        context = super(
            ResearchProjectDetailView, self
        ).get_context_data(**kwargs)
        context['collection_context'] = self.get_collection_context(
            research_project=context['object']
        )
        context['collection_context']['hide_add_research_project'] = True
        context['collection_context']['hide_filter_research_project'] = True
        context['collection_context']['collection_field'] = 'collection_pk'
        context['collection_context']['hide_collection_delete'] = True
        context['collection_context']['hide_collection_update'] = True

        classification_key = 'classification_project_context'
        context[classification_key] = self.get_classification_project_context(
            research_project=context['object']
        )
        context[classification_key]['hide_research_project_col'] = True
        project_delete_key = 'hide_classification_project_delete'
        project_update_key = 'hide_classification_project_update'
        context[classification_key][project_delete_key] = True
        context[classification_key][project_update_key] = True
        return context


view_research_project_detail = ResearchProjectDetailView.as_view()


class ProjectCreateView(
    LoginRequiredMixin, CreateWithInlinesView, NamedFormsetsMixin
):

    """Research project's create view.
    Handle the creation of the :class:`apps.research.models.ResearchProject`
    objects.
    """
    model = ResearchProject
    form_class = ResearchProjectForm
    template_name = 'research/project_change.html'
    inlines = [ProjectRoleInline]
    inlines_names = ['projectrole_formset', ]
    success_url = reverse_lazy('research:project_list')

    def forms_valid(self, form, inlines):
        """If form is valid then set `owner` as currently logged in user,
        and add message that project has been created"""

        user = self.request.user
        form.instance.owner = user
        self.object = form.save(commit=False)
        self.object.save()
        self.object.keywords.clear()
        for keyword in form.cleaned_data['keywords']:
            self.object.keywords.add(keyword)
        projectrole_formset = inlines[0]
        projectrole_formset.save()

        # display a message to a user
        messages.add_message(
            self.request,
            messages.SUCCESS,
            'Your new research project has been successfully added! '
            'However, it needs to be activated by the administrators. '
            'When this is done we will notify you immediately.'
        )
        # notify admins
        if settings.EMAIL_NOTIFICATIONS_RESEARCH_PROJECT:
            mail_admins(
                'New request for Trapper research project',
                'The following research project needs your verification: {url}.'.format(
                    url=self.object.get_admin_url()
                )
            )

        return super(ProjectCreateView, self).form_valid(form)

    def forms_invalid(self, form, inlines):
        """If form is not valid it is re-rendered with error details."""
        messages.add_message(
            self.request,
            messages.ERROR,
            'Error creating new project'
        )
        return super(ProjectCreateView, self).forms_invalid(form, inlines)

view_research_project_create = ProjectCreateView.as_view()


class ProjectUpdateView(
    LoginRequiredMixin, UserPassesTestMixin, UpdateWithInlinesView,
    NamedFormsetsMixin, JSONResponseMixin
):
    """Research project's update view.
    Handle the update of the :class:`apps.research.models.ResearchProject`
    objects.
    """

    model = ResearchProject
    form_class = ResearchProjectForm
    template_name = 'research/project_change.html'
    inlines = [ProjectRoleInline]
    inlines_names = ['projectrole_formset', ]
    raise_exception = True

    def test_func(self, user):
        """Update is available only for users that have enough permissions"""
        return self.get_object().can_update(user)

    def forms_valid(self, form, inlines):
        self.object = form.save(commit=False)
        self.object.save()
        self.object.keywords.clear()
        for keyword in form.cleaned_data['keywords']:
            self.object.keywords.add(keyword)
        projectrole_formset = inlines[0]
        projectrole_formset.save()
        
        messages.add_message(
            self.request,
            messages.SUCCESS,
            'Research project <strong>{name}</strong> has been '
            'successfully updated.'.format(
                name=form.instance.acronym
            )
        )
        return HttpResponseRedirect(self.object.get_absolute_url())

    def forms_invalid(self, form, inlines):
        messages.add_message(
            self.request,
            messages.ERROR,
            'Your form contains errors.'
        )
        return super(ProjectUpdateView, self).forms_invalid(form, inlines)

view_research_project_update = ProjectUpdateView.as_view()


class ProjectDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    research projects.

    Only projects that user has enough permissions for can be deleted
    """

    model = ResearchProject
    redirect_url = 'research:project_list'


view_research_project_delete = ProjectDeleteView.as_view()


class ProjectCollectionAddView(
    LoginRequiredMixin, generic.View, JSONResponseMixin
):
    """
    View used to add collections to existing research project

    User is required to have at least project update permissions to
    add collections, and each collection has to be accessible by user.
    """
    raise_exception = True
    form = ProjectCollectionForm

    def get_project(self):
        try:
            project = ResearchProject.objects.get(
                pk=self.request.POST.get('research_project', None)
            )
        except ResearchProject.DoesNotExist:
            project = None
        else:
            if not project.can_update(user=self.request.user):
                project = None
        return project

    def get_collections(self):
        """Get list of collection pks's from `request.POST.pks` and
        return all collections that are accessible for user"""
        collection_pks = parse_pks(self.request.POST.get('pks', ''))
        collections = Collection.objects.get_accessible(
            user=self.request.user
        ).filter(pk__in=collection_pks)
        return collections

    def post(self, request, *args, **kwargs):
        """
        `request.POST` method is used to append multiple collections
        to research project in single request using AJAX.

        List of collections pks is passed in `pks` key as list of integers
        separated by comma.

        Before append, all collections pks are validated if user can view
        them and only those, which user has enough permissions for, are
        added to project.

        Response contains status of update and list of collections pks that
        were removed.
        """
        context = {'status': True, 'msg': '', 'added': []}

        project = self.get_project()
        if project is not None:
            collections = self.get_collections()
            if collections is not None:
                for collection in collections:
                    project_collection, created = \
                        ResearchProjectCollection.objects.get_or_create(
                            project=project,
                            collection=collection
                        )
                    if created:
                        context['added'].append(project_collection.pk)
            else:
                context['status'] = False
                context['msg'] = 'No suitable collections found'
        else:
            context['status'] = False
            context['msg'] = 'Invalid project, or not enough permissions'

        return self.render_json_response(context_dict=context)


view_research_project_collection_add = ProjectCollectionAddView.as_view()


class ProjectCollectionDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    research project collections.

    Only collections that user has enough permissions for can be deleted
    """
    model = ResearchProjectCollection
    success_msg_tmpl = (
        'Research project collection "{name}" has been deleted'
    )
    fail_msg_tmpl = (
        'You cannot remove research project collection "{name}"'
    )
    redirect_url = 'research:project_list'

    def filter_editable(self, queryset, user):
        """Overwrite this method to check if user is an admin of a project
        that selected collections belong to"""
        to_delete = []
        for obj in queryset:
            if obj.can_delete(user):
                to_delete.append(obj)
        return to_delete

    def bulk_delete(self, queryset):
        for obj in queryset:
            obj.delete()

    def add_message(self, status, template, item):
        """ResearchProjectCollection has no `name` attribute so we have
        to overwrite this method"""
        messages.add_message(
            self.request,
            status,
            template.format(name=item.collection.name)
        )

view_research_project_collection_delete = ProjectCollectionDeleteView.as_view()
