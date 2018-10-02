# -*- coding: utf-8 -*-
"""
Views used to handle logic related to classification projects management in
media classification application
"""
from __future__ import unicode_literals

from django.views import generic
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect, HttpResponse

from braces.views import UserPassesTestMixin, JSONResponseMixin

from extra_views import (
    CreateWithInlinesView, UpdateWithInlinesView,
    NamedFormsetsMixin
)

from trapper.apps.common.tools import parse_pks
from trapper.apps.common.views import BaseDeleteView, LoginRequiredMixin
from trapper.apps.media_classification.models import (
    ClassificationProject, ClassificationProjectCollection
)
from trapper.apps.media_classification.forms import (
    ProjectForm, ProjectRoleInline
)
from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectStatus
)
from trapper.apps.storage.views.collection import CollectionGridContextMixin
from trapper.apps.research.models import ResearchProjectCollection

User = get_user_model()


class ClassificationProjectGridContextMixin(object):
    """Mixin used with views that use any classificator listing
    for changing list behaviour.
    This mixin can be used to:

    * change classification project url (i.e. add filtering)
    """

    def get_classification_project_url(self, **kwargs):
        """Return standard DRF API url for classification projects"""
        return reverse('media_classification:api-classification-project-list')

    def get_classification_project_context(self, **kwargs):
        """Build classification project context"""
        context = {
            'data_url': self.get_classification_project_url(
                **kwargs
            ),
            'model_name': "classification projects",
            'update_redirect': 'true',
        }

        return context


class ProjectListView(
    LoginRequiredMixin, generic.ListView, ClassificationProjectGridContextMixin
):
    """List view of the
    :class:`apps.media_classification.models.ClassificationProject` instances.

    Only classification project that user has enough permissions to view
    are displayed.

    Anonymous users can see only projects that have crowdsourcing enabled.
    """

    model = ClassificationProject
    context_object_name = 'projects'
    template_name = 'media_classification/projects/list.html'

    def get_context_data(self, **kwargs):
        """Update context used to render template with classificator context
        and owners used for filtering"""
        project_context = self.get_classification_project_context()
        context = {
            'classification_project_context': project_context,
        }
        return context

    def get_queryset(self, *args, **kwargs):
        """Limit classification project only to those, which user can view
        details for"""
        base_queryset = super(ProjectListView, self).get_queryset()
        projects = self.model.objects.get_accessible(
            user=self.request.user, base_queryset=base_queryset
        )
        return projects


view_project_list = ProjectListView.as_view()


class ProjectDetailView(
    LoginRequiredMixin, UserPassesTestMixin, generic.DetailView,
    CollectionGridContextMixin
):
    """View used for rendering details of specified classification project.
    User is required to have enough permissions to view project details.
    """
    model = ClassificationProject
    context_object_name = 'project'
    template_name = 'media_classification/projects/detail.html'
    raise_exception = True

    def test_func(self, user):
        """Verify that user has enough permissions to view details"""
        return self.get_object().can_view(user)

    def get_collection_url(self, **kwargs):
        """Alter url for collections DRF API, to get only collections that
        belongs to research project and are accessible for currently logged in
        user"""
        classification_project = kwargs.get('classification_project')
        return '{url}?project={pk}'.format(
            url=reverse(
                'media_classification:api-classification-project-collection-list'
            ),
            pk=classification_project.pk
        )

    def get_context_data(self, **kwargs):
        """Update context data with owners of classification projects
        for filtering"""
        context = super(ProjectDetailView, self).get_context_data(**kwargs)

        context['collection_context'] = self.get_collection_context(
            classification_project=context['object']
        )
        context['collection_context']['collection_field'] = 'collection_pk'
        context['collection_context']['hide_delete'] = True
        context['collection_context']['hide_update'] = True
        context['collection_context']['model_name'] = 'project collections'
        context['collection_context']['owners'] = User.objects.filter(
            owned_collections__researchprojectcollection__classificationprojectcollection__isnull=False
        ).distinct()

        return context

view_project_detail = ProjectDetailView.as_view()


