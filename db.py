import sqlite3


class DataBase:

    def __init__(self, db_path: str = './build/db/projects.db'):
        self.conn = sqlite3.connect('./build/db/projects.db')
        self.cursor = self.conn.cursor()

    def reset(self):
        self.cursor.execute("DROP TABLE IF EXISTS projects")
        self.cursor.execute("DROP TABLE IF EXISTS classes")
        self.cursor.execute("DROP TABLE IF EXISTS methods")
        self.cursor.execute("DROP TABLE IF EXISTS relatedClassesOfMethod")
        self.cursor.execute("DROP TABLE IF EXISTS relatedMethodsOfClass")
        self.cursor.execute("DROP TABLE IF EXISTS relatedMethodsOfMethod")
        self.cursor.execute("DROP TABLE IF EXISTS classVariables")
        self.cursor.execute("DROP TABLE IF EXISTS methodParameters")
        self.conn.commit()

    def create_tables(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS projects (
                    projectName TEXT PRIMARY KEY NOT NULL
                )""")

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS classes (
                    classIdentifier TEXT PRIMARY KEY NOT NULL,
                    projectName TEXT NOT NULL,
                    classModifier TEXT,
                    classSuperInterface TEXT,
                    fullText TEXT NOT NULL,
                    classHeader TEXT,
                    FOREIGN KEY (projectName) REFERENCES projects(projectName)
                )""")

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS methods (
            methodId INTEGER PRIMARY KEY AUTOINCREMENT,
            methodIdentifier TEXT NOT NULL,
            classIdentifier TEXT NOT NULL,
            fullText TEXT,
            FOREIGN KEY (classIdentifier) REFERENCES classes(classIdentifier)
        )""")

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS relatedClassesOfMethod (
            methodId INTEGER NULL,
            classIdentifier TEXT NOT NULL,
            FOREIGN KEY (methodId) REFERENCES methods(methodId),
            FOREIGN KEY (classIdentifier) REFERENCES classes(classIdentifier)
        )""")

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS relatedMethodsOfMethod (
            methodIdSource TEXT NOT NULL,
            methodIdTarget TEXT NOT NULL,
            FOREIGN KEY (methodIdSource) REFERENCES methods(methodId),
            FOREIGN KEY (methodIdTarget) REFERENCES methods(methodId)
        )""")

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS classVariables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            classIdentifier TEXT NOT NULL,
            variableIdentifier TEXT NOT NULL,
            variableType TEXT NOT NULL,
            FOREIGN KEY (classIdentifier) REFERENCES classes(classIdentifier)
        )""")

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS methodParameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            methodId INTEGER NOT NULL,
            parameterType TEXT NOT NULL,
            parameterName TEXT NOT NULL,
            FOREIGN KEY (methodId) REFERENCES methods(methodId)
        )""")

        self.conn.commit()

    def insert_project(self, project_name):
        self.cursor.execute("INSERT INTO projects VALUES (?)", (project_name,))
        self.conn.commit()

    def insert_class(self, class_identifier, project_name, class_modifier, class_super_interface, full_text,
                     class_header):
        self.cursor.execute("INSERT INTO classes VALUES (?, ?, ?, ?, ?, ?)",
                            (class_identifier, project_name, class_modifier, class_super_interface, full_text,
                             class_header))
        self.conn.commit()

    def insert_class_variable(self, class_identifier, variable_identifier, variable_type):
        self.cursor.execute("INSERT INTO classVariables VALUES (NULL, ?, ?, ?)",
                            (class_identifier, variable_identifier, variable_type))
        self.conn.commit()

    def insert_method(self, method_identifier, class_identifier, full_text):
        self.cursor.execute("INSERT INTO methods VALUES (NULL, ?, ?, ?)",
                            (method_identifier, class_identifier, full_text))
        self.conn.commit()

    def insert_method_parameter(self, method_identifier, parameter_type, parameter_name):
        self.cursor.execute("INSERT INTO methodParameters VALUES (NULL, ?, ?, ?)",
                            (method_identifier, parameter_type, parameter_name))
        self.conn.commit()

    def insert_related_method_of_method(self, method_id_source: int, method_id_target: int):
        # source method calls target method
        self.cursor.execute("INSERT INTO relatedMethodsOfMethod VALUES (?, ?)",
                            (method_id_source, method_id_target))
        self.conn.commit()

    def insert_related_class_of_method(self, method_id: int, class_identifier: str):
        self.cursor.execute("INSERT INTO relatedClassesOfMethod VALUES (?, ?)",
                            (method_id, class_identifier))
        self.conn.commit()

    def get_method_id(self, method_identifier, class_identifier):
        self.cursor.execute("SELECT methodId FROM methods WHERE methodIdentifier=? AND classIdentifier =?",
                            (method_identifier, class_identifier))
        result = self.cursor.fetchone()
        if result is None:
            return None
        return result[0]

    def get_class_id(self, class_identifier):
        # return class id or None if class does not exist
        self.cursor.execute("SELECT classIdentifier FROM classes WHERE classIdentifier=?", (class_identifier,))
        result = self.cursor.fetchone()
        if result is None:
            return None
        return result[0]

    def get_method_by_id(self, method_id):
        self.cursor.execute("SELECT * FROM methods WHERE methodId=?", (method_id,))
        result = self.cursor.fetchone()
        if result:
            column_names = [description[0] for description in self.cursor.description]
            result_dict = dict(zip(column_names, result))
            return result_dict
        return None

    def get_related_methods_of_method(self, method_id):
        self.cursor.execute(""" SELECT *
                                FROM methods
                                JOIN relatedMethodsOfMethod ON methods.methodId = relatedMethodsOfMethod.methodIdSource
                                WHERE relatedMethodsOfMethod.methodIdSource = ?""", (method_id,))
        result = self.cursor.fetchall()
        result_list = []
        for row in result:
            column_names = [description[0] for description in self.cursor.description]
            result_dict = dict(zip(column_names, row))
            result_list.append(result_dict)
        return result_list

    def get_related_classes_of_method(self, method_id):
        self.cursor.execute("""SELECT * 
                             FROM classes 
                             INNER JOIN relatedClassesOfMethod 
                             ON classes.classIdentifier = relatedClassesOfMethod.classIdentifier 
                             WHERE relatedClassesOfMethod.methodId = ?"""
                            , (method_id,))
        result = self.cursor.fetchall()
        result_list = []
        for row in result:
            column_names = [description[0] for description in self.cursor.description]
            result_dict = dict(zip(column_names, row))
            result_list.append(result_dict)
        return result_list
