from types import SimpleNamespace

from asgiref.sync import async_to_sync

from realtime.consumers import DocumentConsumer


class FakeChannelLayer:
    def __init__(self):
        self.events = []

    async def group_send(self, group_name, event):
        self.events.append((group_name, event))


def _consumer(*, user_id=2):
    consumer = DocumentConsumer()
    consumer.doc_id = '1'
    consumer.group_name = 'doc_1'
    consumer.channel_name = 'channel'
    consumer.channel_layer = FakeChannelLayer()
    consumer.user_info = {
        'user_id': user_id,
        'username': 'editor',
        'color': '#123456',
    }
    consumer.user = SimpleNamespace(
        is_authenticated=True,
        pk=user_id,
        username='editor',
    )
    consumer.doc_owner_id = 1
    consumer.doc_title = 'Doc'
    consumer.edit_notification_sent = False
    consumer.notified_edit_sessions = set()
    consumer.can_edit_document = True

    consumer.saved_edits = []
    async def save_edit(_content):
        consumer.saved_edits.append(_content)
        return 1

    consumer._save_edit = save_edit
    return consumer


def test_edit_notification_is_enqueued_once_per_consumer_session(mocker):
    enqueue = mocker.patch('realtime.consumers.enqueue_edit_notification')
    consumer = _consumer()

    async_to_sync(consumer._handle_edit)({'type': 'edit', 'delta': {'step': 1}})
    async_to_sync(consumer._handle_edit)({'type': 'edit', 'delta': {'step': 2}})

    enqueue.assert_called_once_with(
        owner_id=1,
        doc_id=1,
        editor_id=2,
        editor_username='editor',
        doc_title='Doc',
    )


def test_edit_notification_is_enqueued_again_after_reconnect(mocker):
    enqueue = mocker.patch('realtime.consumers.enqueue_edit_notification')

    async_to_sync(_consumer()._handle_edit)({'type': 'edit', 'delta': {'step': 1}})
    async_to_sync(_consumer()._handle_edit)({'type': 'edit', 'delta': {'step': 1}})

    assert enqueue.call_count == 2


def test_edit_notification_can_be_requested_again_for_new_frontend_entry(mocker):
    enqueue = mocker.patch('realtime.consumers.enqueue_edit_notification')
    consumer = _consumer()

    async_to_sync(consumer._handle_edit)({
        'type': 'edit',
        'delta': {'step': 1},
        'notify_owner': True,
        'edit_notification_session_id': 'entry-1',
    })
    async_to_sync(consumer._handle_edit)({
        'type': 'edit',
        'delta': {'step': 2},
        'notify_owner': True,
        'edit_notification_session_id': 'entry-1',
    })
    async_to_sync(consumer._handle_edit)({
        'type': 'edit',
        'delta': {'step': 3},
        'notify_owner': True,
        'edit_notification_session_id': 'entry-2',
    })

    assert enqueue.call_count == 2


def test_read_only_consumer_cannot_persist_or_broadcast_edit(mocker):
    enqueue = mocker.patch('realtime.consumers.enqueue_edit_notification')
    consumer = _consumer()
    consumer.can_edit_document = False

    async_to_sync(consumer._handle_edit)({'type': 'edit', 'delta': {'step': 1}})

    assert consumer.saved_edits == []
    assert consumer.channel_layer.events == []
    enqueue.assert_not_called()
