"""Initialize data plugins.

This module handles the initialization of standard and custom data plugins,
and maintains a global registry of plugin protocols vs. plugin instances.

Custom plugins are loaded from locations specified in the `VCP_DATA_PLUGIN_PATH`
environment variable. Valid plugin files have a name ending in `*_plugin.py`
and must contain at least one `QtPyVCPDataPlugin` subclass with the plugin
implementation.
"""
import os
import sys
import inspect
import imp
import uuid

from plugin import QtPyVCPDataPlugin, QtPyVCPDataChannel

# Set up logging
from qtpyvcp.utilities import logger
LOG = logger.getLogger(__name__)

# Global registry of plugin protocols vs. plugin instances
DATA_PLUGIN_REGISTRY = {}

def registerDataPlugin(plugin):
    """Add a plugin to the global registry of protocol names vs. plugin instances.

    Args:
        plugin (QtPyVCPDataPlugin) : The class of the plugin to register.
    """
    # Warn users if we are overwriting a protocol which already has a plugin
    if plugin.protocol in DATA_PLUGIN_REGISTRY:
        LOG.warning("Replacing {} plugin with {} for use with protocol {}"
                    .format(plugin,
                            DATA_PLUGIN_REGISTRY[plugin.protocol],
                            plugin.protocol)
                    )
    DATA_PLUGIN_REGISTRY[plugin.protocol] = plugin()


def loadDataPluginsFromPath(locations, suffix):
    """Load data plugins from a directory.

    Args:
        locations (list) : List of file locations
        suffix (str) : Specify the suffix that files must have in order to
            attempt loading as a QtPyVCPDataPlugin. Defaults to `_plugin`.

    Returns:
        Dictionary of protocol names vs. plugin instances that were added.
    """
    added_plugins = []
    for loc in locations:
        for root, _, files in os.walk(loc):
            if root.split(os.path.sep)[-1].startswith("__"):
                continue

            LOG.info("Looking for QtPyVCP Data Plugins in: {}".format(root))
            for name in files:
                if name.endswith(suffix):
                    try:
                        LOG.info("Trying to load {} ...".format(name))
                        sys.path.append(root)
                        temp_name = str(uuid.uuid4())
                        temp_name = 'qtpyvcp.plugins.' + os.path.splitext(name)[0]
                        module = imp.load_source(temp_name,
                                                 os.path.join(root, name))

                    except Exception as e:
                        LOG.exception("Unable to import plugin file {}. "
                                         "This plugin will be skipped.\n"
                                         "The exception raised was: {}"
                                         .format(name, e)
                                        )
                        continue
                    classes = [obj for obj_name, obj in inspect.getmembers(module)
                               if inspect.isclass(obj)
                               and issubclass(obj, QtPyVCPDataPlugin)
                               and obj is not QtPyVCPDataPlugin]

                    # De-duplicate classes.
                    classes = list(set(classes))
                    for plugin in classes:
                        if plugin.protocol is None:
                            LOG.warning("No protocol specified for {} plugin "
                                        "defined in file {}. Skipping plugin."
                                        .format(plugin.__name__, name))
                            continue

                        # register the plugin
                        registerDataPlugin(plugin)
                        added_plugins.append(plugin.protocol)

    return added_plugins


class NoSuchPlugin(Exception):
    pass


def getPluginFromProtocol(protocol):
    """Get data plugin instance from a protocol name.

    Args:
        protocol (str) : The protocol of the plugin to retrieve.

    Returns:
        A plugin instance, or None.

    Raises:
        NoSuchPlugin if the no plugin for ``protocol`` is found.
    """
    try:
        return DATA_PLUGIN_REGISTRY[protocol]
    except KeyError:
        raise NoSuchPlugin("Failed to find plugin for '{}' protocol.".format(protocol))


# Load the data plugins from VCP_DATA_PLUGINS_PATH
LOG.info("Loading QtPyVCP Data Plugins")

# initialize default plugins
from status_plugin import Status
DATA_PLUGIN_REGISTRY[Status.protocol] = Status()

from tool_table_plugin import ToolTable
DATA_PLUGIN_REGISTRY[ToolTable.protocol] = ToolTable()

# load other plugins
DATA_PLUGIN_SUFFIX = "_plugin.py"
path = os.getenv("VCP_DATA_PLUGIN_PATH", None)
if path is None:
    locations = []
else:
    locations = path.split(os.pathsep)

loadDataPluginsFromPath(locations, DATA_PLUGIN_SUFFIX)