class ProjectCreateView(
    LoginRequiredMixin, CreateWithInlinesView, NamedFormsetsMixin
):
    """ClassificationProject's create view.
    Handle the creation of the
    :class:`apps.media_classification.models.ClassificationProject` objects.
    """

    model = ClassificationProject
    form_class = ProjectForm
    template_name = 'media_classification/projects/change.html'
    inlines = [ProjectRoleInline,]
    inlines_names = ['projectrole_formset',]

    def get_form_kwargs(self):
        """List of research project collections that should be assigned to
        created collection are passed through `request.GET.selected` key as
        list of integers separated by comma"""
        kwargs = super(ProjectCreateView, self).get_form_kwargs()
        kwargs['initial']['selected'] = self.request.GET.get('selected', None)
        return kwargs

    def forms_valid(self, form, inlines):
        """If form is valid then set `owner` as currently logged in user,
        and add message that classification project has been created

        After that all roles selected in creation form are saved into database
        """
        self.object = form.save(commit=False)
        self.object.owner = self.request.user
        self.object.save()

        projectrole_formset = inlines[0]
        projectrole_formset.save()

        messages.add_message(
            self.request,
            messages.SUCCESS,
            ('New classification project <strong>{name}</strong> has '
             'been added').format(
                name=form.instance.name
            )
        )
        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, inlines):
        """If form is not valid, form is re-rendered with error details,
        and message about unsuccessfull operation is shown"""
        messages.add_message(
            self.request,
            messages.ERROR,
            'Error creating new classification project'
        )
        return super(ProjectCreateView, self).forms_invalid(form, inlines)


view_project_create = ProjectCreateView.as_view()


class ProjectUpdateView(
    LoginRequiredMixin, UserPassesTestMixin, UpdateWithInlinesView, 
    NamedFormsetsMixin
):
    """ClassificationProject's update view.
    Handle the update of the
    :class:`apps.media_classification.models.ClassificationProject` objects.
    """

    model = ClassificationProject
    form_class = ProjectForm
    template_name = 'media_classification/projects/change.html'
    inlines = [ProjectRoleInline,]
    inlines_names = ['projectrole_formset',]
    raise_exception = True

    def test_func(self, user):
        """Update is available only for users that have enough permissions"""
        return self.get_object().can_update(user)

    def forms_valid(self, form, inlines):
        """If form is valid then set `owner` as currently logged in user,
        and add message that classification project has been created

        After that all roles selected in creation form are saved into database
        """
        self.object = form.save(commit=False)
        self.object.owner = self.request.user
        self.object.save()

        for formset in inlines:
            formset.save()

        messages.add_message(
            self.request,
            messages.SUCCESS,
            ('The classification project <strong>{name}</strong> has '
             'been successfully updated.').format(
                name=form.instance.name
            )
        )
        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, inlines):
        """If form is not valid, form is re-rendered with error details,
        and message about unsuccessfull operation is shown"""
        messages.add_message(
            self.request,
            messages.ERROR,
            'Error updating classification project'
        )
        return super(ProjectUpdateView, self).forms_invalid(form, inlines)

view_project_update = ProjectUpdateView.as_view()


class ProjectDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    classification projects.

    Only projects that user has enough permissions for can be deleted
    """
    model = ClassificationProject
    redirect_url = 'media_classification:project_list'


view_project_delete = ProjectDeleteView.as_view()


class ProjectCollectionDeleteView(BaseDeleteView):
    """View responsible for handling deletion of single or multiple
    classification project collections.

    Only collections that user has enough permissions for can be deleted
    """
    model = ClassificationProjectCollection
    success_msg_tmpl = (
        'Classification project collection "{name}" has been deleted'
    )
    fail_msg_tmpl = (
        'You cannot remove classification project collection "{name}"'
    )
    redirect_url = 'media_classification:project_list'

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
        """ClassificationProjectCollection has no `name` attribute so we have
        to overwrite this method"""
        messages.add_message(
            self.request,
            status,
            template.format(name=item.collection.collection.name)
        )


view_project_collection_delete = ProjectCollectionDeleteView.as_view()


class ProjectCollectionAddView(
    LoginRequiredMixin, generic.View, JSONResponseMixin
):
    """This view is used to append list of research project collections to
    classification project.

    User is required to have project update permission to add collections.
    """
    raise_exception = True

    def get_project(self):
        try:
            project = ClassificationProject.objects.get(
                pk=self.request.POST.get('classification_project', None)
            )
        except ClassificationProject.DoesNotExist:
            project = None
        else:
            if not project.can_update(user=self.request.user):
                project = None
        return project

    def get_collections(self):
        """For given `request.POST.pks` get list of research project
        collections that will be assigned to classification project"""
        collection_pks = parse_pks(pks=self.request.POST.get('pks', ''))
        collections = ResearchProjectCollection.objects.get_accessible(
            user=self.request.user
        ).filter(
            pk__in=collection_pks
        )
        return collections

    def post(self, request, *args, **kwargs):
        """
        Add selected collections to classification project.
        This is possible only if user requestiong action has update
        rights to project and at least access rights to selected
        research project collections.
        """
        context = {'status': True, 'msg': '', 'added': []}

        project = self.get_project()
        if project is not None:
            collections = self.get_collections()
            if collections is not None:
                for collection in collections:
                    project_collection, created = \
                        ClassificationProjectCollection.objects.get_or_create(
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


view_project_collection_add = ProjectCollectionAddView.as_view()
