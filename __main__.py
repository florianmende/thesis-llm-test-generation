from file_system_parser import FileSystemParser


def main():
    parser = FileSystemParser("./Java_Projects")
    parser.parse()

    print(parser._parse_folder())

    # for i in range(0, 20):
    #     print(files[i])
    #
    # print("Total files: " + str(len(files)))


if __name__ == "__main__":
    main()