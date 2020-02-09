#!/bin/bash
# To create a reverse tunnel to a remote server.

SERVER_COMMAND="$1"
SERVER_ACCOUNT="$2"
SERVER_IP="$3"
SERVER_PORT="$4"
SSH_KEY="$5"

usage() {
    echo "Usage:"
    echo ""
    echo "    Create reverse tunnel"
    echo "    $ ./escape-capsule.sh connect SERVER_ACCOUNT SERVER_IP SERVER_PORT [SSH_KEY]"
    echo ""
    echo "    Terminate reverse tunnel"
    echo "    $ ./escape-capsule.sh disconnect SERVER_ACCOUNT SERVER_IP"
    exit 1
}

create_reverse_tunnel() {
    echo "Create reverse tunnel"
    echo "ssh -i $SSH_KEY -M -S /tmp/sock -NfR $SERVER_PORT:localhost:22 $SERVER_ACCOUNT@$SERVER_IP"
    echo ""
    echo "Login device from server"
    echo "    server $ ssh -p $SERVER_PORT DEVICE_ACCOUNT@localhost"
    echo ""
    ssh -i $SSH_KEY -M -S /tmp/sock -NfR $SERVER_PORT:localhost:22 $SERVER_ACCOUNT@$SERVER_IP
}

terminate_reverse_tunnel() {
    echo "Terminate reverse tunnel"
    echo "ssh -S /tmp/sock -O exit $SERVER_ACCOUNT@$SERVER_IP"
    echo ""
    ssh -S /tmp/sock -O exit $SERVER_ACCOUNT@$SERVER_IP
}

# Check necessary parameters
if [ "$SERVER_COMMAND" = "" ]; then
    usage
elif [ "$SERVER_COMMAND" = "connect" ]; then
    if [ "$SERVER_ACCOUNT" = "" ] || [ "$SERVER_IP" = "" ] || [ "$SERVER_PORT" = "" ]; then
        usage
    fi
elif [ "$SERVER_COMMAND" = "disconnect" ]; then
    if [ "$SERVER_ACCOUNT" = "" ] || [ "$SERVER_IP" = "" ]; then
        usage
    fi
fi

if [ "$SSH_KEY" = "" ]; then
    SSH_KEY="$HOME/.ssh/remote-debugging.pem"
fi

# Show parameter summary
echo "Server account: $SERVER_ACCOUNT, Server IP: $SERVER_IP, port: $SERVER_PORT, ssh_key: $SSH_KEY"
echo ""

# Main
if [ "$SERVER_COMMAND" = "connect" ]; then
    if [ -e /tmp/sock ]; then
        terminate_reverse_tunnel
    fi
    create_reverse_tunnel
elif [ "$SERVER_COMMAND" = "disconnect" ]; then
    terminate_reverse_tunnel
else
    echo "ERROR: Unknown command: $SERVER_COMMAND"
    exit 1
fi
