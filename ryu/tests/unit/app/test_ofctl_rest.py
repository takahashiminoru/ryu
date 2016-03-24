# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# vim: tabstop=4 shiftwidth=4 softtabstop=4

import functools
import unittest
import logging
import os
import sys
import json

from nose.tools import eq_
from webob.request import Request

from ryu.app.wsgi import WSGIApplication

from ryu.app import ofctl_rest
from ryu.controller import dpset
from routes import Mapper
from routes.util import URLGenerator

from ryu.ofproto import ofproto_protocol
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_2
from ryu.ofproto import ofproto_v1_3
from ryu.tests import test_lib

mapper = Mapper()

LOG = logging.getLogger(__name__)
DPID = 1
PORT = 1
QUEUE = 1
XID = 0

# Specify request message path which use POST method
POST_PATH_LIST = [
    '/stats/flow/{dpid}',
    '/stats/aggregateflow/{dpid}',
    '/stats/flowdesc/{dpid}'
]


class DummyDatapath(ofproto_protocol.ProtocolDesc):

    def __init__(self, version):
        super(DummyDatapath, self).__init__(version)
        self.id = DPID
        self.request_msg = None
        self.waiters = None
        _kw = {'port_no': DPID, 'hw_addr': 'ce:0f:31:8a:c8:d9',
               'name': 's1-eth1', 'config': 1, 'state': 1}
        # for OpenFlow1.0
        if version in [ofproto_v1_0.OFP_VERSION]:
            _kw.update(
                {'curr': 2112, 'advertised': 0, 'supported': 0, 'peer': 0})
            port_info = self.ofproto_parser.OFPPhyPort(**_kw)
        # for OpenFlow1.2 or 1.2
        elif version in [ofproto_v1_2.OFP_VERSION, ofproto_v1_3.OFP_VERSION]:
            _kw.update(
                {'curr': 2112, 'advertised': 0, 'supported': 0, 'peer': 0,
                 'curr_speed': 10000000, 'max_speed': 0})
            port_info = self.ofproto_parser.OFPPort(**_kw)
        # for OpenFlow1.4 or later
        else:
            _kw.update({'properties': []})
            port_info = self.ofproto_parser.OFPPort(**_kw)
        self.ports = {DPID: port_info}

    @staticmethod
    def set_xid(msg):
        msg.set_xid(XID)
        return XID

    def send_msg(self, msg):
        msg.serialize()
        self.request_msg = msg

        if self.method == 'GET' or self.path in POST_PATH_LIST:
            lock, msgs = self.waiters[DPID][XID]
            del self.waiters[self.id][msg.xid]
            lock.set()

    def set_waiters(self, waiters, method, path):
        assert self.waiters is None
        self.waiters = waiters
        self.method = method
        self.path = path


class Test_ofctl_rest(unittest.TestCase):

    def _test(self, name, dp, method, path, args, body):
        print('processing %s ...' % name)

        # ----------------------------------
        # 1. Get the function to be tested
        # ----------------------------------

        self._contexts = {
            'dpset': dpset.DPSet(),
            'wsgi': WSGIApplication()
        }
        self.ofctl_rest_app = ofctl_rest.RestStatsApi(**self._contexts)

        # The following code is to shorten
        # the test execution time (1)
        waiters = {}
        dp.set_waiters(waiters, method, path)

        # set static values
        r = Request.blank('')
        l = URLGenerator(Mapper(), r.environ)
        d = self.ofctl_rest_app.data
        d['dpset']._register(dp)

        # ----------------------------------
        # 2. Get the function to be tested
        # ----------------------------------

        dic = self._contexts['wsgi'].mapper.match(
            path, {'REQUEST_METHOD': method})
        if dic is None:
            raise Exception("\"%s %s\" is not implemented" %
                            (method, path))

        # create a instance of StatsController class
        controller_cls = dic['controller']
        controller_ins = controller_cls(r, l, d)

        # The following code is to shorten
        # the test execution time (2)
        controller_ins.waiters = waiters

        # get a func of StatsController (ex. 'get_flow_stats')
        func_name = dic['action']
        func = getattr(controller_ins, func_name)

        # ----------------------------------
        # 3. Run the tests
        # ----------------------------------

        req = Request.blank('')
        req.body = body

        # test
        res = func(req, **args)
        eq_(res.status, '200 OK')


def _add_tests():

    _ofp_vers = {
        'of10': 0x01,
        'of12': 0x03,
        'of13': 0x04,
        'of14': 0x05,
        'of15': 0x06
    }

    this_dir = os.path.dirname(sys.modules[__name__].__file__)
    ofctl_rest_json_root = os.path.join(this_dir, 'ofctl_rest_json/')

    for ofp_ver in _ofp_vers.keys():
        ofctl_rest_json_dir = os.path.join(ofctl_rest_json_root, ofp_ver)

        # read a json file
        json_path = os.path.join(ofctl_rest_json_dir, 'test.json')
        if os.path.exists(json_path):
            _test_cases = json.load(open(json_path))

        # add test
        for test in _test_cases:

            # create value of body
            if test['method'] in ['POST', 'PUT', 'DELETE']:
                dic_ = test.get('body', {"dpid": DPID})
                str_ = json.dumps(dic_)
            else:
                str_ = json.dumps('')

            body = str_.encode('utf-8')

            assert isinstance(body, bytes)

            # create func name
            path = test['path']
            cmd = test['args'].get('cmd', None)
            if cmd:
                path = path.replace('cmd', 'cmd=' + str(cmd))
            name = 'test_ofctl_rest_' + \
                test['method'] + '_' + ofp_ver + '_' + path

            # adding test method
            print('adding %s ...' % name)
            f = functools.partial(
                Test_ofctl_rest._test, name=name,
                dp=DummyDatapath(_ofp_vers[ofp_ver]),
                method=test['method'],
                path=test['path'],
                args=test['args'],
                body=body
            )
            test_lib.add_method(Test_ofctl_rest, name, f)

_add_tests()

if __name__ == "__main__":
    unittest.main()
