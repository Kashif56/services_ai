import os
import sys
import importlib.util
import json
import pluggy
import hashlib

from django.conf import settings
from plugins.hookspecs import PluginHooks
from plugins.models import Plugin

class SecurityError(Exception):
    """Raised when a plugin violates security policies"""
    pass

class ServicesAIPluginManager:
    """Plugin manager for the Services AI platform"""
    
    def __init__(self):
        self.manager = pluggy.PluginManager("services_ai")
        self.manager.add_hookspecs(PluginHooks)
        self.loaded_plugins = {}  # plugin_id -> module
        self.registered_instances = {}  # plugin_id -> registered instance
        
    def get_plugin_dir(self):
        """Get the directory where plugins are stored"""
        # First check if the plugin_packages directory exists in the project root
        project_root = settings.BASE_DIR
        plugin_packages_dir = os.path.join(project_root, 'plugin_packages')
        
        # If not, use the plugins directory within the app
        if not os.path.exists(plugin_packages_dir):
            plugin_packages_dir = os.path.join(project_root, 'plugins')
            
        return plugin_packages_dir
    
    def discover_plugins(self):
        """Discover and load all approved and enabled plugins"""
        from plugins.models import PluginStatus
        
        # Only load plugins that are approved AND enabled
        plugins = Plugin.objects.filter(
            status=PluginStatus.APPROVED,
            enabled=True
        )
        
        for plugin in plugins:
            self.load_plugin(plugin)
    
    def load_plugin(self, plugin):
        """Load a specific plugin"""
        if plugin.id in self.loaded_plugins:
            return self.loaded_plugins[plugin.id]
        
        # Security check: Only load approved plugins
        if not plugin.can_be_loaded():
            print(f"Plugin {plugin.name} cannot be loaded. Status: {plugin.status}, Enabled: {plugin.enabled}")
            return None
        
        try:
            # If plugin path doesn't exist, try to find it in standard locations
            if not os.path.exists(plugin.package_path):
                # Try in plugin_packages directory
                plugin_packages_dir = self.get_plugin_dir()
                plugin_dir = os.path.join(plugin_packages_dir, plugin.name)
                if os.path.exists(plugin_dir):
                    plugin.package_path = plugin_dir
                    plugin.save()
                else:
                    # Try sample_plugin directory as fallback for the Sample Plugin
                    if plugin.name == "Sample Plugin":
                        sample_plugin_dir = os.path.join(plugin_packages_dir, 'sample_plugin')
                        if os.path.exists(sample_plugin_dir):
                            plugin.package_path = sample_plugin_dir
                            plugin.save()
            
            # Security: Validate plugin directory is within allowed paths
            plugin_dir = os.path.abspath(plugin.package_path)
            allowed_base = os.path.abspath(self.get_plugin_dir())
            
            if not plugin_dir.startswith(allowed_base):
                raise SecurityError(f"Plugin path {plugin_dir} is outside allowed directory")
            
            if not os.path.exists(plugin_dir):
                raise FileNotFoundError(f"Plugin directory not found: {plugin_dir}")
                
            if plugin_dir not in sys.path:
                sys.path.insert(0, plugin_dir)
            
            # Add plugin's virtualenv to sys.path
            from plugins.dependency_manager import DependencyManager
            dep_manager = DependencyManager(plugin)
            site_packages = dep_manager.get_site_packages_path()
            
            if site_packages and site_packages not in sys.path:
                sys.path.insert(0, site_packages)
                print(f"[DEPS] Added {site_packages} to sys.path")
            
            # Load the entry point module with sandboxing
            # If entry_point doesn't have .py extension, add it
            entry_point = plugin.entry_point
            if not entry_point.endswith('.py'):
                entry_point = f"{entry_point}.py"
                
            module_path = os.path.join(plugin_dir, entry_point)
            module_name = f"plugin_{plugin.id}"
            
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None:
                print(f"Error loading plugin {plugin.name}: Could not find module at {module_path}")
                return None
            
            # Load module with sandboxing
            from plugins.sandbox import PluginSandbox
            
            try:
                with PluginSandbox(plugin):
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
            except ImportError as e:
                print(f"[SANDBOX] Import blocked while loading {plugin.name}: {e}")
                raise
            
            # Get the plugin class instance if specified in manifest
            if plugin.plugin_class:
                try:
                    # Try to find the plugin class in the module
                    plugin_class = getattr(module, plugin.plugin_class, None)
                    
                    if plugin_class:
                        # Create an instance of the plugin class
                        plugin_instance = plugin_class()
                        # Register the plugin instance with Pluggy
                        self.manager.register(plugin_instance)
                        # Store both module and instance
                        self.registered_instances[plugin.id] = plugin_instance
                        print(f"Registered plugin class {plugin.plugin_class} from {plugin.name}")
                    else:
                        # If plugin class not found, register the module itself
                        self.manager.register(module)
                        self.registered_instances[plugin.id] = module
                        print(f"Plugin class {plugin.plugin_class} not found in {plugin.name}, registering module instead")
                except Exception as e:
                    # If there's an error instantiating the plugin class, register the module itself
                    self.manager.register(module)
                    self.registered_instances[plugin.id] = module
                    print(f"Error instantiating plugin class {plugin.plugin_class} from {plugin.name}: {str(e)}. Registering module instead.")
            else:
                # Register the module directly if no plugin class specified
                self.manager.register(module)
                self.registered_instances[plugin.id] = module
                print(f"Registered module for plugin {plugin.name}")
            
            # Store the loaded plugin module
            self.loaded_plugins[plugin.id] = module
            
            return module
        except Exception as e:
            print(f"Error loading plugin {plugin.name}: {str(e)}")
            return None
    
    def unload_plugin(self, plugin_id):
        """Unload a specific plugin"""
        # Unregister from Pluggy (use the registered instance, not the module)
        if plugin_id in self.registered_instances:
            registered_obj = self.registered_instances[plugin_id]
            try:
                self.manager.unregister(registered_obj)
                print(f"Unregistered plugin {plugin_id} from Pluggy")
            except Exception as e:
                print(f"Error unregistering plugin {plugin_id}: {str(e)}")
            del self.registered_instances[plugin_id]
        
        # Remove from loaded plugins
        if plugin_id in self.loaded_plugins:
            del self.loaded_plugins[plugin_id]
    
    def call_hook(self, hook_name, **kwargs):
        """Call a specific hook with the given arguments"""
        # Extract plugin_id if provided (for filtering specific plugin)
        # Don't pop it - keep it in kwargs so hooks can receive it
        target_plugin_id = kwargs.get('plugin_id', None)
        
        print(f"  [MANAGER] call_hook: {hook_name}")
        print(f"     Loaded plugins: {len(self.loaded_plugins)}")
        print(f"     Registered instances: {len(self.registered_instances)}")
        if target_plugin_id:
            print(f"     Target plugin_id: {target_plugin_id}")
        
        try:
            # Access hook through manager.hook, this is the Pluggy way
            if not hasattr(self.manager, 'hook'):
                print(f"  [ERROR] Plugin manager has no 'hook' attribute. Manager type: {type(self.manager)}")
                # Try to see if hookspecs are properly registered
                print(f"     Registered hookspecs: {self.manager.get_hookspecs()}")
                return []
                
            # Check if the hook exists
            if not hasattr(self.manager.hook, hook_name):
                print(f"  [WARN] Hook '{hook_name}' not found in manager.hook")
                print(f"     Available hooks: {[h for h in dir(self.manager.hook) if not h.startswith('_')]}")
                return []
            
            print(f"  [OK] Hook '{hook_name}' exists")
            
            # Get hook implementations
            hook = getattr(self.manager.hook, hook_name)
            
            # Check how many implementations exist
            try:
                impls = hook.get_hookimpls()
                print(f"     Hook implementations: {len(impls)}")
                for impl in impls:
                    print(f"       - {impl}")
            except Exception as e:
                print(f"     Could not get implementations: {e}")
            
            # Call the hook with error handling and sandboxing
            print(f"  [CALL] Calling hook with kwargs: {list(kwargs.keys())}")
            
            from plugins.error_handler import safe_hook_execution
            from plugins.sandbox import PluginSandbox
            from plugins.models import Plugin
            
            results = []
            
            # Execute each plugin's hook implementation separately with error handling
            for plugin_id, instance in self.registered_instances.items():
                try:
                    # If target_plugin_id is specified, only call that plugin
                    if target_plugin_id is not None and plugin_id != target_plugin_id:
                        continue
                    
                    plugin = Plugin.objects.get(id=plugin_id)
                    
                    # Skip if plugin is disabled
                    if not plugin.enabled:
                        continue
                    
                    # Check if instance has this hook
                    if not hasattr(instance, hook_name):
                        print(f"     Plugin {plugin_id} ({plugin.name}) does not have hook '{hook_name}'")
                        continue
                    
                    print(f"     Calling hook '{hook_name}' on plugin {plugin_id} ({plugin.name})")
                    hook_method = getattr(instance, hook_name)
                    
                    # Create API instance for the plugin if not already provided
                    if 'api' not in kwargs:
                        from plugins.plugin_api import get_plugin_api
                        context = kwargs.get('context', {})
                        kwargs['api'] = get_plugin_api(plugin_id, context=context)
                    
                    # Execute in sandbox with error handling
                    with PluginSandbox(plugin):
                        result = safe_hook_execution(
                            plugin=plugin,
                            hook_name=hook_name,
                            hook_callable=hook_method,
                            **kwargs
                        )
                        
                        if result is not None:
                            results.append(result)
                            print(f"     Hook returned result: {type(result)}")
                
                except Exception as e:
                    print(f"  [ERROR] Critical error in plugin {plugin_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue with other plugins
            
            print(f"  [RESULT] Hook returned {len(results)} results")
            return results
        except Exception as e:
            print(f"  [ERROR] Error calling hook {hook_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return empty list on error for safety
            return []
    
    def reload_all_plugins(self):
        """Reload all plugins"""
        # Store currently loaded plugin IDs
        loaded_ids = list(self.loaded_plugins.keys())
        
        # Unload all plugins
        for plugin_id in loaded_ids:
            self.unload_plugin(plugin_id)
        
        # Rediscover and load plugins
        self.discover_plugins()

# Create a singleton instance
plugin_manager = ServicesAIPluginManager()
