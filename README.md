
# Tg2MaxChannelsBridge

Простейшая система форвардинга между телегой и максом на Bot API с обоих сторон и routes.json для маршрутизации. Поддерживает передачу медиагрупп. Это форк.

TODO:
- [x] refactor to have `send_photo` method instead of code duplicates
- [x] Support
    - [x] Message.photo > send with same file extension and text
    - [x] Message.audio > send with same file extension and text
    - [x] Message.document > send with same file extension and text
    - [x] Message.video > send with same file extension and text
- [x] Not support (skip):
    - [x] Message.sticker > skip
    - [x] Message.voice > skip
    - [x] Message.contact > skip
    - [x] Message.dice > skip
    - [x] Message.game > skip
    - [x] Message.poll > skip
    - [x] Message.location > skip

Aiogram Doc is here:
https://docs.aiogram.dev/en/v3.24.0
