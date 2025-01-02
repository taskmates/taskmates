import subprocess


def kill_jupyter_instances():
    try:
        subprocess.run("kill $(ps aux | grep jupyterlab | grep -v grep | awk '{print $2}')", shell=True,
                       check=True)
        print("Jupyter instance stopped successfully.")
    except subprocess.CalledProcessError as e:
        print("Error stopping Jupyter instance:", e)


if __name__ == '__main__':
    kill_jupyter_instances()
