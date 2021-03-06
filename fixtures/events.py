import logging
import requests
import socket
import subprocess
import time
from datetime import datetime

import pytest
from jinja2 import Template
from py.path import local

from utils.conf import cfme_data


def get_current_time_GMT():
    """ Because SQLite loves GMT.
    """
    return datetime.strptime(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "%Y-%m-%d %H:%M:%S")


class HTMLReport(object):
    def __init__(self, events):
        self.events = events

    def generate(self, filename):
        tpl_filename = local(__file__)\
            .new(basename='../data/templates/event_testing.html')\
            .strpath

        with open(tpl_filename, "r") as tpl, \
                open(filename, "w") as f:
            template = Template(tpl.read())
            f.write(template.render(events=self.events, num_events=len(self.events)))


class EventExpectation(object):
    """ Expectation for an event.

    This object embeds an expectation in order to be able to easily compare
    whether the two expectations are the same but just with different time.
    """

    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, sys_type, obj_type, obj, event, time=None):
        self.sys_type = sys_type
        self.obj_type = obj_type
        self.obj = obj
        self.event = event
        self.arrived = None
        if time:
            self.time = time
        else:
            self.time = get_current_time_GMT()

    def __eq__(self, other):
        try:
            assert self.sys_type == other.sys_type
            assert self.obj_type == other.obj_type
            assert self.obj == other.obj
            assert self.event == other.event
            return True
        except (AssertionError, AttributeError):
            return False

    @property
    def colour(self):
        return "green" if self.arrived else "red"

    @property
    def time_friendly(self):
        return datetime.strftime(self.time, self.TIME_FORMAT)

    @property
    def success_friendly(self):
        return "success" if self.arrived else "failed"

    @property
    def time_difference(self):
        if self.arrived:
            td = self.arrived - self.time
            return int(round(td.total_seconds()))
        else:
            return "Did not come :("


