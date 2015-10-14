# Copyright (c) 2015 Cloudwatt.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


# questions
# - Can we have the same rt use by different bgpvpn connections?
# - Can we have different bgpvpn connections associated to the same net/router?

from neutron.i18n import _LW
from oslo_log import log
from oslo_utils import uuidutils

import json

from neutron.common import exceptions as n_exc

from networking_bgpvpn.neutron.extensions import bgpvpn as bgpvpn_ext
from networking_bgpvpn.neutron.services.common import constants
from networking_bgpvpn.neutron.services.common import utils
from networking_bgpvpn.neutron.services.service_drivers import driver_api
from networking_bgpvpn.neutron.services.service_drivers.opencontrail import \
    exceptions as oc_exc
from networking_bgpvpn.neutron.services.service_drivers.opencontrail import \
    opencontrail_client

OPENCONTRAIL_BGPVPN_DRIVER_NAME = 'OpenContrail'

LOG = log.getLogger(__name__)


class OpenContrailBGPVPNDriver(driver_api.BGPVPNDriverBase):
    """BGP VPN Service Driver class for OpenContrail."""

    def __init__(self, service_plugin):
        super(OpenContrailBGPVPNDriver, self).__init__(service_plugin)
        LOG.debug("OpenContrailBGPVPNDriver service_plugin : %s",
                  service_plugin)

    def _get_opencontrail_api_client(self, context):
        return opencontrail_client.OpenContrailAPIBaseClient(
            tenant=context.tenant,
            token=context.auth_token)

    def _get_tenant_id_for_create(self, context, resource):
        if context.is_admin and 'tenant_id' in resource:
            tenant_id = resource['tenant_id']
        elif ('tenant_id' in resource
              and resource['tenant_id'] != context.tenant_id):
            reason = _('Cannot create resource for another tenant')
            raise n_exc.AdminRequired(reason=reason)
        else:
            tenant_id = context.tenant_id
        return tenant_id

    def _locate_rt(self, oc_client, rt_fq_name):
        try:
            rt_uuid = oc_client.fqname_to_id('route-target', rt_fq_name)
        except oc_exc.OpenContrailAPINotFound:
            body = {
                'route-target': {
                    "fq_name": [':'.join(rt_fq_name)]
                }
            }
            rt_uuid = oc_client.create('Route Target', body)['uuid']

        return rt_uuid

    def _update_rt_ri_association(self, oc_client, operation, ri_id,
                                  rt_fq_name, import_export=None):
        rt_uuid = self._locate_rt(oc_client, rt_fq_name)

        kwargs = {
            "operation": operation,
            "resource_type": "routing-instance",
            "resource_uuid": ri_id,
            "ref_type": "route-target",
            "ref_fq_name": rt_fq_name,
            "ref_uuid": rt_uuid,
            "attributes": {
                "import_export": import_export
            }
        }
        oc_client.ref_update(**kwargs)

        if operation == 'ADD':
            return rt_uuid

        rt = oc_client.show('Route Target', rt_uuid)
        if 'routing_instance_back_refs' not in rt.keys():
            rt = oc_client.remove('Route Target', rt_uuid)
        else:
            return rt_uuid

    def _get_ri_id_of_network(self, oc_client, network_id):
        try:
            network = oc_client.show('Virtual Network', network_id)
            ri_fq_name = network['fq_name'] + [network['fq_name'][-1]]
            for ri_ref in network.get('routing_instances', []):
                if ri_ref['to'] == ri_fq_name:
                    return ri_ref['uuid']
        except (oc_exc.OpenContrailAPINotFound, IndexError):
            raise n_exc.NetworkNotFound(net_id=network_id)

    def _set_bgpvpn_association(self, oc_client, operation, bgpvpn,
                                network_id=None):
        if network_id:
            networks = [network_id]
        else:
            networks = bgpvpn.get('networks', [])
        for network_id in networks:
            net_ri_id = self._get_ri_id_of_network(oc_client, network_id)
            if bgpvpn['type'] == constants.BGPVPN_L3:
                for rt in bgpvpn['route_targets']:
                    rt_fq_name = ['target'] + rt.split(':')
                    self._update_rt_ri_association(oc_client, operation,
                                                   net_ri_id, rt_fq_name)

                for rt in bgpvpn['import_targets']:
                    rt_fq_name = ['target'] + rt.split(':')
                    self._update_rt_ri_association(oc_client, operation,
                                                   net_ri_id, rt_fq_name,
                                                   import_export="import")

                for rt in bgpvpn['export_targets']:
                    rt_fq_name = ['target'] + rt.split(':')
                    self._update_rt_ri_association(oc_client, operation,
                                                   net_ri_id, rt_fq_name,
                                                   import_export="export")

        return bgpvpn

    def create_bgpvpn(self, context, bgpvpn):
        bgpvpn = bgpvpn['bgpvpn']

        LOG.debug("create_bgpvpn_ called with %s" % bgpvpn)

        # Check that route_targets is not empty
        if not bgpvpn['route_targets']:
            raise bgpvpn_ext.BGPVPNMissingRouteTarget

        # Only support l3 technique
        if not bgpvpn['type']:
            bgpvpn['type'] = constants.BGPVPN_L3
        elif bgpvpn['type'] != constants.BGPVPN_L3:
            raise bgpvpn_ext.BGPVPNTypeNotSupported(
                driver=OPENCONTRAIL_BGPVPN_DRIVER_NAME, type=bgpvpn['type'])

        # Does not support to set route distinguisher
        if 'route_distinguishers' in bgpvpn and bgpvpn['route_distinguishers']:
            raise bgpvpn_ext.BGPVPNRDNotSupported(
                driver=OPENCONTRAIL_BGPVPN_DRIVER_NAME)

        oc_client = self._get_opencontrail_api_client(context)

        tenant_id = self._get_tenant_id_for_create(context, bgpvpn)
        bgpvpn['tenant_id'] = tenant_id
        bgpvpn['id'] = uuidutils.generate_uuid()
        bgpvpn['networks'] = []

        oc_client.kv_store('STORE', key=bgpvpn['id'], value={'bgpvpn': bgpvpn})

        return utils.make_bgpvpn_dict(bgpvpn)

    def get_bgpvpns(self, context, filters=None, fields=None):
        LOG.debug("get_bgpvpns called, fields = %s, filters = %s"
                  % (fields, filters))

        oc_client = self._get_opencontrail_api_client(context)

        bgpvpns = []
        for kv_dict in oc_client.kv_store('RETRIEVE'):
            try:
                value = json.loads(kv_dict['value'])
            except ValueError:
                continue
            if (isinstance(value, dict)
                    and 'bgpvpn' in value
                    and utils.filter_resource(value['bgpvpn'], filters)):
                bgpvpns.append(utils.make_bgpvpn_dict(value['bgpvpn'], fields))

        if not context.is_admin:
            return [bgpvpn for bgpvpn in bgpvpns if
                    bgpvpn['tenant_id'] == context.tenant_id]

        return bgpvpns

    def get_bgpvpn(self, context, id, fields=None):
        LOG.debug("get_bgpvpn called for id %s with fields = %s"
                  % (id, fields))

        oc_client = self._get_opencontrail_api_client(context)

        try:
            bgpvpn = json.loads(oc_client.kv_store('RETRIEVE', key=id))
        except (oc_exc.OpenContrailAPINotFound, ValueError):
            raise bgpvpn.BGPVPNNotFound(id=id)

        if (not isinstance(bgpvpn, dict) or 'bgpvpn' not in bgpvpn):
            raise bgpvpn.BGPVPNNotFound(id=id)

        bgpvpn = bgpvpn['bgpvpn']
        if not context.is_admin:
            if bgpvpn['tenant_id'] != context.tenant_id:
                raise bgpvpn_ext.BGPVPNNotFound(id=id)

        return utils.make_bgpvpn_dict(bgpvpn, fields)

    def update_bgpvpn(self, context, id, new_bgpvpn):
        LOG.debug("update_bgpvpn called with %s for %s" % (new_bgpvpn, id))

        fields = None
        oc_client = self._get_opencontrail_api_client(context)
        new_bgpvpn = new_bgpvpn['bgpvpn']

        old_bgpvpn = self.get_bgpvpn(context, id)
        bgpvpn = old_bgpvpn.copy()
        bgpvpn.update(new_bgpvpn)

        (added_keys, removed_keys, changed_keys) = \
            utils.get_bgpvpn_differences(bgpvpn, old_bgpvpn)
        if not (added_keys or removed_keys or changed_keys):
            return utils.make_bgpvpn_dict(bgpvpn, fields)

        rt_keys = set(['route_targets',
                       'import_targets',
                       'export_targets'])

        if 'networks' in changed_keys:
            removed_networks = list(
                set(old_bgpvpn.get('networks', [])) -
                set(bgpvpn.get('networks', []))
            )
            added_networks = list(
                set(bgpvpn.get('networks', [])) -
                set(old_bgpvpn.get('networks', []))
            )

            for network_id in removed_networks:
                self._set_bgpvpn_association(oc_client, 'DELETE', old_bgpvpn,
                                             network_id)
            for network_id in added_networks:
                self._set_bgpvpn_association(oc_client, 'ADD', bgpvpn,
                                             network_id)
        elif (rt_keys & added_keys
              or rt_keys & changed_keys
              or rt_keys & removed_keys):
            self._set_bgpvpn_association(oc_client, 'DELETE', old_bgpvpn)
            self._set_bgpvpn_association(oc_client, 'ADD', bgpvpn)

        oc_client.kv_store('STORE', key=id, value={'bgpvpn': bgpvpn})
        return utils.make_bgpvpn_dict(bgpvpn, fields)

    def delete_bgpvpn(self, context, id):
        LOG.debug("delete_bgpvpn called for id %s" % id)

        bgpvpn = self.get_bgpvpn(context, id)

        oc_client = self._get_opencontrail_api_client(context)
        self._set_bgpvpn_association(oc_client, 'DELETE', bgpvpn)
        oc_client.kv_store('DELETE', key=id)

    def associate_network(self, context, bgpvpn_id, network_id):
        LOG.debug("associate_network called for bgpvpn %s with network %s"
                  % (bgpvpn_id, network_id))

        if not network_id:
            return

        bgpvpn = self.get_bgpvpn(context, bgpvpn_id)
        if network_id not in bgpvpn.get('networks', []):
            bgpvpn['networks'] += [network_id]
            bgpvpn = self.update_bgpvpn(context, bgpvpn_id, {'bgpvpn': bgpvpn})

    def disassociate_network(self, context, bgpvpn_id, network_id):
        LOG.debug("disassociate_network called for bgpvpn %s with network %s"
                  % (bgpvpn_id, network_id))

        if not network_id:
            return

        bgpvpn = self.get_bgpvpn(context, bgpvpn_id)
        try:
            bgpvpn.get('networks', []).remove(network_id)
        except ValueError:
            LOG.warning(_LW("network %(net_id)s was not associated to bgpvpn "
                            "%(bgpvpn_id)s"), {'net_id': network_id,
                                               'bgpvpn_id': bgpvpn_id})
            return
        bgpvpn = self.update_bgpvpn(context, bgpvpn_id, {'bgpvpn': bgpvpn})
