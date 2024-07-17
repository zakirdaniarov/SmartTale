# SmartTale
This platform is a comprehensive marketplace and management system tailored for sewing productions and orders, designed to streamline the entire process from start to finish. It features robust admin and user panels, allowing seamless oversight and interaction between production teams and clients. We have implemented integrated chat functionalities and real-time notifications to ensure smooth and efficient communication, keeping all parties updated on order statuses and production milestones. Whether you're managing large-scale productions or individual custom orders, our platform is designed to enhance efficiency and collaboration in the sewing industry.


### Technologies
---
- Python
- Django Rest Framework
- Swagger UI
- Nginx
- Docker
- PostgreSQL

### Install
---
#### Without docker
1. Clone repository to your local machine:
```
git clone ssh/https-key
```
2. Create virtual environment and activate virtual environment:
- On `Windows`:
```
python -m env venv
```
```
venv\Scripts\activate.bat
```
- On `Linux/MacOs`
```
python3 -m env venv
```
```
source venv/bin/activate
```
3. Add `.env` file to the root and fill with your data next variables:
```
DB_HOST=db
DB_USER=postgres
DB_PASSWORD=postgres_password
DB_NAME=postgres
DB_PORT=5432
POSTGRES_HOST_AUTH_METHOD=trust
DEBUG=True
EMAIL_HOST_USER = 
EMAIL_HOST_PASSWORD = 
```
4. Install all dependecies:
```
pip install -r requirements.txt
```
5. Run the project on your local host:
```
python/python3 manage.py runserver
```
### Authors
---
[Mamatair uulu Zakirbek, 2024](https://github.com/zakirdaniarov)
