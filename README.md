# Personal Finance Tracker

A modern web application for tracking personal finances, built with Flask and Tailwind CSS.

## Project Structure

```
personal-finance-tracker/
├── app.py                 # Main application file with all routes and models
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── package.json          # Node.js dependencies
├── tailwind.config.js    # Tailwind CSS configuration
├── .gitignore           # Git ignore rules
│
├── instance/            # Instance-specific files
│   └── database/        # SQLite database files
│
├── static/              # Static assets
│   ├── css/            # Compiled CSS files
│   ├── js/             # JavaScript files
│   ├── images/         # Image assets
│   ├── uploads/        # User uploads
│   └── vendor/         # Third-party libraries
│
├── templates/           # Jinja2 templates
│   ├── auth/           # Authentication templates
│   ├── dashboard/      # Dashboard templates
│   ├── transactions/   # Transaction templates
│   ├── budgets/        # Budget templates
│   ├── reports/        # Reports templates
│   └── settings/       # Settings templates
│
└── Docs/               # Project documentation
```

## Setup Instructions

1. Clone the repository:
```bash
git clone [repository-url]
cd personal-finance-tracker
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Install Node.js dependencies:
```bash
npm install
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the development server:
```bash
flask run
```

## Development

- All Python code is centralized in `app.py`
- Templates are organized by feature in the `templates/` directory
- Static files are organized by type in the `static/` directory
- Configuration is handled through `config.py` and environment variables

## Environment Variables

Create a `.env` file in the root directory with these variables:
```
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///instance/database/finance.db
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. 