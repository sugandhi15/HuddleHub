###############################################################################
#
#   Copyright: (c) 2015 Carlo Sbraccia
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

# --- global instances of the active database clients (used by the APIs)
obj_clt = None
ts_clt = None

# --- For each object retrieved from database we want to have one and only one
#     instance per session, shared by each client and by the dependency graph.
#     This, not only improves performance (at the cost of heavy memory usage),
#     but, more importantly, ensures the proper functioning of the dependency
#     graph.
obj_instances = dict()
