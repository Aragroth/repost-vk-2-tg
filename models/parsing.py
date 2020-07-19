# -*- coding: utf-8 -*-

from assets.storage import Store
import vk_api
import time


class Parser:

    def __init__(self, vk_token: str, group_to_analyze: int, key_tag: str, sleep_time: int,
                 already_send_posts: Store, posts_analyze_count: int):
        vk_session = vk_api.VkApi(token=vk_token)
        self.vk = vk_session.get_api()

        self.already_send = already_send_posts
        self.tag = key_tag
        self.sleep_time = sleep_time
        self.posts_count = posts_analyze_count
        self.group_id = group_to_analyze

    def get_posts_to_send(self) -> dict:
        """
        Просматривает последние "self.post_count" постов и
        возвращает те, которые ещё не обрабатывались

        :return: Словарь с информацией о каждом посте
        """

        while True:
            last_posts = self.vk.wall.get(owner_id=self.group_id, count=self.posts_count)
            for post in last_posts['items']:
                if not self.already_send.contains(post['id']) and self.tag in post['text']:
                    yield post

            # Я не хочу добавлять каждый пост без "тега-ключа" в список обработанных,
            # потому что человек может захотеть позднее сделать перепост данного
            # поста в тг. Для этого ему будет достаточно отредактировать пост и добавить тег

            # TODO лог в консоль, если привышен лимит api
            # TODO если привышен лимит api, то заснуть до следующего дня

            time.sleep(self.sleep_time)
