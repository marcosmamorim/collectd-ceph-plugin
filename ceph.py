# collectd-ceph-plugin - ceph.py
#
# Author: Marcos Amorim <marcosmamorim@gmail.com>
# Description: This is a collectd plugin which runs under the Python plugin to
# collect metrics from CEPH using S3 API.
# Plugin structure and logging func taken from https://github.com/marcosmamorim/collectd-ceph-plugin
# This plugis has based in two plugins: haproxy.py and rabbitmq-collectd-plugin more info (https://github.com/phrawzty/)

# Copyright 2013 Marcos Amorim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collectd
import requests
from awsauth import S3Auth
import json
import os

# See conf to configure
ACCESS_KEY = 'access_key'
SECRET_KEY = 'SECRET_KEY_key'
SERVER = 'radosgw_address'
VERBOSE_LOGGING = True
METRIC_DELIM = '.' # for the frontend/backend stats
METRIC_TYPES = {
   'bytes_received': ('bytes_received', 'derive'),
   'bytes_sent': ('bytes_sent', 'derive'),
   'category': ('category', 'derive'),
   'ops': ('ops', 'counter'),
   'successful_ops': ('successful_ops', 'counter'),
   'num_objects': ('num_objects', 'counter'),
   'size_kb': ('size_kb', 'derive'),
   'size_kb_actual': ('size_kb_actual', 'derive')
}




def log_verbose(msg):
	if not VERBOSE_LOGGING:
		return
	collectd.info('ceph plugin [verbose]: %s' % msg)

def configure_callback(conf):
	"""Receive configuration block"""
	global ACCESS_KEY, SECRET_KEY, SERVER
	for node in conf.children:
		if node.key == 'AccessKey':
			ACCESS_KEY = node.values[0]
		elif node.key == 'secretKey':
			SECRET_KEY = node.values[0]
		elif node.key == 'Host':
			SERVER = node.values[0]
		elif node.key == 'Verbose':
			VERBOSE_LOGGING = bool(node.values[0])
		else:
			collectd.warning('ceph plugin: Unknown config key: %s.'
							% node.key)
	log_verbose('Configured with ACCESS_KEY=%s, SECRET_KEY=%s, SERVER=%s' % (ACCESS_KEY, SECRET_KEY, SERVER))


def getBucketByUser(user):
	busage = {}

	url = 'http://%s/admin/bucket?format=json&stats=true&uid=%s' % (SERVER, user)
	r = requests.get(url, auth=S3Auth(ACCESS_KEY, SECRET_KEY, SERVER))
	bucketUsage = r.json()
	key_root1 = user

	# For bucket
	for k in bucketUsage:
		bucket = k['bucket']
		if user == 'marcos':
			if bucket == 'mycontainer':
				print k['usage']
		
		# For usage
		for k1,v1 in k['usage'].items():
			#log_verbose('Main: %s' % k1)

			# For usage items
			for k2,v2 in v1.items():
				try:
		    			key_root1, val_type = METRIC_TYPES[k2]
					#log_verbose('Novas chaves: key_root1=%s - val_type=%s' % (key_root1, val_type))
				except KeyError:
					key_root1 = user
					val_type = 'derive'

				key_name = METRIC_DELIM.join([user, bucket, 'summary', k1.replace('rgw.', ''),  k2])
				#log_verbose('Path: %s  bucket: %s, chave: %s, valor: %s' % (key_name, bucket, k2, v2))
				val = collectd.Values(plugin='ceph')
				val.type = val_type
				val.type_instance = key_name
				val.values = [v2]
				val.dispatch()

def getUsers():
	url = 'http://%s/admin/metadata/user?format=json' % SERVER
	r = requests.get(url, auth=S3Auth(ACCESS_KEY, SECRET_KEY, SERVER))
	return r.json()

def getUsageEntries(user):
	ustats = {}
	url = 'http://%s/admin/usage?format=json&uid=%s&show-summary=false"' % (SERVER, user)
	r = requests.get(url, auth=S3Auth(ACCESS_KEY, SECRET_KEY, SERVER))
	usages = r.json()

	if (len(usages['summary']) > 0):
		summary = usages['summary'][0]['total']
		ustats['summary'] = {}
		ustats['summary']['successful_ops'] = summary['successful_ops']
		ustats['summary']['bytes_received'] = summary['bytes_received']
		ustats['summary']['bytes_sent'] = summary['bytes_sent']
		ustats['summary']['ops'] = summary['ops']

	# If no entries return function without data
	if (len(usages['entries']) == 0):
		return  ustats
	
	#TODO
	# Clean old logs from API, didn't work with remove-all parameter
	# Workarround after read usage
	# radosgw-admin usage trim --uid=UID
	cmd = "/usr/bin/radosgw-admin usage trim --uid=%s" % user
	os.system(cmd)

	# Get stats by bucket or list_buckets
	for usage in usages['entries'][0]['buckets']:
		bname = usage['bucket']
		ustats[bname] = {}

		for stats1 in usage['categories']:
			cat = stats1['category']
			ustats[bname][cat] = {}
			ustats[bname][cat]['bytes_received'] = stats1['bytes_received']
			ustats[bname][cat]['bytes_sent'] = stats1['bytes_sent']

	return ustats

def getStats():
	stats = {}
	users = getUsers()

	for user in users:
		ustats = getUsageEntries(user)
		if (ustats):
			stats[user] = ustats

	return stats


def read_callback():
	log_verbose('Read callback called')
	info = getStats()
	users = getUsers()

	for user in users:
		getBucketByUser(user)

	if not info:
		collectd.error('ceph plugin: No info received')
		return

	# Parsing users
	for key,value in info.items():
		log_verbose('Dispatching: %s' %  key)
		key_prefix = ''
		key_root = key
		key_name = METRIC_DELIM.join([key_root, 'summary'])

		for sk1,sv1 in value['summary'].items():
			try:
	    			key_root1, val_type = METRIC_TYPES[sk1]
			except KeyError:
				val_type = 'derive'

			log_verbose('Novo tipo %s para %s' % (val_type, sk1))
			key_name = METRIC_DELIM.join([key_root, 'summary', sk1])
			val = collectd.Values(plugin='ceph')
			val.type = val_type
			val.type_instance = key_name
			val.values = [sv1]
			val.dispatch()

		# Parsing buckets
		for k1,v1 in value.items():
			if k1 == 'summary':
				continue

			#Parsing buckets stats per user
			for k2,v2 in v1.items():
				key_name = METRIC_DELIM.join([key_root, k1, k2, 'bytes_received'])
				val = collectd.Values(plugin='ceph')
				val.type = 'derive'
				val.type_instance = key_name
				val.values = [ v2['bytes_received'] ]
				val.dispatch()

				key_name = METRIC_DELIM.join([key_root, k1, k2, 'bytes_sent'])
				val = collectd.Values(plugin='ceph')
				val.type = 'derive'
				val.type_instance = key_name
				val.values = [ v2['bytes_sent'] ]
				val.dispatch()

# register callbacks
collectd.register_config(configure_callback)
collectd.register_read(read_callback)
