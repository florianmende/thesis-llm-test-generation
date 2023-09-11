from tree_sitter import Language, Parser
import os


class JavaCodeParser:
    """
    This class is responsible for parsing the Java code.
    """

    def __init__(self):
        """
        This method initializes the JavaCodeParser class and builds the parser.
        """

        self.content = None

        # build the parser if it doesn't exist – only needs to be done once
        # requires the file from https://github.com/tree-sitter/tree-sitter-python to be in the vendor folder
        Language.build_library(
            # Store the library in the `build` directory
            'build/tree-sitter-languages.so',

            # Include one or more languages
            [
                'vendor/tree-sitter-java'
            ]
        )

        JAVA_LANGUAGE = Language('build/tree-sitter-languages.so', 'java')

        self.parser = Parser()
        self.parser.set_language(JAVA_LANGUAGE)

    def parse_file(self, filepath, project_name):
        """
        This method parses a single Java file given its filepath.
        :param filepath: Filepath of the Java file to parse.
        :param project_name: Name of the project the file belongs to. Used for naming the output file.
        :return:
        """

        with open(filepath, 'r') as file:
            try:
                file_content = file.read()
            except IOError:
                return {}

        # provides an object tree that can be used to extract information about certain elements
        # the tree variable contains the root node of the constructed sytax tree
        tree = self.parser.parse(bytes(file_content, "utf8"))

        # get all class declarations (usually only one per file)
        classes = [node for node in tree.root_node.children if node.type == "class_declaration"]

        # get all imports
        imports = [node for node in tree.root_node.children if node.type == "import_declaration"]

        # extract metadata for each class in the file and extract methods of the class
        class_ouput_list = []
        for class_node in classes:
            # get class identifier
            class_identifier = [item.text for item in class_node.children if item.type == "identifier"][0] \
                .decode("utf-8")
            class_modifier = [item.text for item in class_node.children if item.type == "modifiers"][0] \
                .decode("utf-8")
            class_super_interfaces = [item.text for item in class_node.children if item.type == "super_interfaces"][0] \
                .decode("utf-8")

            class_body = [item for item in class_node.children if item.type == "class_body"][0]

            class_constructor = [item.text for item in class_body.children if item.type == "constructor_declaration"][0] \
                .decode("utf-8")

            print(class_constructor)

            # class_header contains the definition of class specific variables and comments before the constructor
            # as well as the constructor itself. The correct length of the class_header is determined by the start
            # byte of the constructor and the end byte constructor declaration.
            class_header = ""
            class_header_start_byte = class_node.start_byte
            class_header_end_byte = None
            for node in class_body.children:
                if node.type == "constructor_declaration":
                    class_header_end_byte = node.end_byte

            class_header = file_content[class_header_start_byte:class_header_end_byte]

            class_full_text = class_node.text.decode("utf-8")

            print(class_header)

            # get all method declarations
            methods = [node for node in class_body.children if node.type == "method_declaration"]

            method_output_list = []

            for method in methods:
                method_identifier, method_parameters, method_full_text = self.extract_method_information(method)

                # Construct dictionary with all relevant information and write to file
                method_output = self.construct_method_output_dict(filepath,
                                                                  class_identifier,
                                                                  method_identifier,
                                                                  method_parameters,
                                                                  method_full_text)

                method_output_list.append(method_output)

            # Write method_output_list to a JSON file
            self.write_method_file(method_output_list, project_name, class_identifier)

            # Construct dictionary with all relevant information and write to file on class level
            class_output = self.construct_class_output_dict(filepath,
                                                           class_identifier,
                                                           class_modifier,
                                                           class_super_interfaces,
                                                           class_constructor,
                                                           class_header,
                                                           class_full_text)

            class_ouput_list.append(class_output)

        self.write_class_file(class_ouput_list, project_name, class_identifier)


    @staticmethod
    def extract_method_information(method_node):
        """
        This method extracts all relevant information about a method.
        :param method_node: Node of the method to extract information from.
        :return: Dictionary containing all relevant information about the method.
        """
        method_identifier = [item.text for item in method_node.children if item.type == "identifier"][0] \
            .decode("utf-8")
        method_parameters = [item.text for item in method_node.children if item.type == "formal_parameters"][0] \
            .decode("utf-8")
        method_full_text = method_node.text.decode("utf-8")

        # add comments to the method declarations if they precede the method declaration
        if method_node.prev_named_sibling.type == "comment" or method_node.prev_named_sibling.type == "block_comment":
            method_full_text = method_node.prev_named_sibling.text.decode("utf-8") + "\n" + method_full_text

        return method_identifier, method_parameters, method_full_text

    @staticmethod
    def construct_method_output_dict(filepath, class_identifier, method_identifier, method_parameters,
                                     method_full_text):
        """
        This method constructs a dictionary with all relevant information about a method.
        :param filepath: Filepath of the Java file to parse.
        :param class_identifier: Identifier of the class the method belongs to.
        :param method_identifier: Identifier of the method.
        :param method_parameters: Parameters of the method.
        :param method_full_text: Full text of the method.
        :return: Dictionary containing all relevant information about the method.
        """
        method_output = {
            "filepath": filepath,
            "class_identifier": class_identifier,
            "method_identifier": method_identifier,
            "method_parameters": method_parameters,
            "method_full_text": method_full_text
        }
        return method_output

    @staticmethod
    def construct_class_output_dict(filepath, class_identifier, class_modifier, class_super_interfaces,
                                    class_constructor, class_header, class_full_text):
        """
        This method constructs a dictionary with all relevant information about a class.
        :param filepath: Filepath of the Java file that was parsed.
        :param class_identifier: Identifier of the class.
        :param class_modifier: Modifier of the class.
        :param class_super_interfaces: Interfaces the class implements.
        :param class_constructor: Constructor of the class.
        :param class_header: Class header containing everything from the beginning of the class to the constructor.
        :param class_full_text: Full text of the class.
        :return:
        """
        class_output = {
            "filepath": filepath,
            "class_identifier": class_identifier,
            "class_modifier": class_modifier,
            "class_super_interfaces": class_super_interfaces,
            "class_constructor": class_constructor,
            "class_header": class_header,
            "class_full_text": class_full_text
        }

        return class_output

    @staticmethod
    def write_method_file(method_output_list, project_name, class_identifier):
        """
        This method writes the method_output_list to a JSON file.
        :param method_output_list: List of dictionaries containing the method information.
        :param filepath: Filepath of the Java file to parse.
        :return:
        """
        if not os.path.exists(f"./build/class_parser/{project_name}/{class_identifier}"):
            os.makedirs(f"./build/class_parser/{project_name}/{class_identifier}")
        with open(f"./build/class_parser/{project_name}/{class_identifier}/methods.json", "w") as file:
            file.write(str(method_output_list))

    @staticmethod
    def write_class_file(class_output_list, project_name, class_identifier):
        """
        This method writes the class_output_list to a JSON file.
        :param class_output_list: List of dictionaries containing the class information.
        :param project_name: Name of the project that was parsed.
        :param class_identifier: Name of the class that was parsed.
        :return:
        """
        if not os.path.exists(f"./build/class_parser/{project_name}/{class_identifier}"):
            os.makedirs(f"./build/class_parser/{project_name}/{class_identifier}")
        with open(f"./build/class_parser/{project_name}/{class_identifier}/{class_identifier}.json", "w") as file:
            file.write(str(class_output_list))
