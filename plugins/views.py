import os
import json
import zipfile
import tempfile
import shutil
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.forms import modelformset_factory

from .models import Plugin, PluginPermission
from .plugin_manager import plugin_manager
from .forms import PluginUploadForm
from .events import get_dashboard_widgets

@login_required
def plugin_list(request):
    """View to list all installed plugins"""
    plugins = Plugin.objects.all().order_by('name')
    return render(request, 'plugins/list.html', {'plugins': plugins})

@login_required
def plugin_detail(request, plugin_id):
    """View plugin details"""
    plugin = get_object_or_404(Plugin, id=plugin_id)
    
    # Get plugin permissions
    permissions = plugin.permissions.all()
    
    return render(request, 'plugins/detail.html', {
        'plugin': plugin,
        'permissions': permissions
    })

@login_required
def upload_plugin(request):
    """View to upload a new plugin"""
    if request.method == 'POST':
        form = PluginUploadForm(request.POST, request.FILES)
        if form.is_valid():
            plugin_file = request.FILES['plugin_file']
            
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the plugin zip file
                zip_path = os.path.join(temp_dir, plugin_file.name)
                with open(zip_path, 'wb+') as destination:
                    for chunk in plugin_file.chunks():
                        destination.write(chunk)
                
                try:
                    # Extract the zip file
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Look for manifest.json
                    manifest_path = None
                    for root, dirs, files in os.walk(temp_dir):
                        if 'manifest.json' in files:
                            manifest_path = os.path.join(root, 'manifest.json')
                            break
                    
                    if not manifest_path:
                        messages.error(request, 'Invalid plugin: manifest.json not found')
                        return redirect('plugin_list')
                    
                    # Load and validate manifest
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    # Validate required fields
                    required_fields = ['name', 'version', 'description', 'author', 'email']
                    for field in required_fields:
                        if field not in manifest:
                            messages.error(request, f'Invalid manifest: {field} is required')
                            return redirect('plugin_list')
                    
                    # Create plugin directory if it doesn't exist
                    plugins_dir = os.path.join(settings.BASE_DIR, 'plugin_packages')
                    os.makedirs(plugins_dir, exist_ok=True)
                    
                    # Create directory for this plugin
                    plugin_dir = os.path.join(plugins_dir, manifest['name'])
                    if os.path.exists(plugin_dir):
                        import stat
                        
                        # Use onexc callback to handle permission issues (Python 3.12+)
                        def remove_readonly(func, path, exc_info):
                            """Clear the readonly bit and reattempt the removal"""
                            try:
                                os.chmod(path, stat.S_IWRITE)
                                func(path)
                            except Exception:
                                pass
                        
                        shutil.rmtree(plugin_dir, onexc=remove_readonly)
                    
                    # Copy plugin files
                    plugin_source_dir = os.path.dirname(manifest_path)
                    shutil.copytree(plugin_source_dir, plugin_dir)
                    
                    # Get entry point and plugin class
                    entry_point = manifest.get('entry_point', 'main.py')
                    plugin_class = manifest.get('plugin_class', None)
                    
                    # Create the plugin in the database
                    plugin = Plugin.objects.create(
                        name=manifest['name'],
                        description=manifest['description'],
                        version=manifest['version'],
                        author=manifest['author'],
                        email=manifest['email'],
                        package_path=plugin_dir,
                        entry_point=entry_point,
                        plugin_class=plugin_class,
                        manifest=manifest,
                        enabled=True,
                        uploaded_by=request.user
                    )
                    
                    # Create permissions
                    if 'permissions' in manifest:
                        for permission in manifest['permissions']:
                            PluginPermission.objects.create(
                                plugin=plugin,
                                permission_name=permission,
                                enabled=False  # Default to disabled for security
                            )
                    
                    # Create and install dependencies
                    if 'dependencies' in manifest and 'packages' in manifest['dependencies']:
                        from .dependency_manager import DependencyManager
                        from .models import PluginDependency
                        
                        dep_manager = DependencyManager(plugin)
                        
                        for package_name, version_spec in manifest['dependencies']['packages'].items():
                            # Create dependency record
                            PluginDependency.objects.create(
                                plugin=plugin,
                                package_name=package_name,
                                version_spec=version_spec,
                                install_status='pending'
                            )
                        
                        # Install all dependencies
                        try:
                            dep_manager.install_dependencies()
                            messages.success(request, f'Dependencies installed for {plugin.name}')
                        except Exception as e:
                            messages.warning(request, f'Error installing dependencies: {str(e)}')
                    
                    # Load the plugin
                    if plugin.enabled:
                        plugin_manager.load_plugin(plugin)
                        
                        # Call plugin_installed hook
                        try:
                            plugin_manager.call_hook('plugin_installed')
                        except Exception as e:
                            messages.warning(request, f"Error in plugin_installed hook: {str(e)}")
                    
                    messages.success(request, f'Plugin {plugin.name} installed successfully')
                    return redirect('plugins:plugin_detail', plugin_id=plugin.id)
                
                except Exception as e:
                    messages.error(request, f'Error installing plugin: {str(e)}')
                    return redirect('plugins:plugin_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PluginUploadForm()
    
    return render(request, 'plugins/upload.html', {'form': form})

@login_required
def update_plugin(request, plugin_id):
    """View to update an existing plugin with a new zip file"""
    plugin = get_object_or_404(Plugin, id=plugin_id)
    
    if request.method == 'POST':
        form = PluginUploadForm(request.POST, request.FILES)
        if form.is_valid():
            plugin_file = request.FILES['plugin_file']
            
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract the plugin zip file
                zip_path = os.path.join(temp_dir, plugin_file.name)
                with open(zip_path, 'wb+') as destination:
                    for chunk in plugin_file.chunks():
                        destination.write(chunk)
                
                try:
                    # Extract the zip file
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Look for manifest.json
                    manifest_path = None
                    for root, dirs, files in os.walk(temp_dir):
                        if 'manifest.json' in files:
                            manifest_path = os.path.join(root, 'manifest.json')
                            break
                    
                    if not manifest_path:
                        messages.error(request, 'Invalid plugin: manifest.json not found')
                        return redirect('plugins:plugin_detail', plugin_id=plugin.id)
                    
                    # Load and validate manifest
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    
                    # Validate required fields
                    required_fields = ['name', 'version', 'description', 'author', 'email']
                    for field in required_fields:
                        if field not in manifest:
                            messages.error(request, f'Invalid manifest: {field} is required')
                            return redirect('plugins:plugin_detail', plugin_id=plugin.id)
                    
                    # Verify plugin name matches
                    if manifest['name'] != plugin.name:
                        messages.error(request, f'Plugin name mismatch. Expected "{plugin.name}" but got "{manifest["name"]}"')
                        return redirect('plugins:plugin_detail', plugin_id=plugin.id)
                    
                    # Unload the plugin if it's enabled
                    was_enabled = plugin.enabled
                    if plugin.enabled:
                        plugin_manager.unload_plugin(plugin.id)
                    
                    # Remove old plugin directory with robust error handling
                    import stat
                    import time
                    
                    if os.path.exists(plugin.package_path):
                        removal_success = False
                        try:
                            # Use onexc callback to handle permission issues (Python 3.12+)
                            def remove_readonly(func, path, exc_info):
                                """Clear the readonly bit and reattempt the removal"""
                                try:
                                    os.chmod(path, stat.S_IWRITE)
                                    func(path)
                                except Exception:
                                    pass
                            
                            shutil.rmtree(plugin.package_path, onexc=remove_readonly)
                            removal_success = True
                        except Exception as e:
                            # If still fails, try to rename the directory and continue
                            try:
                                backup_path = f"{plugin.package_path}_old_{int(time.time())}"
                                os.rename(plugin.package_path, backup_path)
                                messages.warning(request, f"Old plugin files moved to backup: {os.path.basename(backup_path)}")
                                removal_success = True
                            except Exception as rename_error:
                                messages.error(request, f"Error removing old plugin files: {str(e)}")
                                return redirect('plugins:plugin_detail', plugin_id=plugin.id)
                    
                    # Create plugin directory
                    plugins_dir = os.path.join(settings.BASE_DIR, 'plugin_packages')
                    os.makedirs(plugins_dir, exist_ok=True)
                    
                    # Create directory for this plugin
                    plugin_dir = os.path.join(plugins_dir, manifest['name'])
                    
                    # Ensure the target directory doesn't exist (in case of edge cases)
                    if os.path.exists(plugin_dir):
                        try:
                            def remove_readonly(func, path, exc_info):
                                """Clear the readonly bit and reattempt the removal"""
                                try:
                                    os.chmod(path, stat.S_IWRITE)
                                    func(path)
                                except Exception:
                                    pass
                            shutil.rmtree(plugin_dir, onexc=remove_readonly)
                        except Exception:
                            # Last resort: rename it
                            backup_path = f"{plugin_dir}_conflict_{int(time.time())}"
                            os.rename(plugin_dir, backup_path)
                    
                    # Copy new plugin files
                    plugin_source_dir = os.path.dirname(manifest_path)
                    shutil.copytree(plugin_source_dir, plugin_dir)
                    
                    # Get entry point and plugin class
                    entry_point = manifest.get('entry_point', 'main.py')
                    plugin_class = manifest.get('plugin_class', None)
                    
                    # Update the plugin in the database
                    plugin.description = manifest['description']
                    plugin.version = manifest['version']
                    plugin.author = manifest['author']
                    plugin.email = manifest['email']
                    plugin.package_path = plugin_dir
                    plugin.entry_point = entry_point
                    plugin.plugin_class = plugin_class
                    plugin.manifest = manifest
                    plugin.save()
                    
                    # Update permissions - remove old ones and add new ones
                    plugin.permissions.all().delete()
                    if 'permissions' in manifest:
                        for permission in manifest['permissions']:
                            PluginPermission.objects.create(
                                plugin=plugin,
                                permission_name=permission,
                                enabled=False  # Default to disabled for security
                            )
                    
                    # Update dependencies
                    if 'dependencies' in manifest and 'packages' in manifest['dependencies']:
                        from .dependency_manager import DependencyManager
                        from .models import PluginDependency
                        
                        # Remove old dependencies
                        plugin.dependencies.all().delete()
                        
                        dep_manager = DependencyManager(plugin)
                        
                        for package_name, version_spec in manifest['dependencies']['packages'].items():
                            # Create dependency record
                            PluginDependency.objects.create(
                                plugin=plugin,
                                package_name=package_name,
                                version_spec=version_spec,
                                install_status='pending'
                            )
                        
                        # Install all dependencies
                        try:
                            dep_manager.install_dependencies()
                            messages.success(request, f'Dependencies updated for {plugin.name}')
                        except Exception as e:
                            messages.warning(request, f'Error installing dependencies: {str(e)}')
                    
                    # Reload the plugin if it was enabled
                    if was_enabled:
                        plugin.enabled = True
                        plugin.save()
                        plugin_manager.load_plugin(plugin)
                    
                    messages.success(request, f'Plugin {plugin.name} updated successfully to version {plugin.version}')
                    return redirect('plugins:plugin_detail', plugin_id=plugin.id)
                
                except Exception as e:
                    messages.error(request, f'Error updating plugin: {str(e)}')
                    return redirect('plugins:plugin_detail', plugin_id=plugin.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PluginUploadForm()
    
    return render(request, 'plugins/update.html', {'form': form, 'plugin': plugin})

@login_required
def approve_plugin(request, plugin_id):
    """Approve a plugin"""
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can approve plugins')
        return redirect('plugins:plugin_list')
    
    plugin = get_object_or_404(Plugin, id=plugin_id)
    plugin.approve(request.user)
    messages.success(request, f'Plugin {plugin.name} has been approved')
    
    return redirect('plugins:plugin_detail', plugin_id=plugin.id)

@login_required
def reject_plugin(request, plugin_id):
    """Reject a plugin"""
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can reject plugins')
        return redirect('plugins:plugin_list')
    
    plugin = get_object_or_404(Plugin, id=plugin_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'No reason provided')
        plugin.reject(request.user, reason)
        messages.success(request, f'Plugin {plugin.name} has been rejected')
        return redirect('plugins:plugin_list')
    
    return render(request, 'plugins/confirm_reject.html', {'plugin': plugin})

@login_required
def toggle_plugin(request, plugin_id):
    """Enable or disable a plugin"""
    plugin = get_object_or_404(Plugin, id=plugin_id)
    plugin.enabled = not plugin.enabled
    plugin.save()
    
    # Reload plugins to apply changes
    if plugin.enabled:
        plugin_manager.load_plugin(plugin.id)
        messages.success(request, f'Plugin {plugin.name} enabled')
    else:
        plugin_manager.unload_plugin(plugin.id)
        messages.success(request, f'Plugin {plugin.name} disabled')
    
    return redirect('plugins:plugin_detail', plugin_id=plugin.id)

@login_required
def toggle_permission(request, plugin_id, permission_id):
    """Enable or disable a plugin permission"""
    permission = get_object_or_404(PluginPermission, id=permission_id, plugin_id=plugin_id)
    permission.enabled = not permission.enabled
    permission.save()
    
    messages.success(request, f'Permission {permission.permission_name} {"enabled" if permission.enabled else "disabled"}')
    return redirect('plugins:plugin_detail', plugin_id=plugin_id)

@login_required
def uninstall_plugin(request, plugin_id):
    """Uninstall a plugin"""
    plugin = get_object_or_404(Plugin, id=plugin_id)
    
    if request.method == 'POST':
        # Call plugin_uninstalled hook if plugin is enabled
        if plugin.enabled:
            try:
                plugin_manager.call_hook('plugin_uninstalled')
            except Exception as e:
                messages.warning(request, f"Error in plugin_uninstalled hook: {str(e)}")
        
        # Unload the plugin
        plugin_manager.unload_plugin(plugin.id)
        
        # Remove plugin directory with robust error handling
        if os.path.exists(plugin.package_path):
            try:
                import stat
                
                # Use onexc callback to handle permission issues (Python 3.12+)
                def remove_readonly(func, path, exc_info):
                    """Clear the readonly bit and reattempt the removal"""
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                
                shutil.rmtree(plugin.package_path, onexc=remove_readonly)
            except Exception as e:
                messages.warning(request, f"Error removing plugin files: {str(e)}")
        
        # Delete plugin from database
        plugin_name = plugin.name
        plugin.delete()
        
        messages.success(request, f'Plugin {plugin_name} uninstalled successfully')
        return redirect('plugins:plugin_list')
    
    return render(request, 'plugins/confirm_uninstall.html', {'plugin': plugin})

@login_required
def get_dashboard_widgets(request):
    """Get dashboard widgets from all plugins as JSON"""
    widgets_html = []
    widget_errors = []
    context = {'user': request.user, 'request': request}
    
    # Get all enabled plugins
    plugins = Plugin.objects.filter(enabled=True)
    
    # For each plugin, call the dashboard_widget hook
    for plugin in plugins:
        try:
            # Check if dashboard_widget permission is enabled
            has_permission = plugin.permissions.filter(permission_name='dashboard_widget', enabled=True).exists()
            if not has_permission:
                continue
                
            # Call the dashboard_widget hook for this plugin
            results = plugin_manager.call_hook('dashboard_widget',
                plugin_id=plugin.id,
                context={
                    'request': request,
                    'user': request.user,
                    'plugin': plugin
                }
            )
            
            # Process the returned widgets
            if results and len(results) > 0:
                for widget in results:
                    if widget:
                        widgets_html.append(widget)
                        
        except Exception as e:
            # Log the error but continue with other plugins
            import traceback
            error_msg = f"Error rendering dashboard widget for {plugin.name}: {str(e)}"
            error_traceback = traceback.format_exc()
            print(error_msg)
            print(error_traceback)
            
            # Add error to widget_errors to display in the dashboard
            widget_errors.append({
                'plugin_name': plugin.name,
                'error_msg': error_msg,
                'traceback': error_traceback
            })
    
    return JsonResponse({
        'widgets': widgets_html, 
        'errors': widget_errors
    })


def plugin_route_handler(request, plugin_slug, path):
    """
    Dynamic route handler for plugin URLs
    Matches: /plugin/{plugin-slug}/{path}
    """
    from django.http import HttpResponse, Http404
    
    try:
        # Find plugin by slug (name converted to lowercase with dashes)
        from .models import PluginStatus
        plugins = Plugin.objects.filter(enabled=True, status=PluginStatus.APPROVED)
        
        plugin = None
        for p in plugins:
            if p.name.lower().replace(" ", "-") == plugin_slug:
                plugin = p
                break
        
        if not plugin:
            raise Http404(f"Plugin '{plugin_slug}' not found or not enabled")
        
        print(f"[ROUTE] Found plugin: {plugin.name} (ID: {plugin.id})")
        print(f"[ROUTE] Plugin enabled: {plugin.enabled}, status: {plugin.status}")
        print(f"[ROUTE] Loaded plugins: {list(plugin_manager.loaded_plugins.keys())}")
        print(f"[ROUTE] Registered instances: {list(plugin_manager.registered_instances.keys())}")
        
        # Check if plugin is loaded
        if plugin.id not in plugin_manager.loaded_plugins:
            print(f"[ROUTE] Plugin {plugin.id} not loaded, attempting to load...")
            try:
                plugin_manager.load_plugin(plugin)
                print(f"[ROUTE] Plugin loaded successfully")
            except Exception as e:
                print(f"[ROUTE] Error loading plugin: {e}")
                import traceback
                traceback.print_exc()
                raise Http404(f"Plugin '{plugin_slug}' could not be loaded: {str(e)}")
        
        # Get routes from plugin with API context
        from .plugin_api import get_plugin_api
        api = get_plugin_api(plugin.id, context={'request': request, 'user': request.user})
        
        print(f"[ROUTE] Calling register_routes hook for plugin {plugin.id}")
        routes = plugin_manager.call_hook('register_routes', plugin_id=plugin.id, api=api)
        print(f"[ROUTE] Routes returned: {routes}")
        
        if not routes:
            raise Http404(f"Plugin '{plugin_slug}' has no routes registered")
        
        # Find matching route
        for route_list in routes:
            if route_list:
                for route in route_list:
                    if len(route) >= 2:
                        pattern = route[0]
                        view_func = route[1]
                        
                        # Normalize both pattern and path (remove trailing slashes for comparison)
                        normalized_pattern = pattern.rstrip('/')
                        normalized_path = path.rstrip('/')
                        
                        # Match the path
                        if normalized_pattern == normalized_path:
                            print(f"[ROUTE MATCH] Pattern '{pattern}' matched path '{path}'")
                            return view_func(request)
        
        # Debug: show what routes are available
        print(f"[ROUTE ERROR] No match for path '{path}'")
        print(f"[ROUTE ERROR] Available routes:")
        for route_list in routes:
            if route_list:
                for route in route_list:
                    if len(route) >= 2:
                        print(f"  - Pattern: '{route[0]}'")
        
        raise Http404(f"No route found for '{path}' in plugin '{plugin_slug}'")
        
    except Plugin.DoesNotExist:
        raise Http404(f"Plugin '{plugin_slug}' not found")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ROUTE ERROR] Exception: {e}")
        print(f"[ROUTE ERROR] Traceback:\n{error_trace}")
        return HttpResponse(f"<h1>Plugin Error</h1><p>{str(e)}</p><pre>{error_trace}</pre>", status=500)


@login_required
def reload_plugins(request):
    """Reload all plugins"""
    if not request.user.is_superuser:
        messages.error(request, 'Only administrators can reload plugins')
        return redirect('plugins:plugin_list')
    
    try:
        # Reload all plugins
        plugin_manager.reload_all_plugins()
        
        loaded_count = len(plugin_manager.loaded_plugins)
        messages.success(request, f'Successfully reloaded {loaded_count} plugin(s)')
    except Exception as e:
        messages.error(request, f'Error reloading plugins: {str(e)}')
    
    return redirect('plugins:plugin_list')
