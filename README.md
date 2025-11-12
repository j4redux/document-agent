# Document Agent

A powerful AI-powered document agent built with Claude (Anthropic API) that provides intelligent document editing, web research, file management, and task automation capabilities. Designed for developers, researchers, and content creators who need an intelligent assistant for complex document workflows.

## 🎯 Overview

This project demonstrates advanced AI agent capabilities using Claude's latest models, featuring:
- **Agentic Tool Use**: Sophisticated multi-step reasoning with 20+ specialized tools
- **Research Capabilities**: Deep web research with source validation and synthesis
- **Document Intelligence**: Smart editing, file analysis, and content generation
- **Task Orchestration**: Automatic todo management for complex workflows
- **Extensible Architecture**: Easy to add custom tools and behaviors

## ✨ Key Features

### Core Capabilities
- **🔍 Web Research**: Powered by Anthropic's web search tool for current information
- **📝 Document Editing**: Create, edit, and refactor markdown/text files with precision
- **💻 Code Operations**: File search, grep, multi-file editing, git operations
- **🖼️ Image Analysis**: Screenshot capture and image understanding
- **📊 Data Processing**: Text transformation, calculations, JSON/CSV handling
- **✅ Task Management**: Automatic todo list generation and tracking

### Advanced Features
- **Multi-step Research**: Comprehensive research workflows with source tracking
- **Bash Command Execution**: Safe command execution with sandboxing
- **Git Integration**: Automated git operations and repository management
- **Jupyter Notebook Support**: Interactive Python execution
- **Context-Aware Editing**: Intelligent file modifications preserving structure

## Quick Start

### 1. Prerequisites

