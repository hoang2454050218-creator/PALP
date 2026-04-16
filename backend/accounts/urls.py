from django.urls import path
from . import views
from . import export_views

app_name = "accounts"

urlpatterns = [
    path("login/", views.CustomTokenObtainPairView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("token/refresh/", views.TokenRefreshCookieView.as_view(), name="token-refresh"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("consent/", views.ConsentView.as_view(), name="consent"),
    path("classes/", views.StudentClassListView.as_view(), name="class-list"),
    path("classes/<int:class_id>/students/", views.ClassStudentsView.as_view(), name="class-students"),
    path("export/my-data/", export_views.ExportMyDataView.as_view(), name="export-my-data"),
    path("export/class/<int:class_id>/", export_views.ExportClassDataView.as_view(), name="export-class"),
    path("delete-my-data/", export_views.DeleteMyDataView.as_view(), name="delete-my-data"),
]
