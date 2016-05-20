#!/bin/bash --norc

set -e
set -u

scdir=$(dirname "$(readlink -f "$0")")

dip=127.0.0.1
dev=lo
cfile="$scdir/.nwspeed.current"

function usage {
  echo "Usage: $0 (off | on latency_ms bandwidth_kbits [port port ...])"
  echo "  \"off\" command disables current slowness"
  echo "  \"on\" command introduces desired slowness for dest $dip and speficied ports"
  [[ $# -ge 1 ]] && exit $1
}

[[ $# -ge 1 ]] || usage 1
if [[ $1 = off ]]; then
  if [[ ! -e $cfile ]]; then
    echo "ERROR: no file $cfile; did you turn slowness on?"
    exit 2
  fi
  if [[ -s $cfile ]]; then
    exec 4<"$cfile"
    while read -u4 port; do
      sudo iptables -D POSTROUTING -t mangle -j CLASSIFY --set-class 0010:0010 -p tcp -d "$dip" --dport "$port" || true
    done
    exec 4<&-
  else
    sudo iptables -D POSTROUTING -t mangle -j CLASSIFY --set-class 0010:0010 -p tcp -d "$dip" || true
  fi
  sudo tc qdisc del dev "$dev" handle 10: root
  rm "$cfile"
  echo "slowness off"
elif [[ $1 = on ]]; then
  [[ $# -ge 3 ]] || usage 1
  if [[ -e $cfile ]]; then
    echo "ERROR: file $cfile found; is slowness already on?"
    exit 2
  fi
  latency=$2
  bandwidth=$3
  shift 3
  sudo tc qdisc add dev "$dev" handle 10: root htb
  sudo tc class add dev "$dev" parent 10: classid 10:1 htb rate 1000000kbit
  sudo tc class add dev "$dev" parent 10:1 classid 10:10 htb rate "$bandwidth"kbit
  sudo tc qdisc add dev "$dev" parent 10:10 handle 100: netem delay "$latency"ms
  touch "$cfile"
  if [[ $# -gt 0 ]]; then
    while [[ $# -gt 0 ]]; do
      port=$1
      sudo iptables -A POSTROUTING -t mangle -j CLASSIFY --set-class 10:10 -p tcp -d "$dip" --dport "$port"
      shift
    done
    echo "$port" >> "$cfile"
  else
    sudo iptables -A POSTROUTING -t mangle -j CLASSIFY --set-class 10:10 -p tcp -d "$dip"
  fi
  echo "slowness on"
  echo "run 'sudo tc -s qdisc' to check"
else
  usage 1
fi
