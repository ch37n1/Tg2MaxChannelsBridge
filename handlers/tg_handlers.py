import asyncio
import logging
import os
import tempfile

from aiogram.types import Message as TgMessage
from maxapi.types import InputMedia

import config
from loader import tg_dp, tg_bot, max_bot

media_groups = {}


# ============ Helper Functions ============

async def download_tg_media(file_id: str, suffix: str = '.jpg') -> str | None:
    """
    Download any media from Telegram and save to temp file.
    
    Args:
        file_id: Telegram file_id for the media
        suffix: File extension (e.g., '.jpg', '.mp4', '.mp3', '.pdf')
    
    Returns:
        Temp file path, or None if download failed.
        Caller is responsible for cleanup.
    """
    try:
        file_info = await tg_bot.get_file(file_id)
        if not file_info.file_path:
            logging.error(f'Could not get file path for file_id {file_id}')
            return None

        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)

        await tg_bot.download_file(file_info.file_path, destination=temp_path)
        return temp_path
    except Exception as e:
        logging.error(f"Error downloading media {file_id}: {e}")
        return None


async def send_to_max(
    max_channel_id: int,
    text: str | None,
    temp_paths: list[str]
) -> bool:
    """
    Send attachments to a Max channel and cleanup temp files.
    
    Args:
        max_channel_id: Target Max channel ID
        text: Message text/caption (can be None or empty)
        temp_paths: List of temp file paths to attach
    
    Returns:
        True if sent successfully, False otherwise.
    """
    attachments: list = [InputMedia(path) for path in temp_paths]
    
    try:
        await max_bot.send_message(
            chat_id=max_channel_id,
            text=text or "",
            attachments=attachments if attachments else None
        )
        return True
    except Exception as e:
        logging.error(f"Error sending to Max channel {max_channel_id}: {e}")
        return False
    finally:
        cleanup_temp_files(temp_paths)


def cleanup_temp_files(temp_paths: list[str]) -> None:
    """Remove temporary files, logging any errors."""
    for path in temp_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logging.error(f"Error removing temp file {path}: {e}")


# ============ Media Group Handling ============

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
            
    # Download all photos
    temp_files = []
    for m in messages:
        if m.photo:
            photo = m.photo[-1]  # Best quality
            temp_path = await download_tg_media(photo.file_id, suffix='.jpg')
            if temp_path:
                temp_files.append(temp_path)
                
    if not temp_files:
        logging.warning(f"No media downloaded for media group {media_group_id}")
        return
    
    # Send to Max (cleanup handled inside send_to_max)
    success = await send_to_max(max_channel_id, text, temp_files)
    if success:
        logging.info(f"Forwarded media group {media_group_id} with {len(temp_files)} items to MAX")


async def handle_media_group(tg_message: TgMessage, max_channel_id: int):
    if tg_message.media_group_id and tg_message.media_group_id not in media_groups:
        media_groups[tg_message.media_group_id] = []
        asyncio.create_task(forward_media_group(tg_message.media_group_id, max_channel_id))
        
    media_groups[tg_message.media_group_id].append(tg_message)

async def handle_single(tg_message: TgMessage, max_channel_id: int):
    """Обработка одиночных сообщений (фото или текст)."""
    text = tg_message.text or tg_message.caption or ""

    # Обработка фото
    if tg_message.photo:
        photo = tg_message.photo[-1]  # Best quality
        temp_path = await download_tg_media(photo.file_id, suffix='.jpg')
        if not temp_path:
            return
        
        success = await send_to_max(max_channel_id, text, [temp_path])
        if success:
            logging.info("Forwarded photo to MAX")
                
    # Обработка только текста
    elif text:
        success = await send_to_max(max_channel_id, text, [])
        if success:
            logging.info("Forwarded text to MAX")

@tg_dp.channel_post()
async def on_channel_post(message: TgMessage):
    """
    Обрабатывает новые посты в Telegram канале и пересылает их в MAX.
    """
    logging.info(f"New post in Telegram channel {message.chat.id}: {message.message_id}")

    logging.info(f'FULL: {message}')

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

