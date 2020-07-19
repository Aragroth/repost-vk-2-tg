# -*- coding: utf-8 -*-

import logging
import os
import re

import requests
import vk_api
import youtube_dl

from assets.attachment_types import *
from assets.utils import Video

logging.basicConfig(filename='assets/warnings.log', format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%d-%b-%Y %H:%M:%S')


class Post:
    """
    Позволяет обработать и подговить "сырой" пост из ВКонтакте
    к отправке в формате сообщений Телеграмма
    """

    def __init__(self, raw_post, group_id, vk_service_token):
        self.raw_post = raw_post
        self.text = raw_post['text']
        self.group_id = group_id

        # нужно для создания "укороченных" vk.cc ссылок из обычных
        vk_session = vk_api.VkApi(token=vk_service_token)
        self.vk = vk_session.get_api()

        self.attachments_storage = []
        # Хранит в себе словари вложений. У каждого словаря ключом является
        # некий тип вложения (типы опеределены в assets.attachment_types).
        # Также есть специальный тип ERROR. Объекты с этим ключом
        # в последствии обрабатываются отдельно и удаляются из списка

    def refactor(self, key_tag):
        """
        Осуществляет чистку текста от частей, которые специфичны и реализованы только в ВКонтакте
        """
        self.refactor_group_links()
        self.refactor_user_links()
        self.refactor_tags(key_tag)

    def refactor_group_links(self):
        """
        Чистит ссылки групп, используемые в ВК. Например: [club12132|SpaceX] -> SpaceX
        """
        for tag in re.findall(r'\[\w*\|(\w*)]', self.text):
            self.text = re.sub(r'\[\w*\|\w*\]', tag, self.text, 1)

    def refactor_user_links(self):
        """
        Чистит ссылки пользователей, используемые в ВК. Например: [@Alisa|ведущий] -> ведущий
        """
        for tag in re.findall(r'\[\w*\|(.+?)]', self.text):
            self.text = re.sub(r'\[\w*\|.+?]', tag, self.text, 1)

    def refactor_tags(self, key_tag):
        """
        Удалит ключевой тег перепоста, а также уберёт идентификатор группы после символа @ в тегах.
        Например: #key_tag #rocketship@Spacex -> #rocketship

        :param key_tag: тег, по которому идёт перепост в телеграмм
        """
        self.text = self.text.replace(key_tag, "", 1)

        for tag in re.findall(r'#(\w+?)@\w*', self.text):
            self.text = re.sub(r'#(\w+?)@\w*', f'#{tag}', self.text, 1)

    def parse_attachments(self):
        """
        Поддерживаете следующие виды вложнеий: видео, фото, ссылки, документы, гиф-анимации.
        Преобразует каждый вид вложения для отправки. Во время преобразования могут возникнут "ошибки".
        Любые виды таких ошибок не прерывают работу скрипта, а позднее логируются.
        """

        for element in self.raw_post['attachments']:
            if element['type'] == 'video':
                self.attachments_storage.append(
                    self.parse_video(element['video'])
                )

            elif element['type'] == 'photo':
                self.attachments_storage.append(
                    self.parse_photo(element['photo'])
                )

            elif element['type'] == 'doc':
                self.attachments_storage.append(
                    self.parse_doc(element['doc'])
                )

            elif element['type'] == 'link':
                self.attachments_storage.append(
                    self.parse_link(element['link'])
                )

        self.validate_parse_errors()
        self.add_links_to_text()
        self.delete_downloads()

    def parse_video(self, video):
        """
        Обработчик видео-вложений. Youtube-видео, встроенные в вк через embedded, становятся обычными
        ссылками. Телеграмм почему-то не добавляет видео в альбом больше 10МБ, поэтому происходит
        попытка сжать видео. Видео длинее 5 минут сразу возвращаются с пометкой VIDEO_LARGE, потому что
        сжатие скорее всего не поможет, а только займёт много времени.

        :param video: словарь с деталями видео
        :return: словарь с объектом Video, либо ошибка
        """

        # у видеозаписей, залитых через вк, нет ключа platform
        if 'platform' in video.keys():
            if video['platform'] != 'YouTube':
                return {ERROR: f"Неизвестная платформа у видео: {self.group_id}_{video['id']}"}

            video_link = self.text_contains_link_of_attached_video(video)
            # возвращает строкой ссылку на видео, если оно есть в тексте, иначе ""
            # TODO переписать этот логический маразм и переименовать метод (-_-)

            if video_link:
                return {LINK_YOUTUBE: video_link}
            else:
                return {ERROR: f"Данное видео уже содержится как ссылка в посте: {self.group_id}_{video['id']}"}

        try:
            video_data = self.download_video(video)

        except Exception as error:
            # Этот лог отдельный, чтобы сохранить traceback ошибки
            logging.error(repr(error), exc_info=True)
            return {ERROR: f"Произошла неизвестная ошибка при загрузке видео: {self.group_id}_{self.video['id']}"}

        return video_data

    def download_video(self, video):
        """
        Пытается скачать видео из вк. Если оно дольше 5 минут, то оно возвращается
        с пометкой VIDEO_LARGE, иначе сжимается до величены меньшей 10MB. (Единственный способ
        добавить видео в альбом-вложений)

        :param video: словарь с исходной информации о видео
        :return: объектом Video
        """
        with youtube_dl.YoutubeDL({'outtmpl': 'downloads/saved.mp4'}) as ydl:
            ydl.download([f"https://vk.com/video{self.group_id}_{video['id']}"])

        if video['duration'] / 60 > 5:
            return {VIDEO_LARGE: self.get_video('downloads/saved.mp4', video)}

        # сжатие через ffmpeg (другие кодеки могут вызывать ошибки, данный работает на linux)
        os.system('ffmpeg -y -i downloads/saved.mp4 -vcodec h264 -acodec mp2 downloads/output.mp4')

        # проверка размера видео на превышение 10MB
        if float(os.path.getsize('downloads/output.mp4') / 1024 / 1024) > 10:
            return {VIDEO_LARGE: self.get_video('downloads/output.mp4', video)}

        return {VIDEO_ALBUM: self.get_video('downloads/output.mp4', video)}

    @staticmethod
    def get_video(filename, video):
        """
        Скачивает видео, сохраняет его биты и метаданные в объект Video

        :param filename: путь к сжатому видео
        :param video: словарь с метаданными видео, предаставляется вк
        :return: объект Video
        """
        with open(filename, "rb") as video_file:
            data = Video(video_file.read(), video['duration'], video['width'], video['height'])

        return data

    def text_contains_link_of_attached_video(self, video):
        """
        Возвращает строкой ссылку на видео, если оно есть в тексте, иначе ""

        :param video: данные о видео
        :return: '' или полная ссылка на видео
        """
        mentioned_links_in_text = self.get_youtube_links_from_text()
        youtube_link = self.get_youtube_link_from_attachment(f"https://vk.com/video{self.group_id}_{video['id']}")

        return youtube_link if youtube_link not in mentioned_links_in_text else ''

    @staticmethod
    def get_youtube_link_from_attachment(vk_video_link):
        """
        По видео-ссылке из ВК, возвращает аналогичную, но из самого ютуба

        :param vk_video_link: ссылыка из вк
        :return: ссылка из ютуба
        """
        video_in_vk = requests.get(vk_video_link)
        link_embed = re.findall(r'//www.youtube.com/embed/\S+?\?', video_in_vk.text)[0]
        short_link = 'https:' + link_embed.replace('/embed/', '/', 1)[:-1].replace('www.youtube.com', 'youtu.be')

        youtube_embedded = requests.get(short_link, allow_redirects=True).url
        full_link = youtube_embedded.split("&")[0]

        return full_link

    def get_youtube_links_from_text(self):
        """
        Выделеят из поста все ссылки, которые могут вести на ютуб.
        В итоге будет список из несокращённых ссылок (не youtu.be), ведущих на youtube.com

        :returns список ссылок
        """
        youtube_links = []

        vk_cc_links = re.findall(r"(vk.cc/\S+)", self.text)

        for vk_link in vk_cc_links:
            data = requests.get("https://" + vk_link)
            link = re.findall(r"value=\"https://www.(youtube.com/watch\?v=\S+?)\"", data.text)
            # в регулярку добавлена часть тега, чтобы не цеплялись лишние ссылки, а была одна

            youtube_links.extend(link)
            # использовался extend, потому что vk.cc ссылка не всегда ведёт на
            # ютуб и re.findall может вернуть пустой список

        short_youtube_links = re.findall(r"(youtu.be/\S+)", self.text)

        for link_be in short_youtube_links:
            youtube_full_link = requests.get("https://" + link_be).url.split("&")[0].lstrip("https://www.")
            youtube_links.append(youtube_full_link)

        links = re.findall(r"https://www.youtube.com/watch?v=\S+\"", self.text)
        youtube_links.extend(links)

        return list(set(youtube_links))

    def validate_parse_errors(self):
        """
        Удалит из данных все уведомлнеия об ошибках произошедших при парсинге
        поста и запишет их в логи (В основном касается скачивания и сжатия видео)
        """
        for error in [element for element in self.attachments_storage if ERROR in element]:
            logging.warning(error[ERROR])

        self.attachments_storage = [element for element in self.attachments_storage if ERROR not in element]

    @staticmethod
    def parse_photo(photo) -> dict:
        """
        Возвращает url картинки с максимальным разрешением

        :param photo: словарь с информацией о фото
        :return: словарь с данными фотографии
        """
        return {PHOTO: photo['sizes'][-1]['url']}

    @staticmethod
    def parse_doc(document):
        """
        Скачивает вк-документ. Если это фотография, то "понижает" вложение до типа
        обычной фотографии. Если это гифка, то она помечается типом "анимация".
        Все остальные вложения будут отпарвлены, как простые документы.

        :param document: словарь с информацией о документу
        :return: словарь с битами вложения
        """
        r = requests.get(document['url'], allow_redirects=True)

        if document['ext'] in ['jpg', 'png']:
            return {PHOTO: r.content}
        elif document['ext'] in ['gif']:
            return {ANIMATION: r.content}
        else:
            return {DOC: r.content}

    def parse_link(self, link):
        """
        Возвращает ссылку, если она не встречалась в тексте поста

        :param link: Словарь с информацией о ссылке
        :return: словарь со ссылкой, либо ошибка
        """
        links_yt = self.get_youtube_links_from_text()

        return {LINK: link['url']} if link not in links_yt else {ERROR: "В посте уже есть эта ссылка"}

    @staticmethod
    def delete_downloads():
        """
        Сотрёт все файлы, которые временно скачивались в директорию download
        """
        list_of_files = [f for f in os.listdir("downloads")]
        for file in list_of_files:
            os.remove(os.path.join("downloads", file))

    def add_links_to_text(self):
        """
        Добавляет полученные ссылки в конец текста поста. Если это ссылка ведёт на ютуб,
        то она будет уреза до домена youtu.be, а если ведёт на любой другой ресурс, то
        будет минифицирована методом API до vk.cc
        """
        links = [element for element in self.attachments_storage if [*element][0] in [LINK_YOUTUBE, LINK]]

        if len(links) == 1:
            self.text += '\n\nСсылка:\n'
        elif links:
            self.text += '\n\nСсылки:\n'
        else:
            return

        for link in links:
            if LINK_YOUTUBE in link:
                self.text += link[LINK_YOUTUBE].replace('watch?v=', '').replace('https://www.youtube.com',
                                                                                'youtu.be') + '\n'
            else:
                self.text += self.vk.utils.getShortLink(url=link[LINK])['short_url'] + '\n'

        self.text = self.text[:-1]
