import glob
import os
import subprocess
import configparser


class TestExecuter:

    def __init__(self):
        self.dependencies = []

    def compile_java_project(self, project_path, output_path):
        """
        Compile a java project using maven
        :param project_name:
        :return:
        """

    def complile_test_case(self, dependencies, compiled_test_dir):
        current_dir = os.getcwd()
        config = configparser.ConfigParser()
        config.read('config.ini')
        mockito_jar = config.get('JARS', 'MOCKITO_JAR')
        junit_jar = config.get('JARS', 'JUNIT_JAR')
        classpath = f"{dependencies}:{mockito_jar}:{junit_jar}"
        classpath_file = os.path.join(compiled_test_dir, 'classpath.txt')
        self.export_classpath(classpath_file, classpath)
        result = subprocess.run(
            f"javac -cp {current_dir}/Java_Projects/jfreechart/target -d {current_dir}/build/compiled_tests @{classpath_file} {current_dir}/Java_Projects/jfreechart/src/generated_tests/java/org/jfree/tests/10_test.java",
            shell=True, capture_output=True, text=True)
        output = result.stdout if result.returncode == 0 else result.stderr
        print(output)
        return result.returncode, output

    @staticmethod
    def export_classpath(classpath_file, classpath):
        with open(classpath_file, 'w') as f:
            classpath = "-cp " + classpath
            f.write(classpath)
        return

    def get_dependencies(self, project_name):
        """
        Get runtime dependencies of a test using maven
        :return:
        """
        mvn_dependency_dir = 'target/dependency'
        deps = []
        # Run mvn command to generate dependencies
        # print("Making dependency for project", self.target_path)
        current_dir = os.getcwd()
        subprocess.run(
            f"mvn dependency:copy-dependencies -DoutputDirectory={mvn_dependency_dir} -f {current_dir}/Java_Projects/{project_name}/pom.xml",
            shell=True)
        subprocess.run(f"mvn install -DskipTests -f {current_dir}/Java_Projects/{project_name}/pom.xml", shell=True)

        dep_jars = glob.glob(f"{current_dir}/Java_Projects/{project_name}" + "/**/*.jar", recursive=True)
        deps.extend(dep_jars)
        deps = list(set(deps))
        return ':'.join(deps)

    def run_test(self, test_case, dependencies, compiled_test_dir, build_dir):
        """
        Run a test using java
        :param test_case:
        :param dependencies:
        :return:
        """
        current_dir = os.getcwd()
        config = configparser.ConfigParser()
        config.read('config.ini')
        mockito_jar = config.get('JARS', 'MOCKITO_JAR')
        junit_jar = config.get('JARS', 'JUNIT_JAR')
        classpath = f"{junit_jar}:{mockito_jar}:{dependencies}:{current_dir}/{build_dir}"
        classpath_file = os.path.join(compiled_test_dir, 'classpath.txt')
        self.export_classpath(classpath_file, classpath)

        cmd = ["java",
                f"@{classpath_file}",
                "org.junit.platform.console.ConsoleLauncher", "--disable-banner", "--disable-ansi-colors",
                "--fail-if-no-tests", "--details=none", "--select-class",
                f"org.jfree.tests.MinuteTest"]

        result = subprocess.run(" ".join(cmd), shell=True)
        print(result)
        output = result.stdout if result.returncode == 0 else result.stderr
        print(output)
        return result.returncode, output


test_executer = TestExecuter()
deps = test_executer.get_dependencies("jfreechart")
# print(deps)
print("Compilation step:")
print(test_executer.complile_test_case(deps, "./build/compiled_tests"))

javac = test_executer.run_test("10_test.java", deps, "build/compiled_tests/org/jfree/tests/", "build/compiled_tests")
print("Execution step:")
print(javac)
