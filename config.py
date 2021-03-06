config_data = {
    # Ссылка на телеграмм-канал, где подключён бот
    'chat_link': "@bla-bla",

    # Телеграм токен бота, которого вы добавили в сообщество
    'telegram_bot_token': "telegram:token",

    # Можно использовать любой токен ВК
    'vk_service_token': "your token",

    # Айди группы, чьи посты надо анализировать
    'vk_group_id': -11111111,

    # Если хотите репостить все посты, оставьте пустым
    'key_tag': "#tag@gruop",

    # Сколько последних постов будет анализироваться каждый раз
    'posts_count': 10,

    # Сколько секунд проходит между каждым анализом.
    # Слишком малое значение исчерпает лимит API
    'sleep_time_seconds': 240
}
