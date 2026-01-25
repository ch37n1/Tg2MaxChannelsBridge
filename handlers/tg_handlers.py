import asyncio
import logging
import os
import tempfile

from aiogram import F
from aiogram.types import Message as TgMessage, Update as TgUpdate
from maxapi.types import InputMedia

import config
from loader import tg_dp, tg_bot, max_bot

media_groups = {}

async def forward_media_group(media_group_id: str, max_channel_id: int):
    """
    Отправляет сгруппированные медиафайлы в MAX.
    """
    await asyncio.sleep(2)  # Ждем, пока соберутся все сообщения группы
    
    if media_group_id not in media_groups:
        return

    messages = media_groups.pop(media_group_id)
    messages.sort(key=lambda m: m.message_id)
    
    # Ищем текст (подпись) - берем первую непустую
    text = ""
    for m in messages:
        caption = m.caption or m.text
        if caption:
            text = caption
            break
            
    temp_files = []
    attachments = []
    
    try:
        for m in messages:
            if m.photo:
                photo = m.photo[-1]
                file_info = await tg_bot.get_file(photo.file_id)
                
                fd, temp_path = tempfile.mkstemp(suffix='.jpg')
                os.close(fd)
                temp_files.append(temp_path)
                
                await tg_bot.download_file(file_info.file_path, destination=temp_path)
                attachments.append(InputMedia(temp_path))
                
        if attachments:
            await max_bot.send_message(
                chat_id=max_channel_id,
                text=text,
                attachments=attachments
            )
            logging.info(f"Forwarded media group {media_group_id} with {len(attachments)} items to MAX")
            
    except Exception as e:
        logging.error(f"Error forwarding media group {media_group_id}: {e}")
    finally:
        # Чистим временные файлы
        for path in temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    logging.error(f"Error removing temp file {path}: {e}")


async def handle_media_group(tg_message: TgMessage, max_channel_id: int):
    if tg_message.media_group_id not in media_groups:
        media_groups[tg_message.media_group_id] = []
        asyncio.create_task(forward_media_group(tg_message.media_group_id, max_channel_id))
        
    media_groups[tg_message.media_group_id].append(tg_message)

async def handle_single(tg_message: TgMessage, max_channel_id: int):
    # Обычная обработка одиночных сообщений
    text = tg_message.text or tg_message.caption or ""

    # Обработка фото
    if tg_message.photo:
        # Берем фото самого лучшего качества
        photo = tg_message.photo[-1]
        file_info = await tg_bot.get_file(photo.file_id)
        file_path = file_info.file_path
        
        # Скачиваем файл
        fd, temp_path = tempfile.mkstemp(suffix='.jpg')
        os.close(fd) 
        
        try:
            await tg_bot.download_file(file_path, destination=temp_path)
            
            # Отправляем в MAX
            media = InputMedia(temp_path)
            await max_bot.send_message(
                chat_id=max_channel_id,
                text=text,
                attachments=[media]
            )
            logging.info("Forwarded photo to MAX")
            
        except Exception as e:
            logging.error(f"Error forwarding photo: {e}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    # Обработка только текста
    elif text:
        try:
            await max_bot.send_message(
                chat_id=max_channel_id,
                text=text
            )
            logging.info("Forwarded text to MAX")
        except Exception as e:
            logging.error(f"Error forwarding text: {e}")

@tg_dp.channel_post()
async def on_channel_post(message: TgMessage):
    """
    Обрабатывает новые посты в Telegram канале и пересылает их в MAX.
    """
    logging.info(f"New post in Telegram channel {message.chat.id}: {message.message_id}")

    target_max_ids = config.CHANNEL_LINKS.get(message.chat.id)
    if not target_max_ids:
        logging.info(f"No targets found for Telegram channel {message.chat.id}")
        return

    for max_id in target_max_ids:
        # Не asyncio.gather(), чтоб не спамить

        # Если это группа медиа
        if message.media_group_id:
            await handle_media_group(message, max_id)
            return

        await handle_single(message, max_id)

        await asyncio.sleep(1)

