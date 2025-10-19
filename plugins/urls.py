from django.urls import path
from . import views

app_name = 'plugins'

urlpatterns = [
    # Plugin Management
    path('', views.plugin_list, name='plugin_list'),
    path('upload/', views.upload_plugin, name='upload_plugin'),
    path('reload/', views.reload_plugins, name='reload_plugins'),
    path('<int:plugin_id>/', views.plugin_detail, name='plugin_detail'),
    path('<int:plugin_id>/update/', views.update_plugin, name='update_plugin'),
    path('<int:plugin_id>/toggle/', views.toggle_plugin, name='toggle_plugin'),
    path('<int:plugin_id>/approve/', views.approve_plugin, name='approve_plugin'),
    path('<int:plugin_id>/reject/', views.reject_plugin, name='reject_plugin'),
    path('<int:plugin_id>/permission/<int:permission_id>/toggle/', views.toggle_permission, name='toggle_permission'),
    path('<int:plugin_id>/uninstall/', views.uninstall_plugin, name='uninstall_plugin'),
    path('dashboard/widgets/', views.get_dashboard_widgets, name='get_dashboard_widgets'),
]