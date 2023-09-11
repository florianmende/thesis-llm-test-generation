from file_system_parser import FileSystemParser
from java_parser import JavaCodeParser


def main():
    parser = FileSystemParser("./Java_Projects")
    parser.parse()

    # parser.parse()["jfreechart"]["files"][0]
    EXAMPLE_FILE = "Java_Projects/jfreechart/src/main/java/org/jfree/chart/annotations/AbstractAnnotation.java"

    my_java_parser = JavaCodeParser()
    my_java_parser.parse_file(EXAMPLE_FILE)



    # for i in range(0, 20):
    #     print(files[i])
    #
    # print("Total files: " + str(len(files)))


if __name__ == "__main__":
    main()