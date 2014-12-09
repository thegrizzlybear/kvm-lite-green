'''
	give out the server characteristics - entry in host_statistics
	update host_ip in vm_statistics  **
	update server_vm_container **
	
'''

import linux_metrics as lm
from time import time,sleep

import psutil as ps

import pymongo as pym
import libvirt
import os
################# DB details ######################
IP = "10.129.23.30"
PORT=27017
###################################################

########### SERVER Details #######################
USER = 'uddhav'
SERVER_IP = "10.129.23.30"

###################################################

def connect_db():
	con = pym.Connection(IP,PORT)	
	db = con.litegreen_1
	
	return db
	
def getCoreFrequency(core_number):
        '''
                get the frequency of the core
        '''
        cmd="cat /proc/cpuinfo| grep 'cpu MHz'| sed -n '%d p' | cut -d ':' -f 2" %(core_number+1)
        output = os.popen(cmd)
        return float(output.read().strip("\n\r "))


def all_cpu_usage():
	all_cpus = ps.cpu_times_percent(interval=1,percpu=True)
	core_details = []
	core_count = ps.cpu_count()
	for i in range(core_count):
		usage = 100.0 - all_cpus[i][3]
		frequency = getCoreFrequency(i)
		
		d  ={}
		d['usage'] = usage
		d['frequency'] = frequency

		core_details.append(d)
		

	return [core for core in core_details] # return a list of core details



def cpu_usage():
	cpu_pcts = lm.cpu_stat.cpu_percents(sample_duration=1)
	usage = 100 - cpu_pcts['idle']

	return usage



def mem_usage():
	mem = lm.mem_stat.mem_stats()
	return mem[0],mem[1],mem[1]-mem[0]


def cpu_load():
	load = lm.cpu_stat.load_avg()

	return load[1],load[2]

def getVCPUS(domain,handler,cores):
        '''
                returns list of tuple (vcpu,real_cpu) i.e. which vpcu is mapped to which real cpu
        '''
        vcpu_map_cpu = []

        vcpus = domain.vcpus() # get the information about the vcpu for a domain
        vcpu_states = vcpus[0]
        number_of_vcpus = len(vcpu_states) # get the number of vcpus belonging to a vm
        for mapping in range(number_of_vcpus):

                vm_cpu = vcpu_states[mapping][0] # what is the vcpu number 
                real_cpu = vcpu_states[mapping][3] # what is the real cpu number
                core_freq = getCoreFrequency(real_cpu)  # what is the frequency of the core 
                #l = (vm_cpu,real_cpu,core_freq)
	
		core_usage = cores[real_cpu]['usage']
	
		handler.vm_statistics.update({"vm_name":domain.name()},{'$set':{"core_frequency":core_freq,"core_usage":core_usage}}) # assuming virtual machine with 1vcpu 
	
                #vcpu_map_cpu.append(l) # append the mapping of virtual cpu to real cpu
        #return vcpu_map_cpu



def update_host_ip(handler,cores):
	con = libvirt.open("qemu:///system")
	ids = con.listDomainsID() # get a list of active domains
		
	domain_names = []
	domains = []

	MAP = [] # list of vcpu to real cpu map with the  instantaneous core frequency; instantaneous because bl***y DVFS enabled
	for id_ in ids:
		dom = con.lookupByID(id_)
		domains.append(dom) # get the list of domain object
		domain_names.append(dom.name()) # get a list of names of active domains
	print domain_names
	
	for dom in domains:
		getVCPUS(dom,handler,cores) # updates the core frequency in the domain document
               # l = [dom.name(),vcpus]
               # MAP.append(l)
	
	for name in domain_names:
		print name
		handler.vm_statistics.update({"vm_name":name},{"$set":{"host_ip":SERVER_IP,"user":USER}})	



def dump_statistics(handler):
	#update_host_ip(handler)
	while True:
		cpu = cpu_usage()
		cores = all_cpu_usage()
		used,total,free = mem_usage()
		load_5,load_15 =  cpu_load()

		
		update_host_ip(handler,cores)

		handler.host_statistics.update({'ip':SERVER_IP},{'$set':{'ip':SERVER_IP,'user':USER,'cpu':cpu,'all_cpu':cores,'mem_used':used,'mem_total':total,'mem_free':free,'5_min':load_5,'15_min':load_15}},True)
		#update_host_ip(handler)

		print "%f %f %f %f %f" %(cpu,used,total,load_5,load_15)
		print cores
		sleep(5)


if __name__ == '__main__':
	handler = connect_db() # connect to the database
	#while True:
	dump_statistics(handler)  # collec cpu, mem and load statistics and place it in the db
	#sleep(5) # sleep for a second
#	all_cpu_usage()
