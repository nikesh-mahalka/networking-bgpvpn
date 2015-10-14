How to use OpenContrail driver for the BGPVPN plugin?
-------------------------------------------------------------------------------

The **OpenContrail** driver for the BGPVPN service plugin is designed to work
jointly with the OpenContrail SDN controller.
OpenContrail proposes a similar script that devstack to deploy a dev and test
environment: https://github.com/Juniper/contrail-installer

* Clone that OpenContrail installer script:
    ```
    git clone git@github.com:Juniper/contrail-installer
    ```

* Compile and run OpenContrail:
    ```
    cd ~/contrail-installer
    cp samples/localrc-all localrc (edit localrc as needed)
    ./contrail.sh build
    ./contrail.sh install
    ./contrail.sh configure
    ./contrail.sh start
    ```

* Then clone devstack:
    ```
    git clone git@github.com:openstack-dev/devstack
    ```

* A glue file is needed in the interim till it is upstreamed to devstack:
    ```
    cp ~/contrail-installer/devstack/lib/neutron_plugins/opencontrail lib/neutron_plugins/
    ```

* Use a sample ``localrc``:
    ```
    cp ~/contrail-installer/devstack/samples/localrc-all localrc
    ```

* Add the following to that ``localrc``:
    ```
    [[post-config|/$NETWORKING_BGPVPN_CONF]]
    [service_providers]
    service_provider=BGPVPN:OpenContrail:networking_bgpvpn.neutron.services.service_drivers.opencontrail.opencontrail.OpenContrailBGPVPNDriver:default
    ```

* Run stack.sh
    ```
    ./stack.sh
    ```