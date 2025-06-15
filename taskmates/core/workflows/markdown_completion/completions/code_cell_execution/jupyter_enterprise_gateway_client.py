#!/usr/bin/env python3

import argparse
import asyncio
import json
import os

import requests
from jupyter_server.gateway.gateway_client import GatewayClient
from jupyter_server.gateway.managers import GatewayKernelManager

# Constants
DEFAULT_GATEWAY_URL = os.getenv("ENTERPRISE_GATEWAY_ENDPOINT", "http://localhost:10100")


# Functions to interact with Jupyter Enterprise Gateway
def list_sessions(gateway_url):
    response = requests.get(f"{gateway_url}/api/sessions")
    response.raise_for_status()
    return response.json()


def create_session(gateway_url, payload):
    response = requests.post(f"{gateway_url}/api/sessions", json=payload)
    response.raise_for_status()
    return response.json()


def delete_session(gateway_url, session_id):
    response = requests.delete(f"{gateway_url}/api/sessions/{session_id}")
    response.raise_for_status()
    return response.status_code == 204


def delete_all_sessions(gateway_url):
    sessions = list_sessions(gateway_url)
    for session in sessions:
        delete_session(gateway_url, session['id'])


def get_kernel(gateway_url, kernel_id):
    response = requests.get(f"{gateway_url}/api/kernels/{kernel_id}")
    response.raise_for_status()
    return response.json()


def get_session(gateway_url, session_id):
    response = requests.get(f"{gateway_url}/api/sessions/{session_id}")
    response.raise_for_status()
    return response.json()


def list_kernels(gateway_url):
    response = requests.get(f"{gateway_url}/api/kernels")
    response.raise_for_status()
    return response.json()


def create_kernel(gateway_url, payload):
    response = requests.post(f"{gateway_url}/api/kernels", json=payload)
    response.raise_for_status()
    return response.json()


def delete_kernel(gateway_url, kernel_id):
    response = requests.delete(f"{gateway_url}/api/kernels/{kernel_id}")
    response.raise_for_status()
    return response.status_code == 204


def delete_all_kernels(gateway_url):
    kernels = list_kernels(gateway_url)
    for kernel in kernels:
        delete_kernel(gateway_url, kernel['id'])


def find_or_create_session(path, gateway_url=DEFAULT_GATEWAY_URL):
    sessions = list_sessions(gateway_url)
    for session in sessions:
        if session.get('notebook', {}).get('path') == path:
            return session
    # If not found, create a new session
    payload = {"path": path, "type": "python3", "kernel": {"name": "python3"}}
    return create_session(gateway_url, payload)


async def get_kernel_manager(gateway_url, path=None, kernel_id=None):
    # Set any other gateway-specific parameters on the GatewayClient (singleton) instance
    gw_client = GatewayClient.instance()
    gw_client.url = gateway_url

    if path:
        # Find an existing session with the specified path or create a new one
        session_path = str(path)
        session = find_or_create_session(session_path, gw_client.url)
        kernel_id = session['kernel']['id']
        # kernel_id = '3a9e82bd-a8f0-46c1-8fd7-3618f0bba40c'

    kernel_model = get_kernel(gw_client.url, kernel_id)
    # Connect to the existing kernel using the kernel ID
    km = GatewayKernelManager()
    km.kernel_id = kernel_id
    km.model = kernel_model
    km.kernel_url = DEFAULT_GATEWAY_URL + "/api/kernels/" + kernel_id
    await km.refresh_model(kernel_model)
    # has_kernel = km.has_kernel
    # is_alive = await km.is_alive()
    # print(f"has_kernel {has_kernel}")
    # print(f"is_alive {is_alive}")
    return km


async def interrupt_kernel(gateway_url, path=None, kernel_id=None):
    km = await get_kernel_manager(gateway_url, path, kernel_id)
    await km.interrupt_kernel()
    print("Kernel interrupted successfully")


# CLI Argument Parser
parser = argparse.ArgumentParser(description="CLI tool to interact with Jupyter Enterprise Gateway")
parser.add_argument("cmd", help="Command to execute", choices=[
    "list-sessions", "create-session", "delete-session", "delete-all-sessions",
    "list-kernels", "create-kernel", "delete-kernel", "delete-all-kernels",
    "find-or-create-session", "get-kernel", "get-session", "interrupt"
])
parser.add_argument("--payload", help="JSON payload for creating sessions or kernels")
parser.add_argument("--id", help="ID of the session or kernel to delete")
parser.add_argument("--path", help="Path to find or create a session")
parser.add_argument("--url", help="URL of the Jupyter Enterprise Gateway", default=DEFAULT_GATEWAY_URL)


def main():
    # Parse arguments
    args = parser.parse_args()
    # Execute the command
    if args.cmd == "list-sessions":
        print(json.dumps(list_sessions(args.url), ensure_ascii=False))

    elif args.cmd == "create-session":
        if not args.payload:
            raise ValueError("Payload is required for creating a session")
        payload = json.loads(args.payload)
        print(json.dumps(create_session(args.url, payload), ensure_ascii=False))

    elif args.cmd == "delete-session":
        if not args.id:
            raise ValueError("Session ID is required for deleting a session")
        delete_session(args.url, args.id)
        print(f"Session {args.id} deleted successfully")

    elif args.cmd == "delete-all-sessions":
        delete_all_sessions(args.url)
        print("All sessions deleted successfully")

    elif args.cmd == "list-kernels":
        print(json.dumps(list_kernels(args.url), ensure_ascii=False))

    elif args.cmd == "create-kernel":
        if not args.payload:
            raise ValueError("Payload is required for creating a kernel")
        payload = json.loads(args.payload)
        print(json.dumps(create_kernel(args.url, payload), ensure_ascii=False))

    elif args.cmd == "delete-kernel":
        if not args.id:
            raise ValueError("Kernel ID is required for deleting a kernel")
        delete_kernel(args.url, args.id)
        print(f"Kernel {args.id} deleted successfully")

    elif args.cmd == "delete-all-kernels":
        delete_all_kernels(args.url)
        print("All kernels deleted successfully")

    elif args.cmd == "find-or-create-session":
        if not args.path:
            raise ValueError("Path is required to find or create a session")
        session = find_or_create_session(args.path, args.url)
        print(json.dumps(session, ensure_ascii=False))

    elif args.cmd == "get-kernel":
        if not args.id:
            raise ValueError("Kernel ID is required for retrieving a kernel")
        kernel = get_kernel(args.url, args.id)
        print(json.dumps(kernel, ensure_ascii=False))

    elif args.cmd == "get-session":
        if not args.id:
            raise ValueError("Session ID is required for retrieving a session")
        session = get_session(args.url, args.id)
        print(json.dumps(session, ensure_ascii=False))

    elif args.cmd == "interrupt":
        if not args.path:
            raise ValueError("Path is required for interrupting a kernel")
        asyncio.run(interrupt_kernel(args.url, args.path))


if __name__ == "__main__":
    main()
