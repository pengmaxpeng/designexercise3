# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: chat.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'chat.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nchat.proto\x12\x04\x63hat\"C\n\x18ReplicateMutationRequest\x12\x16\n\x0eoperation_type\x18\x01 \x01(\t\x12\x0f\n\x07payload\x18\x02 \x01(\t\"=\n\x19ReplicateMutationResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"2\n\x0cLoginRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x10\n\x08password\x18\x02 \x01(\t\"G\n\rLoginResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12\x14\n\x0cunread_count\x18\x03 \x01(\x05\":\n\x14\x43reateAccountRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x10\n\x08password\x18\x02 \x01(\t\"9\n\x15\x43reateAccountResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"!\n\rLogOffRequest\x12\x10\n\x08username\x18\x01 \x01(\t\"2\n\x0eLogOffResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"(\n\x14\x44\x65leteAccountRequest\x12\x10\n\x08username\x18\x01 \x01(\t\"9\n\x15\x44\x65leteAccountResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"H\n\x12SendMessageRequest\x12\x0e\n\x06sender\x18\x01 \x01(\t\x12\x11\n\trecipient\x18\x02 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x03 \x01(\t\"7\n\x13SendMessageResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"6\n\x13ReadMessagesRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\r\n\x05limit\x18\x02 \x01(\x05\";\n\x14ReadMessagesResponse\x12#\n\x08messages\x18\x01 \x03(\x0b\x32\x11.chat.ChatMessage\">\n\x15\x44\x65leteMessagesRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x13\n\x0bmessage_ids\x18\x02 \x03(\x05\":\n\x16\x44\x65leteMessagesResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"?\n\x17ViewConversationRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x12\n\nother_user\x18\x02 \x01(\t\"?\n\x18ViewConversationResponse\x12#\n\x08messages\x18\x01 \x03(\x0b\x32\x11.chat.ChatMessage\"9\n\x13ListAccountsRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x10\n\x08wildcard\x18\x02 \x01(\t\")\n\x14ListAccountsResponse\x12\x11\n\tusernames\x18\x01 \x03(\t\"$\n\x10SubscribeRequest\x12\x10\n\x08username\x18\x01 \x01(\t\"M\n\x0b\x43hatMessage\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0e\n\x06sender\x18\x02 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x03 \x01(\t\x12\x11\n\ttimestamp\x18\x04 \x01(\t2\xa8\x06\n\x0b\x43hatService\x12\x32\n\x05Login\x12\x12.chat.LoginRequest\x1a\x13.chat.LoginResponse\"\x00\x12J\n\rCreateAccount\x12\x1a.chat.CreateAccountRequest\x1a\x1b.chat.CreateAccountResponse\"\x00\x12\x35\n\x06LogOff\x12\x13.chat.LogOffRequest\x1a\x14.chat.LogOffResponse\"\x00\x12J\n\rDeleteAccount\x12\x1a.chat.DeleteAccountRequest\x1a\x1b.chat.DeleteAccountResponse\"\x00\x12\x44\n\x0bSendMessage\x12\x18.chat.SendMessageRequest\x1a\x19.chat.SendMessageResponse\"\x00\x12G\n\x0cReadMessages\x12\x19.chat.ReadMessagesRequest\x1a\x1a.chat.ReadMessagesResponse\"\x00\x12M\n\x0e\x44\x65leteMessages\x12\x1b.chat.DeleteMessagesRequest\x1a\x1c.chat.DeleteMessagesResponse\"\x00\x12S\n\x10ViewConversation\x12\x1d.chat.ViewConversationRequest\x1a\x1e.chat.ViewConversationResponse\"\x00\x12G\n\x0cListAccounts\x12\x19.chat.ListAccountsRequest\x1a\x1a.chat.ListAccountsResponse\"\x00\x12\x44\n\x13SubscribeToMessages\x12\x16.chat.SubscribeRequest\x1a\x11.chat.ChatMessage\"\x00\x30\x01\x12T\n\x11ReplicateMutation\x12\x1e.chat.ReplicateMutationRequest\x1a\x1f.chat.ReplicateMutationResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'chat_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_REPLICATEMUTATIONREQUEST']._serialized_start=20
  _globals['_REPLICATEMUTATIONREQUEST']._serialized_end=87
  _globals['_REPLICATEMUTATIONRESPONSE']._serialized_start=89
  _globals['_REPLICATEMUTATIONRESPONSE']._serialized_end=150
  _globals['_LOGINREQUEST']._serialized_start=152
  _globals['_LOGINREQUEST']._serialized_end=202
  _globals['_LOGINRESPONSE']._serialized_start=204
  _globals['_LOGINRESPONSE']._serialized_end=275
  _globals['_CREATEACCOUNTREQUEST']._serialized_start=277
  _globals['_CREATEACCOUNTREQUEST']._serialized_end=335
  _globals['_CREATEACCOUNTRESPONSE']._serialized_start=337
  _globals['_CREATEACCOUNTRESPONSE']._serialized_end=394
  _globals['_LOGOFFREQUEST']._serialized_start=396
  _globals['_LOGOFFREQUEST']._serialized_end=429
  _globals['_LOGOFFRESPONSE']._serialized_start=431
  _globals['_LOGOFFRESPONSE']._serialized_end=481
  _globals['_DELETEACCOUNTREQUEST']._serialized_start=483
  _globals['_DELETEACCOUNTREQUEST']._serialized_end=523
  _globals['_DELETEACCOUNTRESPONSE']._serialized_start=525
  _globals['_DELETEACCOUNTRESPONSE']._serialized_end=582
  _globals['_SENDMESSAGEREQUEST']._serialized_start=584
  _globals['_SENDMESSAGEREQUEST']._serialized_end=656
  _globals['_SENDMESSAGERESPONSE']._serialized_start=658
  _globals['_SENDMESSAGERESPONSE']._serialized_end=713
  _globals['_READMESSAGESREQUEST']._serialized_start=715
  _globals['_READMESSAGESREQUEST']._serialized_end=769
  _globals['_READMESSAGESRESPONSE']._serialized_start=771
  _globals['_READMESSAGESRESPONSE']._serialized_end=830
  _globals['_DELETEMESSAGESREQUEST']._serialized_start=832
  _globals['_DELETEMESSAGESREQUEST']._serialized_end=894
  _globals['_DELETEMESSAGESRESPONSE']._serialized_start=896
  _globals['_DELETEMESSAGESRESPONSE']._serialized_end=954
  _globals['_VIEWCONVERSATIONREQUEST']._serialized_start=956
  _globals['_VIEWCONVERSATIONREQUEST']._serialized_end=1019
  _globals['_VIEWCONVERSATIONRESPONSE']._serialized_start=1021
  _globals['_VIEWCONVERSATIONRESPONSE']._serialized_end=1084
  _globals['_LISTACCOUNTSREQUEST']._serialized_start=1086
  _globals['_LISTACCOUNTSREQUEST']._serialized_end=1143
  _globals['_LISTACCOUNTSRESPONSE']._serialized_start=1145
  _globals['_LISTACCOUNTSRESPONSE']._serialized_end=1186
  _globals['_SUBSCRIBEREQUEST']._serialized_start=1188
  _globals['_SUBSCRIBEREQUEST']._serialized_end=1224
  _globals['_CHATMESSAGE']._serialized_start=1226
  _globals['_CHATMESSAGE']._serialized_end=1303
  _globals['_CHATSERVICE']._serialized_start=1306
  _globals['_CHATSERVICE']._serialized_end=2114
# @@protoc_insertion_point(module_scope)
