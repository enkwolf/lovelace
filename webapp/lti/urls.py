from django.urls import path

from . import views
app_name = "lovelace_lti"

urlpatterns = [
    path("assignment-success/", views.SuccessView.as_view(), name="assignment-success"),
    path("assignment/", views.LTIAssignmentView.as_view(), name="content"),
    path("assignment/test/", views.LTITestAssignmentView.as_view()),
    path("assignment/<course:course>/<instance:instance>/<content:content>/<revision:revision>/check/", views.LTICheckAnswer.as_view(), name="check"),
    path("assignment/<course:course>/<instance:instance>/<content:content>/<revision:revision>/progress/<slug:task_id>/", views.LTICheckProgress.as_view(), name="check_progress")
]