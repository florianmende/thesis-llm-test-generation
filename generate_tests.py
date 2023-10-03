from prompt_constructor import PromptConstructor
from llm import LocalServerLlm
from langchain.llms import OpenAI
import os
from db import DataBase
from utils import make_dir_if_not_exists, write_file, replace_str_in_file, delete_lines_starting_with, measure_execution_time
from run_test import TestExecuter
from java_parser import JavaCodeParser
import logging, datetime

current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
logging.basicConfig(filename=f'logs/{current_time}.log',
                    level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def generate_target_filepaths(project_name: str, db: DataBase):
    filepath = db.get_filepath_for_method(i)
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


project_name = "datafaker-main"

llm = LocalServerLlm()
db = DataBase(project_name)
prompt_constructor = PromptConstructor(project_name, 1500)
test_executer = TestExecuter(project_name, False)
java_parser = JavaCodeParser()

# get number of methods in db
num_methods = db.get_num_of_methods()

results = []

for i in range(37, num_methods + 1):
    print("\n Generating test for method " + str(i))
    logging.info("Generating test for method " + str(i))
    prompt = prompt_constructor.construct_initial_prompt(str(i))
    logging.info("Prompt created: " + prompt)

    if prompt:
        print("> Prompt created, querying LLM")
        answer = llm(prompt)
        print("> LLM answered, processing answer")
        logging.info("LLM answered, processing answer")
        # delete the last line of the answer as it should always be ``` due to the prompt
        answer = answer[:answer.rfind("```")]

        filepaths = generate_target_filepaths(project_name, db)

        # add package information to answer and delete old package information if exists
        if answer.rfind("package") != -1:
            answer = delete_lines_starting_with(answer, "package")
        answer = "package " + filepaths['package'] + ";\n\n" + answer

        logging.info("Answer created: " + answer)
        # create folder if not exists
        for folder in filepaths:
            if folder != "package":
                make_dir_if_not_exists(filepaths[folder])

        write_file(filepaths['prompt_path'], str(i) + "_prompt.md", "", prompt)
        write_file(filepaths['execution_filepath'], str(i) + "_test.java", "", answer)

        # change class name
        current_class_name = java_parser.extract_class_name(filepaths['execution_filepath'] + f"/{i}_test.java")
        new_class_name = db.get_class_identifier_for_method(i) + f"Test_Method_{str(i)}_Run_1"
        if current_class_name:
            logging.info("Class name extracted: " + current_class_name)
            replace_str_in_file(filepaths['execution_filepath'] + f"/{i}_test.java", current_class_name, new_class_name)
            # rename file to new class name
            os.rename(filepaths['execution_filepath'] + f"/{i}_test.java",
                      filepaths['execution_filepath'] + f"/{new_class_name}.java")
        else:
            print(">> Could not extract class name from test file, skipping test")
            logging.info("Could not extract class name from test file, skipping test")
            continue

        # TODO Change Run var for more than one run per method
        print("> Wrote test to file, compiling...")

        # compile the test
        compilation_result_code, compilation_output = test_executer.compile_test_case(f"classpath_{str(i)}.txt",
                                                                                      filepaths['execution_filepath'] +
                                                                                      f"/{new_class_name}.java")

        if compilation_result_code != 0:
            print(">> Compilation failed, running LLM repair")
            logging.info("Initial compilation failed with the following output: " + compilation_output)
            logging.info("Running LLM repair")
            # read in text of test file which caused the error
            test_file_text = ""
            with open(filepaths['execution_filepath'] + f"/{new_class_name}.java", 'r') as file:
                test_file_text = file.read()
            prompt = prompt_constructor.construct_compile_error_repair_prompt(test_file_text, compilation_output)

            if prompt:
                logging.info("Prompt created: " + prompt)
                answer = llm(prompt)
                answer = answer[:answer.rfind("```")]

                # add package information to answer and delete old package information if exists
                if answer.rfind("package") != -1:
                    answer = delete_lines_starting_with(answer, "package")
                answer = "package " + filepaths['package'] + ";\n\n" + answer

                logging.info("Answer created: " + answer)
                # change text of test file to repaired version
                write_file(filepaths['execution_filepath'], new_class_name, ".java", answer)

                # compile the test again
                compilation_result_code, compilation_output = test_executer.compile_test_case(f"classpath_{str(i)}.txt",
                                                                                              filepaths[
                                                                                                  'execution_filepath'] +
                                                                                              f"/{new_class_name}.java")
            else:
                print(">> Could not create repair prompt, skipping test")
                logging.info("Could not create repair prompt, skipping test")
                continue

            if compilation_result_code != 0:
                print(">> Compilation failed after repair, skipping test \n")
                logging.info("Compilation failed after repair, skipping test")
                # copy java file to from execution folder to compile error folder
                os.rename(filepaths['execution_filepath'] + f"/{new_class_name}.java",
                            filepaths['compile_error_filepath'] + f"/{new_class_name}.java")
                continue

        if compilation_result_code == 0:
            print("> Compilation successful \n")
            logging.info("Compilation successful")

            print("> Executing test \n")

            execution_result_code, execution_output = test_executer.run_test(f"classpath_{str(i)}.txt", filepaths[
                'package'] + f".{new_class_name}")

            if execution_result_code != 0:
                print(">> Execution failed, skipping test")
                logging.info("Execution failed with the following output: ")
                # copy java file to from execution folder to execution error folder
                os.rename(filepaths['execution_filepath'] + f"/{new_class_name}.java",
                          filepaths['execution_error_filepath'] + f"/{new_class_name}.java")
                print(execution_output)
                continue

            if execution_result_code == 0:
                print(">> Execution successful, test will be saved \n")
                logging.info("Execution successful, test will be saved")
                # move java file to from execution folder to passed folder
                os.rename(filepaths['execution_filepath'] + f"/{new_class_name}.java",
                            filepaths['passed_filepath'] + f"/{new_class_name}.java")
                print(">> Test finished \n")
