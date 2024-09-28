import argparse
import subprocess
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

def run_ffuf(url, wordlist, output_dir, index, total):
    domain = url.split('/')[2].replace('.', '_')
    output_file = os.path.join(output_dir, f"{domain}.json")  # Changed to JSON format
    formatted_output_file = os.path.join(output_dir, f"{domain}_formatted.txt")

    # Print URL with progress in blue and bold
    print(f"\033[34;1mRunning ffuf for: {url} ({index}/{total})\033[0m")

    command = [
        'ffuf',
        '-w', wordlist,
        '-u', f"{url}/FUZZ",
        '-o', output_file,
        '-of', 'json',  # Output format changed to JSON
        '-c',          # Colorize output
        '-v'           # Verbose output
    ]

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if stderr:
            print(stderr.decode(), file=sys.stderr)

        # Process the output with jq to format it
        jq_command = [
            'jq',
            '-r',
            'try .results[] | "\(.status) \(.length) \(.url)"',
            output_file
        ]
        with open(formatted_output_file, 'w') as f:
            subprocess.run(jq_command, stdout=f)

        print(f"\033[32;1mFinished processing {url}, results saved to {formatted_output_file}\033[0m")

    except Exception as e:
        print(f"Error running ffuf: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Run ffuf with a specified wordlist.')
    parser.add_argument('-w', '--wordlist', required=True, help='Path to the wordlist file')
    parser.add_argument('-u', '--urls', required=True, help='Path to the file containing URLs')
    parser.add_argument('-o', '--output', required=True, help='Output directory for results')
    args = parser.parse_args()

    wordlist = args.wordlist
    urls_file = args.urls
    output_dir = args.output

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Read the URLs from the file
    try:
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f]
    except Exception as e:
        print(f"Error reading URLs file: {e}", file=sys.stderr)
        sys.exit(1)

    # Create a queue and populate it with URLs
    url_queue = Queue()
    for url in urls:
        url_queue.put(url)

    # Function to process a URL from the queue
    def worker():
        while not url_queue.empty():
            url = url_queue.get()
            index = urls.index(url) + 1
            total = len(urls)
            run_ffuf(url, wordlist, output_dir, index, total)
            url_queue.task_done()

    # Run up to 10 threads concurrently
    num_threads = 10
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker) for _ in range(num_threads)]
        # Wait for all threads to complete
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()
