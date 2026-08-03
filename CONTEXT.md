# Exchange Gateway

Exchange Gateway exposes Exchange/EWS mail operations and event delivery as a
stable API for applications that own an Exchange account.

## Language

**Exchange account**:
The configured Exchange mailbox and credentials through which mail operations
are performed. _Avoid_: user, mailbox configuration.

**Webhook subscription**:
An account-owned registration of an HTTP endpoint and event types, protected
by a signing secret. _Avoid_: callback, listener.

**Webhook signing secret**:
The shared secret used only to authenticate a webhook delivery. It is never a
readable attribute of a webhook subscription. _Avoid_: encrypted secret.

**Webhook delivery**:
A persisted attempt to send one Exchange event to a webhook subscription.
_Avoid_: webhook event, notification.

**Email detail**:
The complete API representation of one Exchange message, including its body,
attachments, and conversation metadata. _Avoid_: email record, message data.

**Reply/forward draft**:
An Exchange draft created from a reply or forward before any added attachments
are saved or the message is sent. _Avoid_: unsent reply, pending forward.

**Current-message body (`unique_body`)**:
The part of an email authored in the current message, excluding quoted content
from earlier messages in the conversation. _Avoid_: clean body, new body.

**Conversation metadata**:
The stable identifiers and message-reference headers that relate an email to
other messages in its conversation. _Avoid_: thread body, quoted content.
