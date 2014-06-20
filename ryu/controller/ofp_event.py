# Copyright (C) 2012 Nippon Telegraph and Telephone Corporation.
# Copyright (C) 2011 Isaku Yamahata <yamahata at valinux co jp>
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

"""
OpenFlow event definitions.
"""

import inspect

from ryu.controller import handler
from ryu import ofproto
from ryu import utils
from . import event


class EventOFPMsgBase(event.EventBase):
    def __init__(self, msg):
        super(EventOFPMsgBase, self).__init__()
        self.msg = msg


#
# Create ofp_event type corresponding to OFP Msg
#

_OFP_MSG_EVENTS = {}
#
#_OFP_MSG_EVENTS[name] ← name に対応したクラス定義を返却してくれる
#　　　　　　　　　　　　　　通常は引数として msg を与える。

# ----------------------------------------------------------
# 概要＠イベントクラス（msgを入れてあげるとイベント（人が理解可能な
#　　　　形に変換してくれるクラス）に変換してくれるクラス
# 　1.メッセージクラス名（_ofp_msg_name_to_ev_nameで取得）
#　　　　に応じたイベントを取得
# 　２.イベントにmsg引数を与えて処理を実施


# メッセージ名をイベント名に変換する
#　→メッセージ名に Event 文字列　を先頭追加
def _ofp_msg_name_to_ev_name(msg_name):
    return 'Event' + msg_name

# メッセージをイベントに変換する（引数：メッセージ）
#　↓のofp_msg_to_ev_clsを呼び出す
def ofp_msg_to_ev(msg):
    return ofp_msg_to_ev_cls(msg.__class__)(msg)

# メッセージをイベントクラスに変換する（引数：メッセージクラス）
def ofp_msg_to_ev_cls(msg_cls):
    name = _ofp_msg_name_to_ev_name(msg_cls.__name__)
    return _OFP_MSG_EVENTS[name]


# ----------------------------------------------------------
# 概要＠イベントクラスの作成部
#

#　イベントクラス生成（内部メソッド）
def _create_ofp_msg_ev_class(msg_cls):
    #クラス定義の名前（クラス名）を取得
    name = _ofp_msg_name_to_ev_name(msg_cls.__name__)
    # print 'creating ofp_event %s' % name

    #もし、イベント一覧辞書に存在する場合は、　リターン　（処理終了）
    if name in _OFP_MSG_EVENTS:
        return

    #cls に タプルを格納
    #(name, メッセージ基底のタプル, 辞書＠謎★ )
    cls = type(name, (EventOFPMsgBase,),
               dict(__init__=lambda self, msg:
                    super(self.__class__, self).__init__(msg)))
    #★謎
    globals()[name] = cls
    #イベント一覧に key=クラス名　で　クラス定義を格納
    _OFP_MSG_EVENTS[name] = cls

#　イベントクラス生成（内部メソッド）
def _create_ofp_msg_ev_from_module(ofp_parser):
    # print mod

    # 1. ofp_parserからクラス定義を取得
    #    ★inspect.getmembers(ofp_parser, inspect.isclass):とは
    #    ★inspect.isclassとは
    for _k, cls in inspect.getmembers(ofp_parser, inspect.isclass):
        # 2. 取得したクラスに「cls_msg_type」が存在しない場合はループ継続
        # 　　※ここで取得するクラスの一覧は xxx_parser を参考のこと
        if not hasattr(cls, 'cls_msg_type'):
            continue
        # 3.　内部メソッドを呼ぶ（引数は cls_msg_type 属性を持つクラス定義）
        _create_ofp_msg_ev_class(cls)

#　イベントクラス生成のトリガ

#def get_ofp_modules():
    #"""get modules pair for the constants and parser of OF-wire of
    #a given OF version.
    #"""
    #return ofproto_protocol._versions
    #
    # ofproto_protocol._versions.values():
    #　→RYUが対応しているバージョンの　値　（orproto ofparser）　を種尾T区

for ofp_mods in ofproto.get_ofp_modules().values():
    ofp_parser = ofp_mods[1]
    # 1. RYU が対応している　of_parser を順番に取得
    # print 'loading module %s' % ofp_parser
    # 2. parserを引数として↓のメソッドに渡す
    _create_ofp_msg_ev_from_module(ofp_parser)


class EventOFPStateChange(event.EventBase):
    def __init__(self, dp):
        super(EventOFPStateChange, self).__init__()
        self.datapath = dp

#★
handler.register_service('ryu.controller.ofp_handler')
