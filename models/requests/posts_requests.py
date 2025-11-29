# models/requests/posts_requests.py

from pydantic import BaseModel
from utils.data_generators.fake_credentials import faker


class PublishPostPayload(BaseModel):
    title: str
    content: str

    # ---------- методы-утилиты ----------
    @classmethod
    def random(cls) -> "PublishPostPayload":
        """создаёт случайный валидный пост"""
        return cls(
            title=faker.sentence(nb_words=5),
            content=faker.paragraph(nb_sentences=2)
        )


class AddCommentPayload(BaseModel):
    text: str

    # ---------- методы-утилиты ----------
    @classmethod
    def random(cls) -> "AddCommentPayload":
        """создаёт случайный валидный комментарий"""
        return cls(
            text=faker.sentence(nb_words=5)
        )
