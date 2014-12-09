from linux_metrics import cpu_stat, mem_stat
from time import sleep

from pymongo import Connection



db= 'litegreen_1'
db_host = "10.129.23.30"
db_port = 27017
db_collection = "vm_statistics"

#####################################

DOMAIN = "ubuntu"
VM_IP = "10.129.23.34"




####################################



def connect_db():
	con = Connection(db_host,db_port) #connect to the host
	d_b = con.litegreen_1 # select the database
	col = d_b.vm_statistics # select the collection
 
	return col
'''
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
'''	


def dump_stats(handler):
	while True:
		cpu_pcts = cpu_stat.cpu_percents(1) #instantaneous cpu usage
		utilization = 100 - cpu_pcts['idle']

		#cores = all_cpu_usage()
		load_ = cpu_stat.load_avg()
		load_5,load_15 = load_[1],load_[2]
		
		mem_tuple = mem_stat.mem_stats() #instantaneous memory usage
		used,total = mem_tuple[0],mem_tuple[1]

		free = total - used
		
			
		
		
		handler.update({"vm_name":DOMAIN},{"$set":{"vm_name":DOMAIN,"vm_ip":VM_IP,"cpu":utilization,"5_min":load_5,"15_min":load_15,"mem_free":free,"mem_used":used,"mem_total":total,"mouse":"no"}},True)	 # update if document present else insert the document. update the cpu,mem of the virtual every 5 seconds
		print "upated the tuple"

		sleep(5)	

if __name__ == '__main__':
	col = connect_db()

	dump_stats(col)
