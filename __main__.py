import configparser
from file_system_scanner import FileSystemScanner
from java_parser import JavaCodeParser
from utils import print_progress_bar, get_user_choices, IntRangeAction, create_log_csv
from json_to_db import convert_json_to_db
import argparse
from generate_tests import TestGenerator
import multiprocessing
from datetime import datetime
from db import DataBase

def main():
    argument_parser = argparse.ArgumentParser(description='Automated Unit Test Generation for Java Projects using LLMs')
    argument_parser.add_argument('--only_parse', type=bool, default=False,
                                 help='If the projects should only be parsed to json files. (no database will be generated or tests generated)')
    argument_parser.add_argument('--only_generate_tests', type=bool, default=False,
                                 help='When database for projects was already created, test generation can be run in isolation (no parsing to json files or database generation)')
    argument_parser.add_argument('--runs', type=int, default=1,
                                 help='Amount of times the test generation should be run for each project')
    argument_parser.add_argument('--method_range', action=IntRangeAction,
                                 help='Only run test generation for the methods in the range. Specify a range of integers in the format start:end')
    argument_parser.add_argument('--multiprocessing', type=int, default=0,
                                 help='Amount of processes to use for test generation. If 0, no multiprocessing will be used.')
    argument_parser.add_argument('--compilation_repair_rounds', type=int, default="1",
                                 help='Amount of rounds to run the compilation repair for each method.')
    argument_parser.add_argument('--execution_repair_rounds', type=int, default=1,
                                 help='Amount of rounds to run the execution repair for each method.')
    argument_parser.add_argument('--run_id', type=str, default=None,
                                 help='Option to manually specify the run id which will be used to name the generated tests and log files.')

    args = argument_parser.parse_args()
    config = configparser.ConfigParser()
    config.read('config.ini')

    if config.getboolean("INFERENCE", "USE_HUGGINGFACE") and config.getboolean("INFERENCE", "USE_LOCAL_WEB_SERVER"):  # both true
        raise Exception("Both USE_HUGGINGFACE and USE_LOCAL_WEB_SERVER are set to true. Please set one of them to false.")

    if args.run_id is not None:
        RUN_ID = args.run_id
    else:
        RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

    create_log_csv(RUN_ID)

    parser = FileSystemScanner("./Java_Projects")
    files = parser.parse()

    my_java_parser = JavaCodeParser()

    print("\n")

    choice = get_user_choices([project for project in files], "Choose project to parse: ")

    for project in [project for project in files if project in choice]:
        if not args.only_generate_tests:
            n_files = len(files[project]["files"])
            curr_file = 1
            for file in files[project]["files"]:
                my_java_parser.parse_file(file, project)
                print_progress_bar(curr_file, n_files, prefix="Parsing files in project: {}".format(project),
                                   display_100_percent=True)
                curr_file += 1

        if args.only_parse:
            exit()

    if not args.only_generate_tests:
        convert_json_to_db(choice)

    if args.multiprocessing != 0:
        pool = multiprocessing.Pool(args.multiprocessing)
        if not args.method_range:
            db = DataBase(choice[0])
            n_methods = db.get_num_of_methods()
            pool.map_async(multiprocessed_generation, [(x, choice[0], args.compilation_repair_rounds, args.execution_repair_rounds, RUN_ID) for x in range(1, n_methods+1)]).get(timeout=3600)
        else:
            pool.map(multiprocessed_generation, [(x, choice[0], args.compilation_repair_rounds, args.execution_repair_rounds, RUN_ID) for x in args.method_range])

        pool.close()
        pool.join()
    else:
        for project in choice:
            test_generator = TestGenerator(project, RUN_ID)

            if not args.method_range:
                test_generator.generate_tests_for_whole_project(args.runs, args.compilation_repair_rounds,
                                                                args.execution_repair_rounds)
            else:
                test_generator.generate_tests_for_method_range(args.method_range, args.runs, args.compilation_repair_rounds,
                                                               args.execution_repair_rounds)


def multiprocessed_generation(args):
    method_id, project_choice, compilation_repair_rounds, execution_repair_rounds, RUN_ID = args
    test_generator = TestGenerator(project_choice, RUN_ID)
    test_generator.generate_test_for_method(method_id, compilation_repair_rounds, execution_repair_rounds)


if __name__ == "__main__":
    main()
