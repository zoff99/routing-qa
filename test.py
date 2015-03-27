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

remote_object = bus.get_object("org.navit_project.navit", # Connection name
                               "/org/navit_project/navit/default_navit" ) # Object's path

iface = dbus.Interface(remote_object, dbus_interface="org.navit_project.navit")
iter = iface.attr_iter()
path = remote_object.get_attr_wi("navit",iter)
navit = bus.get_object('org.navit_project.navit', path[1])
iface.attr_iter_destroy(iter)

gpx_directory=sys.argv[1]
if not os.path.exists(gpx_directory):
    os.makedirs(gpx_directory)

junit_directory=sys.argv[2]
if not os.path.exists(junit_directory):
    os.makedirs(junit_directory)

tests=[]
for filename in glob.glob('*.yaml'):
    print "Testing "+filename
    f = open(filename)
    dataMap = yaml.safe_load(f)
    f.close()
    start_time = time.time()
    navit.set_center_by_string("geo: "+str(dataMap['from']['lng']) + " " + str(dataMap['from']['lat']))
    navit.set_position("geo: "+str(dataMap['from']['lng']) + " " + str(dataMap['from']['lat']))
    navit.set_destination("geo: "+str(dataMap['to']['lng']) + " " + str(dataMap['to']['lat']),"python dbus")
    # FIXME : we should listen to a dbus signal notifying that the routing is complete instead
    time.sleep(1)
    navit.export_as_gpx(gpx_directory+"/"+filename + ".gpx")

    doc = lxml.etree.parse(gpx_directory+"/"+filename+".gpx")
    rtept_count = doc.xpath('count(//rtept)')

    test_cases = TestCase(filename, '', time.time() - start_time, '', '')
    if not(eval(str(rtept_count) + dataMap['success']['operator'] + str(dataMap['success']['value']))):
        test_cases.add_failure_info('navigation items count mismatch')
    tests.append(test_cases)

ts = [TestSuite("Navit routing tests", tests)]

with open(junit_directory+'output.xml', 'w+') as f:
    TestSuite.to_file(f, ts, prettyprint=False)
