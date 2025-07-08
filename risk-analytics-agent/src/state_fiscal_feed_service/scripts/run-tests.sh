#!/bin/bash

# Test runner script for State Fiscal Feed system

set -e

echo "🧪 Running State Fiscal Feed Test Suite"
echo "======================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    print_status "Activated virtual environment"
else
    print_error "Cannot find virtual environment activation script"
    exit 1
fi

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt
pip install -e ".[dev,test]"

# Check code formatting
print_status "Checking code formatting with Black..."
if black --check src tests; then
    print_status "✅ Code formatting is correct"
else
    print_error "❌ Code formatting issues found. Run 'black src tests' to fix."
    exit 1
fi

# Run linting
print_status "Running linting with Flake8..."
if flake8 src tests; then
    print_status "✅ Linting passed"
else
    print_error "❌ Linting issues found"
    exit 1
fi

# Run type checking
print_status "Running type checking with MyPy..."
if mypy src; then
    print_status "✅ Type checking passed"
else
    print_error "❌ Type checking issues found"
    exit 1
fi

# Run tests
print_status "Running test suite..."

# Unit tests
print_status "Running unit tests..."
pytest tests/unit -v --cov=src --cov-report=term-missing --cov-report=html

if [ $? -eq 0 ]; then
    print_status "✅ Unit tests passed"
else
    print_error "❌ Unit tests failed"
    exit 1
fi

# Integration tests
print_status "Running integration tests..."
pytest tests/integration -v

if [ $? -eq 0 ]; then
    print_status "✅ Integration tests passed"
else
    print_error "❌ Integration tests failed"
    exit 1
fi

# End-to-end tests
print_status "Running end-to-end tests..."
pytest tests/e2e -v -m "not slow"

if [ $? -eq 0 ]; then
    print_status "✅ End-to-end tests passed"
else
    print_error "❌ End-to-end tests failed"
    exit 1
fi

# Generate coverage report
print_status "Generating coverage report..."
coverage report --skip-covered
coverage html

print_status "📊 Coverage report generated in htmlcov/index.html"

# Run slow tests if requested
if [ "$1" = "--slow" ]; then
    print_status "Running slow tests..."
    pytest tests/e2e -v -m "slow"
    
    if [ $? -eq 0 ]; then
        print_status "✅ Slow tests passed"
    else
        print_error "❌ Slow tests failed"
        exit 1
    fi
fi

echo ""
print_status "🎉 All tests passed successfully!"
echo ""
print_status "Test Summary:"
echo "  ✅ Code formatting (Black)"
echo "  ✅ Linting (Flake8)"
echo "  ✅ Type checking (MyPy)"
echo "  ✅ Unit tests"
echo "  ✅ Integration tests"
echo "  ✅ End-to-end tests"

if [ "$1" = "--slow" ]; then
    echo "  ✅ Performance tests"
fi

echo ""
print_status "Coverage report: htmlcov/index.html"
print_status "Ready for deployment! 🚀"