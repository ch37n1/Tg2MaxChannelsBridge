
# Tg2MaxChannelsBridge

Простейшая система форвардинга между телегой и максом на Bot API с обоих сторон и routes.json для маршрутизации. Поддерживает передачу медиагрупп. Это форк.

TODO:
- [x] refactor to have `send_photo` method instead of code duplicates
- [ ] Support
    - [ ] Message.photo >  send with same file extension and text (now 
    - [ ] Message.audio >  send with same file extension and text
    - [ ] Message.document > send with same file extension and text
    - [ ] Message.video > send with same file extension and text
- [ ] Not support:
    - Message.sticker > skip
    - Message.voice > skip
    - Message.checklist > skip
    - Message.contact > skip
    - Message.dice > skip
    - Message.game > skip
    - Message.poll > skip
    - Message.location > skip

Aiogram Doc is here:
https://docs.aiogram.dev/en/v3.24.0
