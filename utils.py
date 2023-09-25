import sys
import time


def print_progress_bar(iteration, total, prefix='', length=50, fill='█', display_100_percent=False):
    percent = ("{:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)

    if iteration == total and display_100_percent:
        percent = "100.0"
        bar = fill * length

    sys.stdout.write('\r{} |{}| {}% Complete'.format(prefix, bar, percent))

    if iteration == total and display_100_percent:
        sys.stdout.write('\n')  # Move to the next line for 100% display
    elif iteration != total:
        sys.stdout.write('\r')  # Move back to the beginning of the line

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