import subprocess
import pymongo as pm

from time import sleep


IP = "10.129.23.30"
PORT = 27017


'''
 we get the domain name to migrate from host machine to the server machine with the server machine to migrate ... blocking
 we migrate the machine to the server
 send the migration success message to the controller 
 check if no vms are lying around, if not then suspend the machine else continue 

'''


def get_my_ip():
	
	return "10.129.23.30"

def connect_db():
	con = pm.Connection(IP,PORT)
	db= con.litegreen_1
	
	return db

def where_to_migrate(handler):
	'''
		get the location and the virtual machine to migrate
	'''
	print '*'*20
	
	my_ip = get_my_ip() # get my ip address
	docs = handler.migration_decision.find({'host_ip':my_ip}) # get the document corresponding to my ip address
	
	migration_tuple = []
	for doc in docs:
		decision = doc['decision'] # check the migration decision
		if decision == "YES":	
			server_vm_user = doc['server_user']
			server_vm = doc['server_ip']  # where to migrate
			client_vm = doc['vm_name']  # which vm to migrate

			temp = []
			temp.append(server_vm_user)
			temp.append(server_vm)
			temp.append(client_vm)

			migration_tuple.append(temp)
		else:
			#sleep(10) #sleep for 10 seconds
			continue 	
	
	return migration_tuple # return the list of migration tuples
	

def set_migration_status(handler,dom,server,status):
	handler.migration_status.update({'vm_name':domain},{'$set':{'vm_name':domain,'destination_ip':server,'status':status}},True)

def do_migration(migration_details,handler):

	domain = migration_details[2] #vm to migrate
	server = migration_details[1] #where to migrate
	user   = migration_details[0] #to which user to migrate
	sucessful_migration = True
        #migration_cmd = "virsh migrate --live  ubuntu qemu+ssh://bhasky@192.168.0.103/system --verbose"
        migration_cmd = "virsh migrate --live  %s qemu+ssh://%s@%s/system --verbose"  %(domain, user, server)
	cmd= "virsh -c  qemu:///system list --all"
        try:
		
		handler.migration_status.update({'vm_name':domain},{'$set':{'vm_name':domain,'destination_ip':server,'status':"IN-PROGRESS"}},True)
                status = subprocess.call(migration_cmd,shell=True)
		#'''
		print "migration in progress"
		sleep(10)
		print "done with migration"
		handler.migration_status.update({'vm_name':domain},{'$set':{'vm_name':domain,'destination_ip':server,'status':"DONE"}},True)
		print domain,server,user
		handler.vm_statistics.update({"vm_name":domain},{'$set':{'host_ip':server,"user":user}})
		handler.migration_decision.remove({"vm_name":domain}) # remove the decision to avoid false behavior
		#'''
        except:
                print 'failed to execute'
		sucessful_migration = False
		#set_migration_status(handlerdomain,server,"FAILED")
		handler.migration_status.update({'vm_name':domain},{'$set':{'vm_name':domain,'destination_ip':server,'status':"FAILED"}},True)
                #break

#	if sucessful_migration :
#		handler.migration_status.update({'vm_name':domain},{'$set':{'vm_name':domain,'destination_ip':server,'status':"DONE"}},True)
		


'''
def send_migration_success_message(dom,status):
	d={}
	d['dom_name'] = dom
	if status ==  0:
		d['migration_status'] = 'SUCCESSFUL'
	else:
		d['migration_status'] = 'UNSUCCESSFUL'
'''


if __name__ == '__main__':

	handler=connect_db() # get the handler of the database
	
	while True:
		migrate_tuples = where_to_migrate(handler) # get all the tuples to migrate
		sleep(1)
		print migrate_tuples
		for t in migrate_tuples:
		
			status = do_migration(t,handler) # migarte individual tuple 
			#should_continue_migration() # should check if we should proceed with migration on a particular server
			'''
			before every migration call, go ask controller if for the t[1] server whether it is possible to migrate or what
			if controller says, yes then migrate else ditch the migration
			
			the controller needs to remove status message from the migration_status collection.

			check if no vms are lying around to suspend the machine.
			'''
		#suspend_physical_machine()	
