import subprocess
import re


def list_jupyter_instances(base_path=None):
    result = subprocess.run(['jupyter', 'notebook', 'list'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    servers = []
    for line in lines:
        if " :: " not in line:
            continue
        endpoint, instance_base_path = line.split(" :: ")
        match = re.search(r'(http://.*:\d+)/\?token=(\w+)', line)
        if match:
            base_url = match.group(1)
            token = match.group(2)
            if base_path is not None and instance_base_path.strip() != base_path:
                continue

            servers.append((base_url, token, instance_base_path))
    return servers


if __name__ == '__main__':
    print(list_jupyter_instances('/'))
    print(list_jupyter_instances('/Users/ralphus/Development/taskmates-project/taskmates-extras'))
