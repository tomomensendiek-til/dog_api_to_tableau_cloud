import os
import requests
from datetime import datetime

from tableauhyperapi import (
    HyperProcess,
    Telemetry,
    Connection,
    CreateMode,
    TableDefinition,
    SqlType,
    Inserter
)

from tableauserverclient import (
    PersonalAccessTokenAuth,
    Server,
    DatasourceItem
)


DOG_API_URL = "https://dog.ceo/api/breeds/image/random"
HYPER_FILE = "dog_image.hyper"
TABLE_NAME = "Extract"

# Tableau Cloud credentials from GitHub Secrets
TABLEAU_SERVER_URL = os.environ["TABLEAU_SERVER_URL"]
TABLEAU_SITE_ID = os.environ["TABLEAU_SITE_ID"]
TABLEAU_PAT_NAME = os.environ["TABLEAU_PAT_NAME"]
TABLEAU_PAT_SECRET = os.environ["TABLEAU_PAT_SECRET"]
TABLEAU_PROJECT_ID = os.environ["TABLEAU_PROJECT_ID"]

DATASOURCE_NAME = "dog_api_output"

def fetch_dog_data():
    print("Fetching dog image...")
    response = requests.get(DOG_API_URL)
    response.raise_for_status()
    data = response.json()
    image_url = data["message"]
    breed = image_url.split("/")[-2]
    created_at = datetime.utcnow().isoformat()
    return {
        "breed": breed,
        "image_url": image_url,
        "created_at": created_at
    }

def create_hyper_file(dog_data):
    print("Creating Hyper file...")
    if os.path.exists(HYPER_FILE):
        os.remove(HYPER_FILE)
    table_definition = TableDefinition(
        table_name=TABLE_NAME,
        columns=[
            TableDefinition.Column("breed", SqlType.text()),
            TableDefinition.Column("image_url", SqlType.text()),
            TableDefinition.Column("created_at", SqlType.text())
        ]
    )

    with HyperProcess(
        telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU
    ) as hyper:
        with Connection(
            endpoint=hyper.endpoint,
            database=HYPER_FILE,
            create_mode=CreateMode.CREATE_AND_REPLACE
        ) as connection:
            connection.catalog.create_table(table_definition)

            with Inserter(connection, table_definition) as inserter:

                inserter.add_row([
                    dog_data["breed"],
                    dog_data["image_url"],
                    dog_data["created_at"]
                ])

                inserter.execute()
    print(f"Created Hyper file: {HYPER_FILE}")

def publish_to_tableau():
    tableau_auth = PersonalAccessTokenAuth(
        token_name=TABLEAU_PAT_NAME,
        personal_access_token=TABLEAU_PAT_SECRET,
        site_id=TABLEAU_SITE_ID
    )
    server = Server(
        TABLEAU_SERVER_URL,
        use_server_version=True
    )
    with server.auth.sign_in(tableau_auth):
        datasource = DatasourceItem(
            project_id=TABLEAU_PROJECT_ID,
            name=DATASOURCE_NAME
        )
        print("Publishing datasource to Tableau Cloud...")
        published_datasource = server.datasources.publish(
            datasource,
            HYPER_FILE,
            mode="Overwrite"
        )
        print("Publish complete!")

def main():
    dog_data = fetch_dog_data()
    create_hyper_file(dog_data)
    publish_to_tableau()

if __name__ == "__main__":
    main()
