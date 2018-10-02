# -*- coding:utf-8 -*-
from django.conf.urls import url, include
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy

from rest_framework.routers import DefaultRouter
from rest_framework.urlpatterns import format_suffix_patterns

from trapper.apps.media_classification.views import (
    api as classification_api_views
)
from trapper.apps.media_classification.views import (
    classifications as classifications_views,
    user_classifications as user_classifications_views,
    projects as projects_views,
    classificators as classificators_views,
    sequences as sequences_views 
)


router = DefaultRouter(trailing_slash=False)

router.register(
    r'classificators',
    classification_api_views.ClassificatorViewSet,
    base_name='api-classificator'
)

router.register(
    r'user-classifications',
    classification_api_views.UserClassificationViewSet,
    base_name='api-user-classification'
)

router.register(
    r'classifications',
    classification_api_views.ClassificationViewSet,
    base_name='api-classification'
)

router.register(
    r'classifications_map',
    classification_api_views.ClassificationMapViewSet,
    base_name='api-classification-map'
)

router.register(
    r'classification-projects',
    classification_api_views.ClassificationProjectViewSet,
    base_name='api-classification-project'
)

router.register(
    r'classification-project-collections',
    classification_api_views.ClassificationProjectCollectionViewSet,
    base_name='api-classification-project-collection'
)

router.register(
    r'sequences',
    classification_api_views.SequenceViewSet,
    base_name='api-sequence'
)

router.register(
    r'classification/(?P<collection_pk>\d+)/(?P<current_resource_pk>\d+)/resources/$',
    classification_api_views.ClassificationResourcesViewSet,
    base_name='api-classification-resources'
)

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(
        r'^api/classifications/results/(?P<project_pk>\d+)/',
        classification_api_views.ClassificationResultsView.as_view(),
        name='api-classification-results'
    ),
    url(
        r'^api/classifications/results/agg/(?P<project_pk>\d+)/',
        classification_api_views.ClassificationResultsAggView.as_view(),
        name='api-classification-results-agg'
    ),
    url(
        r'^api/classifications/import',
        classification_api_views.ClassificationImport.as_view(),
        name='api-classification-import'
    )
]

urlpatterns += [

    url(
        r'^$',
        RedirectView.as_view(
            url=reverse_lazy('media_classification:project_list')
        ),
        name='project_index'
    ),

    # Project views
    url(
        r'project/list/$',
        projects_views.view_project_list, 
        name='project_list'
    ),
    url(
        r'project/detail/(?P<pk>\d+)/$',
        projects_views.view_project_detail,
        name='project_detail'
    ),

    url(
        r'project/create/$', 
        projects_views.view_project_create,
        name='project_create'
    ),
    url(
        r'project/update/(?P<pk>\d+)/$', 
        projects_views.view_project_update,
        name='project_update'
    ),
    url(
        r'project/delete/(?P<pk>\d+)/$',
        projects_views.view_project_delete,
        name='project_delete'
    ),
    url(
        r'^project/delete/$',
        projects_views.view_project_delete,
        name='project_delete_multiple'
    ),
    url(
        r'project/collection/add/$',
        projects_views.view_project_collection_add,
        name='project_collection_add'
    ),
    url(
        r'project/collection/delete/(?P<pk>\d+)/$',
        projects_views.view_project_collection_delete,
        name='project_collection_delete'
    ),
    url(
        r'^project/collection/delete/$',
        projects_views.view_project_collection_delete,
        name='project_collection_delete_multiple'
    ),

    # Classificator views
    url(
        r'classificator/list/$', 
        classificators_views.view_classificator_list,
        name='classificator_list'
    ),
    url(
        r'classificator/detail/(?P<pk>\d+)/$',
        classificators_views.view_classificator_detail, 
        name='classificator_detail'
    ),

    url(
        r'classificator/create/$', 
        classificators_views.view_classificator_create,
        name='classificator_create'
    ),
    url(
        r'classificator/update/(?P<pk>\d+)/$',
        classificators_views.view_classificator_update,
        name='classificator_update'
    ),
    url(
        r'classificator/clone/(?P<pk>\d+)/$',
        classificators_views.view_classificator_clone,
        name='classificator_clone'
    ),
    url(
        r'^classificator/delete/(?P<pk>\d+)/$',
        classificators_views.view_classificator_delete,
        name='classificator_delete'
    ),
    url(
        r'^classificator/delete/$',
        classificators_views.view_classificator_delete,
        name='classificator_delete_multiple'
    ),

    # Sequence views
    url(
        r'sequence/create/$',
        sequences_views.view_sequence_change,
        name='sequence_create'
    ),
    url(
        r'sequence/update/$',
        sequences_views.view_sequence_change,
        name='sequence_update'
    ),
    url(
        r'sequence/change/$',
        sequences_views.view_sequence_change,
        name='sequence_change'
    ),
    url(
        r'sequence/delete/$',
        sequences_views.view_sequence_delete,
        name='sequence_delete'
    ),
    url(
        r'^sequence/build/$',
        sequences_views.view_sequence_build,
        name='sequence_build'
    ),

    # Classification views
    url(
        r'classification/detail/(?P<pk>\d+)/$',
        classifications_views.view_classification_detail,
        name='classification_detail'
    ),
    url(
        r'^classification/list/(?P<pk>\d+)/$',
        classifications_views.view_classification_list,
        name='classification_list'
    ),
    url(
        r'classification/import/$',
        classifications_views.view_classification_import,
        name='classification_import'
    ),
    url(
        r'classification/import/(?P<pk>\d+)/$',
        classifications_views.view_classification_import,
        name='classification_import'
    ),
    url(
        r'classification/export/(?P<pk>\d+)/$',
        classifications_views.view_classification_export,
        name='classification_export'
    ),
    url(
        r'classification/form/(?P<pk>\d+)/$',
        classifications_views.view_classification_tag,
        name='classification_tag'
    ),
    url(
        r'classification/delete/(?P<pk>\d+)/$',
        classifications_views.view_classification_delete,
        name='classification_delete'
    ),
    url(
        r'classification/delete/$',
        classifications_views.view_classification_delete,
        name='classification_delete_multiple'
    ),
    url(
        r'classify/(?P<project_pk>\d+)/(?P<collection_pk>\d+)/$',
        classifications_views.view_classify_collection,
        name='classify_collection'
    ),
    url(
        r'classify/(?P<pk>\d+)/$',
        classifications_views.view_classify_resource,
        name='classify'
    ),
    url(
        r'classify/(?P<pk>\d+)/user/(?P<user_pk>\d+)/$',
        classifications_views.view_classify_resource,
        name='classify_user'
    ),
    url(
        r'classify/approve/(?P<pk>\d+)/$',
        classifications_views.view_classify_approve,
        name='classify_approve'
    ),

    # UserClassification views
    url(
        r'user_classification/list/(?P<pk>\d+)/$',
        user_classifications_views.view_user_classification_list,
        name='user_classification_list'
    ),
    url(
        r'user_classification/approve/(?P<pk>\d+)/$',
        user_classifications_views.view_user_classification_bulk_approve,
        name='user_classification_bulk_approve'
    )

]


