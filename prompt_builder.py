from db import DataBase
from llama_cpp import Llama
import tiktoken
from prompt_templates import compile_error_prompt, prompt_template_1, prompt_template_2, prompt_template_3, \
    prompt_template_4, system_prompt, execution_error_prompt
import configparser


class PromptBuilder:

    def __init__(self, db_name):
        """
        This class is responsible for constructing the prompt for the LLM given a reference to a method in the database
        :param db_name: the name of the database
        :param max_tokens: the maximum number of tokens allowed in the prompt
        """
        self.db = DataBase(db_name)

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.USE_MODEL = self.config.getboolean('MODEL', 'USE_MODEL')

        if self.USE_MODEL:
            self.MODEL_PATH = self.config.get('MODEL', 'MODEL_PATH')

        self.max_tokens = int(self.config.get('MODEL', 'MODEL_MAX_INPUT_TOKENS'))

    def construct_initial_prompt(self, method_id):
        method = self.db.get_method_by_id(method_id)
        method_name = method["methodIdentifier"]
        class_name = method["classIdentifier"]
        related_methods = self.db.get_related_methods_of_method(method_id)
        related_classes = self.db.get_related_classes_of_method(method_id)
        imports = self.db.get_imports_of_class(class_name)
        package = self.db.get_package_of_class(class_name)
        class_header = self.db.get_class_header_for_method(method_id)

        related_methods_formatted = self.construct_code_prompt_from_dict_list(related_methods, "java", True)
        related_classes_formatted = self.construct_code_prompt_from_dict_list(related_classes, "java", False)

        size = 1
        prompt = ""
        while size <= 4 and self.check_token_limit(
                self._generate_prompts_with_different_size(size, method_name, class_name, method,
                                                           related_methods_formatted,
                                                           related_classes_formatted, imports, package, class_header)):
            prompt = self._generate_prompts_with_different_size(size, method_name, class_name, method,
                                                                related_methods_formatted, related_classes_formatted,
                                                                imports, package, class_header)
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
                prompt += "Method: " + str(code["methodIdentifier"]) + " of the class " + str(
                    code["classIdentifier"]) + ":\n"
            prompt += "```" + language_identifier + "\n"
            prompt += str(code["fullText"])
            prompt += "\n```\n"
        return prompt if prompt != "" else "No relations found."

    def check_token_limit(self, prompt: str):
        """
        Checks if the prompt is too long for the given token limit.
        :param prompt: the prompt to check
        :param token_limit: the token limit to check against
        :return: True if the prompt is too long, False otherwise
        """
        if self.USE_MODEL:
            tokens = self.tokenize_with_model(prompt, self.MODEL_PATH)
        else:
            tokens = self.tokenize_with_tiktoken(prompt)
        return len(tokens) < self.max_tokens

    def construct_compile_error_repair_prompt(self, method_text, error_message):
        """
        Constructs a prompt for the repair of a compile error.
        :param method_text: the method text
        :param error_message: the error message
        :return: A prompt that instructs the LLM to repair the compile error
        """
        prompt = str.format(compile_error_prompt.compile_error_prompt,
                            error_message=error_message,
                            method_text=method_text)
        if self.check_token_limit(prompt):
            return prompt
        else:
            return ""

    def construct_execution_error_repair_prompt(self, method_text, error_message):
        """
        Constructs a prompt for the repair of an execution error.
        :param method_text: the method text
        :param error_message: the error message
        :return: A prompt that instructs the LLM to repair the execution error
        """
        prompt = str.format(execution_error_prompt.execution_error_prompt,
                            error_message=error_message,
                            method_text=method_text)
        if self.check_token_limit(prompt):
            return prompt
        else:
            return ""

    def tokenize_with_model(self, prompt: str, model_path: str):
        """
        Generates a list of tokens for the prompt.
        Uses the Llama tokenizer provided by llama-cpp-python.
        :param prompt: the prompt to generate tokens for
        :param model_path: the path to the model to use
        :return: A list of integers representing the tokens
        """
        llm = Llama(model_path, n_ctx=self.max_tokens, verbose=False)
        tokens = llm.tokenize(bytes(prompt, "utf-8"))
        return tokens

    @staticmethod
    def tokenize_with_tiktoken(prompt: str):
        """
        Generates a list of tokens for the prompt using tiktoken with the cl100k_base encoding.
        Using this method can be useful when running the application with OpenAI models, as they use
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
                                              related_classes_formatted: str,
                                              imports: str,
                                              package: str,
                                              class_header: str):

        if size == 1:
            prompt_template = "\n".join(
                [
                    system_prompt.system_prompt,
                    prompt_template_1.prompt_template_1
                ])

            return prompt_template.format(
                method_name=method_name,
                class_name=class_name,
                method_code=method["fullText"],
                testing_framework="JUnit 5",
                mocking_framework="Mockito",
                package=package,
                imports=imports
            )

        elif size == 2:
            prompt_template = "\n".join(
                [
                    system_prompt.system_prompt,
                    prompt_template_2.prompt_template_2
                ])

            return prompt_template.format(
                method_name=method_name,
                class_name=class_name,
                method_code=method["fullText"],
                testing_framework="JUnit 5",
                mocking_framework="Mockito",
                package=package,
                imports=imports,
                class_header=class_header
            )

        elif size == 3:
            prompt_template = "\n".join(
                [
                    system_prompt.system_prompt,
                    prompt_template_3.prompt_template_3
                ])

            return prompt_template.format(
                method_name=method_name,
                class_name=class_name,
                method_code=method["fullText"],
                testing_framework="JUnit 5",
                mocking_framework="Mockito",
                related_methods=related_methods_formatted,
                package=package,
                imports=imports,
                class_header=class_header
            )

        elif size == 4 or size == 5:
            prompt_template = "\n".join(
                [
                    system_prompt.system_prompt,
                    prompt_template_4.prompt_template_4
                ])

            return prompt_template.format(
                method_name=method_name,
                class_name=class_name,
                method_code=method["fullText"],
                testing_framework="JUnit 5",
                mocking_framework="Mockito",
                related_methods=related_methods_formatted,
                related_classes=related_classes_formatted,
                package=package,
                imports=imports,
                class_header=class_header
            )
