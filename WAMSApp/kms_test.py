# """
# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except
# in compliance with the License. A copy of the License is located at

# https://aws.amazon.com/apache-2-0/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
# """

# from __future__ import print_function

# import os
# import base64
# import json
# import logging
# import botocore
# import aws_encryption_sdk


# def cycle_string(key_arn, source_plaintext, botocore_session):
#     """Encrypts and then decrypts a string using a KMS customer master key (CMK)

#     :param str key_arn: Amazon Resource Name (ARN) of the KMS CMK
#     (http://docs.aws.amazon.com/kms/latest/developerguide/viewing-keys.html)
#     :param bytes source_plaintext: Data to encrypt
#     :param botocore_session: Existing Botocore session instance
#     :type botocore_session: botocore.session.Session
#     """

#     # Create a KMS master key provider.
#     kms_kwargs = dict(key_ids=[key_arn])
#     if botocore_session is not None:
#         kms_kwargs['botocore_session'] = botocore_session
#     master_key_provider = aws_encryption_sdk.KMSMasterKeyProvider(**kms_kwargs)

#     # Encrypt the plaintext source data.
#     ciphertext, encryptor_header = aws_encryption_sdk.encrypt(
#         source=source_plaintext,
#         key_provider=master_key_provider
#     )
#     print('Ciphertext: ', ciphertext)

#     # Decrypt the ciphertext.
#     cycled_plaintext, decrypted_header = aws_encryption_sdk.decrypt(
#         source=ciphertext,
#         key_provider=master_key_provider
#     )

#     # Verify that the "cycled" (encrypted, then decrypted) plaintext is identical to the source
#     # plaintext.
#     assert cycled_plaintext == source_plaintext

#     # Verify that the encryption context used in the decrypt operation includes all key pairs from
#     # the encrypt operation. (The SDK can add pairs, so don't require an exact match.)
#     #
#     # In production, always use a meaningful encryption context. In this sample, we omit the
#     # encryption context (no key pairs).
#     assert all(
#         pair in decrypted_header.encryption_context.items()
#         for pair in encryptor_header.encryption_context.items()
#     )

#     print('Decrypted: ', cycled_plaintext)


# text =  "Raj"
# key_arn = "arn:aws:kms:eu-west-2:320594085615:key/7f226d3a-0b17-47a6-8220-598281a6690a"
# botocore_session = botocore.session.get_session()

# cycle_string(key_arn,text,botocore_session)

import boto3
import base64

if __name__ == '__main__':
    session = boto3.session.Session()

    kms = session.client('kms', region_name='eu-west-2')

    key_id = 'alias/myapp-key'
    stuff = kms.encrypt(KeyId=key_id, Plaintext='Geepas')
    binary_encrypted = stuff[u'CiphertextBlob']
    encrypted_password = base64.b64encode(binary_encrypted)
    print("Encrypted : ")
    print(encrypted_password.decode())

    binary_data = base64.b64decode(encrypted_password)
    meta = kms.decrypt(CiphertextBlob=binary_data)
    plaintext = meta[u'Plaintext']
    print("Decrypted : ")
    print(plaintext.decode())


"""
access_key = 'AKIAI7PSOABCBAJGX36Q' #replace with your access key
seller_id = 'A3DNFJ8JVFH39T' #replace with your seller id
secret_key = '9un2k+5Q4eCFI4SRDjNyLhjTAHXrsFkZe0mWIRop' #replace with your secret key
marketplace_ae = 'A2VIGQ35RCS4UG'

GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, RELOAD, PROCESS, REFERENCES, INDEX, ALTER, SHOW DATABASES, CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, REPLICATION SLAVE, REPLICATION CLIENT, CREATE VIEW, SHOW VIEW, CREATE ROUTINE, ALTER ROUTINE, CREATE USER, EVENT, TRIGGER ON *.* TO `admin`@`%` WITH GRANT OPTION
"""