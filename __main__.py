from file_system_parser import FileSystemParser
from java_parser import JavaCodeParser
from utils import print_progress_bar, get_user_choices
from json_to_db import convert_json_to_db


def main():
    parser = FileSystemParser("./Java_Projects")
    files = parser.parse()

    my_java_parser = JavaCodeParser()

    print("\n")

    choice = get_user_choices([project for project in files], "Choose projects to parse: ")

    for project in [project for project in files if project in choice]:
        n_files = len(files[project]["files"])
        curr_file = 1
        for file in files[project]["files"]:
            my_java_parser.parse_file(file, project)
            print_progress_bar(curr_file, n_files, prefix="Parsing files in project: {}".format(project),
                               display_100_percent=True)
            curr_file += 1

    convert_json_to_db(choice)


if __name__ == "__main__":
    main()
