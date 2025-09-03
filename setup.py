# setup.py - Python 프로젝트 식별용
from setuptools import setup, find_packages

setup(
    name="labor-app",
    version="1.0.0",
    description="노무비 관리 시스템",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "Flask>=3.0.2",
        "gunicorn>=21.2.0",
        "Werkzeug>=3.0.2",
        "python-dotenv>=1.0.0",
        "psycopg2-binary>=2.9.7",
        "flask-cors>=6.0.1",
        "flask-jwt-extended>=4.7.1",
        "PyJWT>=2.10.1",
    ],
)