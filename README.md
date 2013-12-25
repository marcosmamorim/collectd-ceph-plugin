collectd-ceph-plugin
====================

This is a collectd plugin which runs under the Python plugin to collect metrics from CEPH using S3 API


Prepare to use
==============
Install python dependecies

python-requests<br>
python-boto

pip install requests-aws

Copy ceph.py to your ModulePath


RADOS Configure
======================

We need add permission to user to access informations about users, buckets and metadata

Login in your radosgw and execute this commands

radosgw-admin caps add --uid=USERNAME --caps="users=read"<br>
radosgw-admin caps add --uid=USERNAME --caps="buckets=read"<br>
radosgw-admin caps add --uid=USERNAME --caps="metadata=read"<br>
radosgw-admin caps add --uid=USERNAME --caps="usage=*"<br>
<br>
We need read and write to usage caps, beacause we remove old stats from users


Check if usage enable
=====================

Check in /etc/ceph/ceph.conf if usage and logs already enabled, if not, add this options to client.radosgw.gateway section<br><br>

rgw enable usage log = true<br>
rgw usage log tick interval = 30<br>
rgw usage log flush threshold = 1024<br>
rgw usage max shards = 32<br>
rgw usage max user shards = 1<br>


Configure
=========

Add configuration to collectd-ceph-plugin into <Plugin python> section at collectd.conf<br>


<Plugin python><br>
    Import "ceph"<br>
    <module ceph><br>
        AccessKey "access_key"<br>
        secretKey "secret_key"<br>
        Host "radosgw_address"<br>
        Verbose True<br>
    </module><br>
</Plugin><br>

Update values:<br>

AccessKey: Your access key<br>
SecretKey: Your secret key<br>
Host: IP or hostname to RADOS Gateway<br>
Verbose: Turn on or off verbose mode<br>

Graphite
========

For perfect integration with plugin write_graphite, we need change parameter EscapeCharacter in section Cabon to

EscapeCharacter "."