class EventListener(object):

    TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"

    def __init__(self, listener_port, settle_time, log_file="test_events.log"):
        self.listener_port = int(listener_port)
        listener_filename = local(__file__).new(basename='../scripts/listener.py').strpath
        self.listener_script = "%s %d" % (listener_filename, self.listener_port)
        self.settle_time = int(settle_time)
        self.expectations = []
        logging.basicConfig(filename=log_file, level=logging.INFO)
        self.listener = None

    def get_listener_host(self):
        return "http://%s" % self.get_ip_address()

    def get_ip_address(self):
        """ This returns this machine's active IP address.

        It uses Sean's service to query the address.
        """
        data = cfme_data.get("event_testing")
        assert data, "No event_testing section in cfme_data yaml"
        ipecho = data.get("ip_echo")
        assert ipecho, "No event_testing/ip_echo in cfme_data yaml"
        try:
            host = ipecho["host"]
            port = int(ipecho["port"])
        except (TypeError, KeyError):
            raise Exception("Could not read data from event_testing/ip_echo/{host, port}")
        connection = socket.create_connection((host, port))
        try:
            return str(connection.recv(39)).strip()
        finally:
            connection.close()

    def _get(self, route):
        """ Query event listener
        """
        assert not self.finished, "Listener dead!"
        listener_url = "%s:%d" % (self.get_listener_host(), self.listener_port)
        logging.info("checking api: %s%s" % (listener_url, route))
        r = requests.get(listener_url + route)
        r.raise_for_status()
        response = r.json()
        logging.debug("Response: %s" % response)
        return response

    def mgmt_sys_type(self, sys_type, obj_type):
        """ Map management system type from cfme_data.yaml to match event string
        """
        # TODO: obj_type ('ems' or 'vm') is the same for all tests in class
        #       there must be a better way than to pass this around
        ems_map = {"rhevm": "EmsRedhat",
                   "virtualcenter": "EmsVmware"}
        vm_map = {"rhevm": "VmRedhat",
                  "virtualcenter": "VmVmware"}
        if obj_type in "ems":
            return ems_map.get(sys_type)
        elif obj_type in "vm":
            return vm_map.get(sys_type)

    def check_db(self, sys_type, obj_type, obj, event, after=None, before=None):
        """ Utility to check listener database for event

        :param after: Return only events that happened AFTER this time
        :param before: Return only events that happened BEFORE this time

        Both can be combined. If None, then the filter won't be applied.
        """
        max_attempts = 2
        sleep_interval = 5
        req = "/events/%s/%s?event=%s" % (self.mgmt_sys_type(sys_type, obj_type), obj, event)
        # Timespan limits
        if after:
            req += "&from_time=%s" % datetime.strftime(after, self.TIME_FORMAT)
        if before:
            req += "&to_time=%s" % datetime.strftime(before, self.TIME_FORMAT)

        for attempt in range(1, max_attempts + 1):
            data = self._get(req)
            try:
                assert len(data) > 0
            except AssertionError as e:
                if attempt < max_attempts:
                    logging.debug("Waiting for DB (%s/%s): %s" % (attempt, max_attempts, e))
                    time.sleep(sleep_interval)
                    pass
                # Enough sleeping, something went wrong
                else:
                    logging.exception("Check DB failed. Max attempts: '%s'." % (max_attempts))
                    return False
            else:
                # No exceptions raised
                logging.info("DB row found for '%s'" % req)
                return datetime.strptime(data[0]["event_time"], "%Y-%m-%d %H:%M:%S")
        return False

    def check_all_expectations(self):
        """ Check whether all triggered events have been captured.

        Sets a flag for each event.

        Simplified to check just against the time of registration
        and the begin of this check.

        @todo: Wouldn't it be better with also a event list from the listener?
        """
        check_started = get_current_time_GMT()
        for expectation in self.expectations:
            # Get the events with the same parameters, just with different time
            the_same = [item
                        for item
                        in self.expectations
                        if item == expectation and item is not expectation
                        ]
            # Split them into preceeding and following events
            preceeding_events = [event
                                 for event
                                 in the_same
                                 if event.time <= expectation.time and event is not expectation
                                 ]
            # Get immediate predecessor's of follower's time of this event
            preceeding_event = preceeding_events[-1].time if preceeding_events else expectation.time
            #following_event = following_events[0].time if following_events else check_started
            # Shorten the params
            params = [expectation.sys_type,
                      expectation.obj_type,
                      expectation.obj,
                      expectation.event]
            came = self.check_db(*params, after=preceeding_event, before=check_started)
            if came:
                expectation.arrived = came
        return self.expectations

    @property
    def expectations_count(self):
        return len(self.expectations)

    def add_expectation(self, sys_type, obj_type, obj, event):
        expectation = EventExpectation(sys_type, obj_type, obj, event)  # Time added automatically
        self.expectations.append(expectation)

    def __call__(self, sys_type, obj_type, obj, events):
        if not isinstance(events, list):
            events = [events]
        for event in events:
            print "Registering event", event
            logging.info("Event registration: \n%s" % str(locals()))    # Debug
            self.add_expectation(sys_type, obj_type, obj, event)

    @pytest.fixture(scope="session")
    def register_event(self):
        """ Event registration fixture

        This fixture is used to notify the testing system that some event
        should have occured during execution of the test case using it.
        It does not register anything by itself, but it is used as a
        function like this::

        >>> def test_something(foo, bar, register_event):
        ...     register_event("systype", "objtype", "obj", "event")
        ...     # or
        ...     register_event("systype", "objtype", "obj", ["event1", "event2"])
        ...     # do_some_stuff_that_triggers()

        It also registers the time when the registration was done so we can filter
        out the same events, but coming in other times (like vm on/off/on/off will
        generate 3 unique events, but twice, distinguishable only by time).
        It can also partially prevent scumbag 'Jimmy' ruining the test if he does
        something in the hypervisor that the listener registers.
        """
        return self

    @pytest.fixture(scope="session")
    def listener_info(self):
        """ Listener fixture

        This fixture provides listener's address and port.
        It is used in setup test cases located at:
        ``/tests/test_setup_event_testing.py``
        """
        return type(
            "Listener",
            (object,),
            {
                "host": self.get_listener_host(),
                "port": self.listener_port
            }
        )

    @property
    def finished(self):
        if not self.listener:
            return True
        return self.listener.poll() is not None

    def start(self):
        assert not self.listener, "Listener can't be running in order to start it!"
        logging.info("Starting listener...\n%s" % self.listener_script)
        self.listener = subprocess.Popen(self.listener_script,
                                         stderr=subprocess.PIPE,
                                         shell=True)
        logging.info("(%s)\n" % self.listener.pid)
        time.sleep(3)
        assert not self.finished, "Listener has died. Something must be blocking selected port"
        logging.info("Listener alive")

    def stop(self):
        assert self.listener, "Listener must be running in order to stop it!"
        logging.info("\nKilling listener (%s)..." % (self.listener.pid))
        self.listener.kill()
        (stdout, stderr) = self.listener.communicate()
        self.listener = None
        logging.info("%s\n%s" % (stdout, stderr))

    def pytest_unconfigure(self, config):
        """ Collect and clean up the testing.

        If the event testing is active, collects results, stops the listener
        and generates the report.
        """
        if config.getoption("event_testing_enabled"):
            # Collect results
            try:
                print "Collecting event testing results ..."
                assert not self.finished, "Listener died prematurely!"
                print "Waiting %d seconds for any remaining events to come ..." % self.settle_time
                time.sleep(self.settle_time)
                print "Running check ..."
                expectations_list = self.check_all_expectations()
                # Generate result report
                report = HTMLReport(expectations_list)
                report.generate(config.getoption("event_testing_result"))
            finally:
                self.stop()
        else:
            print "Event testing disabled, no collecting, no reports"


def pytest_addoption(parser):
    parser.addoption('--event-testing',
                     action='store_true',
                     dest='event_testing_enabled',
                     default=False,
                     help='Enable testing of the events. (default: %default)')
    parser.addoption('--event-testing-result',
                     action='store',
                     dest='event_testing_result',
                     default="events.html",
                     help='Filename of result report. (default: %default)')
    parser.addoption('--event-testing-port',
                     action='store',
                     dest='event_testing_port',
                     default="65432",
                     help='Port of the testing listener. (default: %default)')
    parser.addoption('--event-testing-settletime',
                     action='store',
                     dest='event_testing_settletime',
                     default=60,
                     help='Time to wait after all testing has been finished' +
                     'for remaining events to come. (default: %default)')


def pytest_configure(config):
    """ Event testing setup.

    Sets up and registers the EventListener plugin for py.test.
    If the testing is enabled, listener is started.
    """
    plugin = EventListener(config.getoption("event_testing_port"),
                           config.getoption("event_testing_settletime"))
    registration = config.pluginmanager.register(plugin, "event_testing")
    assert registration
    if config.getoption("event_testing_enabled"):
        plugin.start()
