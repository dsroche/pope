#!/bin/bash --norc

set -e
set -u

scdir=$(dirname "$(readlink -f "$0")")

function usage {
  echo "Usage: $0 qsize seed rsize lat_start lat_end lat_step bw_start bw_end bw_step"
  [[ $# -ge 1 ]] && exit $1
}

[[ $# -eq 9 ]] || usage 1

qsize=$1
seed=$2
rsize=$3
lat_start=$4
lat_end=$5
lat_step=$6
bw_start=$7
bw_end=$8
bw_step=$9

[[ $lat_start -le $lat_end ]] || usage 2
[[ $bw_start -ge $bw_end ]] || usage 3

num_lat=$(( (lat_end - lat_start + lat_step) / lat_step ))
num_bw=$(( ( bw_start - bw_end + bw_step) / bw_step ))

cd "$scdir"
datfile="salary2014nz.csv"
qfile="nwbench-data/full-${qsize}q-${seed}s-${rsize}l.queries"

nwspeed="$scdir/nwspeed.sh"
resfile="$scdir/nwdata.txt"

echo "Will run $(( num_lat * num_bw )) experiments using query file"
echo "$qfile"

op=12345
pp=12344
pw=abc

for (( cur_lat=lat_start ; cur_lat <= lat_end ; cur_lat=(cur_lat + lat_step) )); do
  for (( cur_bw=bw_start ; cur_bw >= bw_end ; cur_bw=(cur_bw - bw_step) )); do
    echo "============================================================"
    echo "Running with latency $cur_lat and bandwidth $cur_bw"
    "$nwspeed" on $cur_lat $cur_bw $op $pp
    res=$(python3 -OO nwbench.py 127.0.0.1 $pp "$pw" "$datfile" "$qsize" -f "$qfile")
    echo "$qsize,$rsize,$cur_lat,$cur_bw,$res" >> "$resfile"
    "$nwspeed" off
    echo
  done
done

