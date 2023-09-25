from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
import os


class LocalServerLlm(OpenAI):
    """
    This class can be used to make the langchain API work with a local server hosted through
    the llama-cpp-python project.
    Simply adjust the e
    """

    def __init__(self):
        os.environ[
            "OPENAI_API_KEY"
        ] = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # can be anything
        os.environ["OPENAI_API_BASE"] = "http://localhost:8000/v1"
        os.environ["OPENAI_API_HOST"] = "http://localhost:8000"

        super().__init__(
            model_name="text-davinci-003",  # can be anything indeed
            temperature=0.75,
            openai_api_base="http://localhost:8000/v1",
            max_tokens=2000,
            top_p=1.0,
            model_kwargs=dict(
                openai_key="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                top_k=1,
            ),
            presence_penalty=0.0,
            n=1,
            best_of=1,
            batch_size=1,
            logit_bias={},
            streaming=False,
            stop_field=["Human: "]
        )
