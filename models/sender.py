# -*- coding: utf-8 -*-

import time

import telebot
from telebot.types import InputMediaPhoto, InputMediaVideo

from assets.attachment_types import *
from assets.utils import AttachmentParts


class TelegramSender:
    """
    Отправит обработанный объект типа Post в телеграмм канал
    """
    SYMBOLS_WITH_ATTACHMENT = 950
    SYMBOLS_ONLY_TEXT = 4000
    # ограничения на число символов в сообщении с вложением и без

    def __init__(self, tg_token, chat_link):
        self.attachments = None
        self.tg_client = telebot.TeleBot(tg_token)
        self.chat_link = chat_link

    def send_post_as_messages(self, post):
        """
        Подготовит вложения к финальной отправке. Использует генератор message_generator
        Для разбиения текста поста на сообщения. Приоритетно обрабатываются вложения в алюбоме.
        Все оставшиеся вложения отправляются по одиночке и дополняются текстом поста
        (если он остался). В конце отправляются остатки текста.

        :param post: обработанный объект типа Post
        """
        self.attachments = AttachmentParts([], [], [], [])
        self.create_telegram_attachments(post)

        if not post.text:
            self.send_with_no_text()
            return

        message_generator = self.message_parts_generator(post.text)
        next(message_generator)

        if self.attachments.album_sendings:
            self.send_with_album_sendings(message_generator)

        if self.attachments.videos:
            self.send_with_videos(message_generator)

        if self.attachments.docs:
            self.send_with_docs(message_generator)

        if self.attachments.animations:
            self.send_with_animations(message_generator)

        self.send_last_messages_of_text(message_generator)

    def create_telegram_attachments(self, post):
        """
        Группирует вложения по типам, по возможности объединяет малые видео и картинки в один альбом

        :param post: обработанный объект типа Post
        """
        # TODO create_telegram_attachments попробовать делать это сразу в методе parse_attachments у поста

        for att in post.attachments_storage:
            att_type = [*att.keys()][0]
            if att_type in [VIDEO_ALBUM, PHOTO]:
                self.attachments.album_sendings.append({att_type: att[att_type]})

            elif att_type in [VIDEO_LARGE]:
                self.attachments.videos.append({att_type: att[att_type]})

            elif att_type in [DOC]:
                self.attachments.docs.append({att_type: att[att_type]})

            elif att_type in [ANIMATION]:
                self.attachments.animations.append({att_type: att[att_type]})

    def send_with_album_sendings(self, message_generator):
        """
        Отправляет вложения альбома

        :param message_generator: генератор сообщений
        """
        attachments_album = []
        file_first = self.attachments.album_sendings[0]
        caption_message = message_generator.send(type(self).SYMBOLS_WITH_ATTACHMENT)

        attachments_album.append(
            InputMediaPhoto(file_first[PHOTO], caption=caption_message) if PHOTO in file_first.keys()
            else InputMediaVideo(file_first[VIDEO_ALBUM].media, duration=file_first[VIDEO_ALBUM].duration,
                                 width=file_first[VIDEO_ALBUM].width, caption=caption_message,
                                 height=file_first[VIDEO_ALBUM].height)
        )

        for file in self.attachments.album_sendings[1:]:
            attachments_album.append(
                InputMediaPhoto(file[PHOTO]) if PHOTO in file.keys() else InputMediaVideo(
                    file[VIDEO_ALBUM].media, duration=file[VIDEO_ALBUM].duration,
                    width=file[VIDEO_ALBUM].width, height=file[VIDEO_ALBUM].height)
            )

        self.tg_client.send_media_group(self.chat_link, attachments_album)
        time.sleep(3)

    def send_with_videos(self, message_generator):
        """
        Отправляет видео-вложения

        :param message_generator: генератор сообщений
        """
        for file in self.attachments.videos:

            try:
                sending_message = message_generator.send(type(self).SYMBOLS_WITH_ATTACHMENT)

                self.tg_client.send_video(self.chat_link, file[VIDEO_LARGE].media, file[VIDEO_LARGE].duration,
                                          width=file[VIDEO_LARGE].width, height=file[VIDEO_LARGE].height,
                                          caption=sending_message)

            except StopIteration:
                self.tg_client.send_video(self.chat_link, file[VIDEO_LARGE].media, file[VIDEO_LARGE].duration,
                                          width=file[VIDEO_LARGE].width,
                                          height=file[VIDEO_LARGE].height)
            time.sleep(3)

    def send_with_docs(self, message_generator):
        """
        Отправляет вложения-документы

        :param message_generator: генератор сообщений
        """
        for file in self.attachments.docs:
            try:
                sending_message = message_generator.send(type(self).SYMBOLS_WITH_ATTACHMENT)
                self.tg_client.send_document(self.chat_link, file[DOC], caption=sending_message)

                time.sleep(3)
            except StopIteration:
                self.tg_client.send_document(self.chat_link, file[DOC])
                time.sleep(3)

    def send_with_animations(self, message_generator):
        """
        Отправляет вложения-анимации (gif картикни)

        :param message_generator: генератор сообщений
        """
        # TODO - pull request библиотеки pytelebot, где добавить параметры width и height для send_animation
        for file in self.attachments.animations:
            try:
                sending_message = message_generator.send(type(self).SYMBOLS_WITH_ATTACHMENT)
                self.tg_client.send_animation(self.chat_link, file[ANIMATION], duration=10, caption=sending_message)
                time.sleep(3)

            except StopIteration:
                self.tg_client.send_animation(self.chat_link, file[ANIMATION], duration=10)
                time.sleep(3)

    def send_with_no_text(self):
        """
        Отправляет пост, у которого нет исходного текста
        """
        album_attachments = []

        for file in self.attachments.album_sendings:
            album_attachments.append(
                InputMediaPhoto(file[PHOTO]) if PHOTO in file.keys()[0] else InputMediaVideo(
                    file[VIDEO_ALBUM].media, duration=file[VIDEO_ALBUM].duration,
                    width=file[VIDEO_ALBUM].width,
                    height=file[VIDEO_ALBUM].height))

        self.tg_client.send_media_group(self.chat_link, album_attachments)
        time.sleep(3)

        for file in self.attachments.videos:
            self.tg_client.send_video(self.chat_link, file.media, file.duration, width=file.width, height=file.height)
            time.sleep(3)

        for file in self.attachments.docs:
            self.tg_client.send_document(self.chat_link, file.media)
            time.sleep(3)

    def send_last_messages_of_text(self, message_generator):
        """
        Отправляет куски текста, оставшиеся без вложений, в длинных сообщениях

        :param message_generator:
        """
        try:
            while True:
                sending_message = message_generator.send(type(self).SYMBOLS_ONLY_TEXT)
                self.tg_client.send_message(self.chat_link, sending_message)
                time.sleep(3)
        finally:
            time.sleep(5)
            # без return ошибка всё-равно появится. Return блокирует её появление
            return

    @staticmethod
    def message_parts_generator(text):
        """
        Генерирует "порции" текста. Приоритет деления - не по количеству символов, а по
        словам. (в строке "привет мир!" никогда не будет варианта деления: "при" + "вет мир!")

        :param text: текст, который делится на сообщения
        :return: кусок текста, который помещается по символам в сообщение
        """
        count_symbols = yield
        text_split = text.split(" ")
        message_part = ""

        for num in range(len(text_split)):
            if len(message_part + ' ' + text_split[num]) < count_symbols:
                message_part += text_split[num] + ' '

            else:
                count_symbols = yield message_part[:-1]
                message_part = text_split[num] + ' '

        yield message_part[:-1]
