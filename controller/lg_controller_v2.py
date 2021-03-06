'''
	will contain only the part one: migration of the virtual machines from the server of virtual machines
	
	vm_statistics{vm_name, vm ip, physical machine ip,cpu, mem, mouse_movements }
	server_vm_satistcs {server_name/ip,user_name, cpu,memory, workload}
	server_vm_container{number_of_vms,which_vms}	
	migration_decision {vm_name, migration_dec,vm_ip,physical_ip, server_ip, server_user} # used to set/reset the migration decision
	migration_status{vm,source, destination,status}
	vm_info{dom_name,vm_ip,host_ip}
	host_info{host_ip,user}
	server_info{user,ip}
'''

import pymongo as pym
from time import time, sleep

client = pym.Connection('baggins',27017)
db	 = client['litegreen_1']

##################################################################################
# Thresholds can be changed ... to test
cpu_lower_thresh = 0.10
#cpu_upper_thresh = 40
cpu_upper_thresh = 1.0

server_cpu_max = 90
min_server_mem_reqd = 200*1024*1024 #bytes

host_cpu_max = 95
min_host_mem_reqd = 200*1024*1024 #bytes

##################################################################################

'''
	find all the vms to which vms are under used to allow their migration
'''
def check_statistics_etp():
	sinfo = db['server_info']
	s_avl = sinfo.find()

	s_ips = []
	for s in s_avl:
		s_ips.append(s['host_ip'])

	# Print IP of all servers
	#for s in s_ips:
	#	print s

	vms = db['vm_statistics']
	stat = vms.find({"5_min": {"$lt": cpu_lower_thresh}, "mouse": "no", "host_ip":{"$nin":s_ips}})
	return stat

'''
	find all the vms to which are currently on server but need to be 
'''
def check_statistics_mtp():
	sinfo = db['server_info']
	s_avl = sinfo.find()

	s_ips = []
	for s in s_avl:
		s_ips.append(s['host_ip'])

	vms = db['vm_statistics']
	stat = vms.find({"5_min": {"$gt": cpu_upper_thresh}, "mouse": "no", "host_ip":{"$in":s_ips}})
	return stat

'''
	Gets least loaded client in terms of CPU & check if migration is possible
	If it is then return the True flag, and client details
'''
def select_free_client(vm):
	print '===== Checking for lightly loaded Hosts====='
	hinfo  = db['host_statistics']
	print ('vm[cpu] = %f, vm[mem_total] = %f') % (vm['cpu']/100.0, vm['mem_total'])

	hosts = hinfo.find({ "mem_free":{"$gte": vm['mem_total'] + min_host_mem_reqd}}).sort("cpu").sort("mem_free")
	for host in hosts:
		all_cores = host['all_cpu']

		# Logic is same as in check_available_resources()
		vm_inst_psec = vm['core_frequency'] * vm['core_usage'] / 100
		print 'Freq = %dM,Usage = %d,VM_inst/sec = %dM' % (vm['core_frequency'], vm['core_usage'], vm_inst_psec)

		for core in all_cores:
			host_inst_psec	 = 1.0000*core['frequency'] * (100 - core['usage']) /100
			factor			 = 1.0000*vm['core_frequency'] / core['frequency']
			translated_psec  = vm_inst_psec * factor

			print 'Host inst/sec = %fM, factor = %f, translated inst/sec = %fM'%(host_inst_psec, factor, translated_psec)

			if host_inst_psec > translated_psec :
				return True, host['ip'], host['user']
	
	return False, '',''

'''
	Gets least loaded server in terms of CPU & check if the machine is free for the migration
	If it is then return the True flag, which server is free and what is the user name@ the server to allow the execution of the migration process
'''
def check_available_resources(vm):
	print '===== Checking for lightly loaded Server====='
	sinfo  = db['server_statistics']
	print ('vm[cpu] = %f, vm[mem_total] = %f') % (vm['cpu']/100.0, vm['mem_total'])

	# select where vm[mem] + min_server_mem_reqd  <= server[free] 
	# sorting happens based on lightly loaded CPU, which is then sorted based on mem
	# In this way we get a server which is lightly loaded in terms of both mem n CPU 
	servers = sinfo.find({ "mem_free":{"$gte": vm['mem_total'] + min_server_mem_reqd}}).sort("cpu").sort("mem_free")
	for server in servers:
		#print server
		all_cores = server['all_cpu']

		# Check if any core can effectively handle the vcpu(s) load
		# requires 3 steps for each:
		# 1. Get inst/sec by Freq of Core * utilization of ith server core
		# 2. Get inst/sec from vm_statistics which is updated by host (same logic)
		# This has a catch bcz it has to be evaluated by first checking which core of 
		# host is mapped to vcpu & getting its freq n utilization
		# 3. Translate the inst/sec of host into server core & return if possible to allocate
		vm_inst_psec = vm['core_frequency'] * vm['core_usage'] / 100
		print 'Freq = %dM,Usage = %d,VM_inst/sec = %dM' % (vm['core_frequency'], vm['core_usage'], vm_inst_psec)

		for core in all_cores:
			server_inst_psec = 1.0000*core['frequency'] * (100 - core['usage']) /100
			factor			 = 1.0000*vm['core_frequency'] / core['frequency']
			translated_psec  = vm_inst_psec * factor

			print 'Server inst/sec = %fM, factor = %f, translated inst/sec = %fM'%(server_inst_psec, factor, translated_psec)

			if server_inst_psec > translated_psec :
				return True, server['ip'], server['user']
	
	return False, '',''

	'''
	doc =col.server_statistics()
	for d in doc:
		print d

	crucial logic to hold the virtual machine, mebbe use the sandpiper paper migration logic
	if available == True:
		return True,ip,user
	else:
		return False
	'''

