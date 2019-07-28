# Copyright 2019 DT42
#
# This file is part of BerryNet.
#
# BerryNet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BerryNet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BerryNet.  If not, see <http://www.gnu.org/licenses/>.

# Reference
# https://www.geeksforgeeks.org/send-mail-attachment-gmail-account-using-python/

"""Gmail client sends an email with inference result.

The email will contain two attachments: image and text.
"""

import argparse
import json
import logging
import os
import smtplib

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from os.path import join as pjoin

from berrynet import logger
from berrynet.comm import Communicator
from berrynet.comm import payload


def create_mime_attachment(filepath):
    filename = os.path.basename(filepath)
    attachment = open(filepath, "rb")

    # instance of MIMEBase and named as p
    p = MIMEBase('application', 'octet-stream')
    # To change the payload into encoded form
    p.set_payload(attachment.read())
    # encode into base64
    encoders.encode_base64(p)
    p.add_header('Content-Disposition',
                 "attachment; filename= %s" % filename)
    return p


def send_email_text(sender_address,
                    sender_password,
                    receiver_address,
                    body='',
                    subject='BerryNet mail client notification',
                    attachments=None):
    # instance of MIMEMultipart
    msg = MIMEMultipart()

    msg['From'] = sender_address
    msg['To'] = receiver_address
    msg['Subject'] = subject
    logger.debug('Sender: {}'.format(msg['From']))
    logger.debug('Receiver: {}'.format(msg['To']))
    logger.debug('Subject: {}'.format(msg['Subject']))

    # attach the body with the msg instance
    msg.attach(MIMEText(body, 'plain'))

    for fpath in attachments:
        logger.debug('Attachment: {}'.format(fpath))
        msg.attach(create_mime_attachment(fpath))

    # creates SMTP session
    s = smtplib.SMTP('smtp.gmail.com', 587)
    # start TLS for security
    s.starttls()
    # Authentication
    s.login(sender_address, sender_password)
    # Converts the Multipart msg into a string
    text = msg.as_string()
    # sending the mail
    s.sendmail(sender_address, receiver_address, text)
    # terminating the session
    s.quit()


class GmailService(object):
    def __init__(self, comm_config):
        self.comm_config = comm_config
        for topic, functor in self.comm_config['subscribe'].items():
            self.comm_config['subscribe'][topic] = eval(functor)
        self.comm = Communicator(self.comm_config, debug=True)
        self.email = comm_config['email']
        self.pipeline_compatible = comm_config['pipeline_compatible']
        self.target_label = comm_config['target_label']

    def find_target_label(self, target_label, generalized_result):
        label_list = [i['label'] for i in generalized_result['annotations']]
        logger.debug('Result labels: {}'.format(label_list))
        return target_label in label_list

    def update(self, pl):
        payload_json = payload.deserialize_payload(pl.decode('utf-8'))
        if self.pipeline_compatible:
            b64img_key = 'image_blob'
        else:
            b64img_key = 'bytes'
        jpg_bytes = payload.destringify_jpg(payload_json[b64img_key])
        payload_json.pop(b64img_key)
        logger.debug('inference text result: {}'.format(payload_json))

        match_target_label = self.find_target_label(self.target_label,
                                                    payload_json)

        logger.debug('Find target label {0}: {1}'.format(
            self.target_label, match_target_label))

        if match_target_label:
            timestamp = datetime.now().isoformat()
            notification_image = pjoin('/tmp', timestamp + '.jpg')
            notification_text = pjoin('/tmp', timestamp + '.json')
            with open(notification_image, 'wb') as f:
                f.write(jpg_bytes)
            with open(notification_text, 'w') as f:
                f.write(json.dumps(payload_json, indent=4))

            try:
                send_email_text(
                    self.email['sender_address'],
                    self.email['sender_password'],
                    self.email['receiver_address'],
                    body=('Target label {} is found. '
                          'Please check the attachments.'
                          ''.format(self.target_label)),
                    subject='BerryNet mail client notification',
                    attachments=set([notification_image, notification_text]))
            except Exception as e:
                logger.warn(e)

            os.remove(notification_image)
            os.remove(notification_text)
        else:
            # target label is not in generalized result, do nothing
            pass

    def run(self, args):
        """Infinite loop serving inference requests"""
        self.comm.run()


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        '--sender-address',
        required=True,
        help='Email address of sender. Ex: foo@email.org'
    )
    ap.add_argument(
        '--sender-password',
        required=True,
        help='Password of sender email address.'
    )
    ap.add_argument(
        '--receiver-address',
        required=True,
        help='Email address of receiver. Ex: bar@email.org'
    )
    ap.add_argument(
        '--target-label',
        required=True,
        help='Send notification email if the label is in inference result.'
    )
    ap.add_argument(
        '--broker-ip',
        default='localhost',
        help='MQTT broker IP.'
    )
    ap.add_argument(
        '--broker-port',
        default=1883,
        type=int,
        help='MQTT broker port.'
    )
    ap.add_argument(
        '--topic',
        nargs='*',
        default=['berrynet/engine/tflitedetector/result'],
        help='The topic to listen, and can be indicated multiple times.'
    )
    ap.add_argument(
        '--topic-action',
        default='self.update',
        help='The action for the indicated topics.'
    )
    ap.add_argument(
        '--topic-config',
        default=None,
        help='Path of the MQTT topic subscription JSON.'
    )
    ap.add_argument(
        '--pipeline-compatible',
        action='store_true',
        help=(
            'Change key of b64 image string in generalized result '
            'from bytes to image_blob. '
            'Note: This is an experimental parameter.'
        )
    )
    ap.add_argument('--debug',
        action='store_true',
        help='Debug mode toggle'
    )
    return vars(ap.parse_args())


def main():
    args = parse_args()
    if args['debug']:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Topics and actions can come from two sources: CLI and config file.
    # Setup topic_config by parsing values from the two sources.
    if args['topic_config']:
        with open(args['topic_config']) as f:
            topic_config = json.load(f)
    else:
        topic_config = {}
    topic_config.update({t:args['topic_action'] for t in args['topic']})

    comm_config = {
        'subscribe': topic_config,
        'broker': {
            'address': args['broker_ip'],
            'port': args['broker_port']
        },
        'email': {
            'sender_address': args['sender_address'],
            'sender_password': args['sender_password'],
            'receiver_address': args['receiver_address']
        },
        'pipeline_compatible': args['pipeline_compatible'],
        'target_label': args['target_label']
    }
    dc_service = GmailService(comm_config)
    dc_service.run(args)


if __name__ == '__main__':
    main()


