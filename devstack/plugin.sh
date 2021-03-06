#!/bin/bash

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set +o xtrace

if [[ "$1" == "source" ]]; then
	# no-op
	:
elif [[ "$1" == "stack" && "$2" == "install" ]]; then
	echo_summary "Installing networking-bgpvpn"
	setup_develop $NETWORKING_BGPVPN_DIR
elif [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
	echo_summary "Enabling networking-bgpvpn service plugin"
	_neutron_service_plugin_class_add $BGPVPN_PLUGIN_CLASS
elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        if is_service_enabled q-svc; then
                echo_summary "Configuring networking-bgpvpn"
                mkdir -v -p $NEUTRON_CONF_DIR/policy.d && cp -v $NETWORKING_BGPVPN_DIR/etc/neutron/policy.d/bgpvpn.conf $NEUTRON_CONF_DIR/policy.d
                mkdir -v -p $(dirname $NETWORKING_BGPVPN_CONF) && cp -v $NETWORKING_BGPVPN_DIR/etc/neutron/networking_bgpvpn.conf $NETWORKING_BGPVPN_CONF
                inicomment $NETWORKING_BGPVPN_CONF service_providers service_provider
                iniadd $NETWORKING_BGPVPN_CONF service_providers service_provider $NETWORKING_BGPVPN_DRIVER
        fi
fi
if [[ "$1" == "unstack" ]]; then
	#no-op
	:
fi
if [[ "$1" == "clean" ]]; then
	#no-op
	:
fi

set +x
$xtrace

