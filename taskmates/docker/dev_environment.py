import socket
import time
from pathlib import Path
from typing import Optional, List, Union, Dict

from python_on_whales import DockerClient


class DevEnvironment:
    def __init__(
            self,
            compose_files: Union[str, Path, List[Union[str, Path]]],
            project_name: str,
            project_directory: Optional[Union[str, Path]] = None,
            environment: Optional[Dict[str, str]] = None,
            service: Optional[str] = "devcontainer"
    ):
        self.compose_files = [Path(f) for f in
                              ([compose_files] if isinstance(compose_files, (str, Path)) else compose_files)]
        self.project_name = project_name
        self.project_directory = Path(project_directory) if project_directory else self.compose_files[0].parent
        self.environment = environment or {}
        self.service = service
        self._docker_client: Optional[DockerClient] = None
        self._is_running = False

    @property
    def client(self) -> DockerClient:
        if not self._docker_client:
            self._docker_client = DockerClient(
                compose_files=self.compose_files,
                compose_project_name=self.project_name,
                compose_project_directory=self.project_directory
            )
        return self._docker_client

    def up(self) -> None:
        try:
            # Start the environment
            self.client.compose.up(
                wait=True,
                detach=True,
                build=True,  # Always build to ensure latest changes are applied
            )
            self._is_running = True
        except Exception as e:
            raise RuntimeError(f"Failed to start development environment: {str(e)}") from e

    def stop(self) -> None:
        if not self._is_running:
            return

        try:
            self.client.compose.stop()
            self._is_running = False
        except Exception as e:
            raise RuntimeError(f"Failed to stop development environment: {str(e)}") from e

    def destroy(self) -> None:
        try:
            self.client.compose.down(volumes=True, remove_orphans=True)
            self._is_running = False

            # Clean up environment file
            env_file = self.project_directory / ".env"
            if env_file.exists():
                env_file.unlink()
        except Exception as e:
            raise RuntimeError(f"Failed to destroy development environment: {str(e)}") from e

    def get_service_port(self, service_name: Optional[str] = None, container_port: int = 0) -> int:
        service_name = service_name or self.service
        if not service_name:
            raise ValueError("No service name provided and no default service set")

        if not self._is_running:
            raise RuntimeError(f"Service {service_name} is not running")

        try:
            container = self.client.compose.ps(services=[service_name])[0]
            ports = container.network_settings.ports
            port_key = f"{container_port}/tcp"

            if port_key in ports and ports[port_key]:
                return int(ports[port_key][0]["HostPort"])

            raise RuntimeError(f"No mapping found for container port {container_port}")
        except Exception as e:
            raise RuntimeError(f"Failed to get port for service {service_name}: {str(e)}") from e

    def wait_for_port(self, host: str, port: int, timeout: int = 30) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection((host, port), timeout=1):
                    return True
            except (socket.timeout, ConnectionRefusedError):
                time.sleep(1)
        return False

    def get_logs(self, service_name: Optional[str] = None,
                 since: Optional[str] = None,
                 until: Optional[str] = None,
                 tail: Optional[int] = None) -> str:
        service_name = service_name or self.service
        if not service_name:
            raise ValueError("No service name provided and no default service set")

        if not self._is_running:
            raise RuntimeError(f"Service {service_name} is not running")

        try:
            return self.client.compose.logs(
                services=[service_name],
                since=since,
                until=until,
                tail=tail
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get logs for service {service_name}: {str(e)}") from e

    @property
    def is_running(self) -> bool:
        return self._is_running

    def execute(self, command: List[str],
                service: Optional[str] = None,
                workdir: Optional[str] = None,
                envs: Optional[Dict[str, str]] = None,
                tty: bool = False) -> str:
        service = service or self.service
        return self.client.compose.execute(
            service=service,
            command=command,
            workdir=workdir,
            envs=envs or {},
            tty=tty
        )


def test_dev_environment_logs(tmp_path: Path):
    compose_content = """
services:
  log_test:
    image: alpine:latest
    command: sh -c 'echo "log line 1" && echo "log line 2" && echo "log line 3" && sleep infinity'
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    env = DevEnvironment(
        compose_files=compose_file,
        project_name="test_logs",
        project_directory=tmp_path,
        service="log_test"
    )

    try:
        env.up()
        logs = env.get_logs("log_test")
        assert logs == 'log_test-1  | log line 1\nlog_test-1  | log line 2\nlog_test-1  | log line 3\n'

        tail_logs = env.get_logs("log_test", tail=2)
        assert tail_logs == 'log_test-1  | log line 2\nlog_test-1  | log line 3\n'
    finally:
        env.destroy()


def test_execute(tmp_path: Path):
    compose_content = """
services:
  execute_test:
    image: alpine:latest
    command: sleep infinity
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    env = DevEnvironment(
        compose_files=compose_file,
        project_name="test_execute",
        project_directory=tmp_path,
        service="execute_test"
    )

    try:
        env.up()
        result = env.execute(["echo", "Hello, World!"])
        assert result == "Hello, World!"
    finally:
        env.destroy()


def test_execute_with_envs(tmp_path: Path):
    compose_content = """
services:
  env_test:
    image: alpine:latest
    command: sleep infinity
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    env = DevEnvironment(
        compose_files=compose_file,
        project_name="test_execute_envs",
        project_directory=tmp_path,
        service="env_test"
    )

    try:
        env.up()
        result = env.execute(
            ["sh", "-c", "echo $TEST_VAR"],
            envs={"TEST_VAR": "Hello from environment"}
        )
        assert result.strip() == "Hello from environment"
    finally:
        env.destroy()


def test_get_service_port(tmp_path: Path):
    compose_content = """
services:
  port_test:
    image: alpine:latest
    command: sh -c 'nc -l -p 8080 -k'  # -k keeps listening after client disconnects
    ports:
      - "8080"  # Only specify container port to let Docker assign a random host port
"""
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text(compose_content)

    env = DevEnvironment(
        compose_files=compose_file,
        project_name="test_port",
        project_directory=tmp_path,
        service="port_test"
    )

    try:
        env.up()
        # Get the dynamically assigned port
        port = env.get_service_port(container_port=8080)

        # Verify we can actually connect to the port
        assert env.wait_for_port("localhost", port, timeout=10), f"Could not connect to port {port}"

        # Try to establish a real connection and send/receive data
        with socket.create_connection(("localhost", port), timeout=5) as sock:
            sock.send(b"test\n")
            assert sock.getpeername()[1] == port  # Verify we're connected to the right port

    finally:
        env.destroy()