- Python 3.12 or higher
- Anthropic API key ([get one here](https://console.anthropic.com/))

### 2. Installation

#### Option A: Using uv directly (simplest)
```bash
# Clone or download this folder
cd document-agent

# Install dependencies with uv
uv sync

# That's it! No virtual environment needed
```

#### Option B: Using the setup script (traditional venv)
```bash
# Clone or download this folder
cd document-agent

# Run the setup script
./setup.sh
```

#### Option C: Manual installation
```bash
# Clone or download this folder
cd document-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Anthropic API key
# ANTHROPIC_API_KEY=your-actual-api-key
```

### 4. Run the Agent

```bash
uv run python document_agent.py
```

## Usage Examples

Once running, you can:

- `"Create a report on climate change"` - Researches and writes a comprehensive report
- `"Edit README.md to be more concise"` - Edits existing files
- `"Find all TODO comments in this project"` - Searches through files
- `"Take a screenshot and analyze it"` - Captures and analyzes images
- `"Research best practices for email marketing"` - Web research
- `"Help me write a professional email"` - Writing assistance

## 🏗️ Architecture

### Project Structure
```
document-agent/
├── agent.py              # Core agent implementation with tool orchestration
├── document_agent.py     # Main CLI entry point
├── tools/                # Tool implementations
│   ├── file_tools.py     # File read/write/search operations
│   ├── system_tools.py   # Grep, ls, find, todo management
│   ├── anthropic_web_tool.py  # Web search integration
│   ├── research_tools.py # Advanced research capabilities
│   ├── bash_enhanced.py  # Safe bash execution
│   ├── git_tool.py       # Git operations
│   ├── multi_edit.py     # Batch file editing
│   ├── image_tool.py     # Image capture and analysis
│   ├── notebook_tool.py  # Jupyter notebook support
│   └── ...               # Additional specialized tools
├── utils/                # Utility functions
│   ├── history_util.py   # Conversation history management
│   └── tool_util.py      # Tool helper functions
├── tests/                # Integration tests
├── examples/             # Example scripts and evaluations
└── evals/                # Evaluation results
```

### Tool Categories

**Document & File Operations**
- `FileReadTool`, `FileWriteTool`, `MultiEditTool`: Advanced file manipulation
- `FileSearchTool`: Content-based file discovery
- `CatTool`, `GrepTool`, `FindTool`, `LsTool`: Unix-style file operations

**Research & Web**
- `AnthropicWebSearchTool`: Powered search with source tracking
- `ResearchLeadTool`: Multi-step research orchestration
- `QuickResearchTool`: Fast targeted research
- `WebTool`: General web fetching

**Development Tools**
- `BashEnhancedTool`: Safe command execution
- `GitTool`: Repository operations
- `NotebookTool`: Jupyter integration
- `ImageTool`: Screenshot and image analysis

**Intelligence & Planning**
- `TodoReadTool`, `TodoWriteTool`: Task management
- `ThinkTool`: Extended reasoning
- `AgentTool`: Sub-agent delegation
- `ContextPrimeTool`: Context optimization

**Utilities**
- `CalculatorTool`, `RandomNumberTool`: Math operations
- `TextTransformTool`, `Base64Tool`: Data transformation
- `WeatherTool`: External API integration example

## Key Behaviors

- **Ultra-concise**: Maximum 4 lines per response (unless you request details)
- **Direct answers**: No unnecessary preamble or explanations
- **Task tracking**: Automatically organizes complex work
- **Proactive**: Completes tasks thoroughly without prompting

## Commands

Special commands available during interaction:

- `/help` - Show available commands
- `/save <filename>` - Save conversation history
- `/load <filename>` - Load previous conversation
- `/export` - Export conversation as markdown
- `/config` - Show current configuration
- `/exit` or `/quit` - Exit the assistant

## Advanced Configuration

### Using a Different Model

Set the `ANTHROPIC_MODEL` environment variable:
```bash
export ANTHROPIC_MODEL=claude-3-5-haiku-20241022
```


### Enable Observability (Optional)

For detailed tracing with Logfire:
1. Sign up at https://logfire.pydantic.dev/
2. Get your token
3. Set `LOGFIRE_TOKEN` in your .env file

## 🚀 Use Cases

### For Developers
- **Code Documentation**: Generate and maintain technical documentation
- **Repository Analysis**: Analyze codebases, find patterns, refactor code
- **Git Workflow Automation**: Automated commits, branch management, PR descriptions
- **Testing & QA**: Generate test cases, analyze test results

### For Researchers
- **Literature Review**: Comprehensive web research with source tracking
- **Data Analysis**: Process and analyze datasets, generate insights
- **Report Generation**: Create structured reports from research findings
- **Citation Management**: Track and format research sources

### For Content Creators
- **Blog Writing**: Research, outline, and draft blog posts
- **Documentation**: Technical writing with accuracy verification
- **Email Drafting**: Professional email composition with context
- **Content Editing**: Grammar, style, and structure improvements

## 📊 Examples

See the `examples/` directory for:
- `example_research_agent.py`: Demonstration of research capabilities
- `eval_*.py`: Evaluation scripts for testing agent performance
- `test_*.py`: Various test scenarios and use cases

## 🧪 Testing

Run the test suite:
```bash
cd tests
python run_all_tests.py
```

Individual test categories:
```bash
pytest tests/test_basic_tools.py
pytest tests/test_agent_integration.py
pytest tests/test_message_handling.py
```

## 🔧 Troubleshooting

### "API key not found" error
- Ensure your `.env` file exists in the project root
- Verify it contains `ANTHROPIC_API_KEY=your-actual-key`
- Check you're running the command from the project directory

### Import errors
- Verify Python 3.12+ is installed: `python --version`
- Ensure all dependencies are installed: `uv sync` or `pip install -r requirements.txt`
- If using venv, ensure it's activated: `source venv/bin/activate`

### Tool errors
- Some tools (screenshots, git) are platform or context-specific
- Web search requires internet connection
- Bash commands are sandboxed for safety
- Check tool-specific error messages for details

### Performance issues
- Consider using Claude 3.5 Haiku for faster responses
- Limit conversation history for long sessions
- Use specific tools directly rather than general queries

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional tool implementations
- Enhanced error handling
- Performance optimizations
- Documentation improvements
- Test coverage expansion

## 📝 License

MIT License - see LICENSE file for details.

Built on the Anthropic API and inspired by Claude Code best practices.

## 🙏 Acknowledgments

- Anthropic for the Claude API and tool use capabilities
- Anthropic Quickstarts for the foundation framework
- The open-source community for inspiration and tools

## 📧 Contact

For questions, issues, or suggestions, please open an issue on GitHub.
