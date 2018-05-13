from __future__ import (unicode_literals, division, absolute_import, print_function)

import re
import os
import socket

from powerline.segments import with_docstring, Segment
from powerline.theme import requires_segment_info


@requires_segment_info
class Hostname(Segment):
    def __call__(self, pl, segment_info, only_if_ssh=False, exclude_domain=False):
        if only_if_ssh and not segment_info['environ'].get('SSH_CLIENT'):
                return None
        if exclude_domain:
                return socket.gethostname().split('.')[0]
        return [
            {
                'contents': '',
                'highlight_groups': ['hole']
            },
            {
                'contents': '⌂ {}'.format(socket.gethostname()),
            }
        ]


hostname = with_docstring(Hostname(),
    '''Return the current hostname.
        :param bool only_if_ssh:
            only return the hostname if currently in an SSH session
        :param bool exclude_domain:
            return the hostname without domain if there is one
    ''')

