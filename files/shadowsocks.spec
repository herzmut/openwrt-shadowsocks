#!/bin/sh /etc/rc.common

START=90
STOP=15

EXTRA_COMMANDS="rules"
CONFIG_FILE=/var/etc/shadowsocks.json

get_config() {
	config_get_bool enable $1 enable
	config_get server $1 server
	config_get server_port $1 server_port
	config_get local_port $1 local_port
	config_get timeout $1 timeout
	config_get password $1 password
	config_get encrypt_method $1 encrypt_method
	config_get ignore_list $1 ignore_list
	config_get udp_mode $1 udp_mode
	config_get udp_server $1 udp_server
	config_get udp_server_port $1 udp_server_port
	config_get udp_local_port $1 udp_local_port
	config_get udp_timeout $1 udp_timeout
	config_get udp_password $1 udp_password
	config_get udp_encrypt_method $1 udp_encrypt_method
	config_get_bool tunnel_enable $1 tunnel_enable
	config_get tunnel_port $1 tunnel_port
	config_get tunnel_forward $1 tunnel_forward
	config_get lan_ac_mode $1 lan_ac_mode
	config_get lan_ac_ip $1 lan_ac_ip
	config_get wan_bp_ip $1 wan_bp_ip
	config_get wan_fw_ip $1 wan_fw_ip
	config_get ipt_ext $1 ipt_ext
	: ${timeout:=60}
	: ${udp_timeout:=60}
	: ${tunnel_port:=5300}
	: ${tunnel_forward:=8.8.4.4:53}
}

start_rules() {
	local ac_args

	if [ -n "$lan_ac_ip" ]; then
		case $lan_ac_mode in
			1) ac_args="w$lan_ac_ip"
			;;
			2) ac_args="b$lan_ac_ip"
			;;
		esac
	fi
	/usr/bin/ss-rules \
		-s "$server" \
		-l "$local_port" \
		-S "$udp_server" \
		-L "$udp_local_port" \
		-i "$ignore_list" \
		-a "$ac_args" \
		-b "$wan_bp_ip" \
		-w "$wan_fw_ip" \
		-e "$ipt_ext" \
		-o $udp
	return $?
}

start_redir() {
	cat <<-EOF >$CONFIG_FILE
		{
		    "server": "$server",
		    "server_port": $server_port,
		    "local_address": "0.0.0.0",
		    "local_port": $local_port,
		    "password": "$password",
		    "timeout": $timeout,
		    "method": "$encrypt_method"
		}
EOF
	if [ "$udp_mode" = 2 ]; then
		/usr/bin/ss-redir \
			-c $CONFIG_FILE \
			-f /var/run/ss-redir_t.pid
		cat <<-EOF >$CONFIG_FILE
			{
			    "server": "$udp_server",
			    "server_port": $udp_server_port,
			    "local_address": "0.0.0.0",
			    "local_port": $udp_local_port,
			    "password": "$udp_password",
			    "timeout": $udp_timeout,
			    "method": "$udp_encrypt_method"
			}
EOF
	fi
	/usr/bin/ss-redir \
		-c $CONFIG_FILE \
		-f /var/run/ss-redir.pid \
		$udp
	return $?
}

start_tunnel() {
	: ${udp:="-u"}
	/usr/bin/ss-tunnel \
		-c $CONFIG_FILE \
		-l $tunnel_port \
		-L $tunnel_forward \
		-f /var/run/ss-tunnel.pid \
		$udp
	return $?
}

rules() {
	config_load shadowsocks
	config_foreach get_config shadowsocks
	[ "$enable" = 1 ] || exit 0
	mkdir -p /var/run /var/etc

	: ${server:?}
	: ${server_port:?}
	: ${local_port:?}
	: ${password:?}
	: ${encrypt_method:?}
	case $udp_mode in
		1) udp="-u"
		;;
		2)
			udp="-U"
			: ${udp_server:?}
			: ${udp_server_port:?}
			: ${udp_local_port:?}
			: ${udp_password:?}
			: ${udp_encrypt_method:?}
		;;
	esac

	start_rules
}

boot() {
	until iptables-save -t nat | grep -q "^:zone_lan_prerouting"; do
		sleep 1
	done
	start
}

start() {
	rules && start_redir
	[ "$tunnel_enable" = 1 ] && start_tunnel
}

stop() {
	/usr/bin/ss-rules -f
	killall -q -9 ss-redir
	killall -q -9 ss-tunnel
}
