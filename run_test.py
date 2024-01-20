import glob
import os
import subprocess
import configparser
import xml.etree.ElementTree as ET
import warnings


class TestExecuter:

    def __init__(self, project_name: str, dependencies_pre_built: bool = False):
        """
        Test executer class used to compile and run test cases.
        One instance of this class has to be created for each project.
        Calling this constructor will compile the project and create the classpath file for the project.
        :param project_name: Name of the project to run tests for. Used to create the classpath file for compilation and
        execution.
        :param dependencies_pre_built: If true, the dependencies will not be built and it is assumed that they are
        already built.
        """
        self.project_name = project_name
        self.dependencies = []

        self.current_abs_path = os.getcwd()

        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.MOCKITO_JAR = self.config.get('JARS', 'MOCKITO_JAR')
        self.JUNIT_JAR = self.config.get('JARS', 'JUNIT_JAR')

        if not dependencies_pre_built:

            self.make_dependencies()

    def get_dependencies_as_string(self):
        return ":".join(self.dependencies)

    def compile_test_case(self, classpath_file_name, test_file_path):
        """
        Compile a test case using javac
        :param classpath_file_name: Name for the classpath file
        :param test_file_path: Path to the test file to compile (relative to root of the project)
        :return: Tuple of return code and output of the javac command (0 if successful, 1 if not)
        """
        classpath_file_path = f"{self.current_abs_path}/build/artifacts/classpaths_tests_compilation/{self.project_name}"
        if not os.path.exists(classpath_file_path):
            os.makedirs(classpath_file_path)
        classpath = f"{self.get_dependencies_as_string()}:{self.MOCKITO_JAR}:{self.JUNIT_JAR}"
        classpath_file = os.path.join(classpath_file_path, classpath_file_name)
        self.export_classpath(classpath_file, classpath)

        # Compile the test case
        result = subprocess.run(
            f"javac -cp {self.current_abs_path}/build/compiled_projects/{self.project_name}/classes: \
            -d {self.current_abs_path}/build/compiled_tests/{self.project_name} \
            @{classpath_file} \
            {self.current_abs_path}/{test_file_path}",
            shell=True, capture_output=True, text=True)
        output = result.stdout if result.returncode == 0 else result.stderr
        return result.returncode, output

    @staticmethod
    def export_classpath(classpath_file: str, classpath: str):
        """
        Write a list of dependencies seperated by : (classpath) to a file for later use
        :param classpath_file: filepath to write the classpath to
        :param classpath: classpath to write to the file (list of dependencies seperated by :)
        :return:
        """
        with open(classpath_file, 'w') as f:
            classpath = "-cp " + classpath
            f.write(classpath)
        return

    def get_standard_compile_path(self):
        pom_file = f"{self.current_abs_path}/Java_Projects/{self.project_name}/pom.xml"

        # read pom.xml and check if there is a OutputDirectory tag
        # if there is, use that as the standard compile path
        # if there is not, use the default path
        # Parse the XML file
        tree = ET.parse(pom_file)
        root = tree.getroot()

        # Namespace for Maven POM
        ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}

        # Extract the outputDirectory
        output_directory_element = root.find('./maven:build/maven:outputDirectory', ns)
        if output_directory_element is not None:
            return output_directory_element.text
        else:
            return None

    def make_dependencies(self):
        """
        Generate dependencies for a java project using maven and save them in the dependencies list
        """
        mvn_target_dir = f'{self.current_abs_path}/build/compiled_projects/{self.project_name}'
        # Check if dependencies are already generated for the specific project
        if not self.dependencies:
            print("Making dependencies for project:", self.project_name)
            # Run mvn command to generate dependencies
            # Project needs to be a maven project and have a pom.xml file
            subprocess.run(
                f"mvn dependency:copy-dependencies -DoutputDirectory={mvn_target_dir}/dependencies \
                -f {self.current_abs_path}/Java_Projects/{self.project_name}/pom.xml",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Install the project using maven (also compiles the project)
            # Tests are skipped to avoid running old tests from the project
            subprocess.run(f"mvn install -DskipTests -f {self.current_abs_path}/Java_Projects/{self.project_name}/pom.xml",
                           shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # copy compiled files to compiled_projects folder
            # if no outputDirectory is specified in the pom.xml, the standard directory will be used
            compile_path = self.get_standard_compile_path() if self.get_standard_compile_path() else "target"
            target_folder = f"{self.current_abs_path}/build/compiled_projects/{self.project_name}"
            subprocess.run(f"mkdir -p {target_folder}", shell=True)
            subprocess.run(f"cp -r {self.current_abs_path}/Java_Projects/{self.project_name}/{compile_path}/* \
                            {target_folder}", shell=True)
            # remove files
            subprocess.run(f"rm -r {self.current_abs_path}/Java_Projects/{self.project_name}/{compile_path}", shell=True)

            # Get paths of all dependencies (jars) and add them to the dependencies list
            dep_jars = glob.glob(f"{mvn_target_dir}" + "/**/*.jar", recursive=True)
            self.dependencies.extend(list(set(dep_jars)))
            print("Dependencies generated for project:", self.project_name)
        else:
            print("Dependencies already generated for project:", self.project_name)

    def run_test(self, classpath_file_name, class_to_test, timeout: int = 20):
        """
        Run a test using java and junit
        :param classpath_file_name: File name where the classpath should be saved (has to be a txt)
        :param class_to_test: Class which should be run as a test (e.g. org.jfree.tests.junit.chart.JFreeChartTests)
        :param timeout: Timeout for the test execution in seconds
        :return:
        """

        classpath = f"{self.JUNIT_JAR}:{self.MOCKITO_JAR}:{self.get_dependencies_as_string()}:" \
                    f"{self.current_abs_path}/build/compiled_projects/{self.project_name}/classes:" \
                    f"{self.current_abs_path}/build/compiled_tests/{self.project_name}"
        classpath_file_path = f"{self.current_abs_path}/build/artifacts/classpaths_tests_execution/{self.project_name}"

        if not os.path.exists(classpath_file_path):
            os.makedirs(classpath_file_path)

        classpath_file = os.path.join(classpath_file_path, classpath_file_name)
        self.export_classpath(classpath_file, classpath)

        cmd = [
            "java",
            "--add-opens java.base/java.lang=ALL-UNNAMED",
            f"@{classpath_file}",
            "org.junit.platform.console.ConsoleLauncher",
            "--disable-banner",
            "--disable-ansi-colors",
            "--fail-if-no-tests",
            "--details=none",
            "--select-class",
            f"{class_to_test}"
        ]
        try:
            result = subprocess.run(" ".join(cmd), shell=True, timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout if result.stdout else result.stderr
            return result.returncode, output
        except subprocess.TimeoutExpired:
            return 1, "Timeout"