How to use bagpipe driver for the BGPVPN plugin, jointly with the openvswitch ML2 mech driver ?
-----------------------------------------------------------------------------------------------

The **bagpipe** driver for the BGPVPN service plugin is designed to work jointly with the openvswitch
ML2 mechanism driver.  It relies on the use of the _bagpipe-bgp BGP VPN implementation on compute node
and the MPLS implementation in OpenVSwitch.

In devstack:

* follow the instruction in README.rst

* ``local.conf``:

  * enable the ``openvswitch`` ML2 mechanism driver, and activate the agent ARP responder (you need to enable l2population too for the ARP responder to be enabled)

  * add the following to enable the BaGPipe driver for the BGPVPN service plugin::

     NETWORKING_BGPVPN_DRIVER=$NETWORKING_BGPVPN_DRIVER_BAGPIPE

* on a control node, if you want to run the Fake Route-Reflector there::

     enable_plugin bagpipe-bgp https://github.com/Orange-OpenSource/bagpipe-bgp.git
     enable_service b-fakerr

* on compute nodes:

  * install and configure bagpipe-bgp_, typically with a peering to a BGP Router-Reflector or BGP routers, can be done through devstack
    like this::

        enable_plugin bagpipe-bgp https://github.com/Orange-OpenSource/bagpipe-bgp.git
        BAGPIPE_DATAPLANE_DRIVER_IPVPN=mpls_ovs_dataplane.MPLSOVSDataplaneDriver
        # IP of your route-reflector or BGP router, or fakeRR
        # (typically $SERVICE_HOST on compute node, if the control node is running the RR)
        BAGPIPE_BGP_PEERS=1.2.3.4
        enable_service b-bgp

  * the compute node Neutron agent is ``bagpipe-openvswitch`` (inherits from openvswitch agent, with additions to interact with ``bagpipe-bgp``):

    * install networking-bagpipe-l2_  (the code to interact with ``bagpipe-bgp`` comes from there)::

        enable_plugin networking-bagpipe-l2 git://git.openstack.org/stackforge/networking-bagpipe-l2.git

    * define ``Q_AGENT=bagpipe-openvswitch`` in ``local.conf``

.. _bagpipe-bgp: https://github.com/Orange-OpenSource/bagpipe-bgp
.. _networking-bagpipe-l2: https://github.com/stackforge/networking-bagpipe-l2



