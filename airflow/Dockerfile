# Utilisez l'image de base d'Airflow
FROM apache/airflow:2.9.2

# Copiez le fichier requirements.txt et installez les dépendances
COPY requirements.txt .
RUN pip install apache-airflow==${AIRFLOW_VERSION} -r requirements.txt
RUN pip install pymongo scipy imageio matplotlib tensorboard


CMD ["airflow", "webserver"]

