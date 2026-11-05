class ServiceError(Exception):
    """An expected, user-facing error (bad id, wrong course, already answered…).

    The MCP layer turns it into a tool error the model can read and recover from.
    """
