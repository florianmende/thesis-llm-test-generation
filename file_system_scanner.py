import os


class FileSystemScanner:
    """
    This class is used to parse the folder with Java projects and extract all paths to Java files.

    :param folder_path: The path to a folder containing Java projects.
    Each project should be in a separate sub-folder.
    The default value is "./Java_Projects".
    """

    folder_path = None

    def __init__(self, folder_path="./Java_Projects"):
        """
        Initialize the parser.

        :param folder_path: The path to a folder containing Java projects.
        Each project should be in a separate sub-folder.
        The default value is "./Java_Projects".

        """
        self.folder_path = folder_path

    def parse(self):
        """
        Parse the folder with Java projects and extract all paths to Java files excluding test files.
        :return: List of paths to Java files.
        :raises Exception: If the folder does not exist or no Java files are found.
        """

        # handle the case when the folder does not exist
        if not os.path.exists(self.folder_path):
            exception_message = "The folder " + self.folder_path + " does not exist."
            raise Exception(exception_message)

        projects = self._parse_folder()

        for project_name in projects:
            project = projects[project_name]

            java_files = []

            for root, dirs, files in os.walk(project["path"]):
                for file in files:
                    # filter out non-java files as well as files containing "Test" in their name to avoid test files
                    # filter out all files located in a "test" folder to avoid test files
                    if file.endswith(".java") and "Test" not in file and not "test" in root.split(os.sep):
                        java_files.append(os.path.join(root, file))

            if len(java_files) == 0:
                exception_message = "No Java files found in the folder " + self.folder_path + "."
                raise Exception(exception_message)

            print("Found " + str(len(java_files)) + " Java file(s) in the project " + project_name +
                  " (excluding test files).")

            projects[project_name]["files"] = java_files

        return projects

    def _parse_folder(self):
        """
        Parse a folder with Java projects and extracts all project names.
        :return: A dictionary with project names as keys and a dictionary as values:

        - "path" - the path to the project folder
        - "files" - a list of paths to Java files in the project
        """

        folder_path = self.folder_path

        # handle the case when the folder does not exist
        if not os.path.exists(folder_path):
            exception_message = "The folder " + folder_path + " does not exist."
            raise Exception(exception_message)

        items_in_dir = os.listdir(folder_path)
        # filter out non-folders
        project_names = [item for item in items_in_dir if os.path.isdir(os.path.join(folder_path, item))]

        if len(project_names) == 0:
            exception_message = "No Java projects found in the folder " + folder_path + "."
            raise Exception(exception_message)

        print("Found " + str(len(project_names)) + " Java project(s):")
        print("\n".join(project_names))
        print("\n")

        projects = {}
        for project_name in project_names:
            project_path = os.path.join(folder_path, project_name)
            projects[project_name] = {"path": project_path, "files": []}

        return projects
