# Contributing to Reductor

First off, thank you for considering contributing to Reductor\! It's people like you that make Reductor such a great tool for the Laravel community.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead and why**
- **Include details about your configuration and environment**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the steps**
- **Describe the current behavior and explain which behavior you expected**
- **Explain why this enhancement would be useful**

### Pull Requests

- Fill in the required template
- Do not include issue numbers in the PR title
- Follow the PHP and Python style guides
- Include thoughtfully-worded, well-structured tests
- Document new code
- End all files with a newline

## Development Setup

1. Fork the repo and create your branch from `main`
2. Install dependencies:
   ```bash
   composer install
   pip3 install -r requirements.txt
   pip3 install -r requirements-dev.txt
   ```
3. Make your changes
4. Run the test suite:
   ```bash
   composer test
   python3 -m pytest tests/
   ```
5. Run static analysis:
   ```bash
   composer analyse
   composer format
   ```

## Style Guides

### PHP Style Guide

We follow PSR-12 coding standards. Run `composer format` to automatically fix style issues.

### Python Style Guide

We follow PEP 8. Run `black .` to automatically format Python code.

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## Testing

- Write tests for new features
- Update tests when changing functionality
- Ensure all tests pass before submitting PR
- Aim for high code coverage

## Documentation

- Update the README.md with details of changes to the interface
- Update the Laravel guide for Laravel-specific changes
- Add docblocks to all public methods
- Keep the CHANGELOG.md updated

## Questions?

Feel free to open an issue with your question or reach out on our Discord channel.

Thank you for contributing!