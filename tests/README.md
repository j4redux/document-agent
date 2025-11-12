# Document Agent Tests

This directory contains tests for the Document Agent.

## Test Structure

- `test_basic_tools.py` - Tests for individual tool functionality
- `test_agent_integration.py` - Tests for agent setup and integration
- `test_message_handling.py` - Tests for message history and edge cases
- `run_all_tests.py` - Test runner script

## Running Tests

### Run All Tests
```bash
uv run python run_all_tests.py
```

### Run Individual Tests
```bash
uv run python test_basic_tools.py
uv run python test_agent_integration.py
uv run python test_message_handling.py
```

## What's Tested

### Basic Tool Tests
- Calculator operations
- Text transformations
- File read/write operations
- File search functionality

### Agent Integration Tests
- Agent initialization
- Tool discovery and loading
- Message history management
- Slash command handling
- Tool integration without API calls

### Message Handling Tests
- Pydantic object handling
- Tool use/result message pairing
- Context window truncation
- Mixed content types

## Note on API Testing

These tests are designed to work without requiring an Anthropic API key. They test:
- Local tool functionality
- Agent setup and configuration
- Message handling logic
- Integration between components

For full end-to-end testing with API calls, you would need to:
1. Set up a valid API key
2. Create additional integration tests
3. Mock API responses for consistent testing