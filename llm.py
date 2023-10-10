from langchain.llms import OpenAI
import os
import warnings
from utils import measure_execution_time
import requests
from dotenv import load_dotenv
import configparser


class LocalServerLlm(OpenAI):
    """
    This class can be used to make the langchain API work with a local server hosted through
    the llama-cpp-python project.
    """

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.MODEL_MAX_OUTPUT_TOKENS = self.config.getint('INFERENCE', 'MODEL_MAX_OUTPUT_TOKENS')
        self.LOCAL_WEB_SERVER_PORT = self.config.get('INFERENCE', 'LOCAL_WEB_SERVER_PORT')

        os.environ[
            "OPENAI_API_KEY"
        ] = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # can be anything
        os.environ["OPENAI_API_BASE"] = "http://localhost:8000/v1"
        os.environ["OPENAI_API_HOST"] = "http://localhost:8000"

        warnings.filterwarnings("ignore")
        super().__init__(
            model_name="gpt-3.5-turbo",  # can be anything
            openai_api_base=f"http://localhost:{self.LOCAL_WEB_SERVER_PORT}/v1",
            top_p=0.95,
            temperature=0.5,
            max_tokens=self.MODEL_MAX_OUTPUT_TOKENS,
            model_kwargs=dict(
                openai_key="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            ),
            presence_penalty=0.0,
            n=1,
            best_of=3,
            batch_size=1,
            logit_bias={},
            streaming=False,
            stop_field=["</s>"]
        )

    @measure_execution_time(">> LLM query")
    def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


class HuggingFaceLlm:

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.MODEL_MAX_OUTPUT_TOKENS = self.config.getint('INFERENCE', 'MODEL_MAX_OUTPUT_TOKENS')
        self.API_URL = self.config.get('INFERENCE', 'HUGGINGFACE_INFERENCE_URL')

        load_dotenv()
        self.headers = {"Authorization": f"Bearer {os.getenv('HF_API_KEY')}"}

    def query(self, payload):
        response = requests.post(self.API_URL, headers=self.headers, json=payload)
        return response.json()

    @measure_execution_time(">> LLM query")
    def __call__(self, message):
        result = self.query({
            "inputs": message,
            "parameters": {
                "max_new_tokens": self.MODEL_MAX_OUTPUT_TOKENS,
                "return_full_text": False,
                "temperature": 0.5,
                "max_time": 100,
            },
            "options": {
                "use_cache": False,
            }
        })
        if result:
            return result[0]["generated_text"]
