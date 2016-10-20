
echo "Run sgload with url: $1" > /tmp/run_sgload_out
/usr/local/bin/sgload gateload --createwriters --createreaders --sg-url $1
