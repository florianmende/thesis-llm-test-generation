from file_system_parser import FileSystemParser
from java_parser import JavaCodeParser
from utils import print_progress_bar, get_user_choices, IntRangeAction
from json_to_db import convert_json_to_db
import argparse
from generate_tests import TestGenerator
import multiprocessing


def main():
    argument_parser = argparse.ArgumentParser(description='Automated Unit Test Generation for Java Projects using LLMs')
    argument_parser.add_argument('--only_parse', type=bool, default=False,
                                 help='If the projects should only be parsed to json files. (no database will be generated or tests generated)')
    argument_parser.add_argument('--only_generate_tests', type=bool, default=False,
                                 help='When database for projects was already created, test generation can be run in isolation (no parsing to json files or database generation)')
    argument_parser.add_argument('--runs', type=int, default=1,
                                 help='Amount of times the test generation should be run for each project')
    argument_parser.add_argument('--method_range', action=IntRangeAction, help='Only run test generation for the methods in the range. Specify a range of integers in the format start:end')
    argument_parser.add_argument('--multiprocessing', type=int, default=0, help='Amount of processes to use for test generation. If 0, no multiprocessing will be used.')


    args = argument_parser.parse_args()

    parser = FileSystemParser("./Java_Projects")
    files = parser.parse()

    my_java_parser = JavaCodeParser()

    print("\n")

    choice = get_user_choices([project for project in files], "Choose projects to parse: ")

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
        pool.map(multiprocessed_generation, args.method_range)

        pool.close()
        pool.join()

    for project in choice:
        test_generator = TestGenerator(project)

        if not args.method_range:
            test_generator.generate_tests_for_whole_project(args.runs)
        else:
            test_generator.generate_tests_for_method_range(args.method_range, args.runs)


def multiprocessed_generation(method_id):
    test_generator = TestGenerator("commons-csv-master")
    test_generator.generate_test_for_method(method_id)

if __name__ == "__main__":
    main()
