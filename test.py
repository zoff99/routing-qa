import glob
import yaml
import dbus
from dbus import glib
import time
import lxml.etree
import gobject
import sys
import os
from subprocess import call
from junit_xml import TestSuite, TestCase


gobject.threads_init()

glib.init_threads()

bus = dbus.SessionBus()

navit_object = bus.get_object("org.navit_project.navit", # Connection name
                               "/org/navit_project/navit/default_navit" ) # Object's path

iface = dbus.Interface(navit_object, dbus_interface="org.navit_project.navit")
iter = iface.attr_iter()
path = navit_object.get_attr_wi("navit",iter)
navit = bus.get_object('org.navit_project.navit', path[1])
iface.attr_iter_destroy(iter)

route_object = bus.get_object('org.navit_project.navit', '/org/navit_project/navit/default_navit/default_route' )
route = dbus.Interface(route_object, 'org.navit_project.navit.route')

gpx_directory=sys.argv[1]
if not os.path.exists(gpx_directory):
    os.makedirs(gpx_directory)

junit_directory=sys.argv[2]
if not os.path.exists(junit_directory):
    os.makedirs(junit_directory)

export_suffix=sys.argv[3]

tests=[]
for filename in glob.glob('*.yaml'):
    f = open(filename)
    dataMap = yaml.safe_load(f)
    f.close()
    print ""
    print "Testing "+filename+" : "+str(dataMap['from']['lat']) + "," + str(dataMap['from']['lng']) +" to "+str(dataMap['to']['lat']) + "," + str(dataMap['to']['lng'])
    print "http://www.openstreetmap.org/directions?engine=osrm_car&route="+str(dataMap['from']['lat']) + "%2C" + str(dataMap['from']['lng']) +"%3B"+str(dataMap['to']['lat']) + "%2C"+ str(dataMap['to']['lng'])
    print "https://graphhopper.com/maps/?point="+str(dataMap['from']['lat']) + "%2C" + str(dataMap['from']['lng']) +"&point="+str(dataMap['to']['lat']) + "%2C"+ str(dataMap['to']['lng'])
    print "http://www.google.com/maps/dir/"+str(dataMap['from']['lat']) + "," + str(dataMap['from']['lng']) +"/"+str(dataMap['to']['lat']) + ","+ str(dataMap['to']['lng'])
    start_time = time.time()
    try:
        navit.clear_destination()
        navit.set_position("geo: "+str(dataMap['from']['lng']) + " " + str(dataMap['from']['lat']))
        navit.set_destination("geo: "+str(dataMap['to']['lng']) + " " + str(dataMap['to']['lat']),"python dbus")
        # FIXME : we should listen to a dbus signal notifying that the routing is complete instead
        timeout=50
        status=-1
        while timeout>0 and ( status!=33 and status!=17 ):
            try:
               status=route.get_attr("route_status")[1]
               distance=route.get_attr("destination_length")[1]
               print "Route status : "+str(status)+", distance : "+str(distance)+ ", duration : "+str(time.time() - start_time)
               time.sleep(1)
            except:
               time.sleep(1)
            timeout-=1
        if timeout>0 :
            navit.export_as_gpx(gpx_directory+"/"+filename + export_suffix + ".gpx")
            navit.export_as_geojson(gpx_directory+"/"+filename + export_suffix + ".geojson")
            if 'capture' in dataMap:
               if 'zoom_level' in dataMap['capture']:
                 print "Forcing zoom to "+str(dataMap['capture']['zoom_level'])
                 iface2 = dbus.Interface(navit_object, dbus_interface="org.navit_project.navit.navit")
                 iface2.set_attr("zoom", dataMap['capture']['zoom_level'])
               if 'lng' in dataMap['capture']:
                 print "Setting the view center to "+str(dataMap['capture']['lng']) + "," + str(dataMap['capture']['lat'])
                 navit.set_center_by_string("geo: "+str(dataMap['capture']['lng']) + " " + str(dataMap['capture']['lat']))
            else:
                navit.zoom_to_route()
            time.sleep(0.5)    
            os.system("/usr/bin/import -window root "+gpx_directory+"/"+filename+export_suffix + ".png")
        else:
            print "No route found, last status : " + str(status) + ", duration : "+str(time.time() - start_time)

        test_cases = TestCase(filename, '', time.time() - start_time, '', '')
        if dataMap['success']['source'] == 'gpx' :
            doc = lxml.etree.parse(gpx_directory+"/"+filename+export_suffix + ".gpx")
            rtept_count = doc.xpath('count(//rtept)')
        
            if not(eval(str(rtept_count) + dataMap['success']['operator'] + str(dataMap['success']['value']))):
                test_cases.add_failure_info('navigation items count mismatch [ got ' + \
                    str(rtept_count) + ", expected " + dataMap['success']['operator'] + str(dataMap['success']['value']) ) 
                print "navigation items count mismatch [ got " + \
                    str(rtept_count) + ", expected " + dataMap['success']['operator'] + str(dataMap['success']['value'])
        elif dataMap['success']['source'] == 'dbus' :
            if not(eval(dataMap['success']['item'] + dataMap['success']['operator'] + str(dataMap['success']['value']))):
                test_cases.add_failure_info('dbus result mismatch [ got ' + \
                    str(eval(str(dataMap['success']['item']))) + dataMap['success']['operator'] + str(dataMap['success']['value']) )
                print "dbus result mismatch [ got " + \
                    str(eval(str(dataMap['success']['item']))) + dataMap['success']['operator'] + str(dataMap['success']['value'])
    except:
       # We had a failure, like navit crash, dbus timeout, ...

       print "This test failed. Maybe a missing map?"
       test_cases = TestCase(filename, '', time.time() - start_time, '', '')
       test_cases.add_error_info('test failed')
    tests.append(test_cases)

ts = [TestSuite("Navit routing tests", tests)]

with open(junit_directory+'output.xml', 'w+') as f:
    TestSuite.to_file(f, ts, prettyprint=False)
