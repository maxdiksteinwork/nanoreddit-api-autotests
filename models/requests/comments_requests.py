# models/requests/comments_requests.py

from pydantic import BaseModel
from utils.data_generators.fake_credentials import faker


class ReplyCommentPayload(BaseModel):
    text: str

    @classmethod
    def random(cls) -> "ReplyCommentPayload":
        return cls(text=faker.sentence(nb_words=6))
