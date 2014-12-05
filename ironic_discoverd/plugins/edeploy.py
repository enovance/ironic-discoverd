# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""eDeploy plugin."""

import logging

from hardware import matcher
from hardware import state

from ironic_discoverd import conf
from ironic_discoverd.plugins import base
from ironic_discoverd import utils


LOG = logging.getLogger('ironic_discoverd.plugins.edeploy')


class eDeployHook(base.ProcessingHook):
    """Interact with eDeploy ramdisk for discovery data processing hooks."""

    def pre_discover(self, node_info):
        """Pre-discovery hook.

        This hook is run before any processing is done on data, even sanity
        checks.

        :param node_info: raw information sent by the ramdisk, may be modified
                          by the hook.
        :returns: nothing.
        """

        if 'data' not in node_info:
            raise utils.DiscoveryFailed(
                'edeploy plugin: no "data" key in the received JSON')

        LOG.info('pre-discover: %s', node_info['data'])

        hw_items = []
        for info in node_info['data']:
            hw_items.append(tuple(info))

        hw_copy = list(hw_items)
        self._process_data_for_discoverd(hw_copy, node_info)
        sobj = None

        try:
            sobj = state.State(lockname=conf.get('edeploy', 'lockname',
                                                 '/var/lock/discoverd.lock'))
            sobj.load(conf.get('edeploy', 'configdir', '/etc/edeploy'))
            prof, var = sobj.find_match(hw_items)
            node_info['profile'] = prof
            node_info.update(var)
        except Exception as excpt:
            LOG.error('Unable to find a matching hardware profile: %s' % excpt)
        finally:
            if sobj:
                sobj.unlock()
        del node_info['data']

    def _process_data_for_discoverd(self, hw_items, node_info):
        matcher.match_spec(('memory', 'total', 'size', '$memory_mb'),
                           hw_items, node_info)
        matcher.match_spec(('cpu', 'logical', 'number', '$cpus'),
                           hw_items, node_info)
        matcher.match_spec(('system', 'kernel', 'arch', '$cpu_arch'),
                           hw_items, node_info)
        matcher.match_spec(('disk', '$disk', 'size', '$local_gb'),
                           hw_items, node_info)
        matcher.match_spec(('ipmi', 'lan', 'ip-address', '$ipmi_address'),
                           hw_items, node_info)
        node_info['interfaces'] = {}
        while True:
            info = {'ipv4': 'none'}
            if not matcher.match_spec(('network', '$iface', 'serial', '$mac'),
                                      hw_items, info):
                break
            matcher.match_spec(('network', info['iface'], 'ipv4', '$ipv4'),
                               hw_items, info)
            node_info['interfaces'][info['iface']] = {'mac': info['mac'],
                                                      'ip': info['ipv4']}
