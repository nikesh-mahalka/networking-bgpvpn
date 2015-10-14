# Copyright (c) 2015 Orange.
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

import abc
import six

from networking_bgpvpn.neutron.db import bgpvpn_db


@six.add_metaclass(abc.ABCMeta)
class BGPVPNDriverBase(object):
    """BGPVPNDriver interface for driver

    That driver interface does not persist BGPVPN data in any database. The
    driver need to do it by itself.
    """

    def __init__(self, service_plugin):
        self.service_plugin = service_plugin

    @property
    def service_type(self):
        pass

    @abc.abstractmethod
    def create_bgpvpn(self, context, bgpvpn):
        pass

    @abc.abstractmethod
    def get_bgpvpns(self, context, filters=None, fields=None):
        pass

    @abc.abstractmethod
    def get_bgpvpn(self, context, id, fields=None):
        pass

    @abc.abstractmethod
    def update_bgpvpn(self, context, id, bgpvpn):
        pass

    @abc.abstractmethod
    def delete_bgpvpn(self, context, id):
        pass

    @abc.abstractmethod
    def associate_network(self, context, id, network_id):
        pass

    @abc.abstractmethod
    def disassociate_network(self, context, id, network_id):
        pass


@six.add_metaclass(abc.ABCMeta)
class BGPVPNDriverDBMixin(BGPVPNDriverBase):
    """BGPVPNDriverDB Mixin to provision the database on behalf of the driver

    That driver interface persists BGPVPN data in its database and forward
    the result to postcommit methods
    """

    def __init__(self, service_plugin):
        super(BGPVPNDriverDBMixin, self).__init__(service_plugin)
        self.bgpvpn_db = bgpvpn_db.BGPVPNPluginDb()

    def create_bgpvpn(self, context, bgpvpn):
        bgpvpn = self.bgpvpn_db.create_bgpvpn(
            context, bgpvpn)
        self.create_bgpvpn_postcommit(context, bgpvpn)
        return bgpvpn

    def get_bgpvpns(self, context, filters=None, fields=None):
        return self.bgpvpn_db.get_bgpvpns(context, filters, fields)

    def get_bgpvpn(self, context, id, fields=None):
        return self.bgpvpn_db.get_bgpvpn(context, id, fields)

    def update_bgpvpn(self, context, id, bgpvpn):
        old_bgpvpn = self.get_bgpvpn(context, id)

        bgpvpn = self.bgpvpn_db.update_bgpvpn(
            context, id, bgpvpn)

        self.update_bgpvpn_postcommit(context, old_bgpvpn, bgpvpn)
        return bgpvpn

    def delete_bgpvpn(self, context, id):
        bgpvpn = self.bgpvpn_db.delete_bgpvpn(context, id)
        self.delete_bgpvpn_postcommit(context, bgpvpn)

    def associate_network(self, context, id, network_id):
        self.bgpvpn_db.associate_network(context, id, network_id)
        self.associate_network_postcommit(context, id, network_id)

    def disassociate_network(self, context, id, network_id):
        self.bgpvpn_db.disassociate_network(context, id, network_id)
        self.disassociate_network_postcommit(context, id, network_id)

    @abc.abstractmethod
    def create_bgpvpn_postcommit(self, context, bgpvpn):
        pass

    @abc.abstractmethod
    def update_bgpvpn_postcommit(self, context, old_bgpvpn, bgpvpn):
        pass

    @abc.abstractmethod
    def delete_bgpvpn_postcommit(self, context, bgpvpn):
        pass

    @abc.abstractmethod
    def associate_network_postcommit(self, context, bgpvpn_id, network_id):
        pass

    @abc.abstractmethod
    def disassociate_network_postcommit(self, context, bgpvpn_id, network_id):
        pass


class BGPVPNDriver(BGPVPNDriverDBMixin):
    """BGPVPNDriver interface for driver with database.

    Each bgpvpn driver that needs a database persistency will should inherit
    from this driver.
    It can overload needed methods from the following postcommit methods.
    """
    def __init__(self, service_plugin):
        super(BGPVPNDriver, self).__init__(service_plugin)

    def create_bgpvpn_postcommit(self, context, bgpvpn):
        pass

    def update_bgpvpn_postcommit(self, context, old_bgpvpn, bgpvpn):
        pass

    def delete_bgpvpn_postcommit(self, context, bgpvpn):
        pass

    def associate_network_postcommit(self, context, bgpvpn_id, network_id):
        pass

    def disassociate_network_postcommit(self, context, bgpvpn_id, network_id):
        pass
