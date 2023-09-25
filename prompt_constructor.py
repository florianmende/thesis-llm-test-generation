from db import DataBase
from llama_cpp import Llama
import tiktoken
from langchain.prompts import ChatPromptTemplate
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate


class PromptConstructor:

    def __init__(self, db_name):
        """
        This class is responsible for constructing the prompt for the LLM given a reference to a method in the database
        """
        self.db = DataBase(db_name)

    def prompt(self, method_id):
        pass

    def construct_initial_prompt(self, method_id):
        method = self.db.get_method_by_id(method_id)
        method_name = method["methodIdentifier"]
        class_name = method["classIdentifier"]
        related_methods = self.db.get_related_methods_of_method(method_id)
        related_classes = self.db.get_related_classes_of_method(method_id)

        related_methods_formatted = self.construct_code_prompt_from_dict_list(related_methods, "java", True)
        related_classes_formatted = self.construct_code_prompt_from_dict_list(related_classes, "java", False)

        size = 1
        prompt = ""
        while size <= 3 and self.check_token_limit(
                self._generate_prompts_with_different_size(size, method_name, class_name, method,
                                                           related_methods_formatted,
                                                           related_classes_formatted)):
            prompt = self._generate_prompts_with_different_size(size, method_name, class_name, method,
                                                                related_methods_formatted, related_classes_formatted)
            size += 1

        return prompt

    def construct_error_prompt(self, method_id, error_message):
        pass

    @staticmethod
    def construct_code_prompt_from_dict_list(code_list, language_identifier, is_method):
        """
        Constructs a prompt from a list of code snippets.
        :param code_list: the list of code snippets
        :param language_identifier: the language identifier
        :param is_method: True if the code snippets are methods, False otherwise
        :return: Single string containing all code snippets wrapped in code blocks
        """
        prompt = ""
        for code in code_list:
            if is_method:
                prompt += "Method: " + str(code["methodIdentifier"]) + "of the class " + str(
                    code["classIdentifier"]) + ":\n"
            prompt += "```" + language_identifier + "\n"
            prompt += str(code["fullText"])
            prompt += "\n```\n"
        return prompt if prompt != "" else "No relations found."

    @staticmethod
    def check_token_limit(prompt: str, token_limit: int = 4096):
        """
        Checks if the prompt is too long for the given token limit.
        :param prompt: the prompt to check
        :param token_limit: the token limit to check against
        :return: True if the prompt is too long, False otherwise
        """
        tokens = PromptConstructor.tokenize_with_model(prompt, "vendor/model/codellama-13b-instruct.Q4_K_M.gguf")
        print("Tokens: " + str(len(tokens)))
        return len(tokens) < token_limit

    @staticmethod
    def tokenize_with_model(prompt: str, model_path: str):
        """
        Generates a list of tokens for the prompt.
        Uses the Llama tokenizer provided by llama-cpp-python.
        :param prompt: the prompt to generate tokens for
        :param model_path: the path to the model to use
        :return: A list of integers representing the tokens
        """
        # tokenizer = LlamaTokenizerFast.from_pretrained(model_path)
        llm = Llama(model_path)
        tokens = llm.tokenize(bytes(prompt, "utf-8"))
        return tokens

    @staticmethod
    def tokenize_with_tiktoken(prompt: str):
        """
        Generates a list of tokens for the prompt using tiktoken with the cl100k_base encoding.
        Using this method can be usefull when running the application with OpenAI models, as they use
        the same encoding.
        :param prompt: the prompt to generate tokens for
        :return: A list of integers representing the tokens
        """
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(prompt)
        return tokens

    @staticmethod
    def _generate_prompts_with_different_size(size: int,
                                              method_name: str,
                                              class_name: str,
                                              method: dict,
                                              related_methods_formatted: str,
                                              related_classes_formatted: str, ):

        system_prompt = """
You are an expert programming assistant with attention to detail who wants to help other humans by writing \
unit tests in Java for them. 
The unit test must use the following testing framework: {testing_framework}
The unit test must use the following mocking framework: {mocking_framework}
Human will provide you with the source code of the method to be tested as well as some additional information.
Only answer with code, no additional explanations required. Add comments in the code, explaining each line and its purpose.
Name the test method accordingly to the method to be tested.
Import required classes and methods. Create a new class if necessary.
Always add necessary assertions to the test method.
                            """

        if size == 1:
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    SystemMessagePromptTemplate.from_template(
                        system_prompt
                    ),
                    HumanMessagePromptTemplate.from_template(
                        """
Generate a unit test for the following method:
Method: {method_name}
Class: {class_name}
Method code: {method_code}

Assistant: 
```java
                        """
                    )
                ])

            return prompt_template.format(
                method_name=method_name,
                class_name=class_name,
                method_code=method["fullText"],
                testing_framework="JUnit 5",
                mocking_framework="Mockito",
            )

        elif size == 2:
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    SystemMessagePromptTemplate.from_template(
                        system_prompt
                    ),
                    HumanMessagePromptTemplate.from_template(
                        """
Generate a unit test for the following method:
Method: {method_name}
Class: {class_name}
Method code: {method_code}

Here is some additional code that might be useful:

Related methods: 

{related_methods}

Assistant:
```java
                        """
                    )
                ])

            return prompt_template.format(
                method_name=method_name,
                class_name=class_name,
                method_code=method["fullText"],
                testing_framework="JUnit 5",
                mocking_framework="Mockito",
                related_methods=related_methods_formatted
            )

        elif size == 3 or size == 4:
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    SystemMessagePromptTemplate.from_template(
                        system_prompt
                    ),
                    HumanMessagePromptTemplate.from_template(
                        """
Generate a unit test for the following method:
Method: {method_name}
Class: {class_name}
Method code: {method_code}

Here is some additional code that might be useful:

Related methods: 

{related_methods}

Related classes: 

{related_classes}


Assistant:
```java
                        """
                    )
                ])

            return prompt_template.format(
                method_name=method_name,
                class_name=class_name,
                method_code=method["fullText"],
                testing_framework="JUnit 5",
                mocking_framework="Mockito",
                related_methods=related_methods_formatted,
                related_classes=related_classes_formatted,
            )
