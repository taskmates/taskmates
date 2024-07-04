import asyncio

from taskmates.server.server import app


class ServerCommand:
    @staticmethod
    def add_arguments(parser):
        parser.add_argument('--host', default='localhost', help='Host to bind the server to')
        parser.add_argument('--port', type=int, default=5000, help='Port to bind the server to')

    @staticmethod
    async def execute(args):
        import hypercorn.asyncio

        config = hypercorn.Config()
        config.bind = f"{args.host}:{args.port}"
        config.use_reloader = True

        print(f"Starting Taskmates server on {args.host}:{args.port}")
        await hypercorn.asyncio.serve(app, config)


# Add test for ServerCommand
import pytest
from unittest.mock import patch, MagicMock


def test_server_command():
    command = ServerCommand()

    # Test add_arguments
    parser = MagicMock()
    command.add_arguments(parser)
    parser.add_argument.assert_any_call('--host', default='localhost', help='Host to bind the server to')
    parser.add_argument.assert_any_call('--port', type=int, default=5000, help='Port to bind the server to')

    # Test execute
    args = MagicMock(host='127.0.0.1', port=8000)
    with patch('hypercorn.asyncio.serve') as mock_serve, \
            patch('hypercorn.Config') as mock_config:
        asyncio.run(command.execute(args))
        mock_config.assert_called_once()
        mock_serve.assert_called_once()
        assert mock_config().bind == '127.0.0.1:8000'
        assert mock_config().use_reloader is True


if __name__ == "__main__":
    pytest.main([__file__])
