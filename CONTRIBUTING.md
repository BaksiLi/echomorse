# Contributing to Echo-Morse

Thank you for considering contributing to Echo-Morse! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

1. **Fork the repository**
2. **Clone your fork locally**
   ```bash
   git clone https://github.com/yourusername/echo-morse.git
   cd echo-morse
   ```
3. **Set up the development environment**
   ```bash
   pdm install -d
   ```
4. **Create a branch for your changes**
   ```bash
   git checkout -b feature-or-fix-name
   ```
5. **Make your changes**
   - Write code that follows the project's style guide
   - Add or update tests as necessary
   - Update documentation as needed
   - Keep your changes focused on a single issue/feature

6. **Run tests and linting**
   ```bash
   pdm run test
   pdm run lint
   pdm run typecheck
   ```

7. **Commit your changes**
   - Use clear, descriptive commit messages
   - Reference issue numbers in commit messages where appropriate

8. **Push to your fork**
   ```bash
   git push origin feature-or-fix-name
   ```

9. **Submit a pull request**
   - Provide a clear description of your changes
   - Reference any related issues

## Development Guidelines

### Code Style

This project uses:
- `black` for code formatting
- `ruff` for linting
- `mypy` for type checking

### Testing

- Write tests for all new features and bug fixes
- Tests are written using `pytest`
- Ensure all tests pass before submitting a pull request

### Documentation

- Update documentation for any changed functionality
- Document new features with examples
- Keep code comments clear and concise

## Adding Voice Packs

See the README.md for information on the voice system. When contributing new voice packs:

1. Ensure all audio files are properly licensed for distribution
2. Include proper attribution in voice_config.json
3. Keep file sizes reasonable (optimize audio files)
4. Test your voice pack with various inputs

## Reporting Bugs

Please use GitHub Issues to report bugs. Include:
- A clear description of the bug
- Steps to reproduce
- Expected vs. actual behavior
- Screenshots if applicable
- System information (OS, Python version, etc.)

## Feature Requests

Feature requests are welcome. Please use GitHub Issues and provide:
- A clear description of the feature
- The problem it would solve
- Any ideas for implementation

## Publishing to PyPI

When a new release is ready, follow these steps to publish Echo-Morse to PyPI:

1. **Update Version**: Increment the version number in `pyproject.toml`

2. **Update Changelog**: Add a new entry to the `CHANGELOG.md` file with the new version number and release details

3. **Build the Package**:
   ```bash
   # Remove previous builds
   rm -rf dist/
   
   # Build the package
   pdm build
   ```

4. **Test the Package** (optional but recommended):
   ```bash
   # Install the package locally 
   pip install dist/*.whl --force-reinstall
   
   # Verify the installation works
   echomorse --version
   ```

5. **Upload to TestPyPI** (optional):
   ```bash
   # First, ensure you have twine installed
   pip install twine
   
   # Upload to TestPyPI
   twine upload --repository-url https://test.pypi.org/legacy/ dist/*
   ```

6. **Upload to PyPI**:
   ```bash
   # Upload to the real PyPI
   twine upload dist/*
   ```

   You'll need to have a PyPI account and be listed as a maintainer of the package.

7. **Create a GitHub Release**: Create a new release on GitHub with the same version number and release notes.

## License

By contributing to Echo-Morse, you agree that your contributions will be licensed under the project's MIT License. 