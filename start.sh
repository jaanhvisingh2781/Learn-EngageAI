#!/bin/bash

# start.sh - LearnEngage AI Application Startup Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed. Please install Python 3.7 or higher."
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info[0])')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info[1])')
    
    if [ $PYTHON_MAJOR -lt 3 ] || ([ $PYTHON_MAJOR -eq 3 ] && [ $PYTHON_MINOR -lt 7 ]); then
        print_error "Python 3.7 or higher is required. Current version: $PYTHON_VERSION"
        exit 1
    fi
    
    print_status "Using Python $PYTHON_VERSION"
}

# Check if virtual environment exists, create if not
setup_venv() {
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        $PYTHON_CMD -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check if we're in the virtual environment
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_error "Failed to activate virtual environment."
        exit 1
    fi
    
    print_success "Virtual environment activated"
}

# Install required packages
install_requirements() {
    print_status "Installing required packages..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        print_success "Packages installed successfully"
    else
        print_error "Failed to install packages"
        exit 1
    fi
}

# Initialize the database
init_database() {
    print_status "Initializing database..."
    $PYTHON_CMD db.py
    
    if [ $? -eq 0 ]; then
        print_success "Database initialized successfully"
    else
        print_error "Failed to initialize database"
        exit 1
    fi
}

# Check if requirements.txt exists, create if not
check_requirements() {
    if [ ! -f "requirements.txt" ]; then
        print_warning "requirements.txt not found, creating one..."
        cat > requirements.txt << EOL
Flask==2.3.3
pandas==2.0.3
scikit-learn==1.3.0
numpy==1.24.3
joblib==1.3.2
EOL
        print_success "requirements.txt created"
    fi
}

# Run the application
run_app() {
    print_status "Starting LearnEngage AI application..."
    print_warning "The application will be available at: http://localhost:5000"
    $PYTHON_CMD app.py
}

# Main execution
main() {
    print_status "Starting LearnEngage AI setup..."
    
    # Check Python
    check_python
    
    # Check requirements file
    check_requirements
    
    # Setup virtual environment
    setup_venv
    
    # Install requirements
    install_requirements
    
    # Initialize database
    init_database
    
    # Run the application
    run_app
}

# Run main function
main
