from prompt_builder import PromptBuilder
from llm import LocalServerLlm, HuggingFaceLlm
import os
from db import DataBase
from utils import make_dir_if_not_exists, \
    write_file, replace_str_in_file, \
    delete_lines_starting_with, extract_source_code, log_to_csv
from run_test import TestExecuter
from java_parser import JavaCodeParser
import logging
import datetime
import configparser
from timeout_decorator import timeout


class TestGenerator:

    def __init__(self, project_name, run_id):

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.USE_HUGGINGFACE = self.config.getboolean('INFERENCE', 'USE_HUGGINGFACE')
        self.USE_LOCAL_WEB_SERVER = self.config.getboolean('INFERENCE', 'USE_LOCAL_WEB_SERVER')

        self.run_id = run_id

        if self.USE_HUGGINGFACE and self.USE_LOCAL_WEB_SERVER:
            raise Exception("Cannot use both HuggingFace and Local Web Server for inference")
        elif self.USE_HUGGINGFACE:
            self.llm = HuggingFaceLlm()
        elif self.USE_LOCAL_WEB_SERVER:
            self.llm = LocalServerLlm()

        self.project_name = project_name

        self.current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        logging.basicConfig(filename=f'logs/{self.run_id}.log',
                            level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        self.db = DataBase(project_name)
        self.prompt_constructor = PromptBuilder(project_name)
        self.test_executer = TestExecuter(project_name, False)
        self.java_parser = JavaCodeParser()

        # get number of methods in db
        self.num_methods = self.db.get_num_of_methods()

    def generate_target_filepaths(self, project_name: str, method_id: int):
        filepath = self.db.get_filepath_for_method(method_id)
        filepath = filepath.split('/')
        start_idx = filepath.index('java') + 1
        filepath = filepath[start_idx:-1]
        filepath_prefix = ['build', 'generated_tests', project_name]
        test_result_prefix = ['passed', 'compile_error', 'execution_error']
        execution_folder_prefix = ['execution']

        execution_filepath = os.path.join(*(filepath_prefix + execution_folder_prefix + filepath))
        passed_filepath = os.path.join(*(filepath_prefix + [test_result_prefix[0]] + filepath))
        compile_error_filepath = os.path.join(*(filepath_prefix + [test_result_prefix[1]] + filepath))
        execution_error_filepath = os.path.join(*(filepath_prefix + [test_result_prefix[2]] + filepath))

        compile_filepath = os.path.join(*(['build', 'compiled_tests', project_name] + filepath))
        prompt_path = os.path.join(*(['build', 'prompts', project_name] + filepath))

        package = ".".join(filepath) if len(filepath) > 1 else ""

        return {
            'execution_filepath': execution_filepath,
            'passed_filepath': passed_filepath,
            'compile_error_filepath': compile_error_filepath,
            'execution_error_filepath': execution_error_filepath,
            'compile_filepath': compile_filepath,
            'prompt_path': prompt_path,
            'package': package
        }

    def get_answer(self, prompt):
        print("> Prompt created, querying LLM")
        answer = self.llm(prompt)
        print("> LLM answered, processing answer")
        logging.info("LLM answered: " + answer)
        # delete the last line of the answer as it should always be ``` due to the prompt
        source_code_in_answer = extract_source_code(answer)
        if source_code_in_answer:
            answer = source_code_in_answer[-1]
            return answer
        else:
            print("> No source code in answer, skipping method")
            logging.info("No source code in answer, skipping method")
            log_to_csv(self.project_name, method_id, "No Source Code in Answer Error", 1, self.run_id)
            return None

    def add_package_information(self, answer, filepaths):
        """
        Prepare code for compilation by adding package information and deleting old package information if exists
        :param answer:
        :return:
        """
        if answer.rfind("package") != -1:
            answer = delete_lines_starting_with(answer, "package")
        answer = "package " + filepaths['package'] + ";\n\n" + answer

        logging.info("Answer created: " + answer)
        return answer

    def create_target_folders(self, filepaths):
        # create folder if not exists
        for folder in filepaths:
            if folder != "package":
                make_dir_if_not_exists(filepaths[folder])

    def change_class_name(self, method_id, filepaths, run_id=1):
        """
        Change the class name of the test file to a unique Name and rename the file to the new class name
        :param method_id: ID of method to change class name for
        :param filepaths: filpaths dictionary containing the filepaths for the method
        :param run_id: ID of the run which is used to name the class
        :return:
        """
        # change class name
        current_class_name = self.java_parser.extract_class_name(
            filepaths['execution_filepath'] + f"/{method_id}_test.java")
        new_class_name = self.db.get_class_identifier_for_method(
            method_id) + f"Test_Method_{str(method_id)}_Run_{str(self.run_id)}"
        if current_class_name:
            logging.info("Class name extracted: " + current_class_name)
            replace_str_in_file(filepaths['execution_filepath'] + f"/{method_id}_test.java", current_class_name,
                                new_class_name)
            # rename file to new class name
            os.rename(filepaths['execution_filepath'] + f"/{method_id}_test.java",
                      filepaths['execution_filepath'] + f"/{new_class_name}.java")
            return new_class_name
        else:
            print(">> Could not extract class name from test file, skipping test")
            logging.info("Could not extract class name from test file, skipping test")
            return None

    def run_compilation_repair(self, method_id, filepaths, compilation_output, new_class_name):
        try:
            print(">> Compilation failed, running LLM repair")
            logging.info("Compilation failed with the following output: " + compilation_output)
            logging.info("Running LLM repair")
            # read in text of test file which caused the error
            test_file_text = ""
            with open(filepaths['execution_filepath'] + f"/{new_class_name}.java", 'r') as file:
                test_file_text = file.read()
            prompt = self.prompt_constructor.construct_compile_error_repair_prompt(test_file_text,
                                                                                   compilation_output)

            if prompt:
                # query LLM with constructed prompt
                answer = self.get_answer(prompt)
                if not answer:
                    return False

                answer = self.add_package_information(answer, filepaths)

                logging.info("Answer created: " + answer)
                # change text of test file to repaired version
                write_file(filepaths['execution_filepath'], new_class_name, ".java", answer)
                return True
        except Exception as e:
            logging.info("Error during compilation repair: " + str(e))
            return False

    def run_execution_repair(self, filepaths, execution_output, new_class_name):
        try:
            with open(filepaths['execution_filepath'] + f"/{new_class_name}.java", 'r') as file:
                test_file_text = file.read()

            prompt = self.prompt_constructor.construct_execution_error_repair_prompt(test_file_text, execution_output)

            if prompt:
                logging.info("Created execution repair prompt: " + prompt)
                # query LLM with constructed prompt
                answer = self.get_answer(prompt)
                if not answer:
                    return False

                answer = self.add_package_information(answer, filepaths)

                logging.info("Answer created: " + answer)
                # change text of test file to repaired version
                write_file(filepaths['execution_filepath'], new_class_name, ".java", answer)
                return True
            else:
                logging.info("Could not create execution repair prompt")
                return False
        except Exception as e:
            logging.info("Error during execution repair: " + str(e))
            return False

    @timeout(600, use_signals=True)
    def generate_test_for_method(self, method_id, compilation_repair_rounds=1, execution_repair_rounds=3):
        try:
            print("\n Generating test for method " + str(method_id))
            logging.info("Generating test for method " + str(method_id))
            prompt = self.prompt_constructor.construct_initial_prompt(str(method_id))
            logging.info("Prompt created: " + prompt)

            if prompt:
                # query LLM with constructed prompt
                answer = self.get_answer(prompt)
                if not answer:
                    print(">> Could not extract answer from LLM, skipping test")
                    logging.info("Could not extract answer from LLM, skipping test")
                    log_to_csv(self.project_name, method_id, "Answer Extraction Error", 1, self.run_id)
                    return

                filepaths = self.generate_target_filepaths(self.project_name, method_id)

                answer = self.add_package_information(answer, filepaths)

                self.create_target_folders(filepaths)

                write_file(filepaths['prompt_path'], str(method_id) + "_prompt.md", "", prompt)
                write_file(filepaths['execution_filepath'], str(method_id) + "_test.java", "", answer)

                new_class_name = self.change_class_name(method_id, filepaths)

                if not new_class_name:
                    log_to_csv(self.project_name, method_id, "Class Name Extraction Error", 1, self.run_id)
                    return

                print("> Wrote test to file, compiling...")

                # initial compilation of the generated test
                compilation_result_code, compilation_output = self.test_executer.compile_test_case(
                    f"classpath_{str(method_id)}.txt",
                    filepaths['execution_filepath'] +
                    f"/{new_class_name}.java")

                # if compilation fails, try to repair the compilation error
                # run repair rounds until compilation succeeds or the maximum number of repair rounds is reached
                current_repair_round = 1
                while compilation_result_code != 0 and current_repair_round <= compilation_repair_rounds:
                    compilation_repair_sucess = self.run_compilation_repair(method_id, filepaths, compilation_output,
                                                                            new_class_name)

                    if compilation_repair_sucess:
                        # compile the test again
                        compilation_result_code, compilation_output = self.test_executer.compile_test_case(
                            f"classpath_{str(method_id)}.txt",
                            filepaths[
                                'execution_filepath'] +
                            f"/{new_class_name}.java")
                        logging.info("Compilation result: " + str(compilation_output))

                    else:
                        print(">> Could not create repair prompt, skipping test")
                        logging.info("Could not create repair prompt, skipping test")
                        log_to_csv(self.project_name, method_id,
                                   f"Compilation Repair Prompt Construction Error Round {current_repair_round}", 1,
                                   self.run_id)
                        return

                    current_repair_round += 1

                # if compilation still fails after repair, skip the test
                if compilation_result_code != 0:
                    log_to_csv(self.project_name, method_id, f"Compilation Error Round {current_repair_round - 1}", 1,
                               self.run_id, compilation_output)
                    print(">> Compilation failed after repair, skipping test \n")
                    logging.info("Compilation failed after repair, skipping test")
                    # copy java file to from execution folder to compile error folder
                    os.rename(filepaths['execution_filepath'] + f"/{new_class_name}.java",
                              filepaths['compile_error_filepath'] + f"/{new_class_name}.java")
                    return

                # if compilation succeeds, execute the test
                if compilation_result_code == 0:
                    print("> Compilation successful \n")
                    logging.info("Compilation successful")
                    log_to_csv(self.project_name, method_id, f"Compilation Successful Round {current_repair_round - 1}",
                               0,
                               self.run_id)

                    print("> Executing test \n")

                    execution_result_code, execution_output = self.test_executer.run_test(
                        f"classpath_{str(method_id)}.txt",
                        filepaths[
                            'package'] + f".{new_class_name}")

                    current_execution_repair_round = 1
                    while execution_result_code != 0 and current_execution_repair_round <= execution_repair_rounds:
                        print(">> Execution failed, running LLM repair")
                        logging.info("Execution failed with the following output: " + execution_output)
                        logging.info("Running LLM execution repair")

                        execution_repair_sucess = self.run_execution_repair(filepaths, execution_output, new_class_name)

                        if execution_repair_sucess:
                            print(">> Compiling repaired test")
                            logging.info("Compiling repaired test")

                            # compile the test again
                            compilation_result_code, compilation_output = self.test_executer.compile_test_case(
                                f"classpath_{str(method_id)}.txt",
                                filepaths['execution_filepath'] +
                                f"/{new_class_name}.java")
                            if compilation_result_code != 0:
                                print(">> Compilation failed after repair, skipping test \n")
                                logging.info("Compilation failed after repair, skipping test")
                                log_to_csv(self.project_name, method_id,
                                           f"Compilation Error during Execution Repair Round {current_execution_repair_round}",
                                           1,
                                           self.run_id)
                                # skip the test if compilation fails
                                break

                            print(">> Running repaired test")
                            logging.info("Running repaired test")
                            execution_result_code, execution_output = self.test_executer.run_test(
                                f"classpath_{str(method_id)}.txt",
                                filepaths[
                                    'package'] + f".{new_class_name}")
                            logging.info("Execution result: " + str(execution_output))
                        else:
                            print(">> Could not create repair prompt, skipping test")
                            logging.info("Could not create repair prompt, skipping test")
                            log_to_csv(self.project_name, method_id,
                                       f"Execution Repair Prompt Construction Error Round {current_execution_repair_round}",
                                       1,
                                       self.run_id)
                            return

                        current_execution_repair_round += 1

                    if execution_result_code == 0:
                        print(">> Execution successful, test will be saved \n")
                        logging.info("Execution successful, test will be saved")
                        log_to_csv(self.project_name, method_id,
                                   f"Execution Successful after {current_execution_repair_round - 1} repairs", 0,
                                   self.run_id)
                        # move java file to from execution folder to passed folder
                        os.rename(filepaths['execution_filepath'] + f"/{new_class_name}.java",
                                  filepaths['passed_filepath'] + f"/{new_class_name}.java")
                        print(">> Test finished \n")
                    else:
                        print(">> Execution failed after repair, skipping test \n")
                        log_to_csv(self.project_name, method_id,
                                   f"Execution Error after after {current_execution_repair_round - 1} repairs", 1,
                                   self.run_id, execution_output)
                        # copy java file to from execution folder to execution error folder
                        os.rename(filepaths['execution_filepath'] + f"/{new_class_name}.java",
                                  filepaths['execution_error_filepath'] + f"/{new_class_name}.java")
                        return

        except Exception as e:
            logging.exception("Exception occurred " + str(e))
            print("Exception occurred " + str(e))
            print("Skipping method")
            log_to_csv(self.project_name, method_id,
                       "Other Error", 1,
                       self.run_id, str(e))
            return

    def generate_tests_for_whole_project(self, runs_per_method=1, compilation_repair_rounds=1,
                                         execution_repair_rounds=1):
        """
        Generates tests for all methods in the project
        :param runs_per_method: Trys per method
        :param compilation_repair_rounds: Number of repair rounds for compilation errors
        :param execution_repair_rounds: Number of repair rounds for execution errors
        :return:
        """
        self.generate_tests_for_method_range(range(1, self.num_methods + 1), runs_per_method, compilation_repair_rounds,
                                             execution_repair_rounds)

    def generate_tests_for_method_range(self, method_range: range, runs_per_method=1, compilation_repair_rounds=1,
                                        execution_repair_rounds=1):
        """
        Generates tests for a range of methods in the project based on the method id
        :param method_range: range of method ids
        :param runs_per_method: Trys per method
        :param compilation_repair_rounds: Number of repair rounds for compilation errors
        :param execution_repair_rounds: Number of repair rounds for execution errors
        :return:
        """
        for run in range(1, runs_per_method + 1):
            for method_id in method_range:
                try:
                    self.generate_test_for_method(method_id, compilation_repair_rounds, execution_repair_rounds)
                except TimeoutError as e:
                    print("Function execution timed out for method " + str(method_id))
                    logging.info("Function execution timed out for method " + str(method_id))
                    log_to_csv(self.project_name, method_id, "Timeout Error", 1, self.run_id, str(e))
