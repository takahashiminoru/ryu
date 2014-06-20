# Copyright (C) 2014 Nippon Telegraph and Telephone Corporation.
# Copyright (C) 2014 YAMAMOTO Takashi <yamamoto at valinux co jp>
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

from . import ofproto_v1_0
from . import ofproto_v1_0_parser
from . import ofproto_v1_2
from . import ofproto_v1_2_parser
from . import ofproto_v1_3
from . import ofproto_v1_3_parser
from . import ofproto_v1_4
from . import ofproto_v1_4_parser


# RYU が対応しているバージョンを列挙
_versions = {
    ofproto_v1_0.OFP_VERSION: (ofproto_v1_0, ofproto_v1_0_parser),
    ofproto_v1_2.OFP_VERSION: (ofproto_v1_2, ofproto_v1_2_parser),
    ofproto_v1_3.OFP_VERSION: (ofproto_v1_3, ofproto_v1_3_parser),
    ofproto_v1_4.OFP_VERSION: (ofproto_v1_4, ofproto_v1_4_parser),
}

# ↑のキーをサポートバージョンとして、をset型で取得
# OF versions supported by every apps in this process (intersection)
_supported_versions = set(_versions.keys())


# アプリケーションのサポートバージョンを設定
#　→逆に、これを設定しなかった場合、APPの対応versionは↑の1.1～1.4までとなる。
def set_app_supported_versions(vers):
    # サポートバージョンを編集可能できるように宣言
    global _supported_versions

    # サポートバージョンとversのアンドをとる
    _supported_versions &= set(vers)
    # _versions 不在のバージョンを指定しようとした場合、assertエラー
    assert _supported_versions, 'No OpenFlow version is available'


class ProtocolDesc(object):
    """
    OpenFlow protocol version flavor descriptor
    """

    def __init__(self, version=None):
        if version is None:
            version = max(_supported_versions)
            #  versionがNoneの場合、
            #  ↑で設定したサポートバージョンのうち、最大のものを利用
            # 　設定可能なのは、「アプリとしてサポートしているバージョン」
            #　　そのため、　バージョン 1.2 1.3 対応　とした場合
            #
        self.set_version(version)

    # self.ofproto, self.ofproto_parser　を
    # バージョンに応じたもので初期化設定

    # たとえば、ProtocolDesc初期化時の　指定が　version = 1.3　の場合
    # Supported_verison が [1.3 1.4]だったら
    # 1.3 でつながる。
    # OFP_VERSIONSを上書き
    # 元々　[1.3]　を
    #[1.3 1.4]　や　[1.3]　や　[1.4]　で上書き
    #
    #
    #

    def set_version(self, version):
        assert version in _supported_versions
        (self.ofproto, self.ofproto_parser) = _versions[version]

    @property
    def supported_ofp_version(self):
        return _supported_versions
