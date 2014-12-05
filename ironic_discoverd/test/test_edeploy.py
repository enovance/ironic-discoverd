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

import os
import unittest

from hardware import state
import mock

from ironic_discoverd import conf
from ironic_discoverd.plugins import edeploy
from ironic_discoverd import utils


def fake_load(obj, cfg_dir):
    obj._cfg_dir = cfg_dir
    obj._data = [('hw1', '*'), ]


@mock.patch.object(state.State, 'load', fake_load)
@mock.patch.object(state.State, '_load_specs',
                   lambda o, n: [('network', '$iface', 'serial', '$mac'),
                                 ('network', '$iface', 'ipv4', '$ipv4')])
class TestEdeploy(unittest.TestCase):
    def setUp(self):
        conf.init_conf()
        conf.CONF.add_section('edeploy')
        basedir = os.path.dirname(os.path.abspath(__file__))
        conf.CONF.set('edeploy', 'configdir', os.path.join(basedir,
                                                           'edeploy_conf'))

    def test_hook(self):
        hook = edeploy.eDeployHook()
        node_info = {'data': [
            ['network', 'eth0', 'serial', '99:99:99:99:99:99'],
            ['network', 'eth0', 'ipv4', '192.168.100.12'],
        ]}
        hook.pre_discover(node_info)
        self.assertEqual('hw1', node_info['profile'])
        self.assertEqual('eth0', node_info['iface'])
        self.assertEqual('99:99:99:99:99:99',
                         node_info['interfaces']['eth0']['mac'])

    def test_hook_no_data(self):
        hook = edeploy.eDeployHook()
        node_info = {}
        self.assertRaises(utils.DiscoveryFailed, hook.pre_discover, node_info)

    def test_hook_no_profile(self):
        hook = edeploy.eDeployHook()
        node_info = {'data': []}
        hook.pre_discover(node_info)
        self.assertNotIn('profile', node_info)
