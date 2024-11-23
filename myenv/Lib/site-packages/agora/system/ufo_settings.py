###############################################################################
#
#   Copyright: (c) 2015-2018 Carlo Sbraccia
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###############################################################################

from onyx.core import UfoBase, GraphNodeDescriptor, load_system_configuration

__all__ = ["Settings"]


###############################################################################
class Settings(UfoBase):
    """
    This class makes available "on the graph" the system settings as loaded
    from the configuration file.
    """
    # -------------------------------------------------------------------------
    @GraphNodeDescriptor()
    def Platform(self, graph):
        config = load_system_configuration()
        return config.get("settings", "platform", fallback="Bloomberg")


# -----------------------------------------------------------------------------
def prepare_for_test():
    from onyx.core import AddIfMissing
    AddIfMissing(Settings(Name="Settings"))
