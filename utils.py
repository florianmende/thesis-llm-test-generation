import sys
import time
import os
from contextlib import contextmanager
from io import StringIO
import re
import argparse


def extract_source_code(markdown_string):
    pattern = r'```java(.*?)```'
    source_code_sections = re.findall(pattern, markdown_string, re.DOTALL)
    return source_code_sections


@contextmanager
def mute_output():
    # Save the original sys.stdout
    original_stdout = sys.stdout

    # Redirect sys.stdout to a StringIO object to capture the output
    sys.stdout = StringIO()

    try:
        yield
    finally:
        # Restore the original sys.stdout
        sys.stdout = original_stdout


def print_progress_bar(iteration: int, total, prefix: str = '', length=50, fill='█', display_100_percent=False):
    """
    Call in a loop to create terminal progress bar
    :param iteration: current iteration
    :param total: total iterations
    :param prefix: String to print at the beginning of the bar
    :param length: character length of bar
    :param fill: bar fill character
    :param display_100_percent: whether to display to full bar after it reaches 100%
    :return:
    """
    percent = ("{:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)

    if iteration == total and display_100_percent:
        percent = "100.0"
        bar = fill * length

    sys.stdout.write('\r{} |{}| {}% Complete'.format(prefix, bar, percent))

    if iteration == total and display_100_percent:
        sys.stdout.write('\n')  # Move to the next line for 100% display

    sys.stdout.flush()


def get_user_choices(options, text):
    print(text)
    print("Select one or more options (comma-separated):")
    for i, option in enumerate(options, start=1):
        print(f"{i}. {option}")

    while True:
        try:
            choices = input("Enter numbers of your choices (comma-separated): ")
            choice_indices = [int(index.strip()) for index in choices.split(',') if index.strip()]
            if all(1 <= index <= len(options) for index in choice_indices):
                return [options[index - 1] for index in choice_indices]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter valid numbers separated by commas.")


def make_dir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def measure_execution_time(text):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            print(f"{text} took: {round(time.time() - start, 1)} seconds")
            return result
        return wrapper
    return decorator


def write_file(filepath, filename, suffix, content):
    with open(os.path.join(filepath, filename + suffix), "w") as file:
        file.write(content)


def change_class_name_in_java_file(filepath, old_class_name, new_class_name):
    with open(filepath, "r") as file:
        content = file.read()

    content = content.replace(old_class_name, new_class_name)

    with open(filepath, "w") as file:
        file.write(content)


def replace_str_in_file(filepath, old_str, new_str):
    with open(filepath, "r") as file:
        content = file.read()

    content = content.replace(old_str, new_str)

    with open(filepath, "w") as file:
        file.write(content)


def delete_lines_starting_with(text, start_string):
    lines = text.split('\n')  # Split the text into lines
    filtered_lines = [line for line in lines if not line.startswith(start_string)]  # Filter out lines starting with the specified string
    result_text = '\n'.join(filtered_lines)  # Join the remaining lines back into a string
    return result_text


class IntRangeAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # Split the values into start and end integers
        start, end = map(int, values.split(':'))
        setattr(namespace, self.dest, range(start, end + 1))
