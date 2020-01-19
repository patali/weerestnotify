import json
import re
import time

import weechat as w
import hmac
import hashlib
import base64
from urllib import urlencode


SCRIPT_NAME = 'weerestnotify'
SCRIPT_AUTHOR = 'patali'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'MIT'
SCRIPT_DESC = 'Push notifications from WeeChat to a rest api endpoint'

help_text = '''
[commands]
    show_config           Shows your current configuration details
    test                  Sends "Hello world" message to the end point

[settings]: (prefix with plugins.var.python.weerestnotify.<setting>)
    encryption_key        Shared key used for encryption of the notification messages (required)
    end_point_url         Endpoint where the message has to be sent to (required)
'''

configs = {
    'encryption_key': '_required',
    'end_point_url': '_required',
}


def register():
    w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')

def log(msg):
    w.prnt('', '[weerestnotify] debug: {}'.format(str(msg)))

def load_settings():
    for (option, default_value) in configs.items():
        if w.config_get_plugin(option) == '':
            if configs[option] == '_required':
                log('missing plugins.var.python.weerestnotify.{}'.format(option))
            else:
                w.config_set_plugin(option, configs[option])

def setup_hooks():
    global SCRIPT_NAME
    global SCRIPT_DESC
    global help_text

    w.hook_print('', '', '', 1, 'message_hook', '')
    w.hook_command(SCRIPT_NAME, SCRIPT_DESC, '[command] show_config/test', help_text, '', 'handle_argument', '')


def get_channels(kind):
    channels = w.config_get_plugin('{}_channels'.format(kind)).strip()
    if channels == '':
        return set([])
    else:
        return set([channel.strip() for channel in channels.split(' ') if channel])


def handle_argument(data, buffer, args):
    if(args == 'show_config'):
        w.prnt('', 'Show config')
    elif(args == 'test'):
        send_push('weerestnotify', 'This is a test message from weerestnotify notification plugin')
    else:
        w.prnt('', help_text)
    return w.WEECHAT_RC_OK


def get_buf_name(bufferp):
    short_name = w.buffer_get_string(bufferp, 'short_name')
    name = w.buffer_get_string(bufferp, 'name')
    return (short_name or name).decode('utf-8')


def is_ignored(bufferp):
    buf_name = get_buf_name(bufferp)
    return buf_name in get_channels('ignored')


def is_subscribed(bufferp):
    buf_name = get_buf_name(bufferp)
    return buf_name in get_channels('subscribed')


def message_hook(data, bufferp, uber_empty, tagsn, is_displayed, is_highlighted, prefix, message):
    is_pm = w.buffer_get_string(bufferp, 'localvar_type') == 'private'
    regular_channel = not is_subscribed(bufferp) and not is_pm

    if is_ignored(bufferp) and regular_channel:
        log('ignored regular channel skipping')
        return w.WEECHAT_RC_OK
       
    if not is_displayed:
        log('not a displayed message skipping')
        return w.WEECHAT_RC_OK

    if not is_highlighted and regular_channel:
        return w.WEECHAT_RC_OK

    log('passed all checks')

    if is_pm:
        title = 'Private message from {}'.format(prefix.decode('utf-8'))
    else:
        title = 'Message on {} from {}'.format(get_buf_name(bufferp), prefix.decode('utf-8'))

    send_push(title=title, message=message.decode('utf-8'))

    return w.WEECHAT_RC_OK


def http_request_callback(data, url, status, response, err):
    j = json.loads(response)
    if j['ok'] != True:
        w.prnt('', '[weerestnotify] error: {}'.format(response))
        return w.WEECHAT_RC_ERROR

    return w.WEECHAT_RC_OK


def send_push(title, message):
    postfields = {
        'title': title,
        'text': message
    }

    w.hook_process_hashtable(
        'url: %s' % w.config_get_plugin('end_point_url'),
        {
            "httpheader" : "\n".join([
                "Content-Type: application/x-www-form-urlencoded"
                ]),
            "postFields": urlencode(postfields)
        },
        20*1000,
        'http_request_callback',
        ''
    )

def main():
    register()
    load_settings()
    setup_hooks()

main()
