import json
from typing import List

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
        classes = JavaCodeParser.extract_classes_of_tree(tree)

        # get all imports
        # has do be done here, as there is no access to the imports on a class level
        imports = JavaCodeParser.extract_import_declarations(tree)

        # extract metadata for each class in the file and extract methods of the class
        class_output_list = []
        for class_node in classes:
            # filter out test classes based on the @Test annotation
            if JavaCodeParser.is_test_class(class_node):
                continue

            class_output = JavaCodeParser.extract_class_information(class_node, filepath)
            method_output = JavaCodeParser.extract_all_method_information(class_node, class_output["class_identifier"],
                                                                          filepath)

            # Write method_output_list to a JSON file
            self.write_method_file(method_output, project_name, class_output["class_identifier"])

            # Construct dictionary with all relevant information and write to file on class level
            class_output_list.append(class_output)

        if class_output_list:
            self.write_class_file(class_output_list, project_name, class_output["class_identifier"])

    @staticmethod
    def is_test_class(class_node):
        """
        This method checks if a class is a test class based on the @Test annotation.
        :param class_node: A class node produced by tree-sitter.
        :return: True if the class is a test class, False otherwise.
        """
        is_test_class = class_node.text.decode('utf-8').find("@Test") != -1
        return is_test_class

    @staticmethod
    def extract_all_method_information(class_node, class_identifier, filepath):
        """
        This method extracts information about a method including its identifier, parameters and full text.
        :param class_node: A method node produced by tree-sitter.
        :param class_identifier: Identifier of the class the method belongs to.
        :param filepath: Filepath of the Java file the method belongs to.
        :return: Dictionary containing all relevant information.
        """
        class_body = [item for item in class_node.children if item.type == "class_body"][0]
        class_methods = [node for node in class_body.children if node.type == "method_declaration"]
        class_variables = JavaCodeParser.extract_class_level_variable_declaration(class_body)

        method_output_list = []

        for method in class_methods:
            method_identifier = [item.text for item in method.children if item.type == "identifier"][0] \
                .decode("utf-8")
            method_parameter_container = [item for item in method.children if item.type == "formal_parameters"][0]
            method_parameters = [parameter for parameter in method_parameter_container.children if
                                 parameter.type == "formal_parameter"]
            method_parameters_output = {}
            for parameter in method_parameters:
                if parameter.children[0].type == "type_identifier":
                    method_parameters_output[parameter.children[1].text.decode("utf-8")] = \
                        parameter.children[0].text.decode("utf-8")
            method_full_text = method.text.decode("utf-8")

            # add comments to the method declarations if they precede the method declaration
            if method.prev_named_sibling.type == "comment" or method.prev_named_sibling.type == "block_comment":
                method_full_text = method.prev_named_sibling.text.decode("utf-8") + "\n" + method_full_text

            related_classes = JavaCodeParser.extract_related_classes_of_method(method)

            related_methods = JavaCodeParser.extract_related_methods_of_method(method, method_parameters_output,
                                                                               class_identifier, class_variables)

            method_output_list.append({
                "method_identifier": method_identifier,
                "method_parameter_types": method_parameters_output,
                "method_full_text": method_full_text,
                "class_identifier": class_identifier,
                "filepath": filepath,
                "related_classes": related_classes,
                "related_methods": related_methods
            })

        return method_output_list

    @staticmethod
    def extract_class_information(class_node, filepath):
        """
        This method extracts information about a class including its identifier, modifiers, super interfaces,
        related classes and constructors.
        :param class_node: A class node produced by tree-sitter.
        :param filepath: Filepath of the Java file the class belongs to.
        :return: Dictionary containing all relevant information.
        """
        class_identifier = [item.text for item in class_node.children if item.type == "identifier"][0] \
            .decode("utf-8")

        class_modifier = [item.text for item in class_node.children if item.type == "modifiers"]
        class_modifier = class_modifier[0].decode('utf-8') if class_modifier else ""

        class_super_interfaces = [item.text for item in class_node.children if item.type == "super_interfaces"]
        class_super_interfaces = class_super_interfaces[0].decode("utf-8") if class_super_interfaces else ""




        class_body = [item for item in class_node.children if item.type == "class_body"][0]

        class_constructors = JavaCodeParser.extract_class_constructors(class_node)

        # class_header contains the definition of class specific variables and comments before the constructor
        # The correct length of the class_header is determined by the start
        # byte of the class body and the start byte constructor declaration.
        class_header = ""
        class_header_start_byte = class_node.start_byte
        class_header_end_byte = None
        for node in class_body.children:
            if node.type == "constructor_declaration":
                class_header_end_byte = node.start_byte

        # class_header = file_content[class_header_start_byte:class_header_end_byte]

        class_full_text = class_node.text.decode("utf-8")

        class_methods = [JavaCodeParser.extract_method_identifier_parameter_types(node) for node in class_body.children
                         if node.type == "method_declaration"]

        class_variable_declarations = JavaCodeParser.extract_class_level_variable_declaration(class_body)

        class_output = JavaCodeParser.construct_class_output_dict(filepath,
                                                                  class_identifier,
                                                                  class_modifier,
                                                                  class_super_interfaces,
                                                                  class_constructors,
                                                                  # class_header,
                                                                  class_full_text,
                                                                  class_methods,
                                                                  class_variable_declarations)

        return class_output

    @staticmethod
    def extract_class_level_variable_declaration(class_body):
        """
        This method extracts the variable declarations of a class. Following this structure:
        [{
            "variable_identifier": "variableName",
            "variable_type": "variableType"
            }, ...]
        :param class_node: A class node produced by tree-sitter.
        :return: Class variable declarations.
        """
        declarations = [node for node in class_body.named_children if node.type == "field_declaration"]
        variable_declarations = []
        for declaration in declarations:
            variable_type = [item.text for item in declaration.children if item.type == "type_identifier"]
            # certain built-in types are not relevant for the analysis and are not specified by "type_identifier"
            # but "boolean_type" etc. Therefore, we simply set them to "primitive_type" for now.
            if variable_type:
                variable_type = variable_type[0].decode("utf-8")
            else:
                variable_type = "primitive_type"
            variable_identifier = [item.text for item in declaration.children if item.type == "variable_declarator"][0] \
                .decode("utf-8")
            variable_identifier = variable_identifier.split("=")[0].strip()
            variable_declarations.append({
                "variable_identifier": variable_identifier,
                "variable_type": variable_type
            })

        return variable_declarations

    @staticmethod
    def extract_class_constructors(class_node):
        """
        This method extracts the constructors of a class. Following this structure:
        [{
            "constructor_identifier": "ConstructorName",
            "constructor_parameter_types": ["param_type1", "param_type2", ...],
            "related_classes": ["related_class1", "related_class2", ...]
            }, ...]
        :param class_node: A class node produced by tree-sitter.
        :return: Class constructors.
        """
        class_body = [item for item in class_node.children if item.type == "class_body"][0]
        class_constructors = [node for node in class_body.children if node.type == "constructor_declaration"]

        class_constructors_output = []
        for constructor in class_constructors:
            constructor_information = JavaCodeParser.extract_method_identifier_parameter_types(constructor)
            constructor_related_classes = JavaCodeParser.extract_related_classes_of_method(constructor)

            class_constructors_output.append({
                "constructor_identifier": constructor_information["method_identifier"],
                "constructor_parameter_types": constructor_information["method_parameter_types"],
                "related_classes": constructor_related_classes
            })

        return class_constructors_output

    @staticmethod
    def extract_method_identifier_parameter_types(method_node):
        """
        This method extracts the identifier and parameter types of a method.
        :param method_node: A method node produced by tree-sitter.
        :return: Method identifier and parameter types.
        """
        method_identifier = [item.text for item in method_node.children if item.type == "identifier"][0] \
            .decode("utf-8")
        method_parameter_container = [item for item in method_node.children if item.type == "formal_parameters"][0]
        method_parameters = [parameter for parameter in method_parameter_container.children if
                             parameter.type == "formal_parameter"]
        method_parameter_types = [parameter_child.children[0].text.decode("utf-8") for parameter_child in
                                  method_parameters if parameter_child.children[0].type == "type_identifier"]

        return {
            "method_identifier": method_identifier,
            "method_parameter_types": method_parameter_types
        }

    @staticmethod
    def extract_import_declarations(tree_node):
        """
        This method extracts all import declarations of a Java file.
        :param tree_node: Tree returned by the tree-sitter parser.
        :return: List of import declarations.
        """
        imports = [node for node in tree_node.root_node.children if node.type == "import_declaration"]
        return imports

    @staticmethod
    def extract_classes_of_tree(tree_node):
        """
        This method returns all Java classes of a tree node.
        :param tree_node: Tree returned by the tree-sitter parser.
        :return: List of classes.
        """
        classes = [node for node in tree_node.root_node.children if node.type == "class_declaration"]
        return classes

    @staticmethod
    def extract_related_classes_of_method(method_node):
        """
        This method extracts all related classes of a method. Related classes are classes that are used for
        initializing class variables.
        :param method_node: Node of the method to extract information from.
        :return: List of related class identifiers used for initializing class variables.
        """
        method_body = []

        if method_node.type == 'constructor_declaration':
            method_body = [item for item in method_node.children if item.type == "constructor_body"]

        elif method_node.type == 'method_declaration':
            method_body = [item for item in method_node.children if item.type == "block"]

        if method_body:
            method_body = method_body[0]
            object_creation_expressions = JavaCodeParser.find_nodes_with_type(method_body, "object_creation_expression")
            related_classes = [JavaCodeParser.find_nodes_with_type(item, "type_identifier")[0].text.decode("utf-8")
                               for item in object_creation_expressions]

            return related_classes

        return []

    @staticmethod
    def find_nodes_with_type(node, node_type: str = None):
        """
        This method traverses all children nodes of the given node and
        returns a list of all nodes with the specified type.
        :param node: A node produced by tree-sitter.
        :param result: A list of nodes with the specified type.
        :param node_type: A string specifying the type of nodes to return.
        :return: List of nodes with the specified type.
        """
        result = []

        def dfs(node, node_type):
            if node.type == node_type:
                result.append(node)

            for child in node.children:
                dfs(child, node_type)

        dfs(node, node_type)

        return result

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
                                    class_constructors, class_full_text, class_methods, class_variable_declarations):
        """
        This method constructs a dictionary with all relevant information about a class.
        :param filepath: Filepath of the Java file that was parsed.
        :param class_identifier: Identifier of the class.
        :param class_modifier: Modifier of the class.
        :param class_super_interfaces: Interfaces the class implements.
        :param class_constructors: Constructor of the class.
        :param class_header: Class header containing everything from the beginning of the class to the constructor.
        :param class_full_text: Full text of the class.
        :param class_methods: List of dictionaries containing all relevant information about the methods of the class.
        :param class_variable_declarations: List of dictionaries containing class level variable declarations.
        :return:
        """
        class_output = {
            "filepath": filepath,
            "class_identifier": class_identifier,
            "class_modifier": class_modifier,
            "class_super_interfaces": class_super_interfaces,
            "class_constructors": class_constructors,
            # "class_header": class_header,
            "class_full_text": class_full_text,
            "class_methods": class_methods,
            "class_variable_declarations": class_variable_declarations
        }

        return class_output

    @staticmethod
    def write_method_file(method_output_list, project_name, class_identifier):
        """
        This method writes the method_output_list to a JSON file.
        :param method_output_list: List of dictionaries containing the method information.
        :param project_name: Name of the project that was parsed.
        :param class_identifier: Name of the class that was parsed.
        :return:
        """
        if not os.path.exists(f"./build/class_parser/{project_name}/{class_identifier}"):
            os.makedirs(f"./build/class_parser/{project_name}/{class_identifier}")
        with open(f"./build/class_parser/{project_name}/{class_identifier}/methods.json", "w") as file:
            file.write(json.dumps(method_output_list))

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
            file.write(json.dumps(class_output_list))

    @staticmethod
    def extract_related_methods_of_method(method, method_parameters, class_identifier, class_variables):
        method_body = JavaCodeParser.find_nodes_with_type(method, "block")

        if not method_body:
            return []
        else:
            method_body = method_body[0]

        # differentiate between method and constructor
        node_type = method.type.split("_")[0]

        # extract invocations in the method body
        invocations = JavaCodeParser.find_nodes_with_type(method_body, "{}_invocation".format(node_type))

        # get variable declarations within the method body to determine the type of the arguments
        # if the argument is a variable, the type is the type of the variable
        variables = JavaCodeParser.extract_variable_declarations_of_method(method_body)

        methods = []

        for invocation in invocations:
            method_name = invocation.child_by_field_name("name")
            object = invocation.child_by_field_name("object")
            # if object is None, the method is called on the class itself
            object_name = object.text.decode('utf-8') if object else "this"

            # covert objects to corresponding types based on variable declarations in the method
            if object_name in variables:
                object_name = variables[object_name]
            # check if object was passed as argument
            elif object_name in method_parameters:
                object_name = method_parameters[object_name]
            # check if variable is a class variable
            elif object_name.replace("this.", "") in [var["variable_identifier"] for var in class_variables] \
                    and object.type == "field_access":
                object_name = [var["variable_type"] for var in class_variables
                               if var["variable_identifier"] == object_name.replace("this.", "")][0]
            elif object_name == "this":
                object_name = class_identifier

            arguments = invocation.child_by_field_name("arguments")

            # get argument types
            argument_types = JavaCodeParser.extract_method_invocation_argument_types(invocation, variables)

            # construct dictionary
            invocation_dict = {
                "method_name": method_name.text.decode("utf-8"),
                "method_class": object_name,
                "argument_types": argument_types,
            }

            methods.append(invocation_dict)

        return methods

    @staticmethod
    def extract_method_invocation_argument_types(method_invocation, variable_declarations):
        """
        This method extracts the types of the arguments of a method invocation.
        :param method_invocation: Method invocation to extract the argument types from.
        :param variable_declarations: Dictionary containing the variable declarations of the method.
        The keys are the names of the variables and the values are the types of the variables.
        :return: List of argument types following the order of the arguments in the method invocation.
        """
        arguments = method_invocation.child_by_field_name("arguments")
        argument_types = []
        for arg in arguments.named_children:
            if arg.type == "identifier":
                arg = arg.text.decode("utf-8")
                if arg in variable_declarations:
                    argument_types.append(variable_declarations[arg])

        return argument_types

    @staticmethod
    def extract_variable_declarations_of_method(method_body):
        """
        This method extracts all variable declarations of a method.
        :param method_body: Method body to extract the variable declarations from.
        :return: Dictionary containing the names of the variables as keys and the types of the variables as values.
        """
        declarations = JavaCodeParser.find_nodes_with_type(method_body, "local_variable_declaration")

        variable_declarations = {}

        for declaration in declarations:
            variable_type = declaration.child_by_field_name("type").text.decode("utf-8")
            variable_declarator = JavaCodeParser.find_nodes_with_type(declaration, "variable_declarator")[0]
            variable_name = JavaCodeParser.find_nodes_with_type(variable_declarator, "identifier")[0].text.decode(
                "utf-8")
            variable_declarations[variable_name] = variable_type

        return variable_declarations
