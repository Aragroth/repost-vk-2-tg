# -*- coding: utf-8 -*-

from models.post_creator import Post
from tests.consts import real_post, refactored_text
import pytest


def text_post(text):
    return Post({'text': text}, -41126705)


@pytest.fixture
def post_object():
    post_data = Post(real_post, -41126705)
    yield post_data


@pytest.mark.parametrize(
    'input_post, expected_post_text, key_tag',
    [
        pytest.param(text_post('#newspace@yandex'), '', '#newspace@yandex', id='key tag check'),
        pytest.param(text_post('#abc@yandex'), '#abc', '#newspace', id='no key tag in post'),
        pytest.param(text_post('#abc@yandex #tg@newspace\n @new'), '#abc \n @new', '#tg@newspace', id='many tags'),
    ],
)
def test_tags_refactor(input_post, expected_post_text, key_tag):
    input_post.refactor_tags(key_tag)
    assert input_post.text == expected_post_text


@pytest.mark.parametrize(
    'input_post, expected_post_text',
    [
        pytest.param(text_post('[id267990964|Dima Kurdoglo]'), 'Dima Kurdoglo', id='one person'),
        pytest.param(text_post('[id267990964|Dima Kurdoglo] и [id145462869|Alisa Zaripova]'),
                     'Dima Kurdoglo и Alisa Zaripova', id='multiple persons', ),
    ],
)
def test_refactor_user_links(input_post, expected_post_text):
    input_post.refactor_user_links()
    assert input_post.text == expected_post_text


def test_full_refactor(post_object):
    post_object.refactor('#telegram@newspacepress')
    assert post_object.text == refactored_text


def test_parse_attachments(post_object):
    post_object.parse_attachments()
    print(post_object.attachments_storage)


@pytest.mark.skip(reason="Оно работает, но у меня медленный инет, чтобы каждый раз тестить :)")
@pytest.mark.parametrize(
    'post, real_list_of_links',
    [pytest.param(text_post(refactored_text), ['https://youtube.com/watch?v=zaSsO689d3w',
                                               'https://youtube.com/watch?v=wrfzG_5IQyo']),
     pytest.param(text_post("а здесь нет ни каких ссылок на ютуб"), [])],
)
def test_get_youtube_links_from_text(post, real_list_of_links):
    links = post.get_youtube_links_from_text()
    assert links == real_list_of_links


@pytest.mark.skip(reason="Оно работает, но у меня медленный инет, чтобы каждый раз тестить :)")
@pytest.mark.parametrize(
    'vk_link, youtube_link',
    [
        pytest.param("https://vk.com/video-41126705_456239239", 'https://www.youtube.com/watch?v=zaSsO689d3w'),
        pytest.param("https://vk.com/video-41126705_456239227", 'https://www.youtube.com/watch?v=bTQ-SmeLTl8'),
        pytest.param("https://vk.com/video-41126705_456239206", 'https://www.youtube.com/watch?v=527fb3-UZGo'),

    ],
)
def test_get_youtube_link_from_attachment(vk_link, youtube_link):
    data = text_post('some text').get_youtube_link_from_attachment(vk_link)
    assert data == youtube_link


