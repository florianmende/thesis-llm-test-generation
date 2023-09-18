from db import DataBase
import os
import json

db = DataBase()

db.reset()

db.create_tables()

# loop over all projects
for project_name in os.listdir("./build/class_parser"):
    # insert project
    db.insert_project(str(project_name))

    # loop over all classes
    for class_name in os.listdir("./build/class_parser/" + project_name):
        # read in class.json file and convert it to a dictionary
        # check if class file exists
        if os.path.exists("./build/class_parser/" + project_name + "/" + class_name + "/class.json") \
                and os.path.exists("./build/class_parser/" + project_name + "/" + class_name + "/methods.json"):
            class_file = open("./build/class_parser/" + project_name + "/" + class_name + "/class.json", "r")
            method_file = open("./build/class_parser/" + project_name + "/" + class_name + "/methods.json", "r")
            with class_file:
                class_list = json.load(class_file)

            with method_file:
                method_list = json.load(method_file)

            for class_dict in class_list:
                # write to database
                db.insert_class(class_dict["class_identifier"],
                                project_name,
                                class_dict["class_modifier"],
                                class_dict["class_super_interfaces"],
                                class_dict["class_full_text"])

                for var in class_dict["class_variable_declarations"]:
                    db.insert_class_variable(class_dict["class_identifier"],
                                             var["variable_identifier"],
                                             var["variable_type"])

                for method_dict in method_list:
                    # write methods of class to database
                    db.insert_method(method_dict["method_identifier"],
                                     class_dict["class_identifier"],
                                     method_dict["method_full_text"])

                    methodId = db.get_method_id(method_dict["method_identifier"], class_dict["class_identifier"])

                    # write parameters of method to database
                    for key in method_dict["method_parameter_types"]:
                        db.insert_method_parameter(methodId,
                                                   method_dict["method_parameter_types"][key],
                                                   key)

    # create intra-project relations
    for class_name in os.listdir("./build/class_parser/" + project_name):
        if os.path.exists("./build/class_parser/" + project_name + "/" + class_name + "/class.json") \
                and os.path.exists("./build/class_parser/" + project_name + "/" + class_name + "/methods.json"):
            class_file = open("./build/class_parser/" + project_name + "/" + class_name + "/class.json", "r")
            method_file = open("./build/class_parser/" + project_name + "/" + class_name + "/methods.json", "r")
            with class_file:
                class_list = json.load(class_file)

            with method_file:
                method_list = json.load(method_file)

            for class_dict in class_list:
                for method_dict in method_list:
                    source_method_id = db.get_method_id(method_dict["method_identifier"],
                                                        class_dict["class_identifier"])
                    # write intra-project relations to database
                    for related_method in method_dict["related_methods"]:
                        target_method_id = db.get_method_id(related_method["method_name"],
                                                            related_method["method_class"])
                        if target_method_id is not None:
                            # relation between methods
                            db.insert_related_method_of_method(source_method_id, target_method_id)

                        # relation between methods and classes
                    for key in method_dict["method_parameter_types"]:
                        # check if class exists in database
                        class_id = db.get_class_id(method_dict["method_parameter_types"][key])
                        if class_id is not None:
                            db.insert_related_class_of_method(source_method_id, class_id)