'''
	insert the migration message for the virtual machine
''' 
def insert_migration_message(vm, server_ip, server_user):
	d = {}
	d['vm_name'	   ] = vm['vm_name']
	d['host_ip'	   ] = vm['host_ip']
	d['server_ip'  ] = server_ip
	d['server_user'] = server_user
	d['decision'   ] = "YES"
	#d['vm_ip'	   ] = vm['vm_ip'  ]
	#d['user'	   ] = vm['user'   ]
	db.migration_decision.update({'vm_name':vm['vm_name']}, {'$set':d},True)

# check if the migration of the given vm completed or not
def migration_successful(vm):
	done = False
	while not done:
		doc  = db.migration_status.find_one({'vm_name':vm['vm_name']})
		if doc == None:
			continue
		done = False if doc['status'] == 'IN-PROGRESS' else True
		# if true loops out, else loop all time
	return True if db.migration_status.find_one({'vm_name':vm['vm_name']})['status'] == 'DONE' else False


# reset the status of the migration of the given vm
def reset_migration_message_for_vm(vm):
	#doc  = db.migration_status.find_one({'vm_name':vm['vm_name']})
	#doc.update({'status':'DONE'})
	#where the vm, source_ip, is something
	#db.migration_decision.remove({'vm_name':vm['vm_name']})
	# Remove entry from db
	db.migration_status.remove({'vm_name':vm['vm_name']})

'''
 Entry point. Simple logic 
'''
if __name__ == '__main__':
	#loop to find the non zero number of virtual machines

	while True:	#Run infinitely
		
		while True:
			etp = check_statistics_etp() # check the statistics of the virtual machines so as to begin with
			mtp = check_statistics_mtp() # get list of all VMs that must be pushed
			print 'ETP %d| MTP %d' % (etp.count(), mtp.count())
			if (etp.count() + mtp.count()) != 0:
				break

		# You got all vms that are mandatory to be pushed
		# Try migrating as many as possible onto server
		# NOTE : Migration is blocking
		# Also need to 
		for vm in mtp:
			available_space_flag,host_ip,user_name = select_free_client(vm) # chk if it is possible to transfer it to a client
			print available_space_flag,host_ip,user_name

			if available_space_flag == True:
				insert_migration_message(vm, host_ip, user_name) # insert a message for the virtual machine to migrate
				print '[PUSH] Attempting to migrate vm[%s] from %s@%s to %s@%s' % (vm['vm_name'],vm['user'],vm['host_ip'],user_name,host_ip)
				#wait for the migration successful message 
				done = migration_successful(vm)  # function waits for the success/failure message
				print 'Migration %s' % ('successful' if done == True else 'unsuccessful')
				reset_migration_message_for_vm(vm) # reset the migration message in the database


		# You got all vms that are eligible to be pulled
		# Migrate one vm to server & continue
		# NOTE : Migration is blocking
		for vm in etp:
			available_space_flag,server_ip,user_name = check_available_resources(vm) # check for the necessary cloud storages on the server.
			print available_space_flag,server_ip,user_name
			'''
			right now assumption is transferring only one machine to the server, however code will work 
			for multiple servers as well
			'''	
			if available_space_flag == True:
				insert_migration_message(vm, server_ip, user_name) # insert a message for the virtual machine to migrate
				print '[PULL] Attempting to migrate vm[%s] from %s@%s to %s@%s' % (vm['vm_name'],vm['user'],vm['host_ip'],user_name,server_ip)
				#wait for the migration successful message 
				done = migration_successful(vm)  # function waits for the success/failure message
				print 'Migration %s' % ('successful' if done == True else 'unsuccessful')
				reset_migration_message_for_vm(vm) # reset the migration message in the database
				break
