import time

from assets.storage import Store
from config import config_data as config

from models import TelegramSender, Parser, Post

ids_of_parsed_posts = Store('ids')

key_tag = config['key_tag']
vk_token = config['vk_service_token']
group_to_analyze = config['vk_group_id']


telegram_sender = TelegramSender(config['telegram_bot_token'], config['chat_link'])
parser = Parser(vk_token, group_to_analyze, key_tag, config['sleep_time_seconds'],
                ids_of_parsed_posts, config['posts_count'])

for current_post in parser.get_posts_to_send():

    post = Post(current_post, group_to_analyze, vk_token)
    post.refactor(key_tag)
    post.parse_attachments()

    ids_of_parsed_posts.append(current_post['id'])
    # Индексируем пост как отправленный сейчас, чтобы в случае ошибок
    # telegram_sender пост не пытался отправить бесконечное число раз

    telegram_sender.send_post_as_messages(post)
