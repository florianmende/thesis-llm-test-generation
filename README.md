# Implementation: Automated Unit Test Generation with Large Language Models

This repository was developed in the context of the bachelor thesis "Automated Unit Test Generation with Large Language Models" by Florian Mende.

For the code that was used for evaluation refer to the [evaluation repository](https://github.com/florianmende/thesis-evaluation).

## Setup

### Python requirements

To install the required python libraries, run the following command:

```bash
pip install -r requirements.txt
```

### Tree-sitter

The Java parser is based on the tree-sitter python library. To load the Java grammar, the tree-sitter-java repository has to be cloned.
It can be found here: `https://github.com/tree-sitter/tree-sitter-java`

Place the downloaded repository in the `vendor` folder (`vendor/tree-sitter-java`).

The Java grammar will be compiled during the first initialization of the Java parser and stored in the `build` folder.

### Java and Maven

In order to run the test generation algorithm, Java and Maven have to be installed on the system.

Maven will be used to compile the project and copy the required dependencies and save the corresponding classpath.

Java will be used to compile and execute the generated test cases.

### JUnit and Mockito JARs

In order to compile and run the generated test cases, the JUnit and Mockito JARs have to be downloaded and placed in the `dependencies` folder.

The project was tested using the following versions:
```
junit-platform-console-standalone-1.9.2.jar
mockito-core-5.5.0.jar
mockito-junit-jupiter-3.9.0.jar
byte-buddy-1.14.4.jar
byte-buddy-agent-1.14.4.jar:
```

Furthermore, after placing the JARs in the `dependencies` folder, the path to the JARs have to be added to the classpath for compiling and executing the test cases by adding the paths to the config.ini file.
Example:
```
[JARS]
JUNIT_JAR = ./dependencies/junit-platform-console-standalone-1.9.2.jar
MOCKITO_JAR = ./dependencies/mockito-core-5.5.0.jar:./dependencies/mockito-junit-jupiter-3.9.0.jar:./dependencies/byte-buddy-1.14.4.jar:./dependencies/byte-buddy-agent-1.14.4.jar:
```



## Configuration

### Tokenizer

When generating a prompt for the language model, different prompt sizes with increasing context (e.g. related classes) will be generated.
In order to determine, if the generated prompt still fits into the maximum token length of the language model, the prompt will be converted to tokens and checked against the configured maximum token length.

The tokenizer can be configured by changing the `config.ini` file.
This project supports two different tokenizers:
- Local tokenizer through the llama-cpp-python library
- tiktoken tokenizer

If you want to use the tokenizer for a specific model, you have to have llama-cpp installed and set `USE_MODEL` and `MODEL_PATH`in the `config.ini` file.
If you want to use the tiktoken tokenizer, simply set `USE_MODEL` to `false`.

Keep in mind, that this setting only affects the tokenizer used for the prompt generation. It is not the tokenizer used for the inference.

Furthermore, you also need to set the `MODEL_MAX_INPUT_TOKENS` in the `config.ini` file to the maximum number of tokens that should be used for the prompt.
The number of tokens should be based on the maximum number of tokens that the language model can handle and leave some space for the generated test case.
Example: If the model you are using supports a context length of 8192 tokens, a good value for `MODEL_MAX_INPUT_TOKENS` would be 6144, leaving 2048 tokens for the generated test case.

### Inference

This project supports two different methods to run inference on the language model:
- Huggingface inference
- Local inference through a llama-cpp-python powered webserver

To get started quickly, usage of the Huggingface inference is recommended. Simply set `USE_HUGGINGFACE` to `true` and `USE_LOCAL_WEB_SERVER` to `false` in the `config.ini` file. Add the URL of the Huggingface inference API to the `HUGGINGFACE_INFERENCE_URL` field.
Also add your Huggingface API key as a `HF_API_KEY` variable in a `.env` file in the root directory of the project.
Example:
```
HF_API_KEY=hf_abcdefghijk
```

If you want to use the local inference, you have to have llama-cpp-python installed and a webserver running. For further information, please refer to the [llama-cpp-python repository](https://github.com/abetlen/llama-cpp-python).
Set `USE_LOCAL_WEB_SERVER` to `true` and `LOCAL_WEB_SERVER_PORT` to the port of the webserver in the `config.ini` file (assumes the server is running at `localhost/{port}/v1`).
With llama-cpp-python installed, you can start a local web server by running the following command:
```bash
python -m llama_cpp.server --model [path_to_model]
```

Also set the maximum number of tokens that the language model can output in the `config.ini` file.

Example:
```
[INFERENCE]
MODEL_MAX_OUTPUT_TOKENS = 2048
USE_HUGGINGFACE = true
HUGGINGFACE_INFERENCE_URL = https://api-inference.huggingface.co/models/codellama/CodeLlama-34b-Instruct-hf
# if a local webserver should be used to run the inference (run through llama-cpp-python web server module)
USE_LOCAL_WEB_SERVER = false
LOCAL_WEB_SERVER_PORT = 8000
```


## Usage

To generate test cases for a specific project, place the Java Project in the `Java_Projects` folder.
**Important:** The project has to be a Maven project and has to contain a `pom.xml` file as Maven will be used to compile the project and copy the required dependencies.

After placing the project in the `Java_Projects` folder, run the following command:

```bash
python __main__.py
```

The program will parse the `Java_Projects` folder and ask you to select a project to generate test cases for.

There are several options that can be passed to the program:

```
usage: __main__.py [-h] [--only_parse ONLY_PARSE] [--only_generate_tests ONLY_GENERATE_TESTS] [--runs RUNS] [--method_range METHOD_RANGE] [--multiprocessing MULTIPROCESSING]
                   [--compilation_repair_rounds COMPILATION_REPAIR_ROUNDS] [--execution_repair_rounds EXECUTION_REPAIR_ROUNDS]

Automated Unit Test Generation for Java Projects using LLMs

optional arguments:
  -h, --help            show this help message and exit
  --only_parse ONLY_PARSE
                        If the projects should only be parsed to json files. (no database will be generated or tests generated)
  --only_generate_tests ONLY_GENERATE_TESTS
                        When database for projects was already created, test generation can be run in isolation (no parsing to json files or database generation)
  --runs RUNS           Amount of times the test generation should be run for each project
  --method_range METHOD_RANGE
                        Only run test generation for the methods in the range. Specify a range of integers in the format start:end
  --multiprocessing MULTIPROCESSING
                        Amount of processes to use for test generation. If 0, no multiprocessing will be used.
  --compilation_repair_rounds COMPILATION_REPAIR_ROUNDS
                        Amount of rounds to run the compilation repair for each method.
  --execution_repair_rounds EXECUTION_REPAIR_ROUNDS
                        Amount of rounds to run the execution repair for each method.
```

It is recommended to include at least 2 compilation repair rounds and 2 execution repair rounds to increase the chance of generating a test case that compiles and runs.

Example:
```bash
python __main__.py --compilation_repair_rounds 2 --execution_repair_rounds 2
```

All generated test classes that pass are placed in the `build/generated-tests/[project_name]/passed` folder. All generated test classes that fail are placed in the `build/generated-tests/[project_name]/compile_error` or `build/generated-tests/[project_name]/execution_error` folder depending on the error that occurred.
