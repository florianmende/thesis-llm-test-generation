from file_system_parser import FileSystemParser
from java_parser import JavaCodeParser


def main():
    parser = FileSystemParser("./Java_Projects")
    files = parser.parse()

    # parser.parse()["jfreechart"]["files"][0]
    # EXAMPLE_FILE = "Java_Projects/jfreechart/src/main/java/org/jfree/chart/annotations/AbstractAnnotation.java"

    my_java_parser = JavaCodeParser()

    for project in files:
        for file in files[project]["files"]:
            my_java_parser.parse_file(file, project)

    # my_java_parser.parse_file(EXAMPLE_FILE, "jfreechart")


if __name__ == "__main__":
    main()